import html
import os
import secrets
import smtplib
from datetime import date, datetime, time
from email.mime.text import MIMEText
from email.utils import formataddr

import psycopg2
from flask import Flask, jsonify, request
from psycopg2.extras import Json, RealDictCursor

app = Flask(__name__)
DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
if len(INTERNAL_API_KEY) < 32:
    raise RuntimeError("INTERNAL_API_KEY debe tener al menos 32 caracteres")
SMTP_SERVER = os.getenv("SMTP_SERVER", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() in {"1", "true", "yes", "on"}
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
EMAIL_NOTIFICATIONS_ENABLED = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SYSTEM_NAME = os.getenv("SYSTEM_NAME", "ARCONEL - Control de Documentos")


def conn():
    return psycopg2.connect(DATABASE_URL)


def require_internal(admin=False):
    if not secrets.compare_digest(request.headers.get("X-Internal-Key", ""), INTERNAL_API_KEY):
        return jsonify(error="Acceso interno no autorizado"), 401
    if admin and request.headers.get("X-User-Role") != "admin":
        return jsonify(error="Se requiere rol administrador"), 403
    return None


def json_ready(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS notification_log (
      id BIGSERIAL PRIMARY KEY,
      event_type VARCHAR(80) NOT NULL,
      recipient VARCHAR(320) NOT NULL,
      subject VARCHAR(250) NOT NULL,
      status VARCHAR(20) NOT NULL CHECK(status IN ('pending','sent','failed','skipped')),
      attempts INTEGER NOT NULL DEFAULT 0,
      context JSONB NOT NULL DEFAULT '{}'::jsonb,
      error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      sent_at TIMESTAMPTZ
    );
    CREATE INDEX IF NOT EXISTS idx_notification_log_created ON notification_log(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log(status,created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_notification_log_recipient ON notification_log(LOWER(recipient),created_at DESC);

    CREATE TABLE IF NOT EXISTS system_log (
      id BIGSERIAL PRIMARY KEY,
      event_type VARCHAR(100) NOT NULL,
      level VARCHAR(20) NOT NULL DEFAULT 'info' CHECK(level IN ('info','warning','error')),
      module VARCHAR(80) NOT NULL,
      actor_user_id INTEGER,
      actor_name VARCHAR(200),
      actor_role VARCHAR(50),
      ip_address VARCHAR(100),
      detail JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_system_log_created ON system_log(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_system_log_level ON system_log(level,created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_system_log_module ON system_log(module,created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_system_log_actor ON system_log(actor_user_id,created_at DESC);
    """
    with conn() as db, db.cursor() as cur:
        cur.execute(schema)
        db.commit()


def text(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) or "—"
    return str(value) or "—"


def table_rows(rows):
    return "".join(
        f"<tr><td style='padding:9px 12px;border-bottom:1px solid #e8edf3;color:#52606d;width:34%;font-weight:600'>{html.escape(str(label))}</td>"
        f"<td style='padding:9px 12px;border-bottom:1px solid #e8edf3;color:#172b4d'>{html.escape(text(value))}</td></tr>"
        for label, value in rows
        if value not in (None, "", [], {})
    )


def document_rows(context):
    labels = [
        ("Código", context.get("code")),
        ("Tipo de documento", context.get("document_label") or context.get("document_type")),
        ("Empresa", context.get("company")),
        ("Gestión", context.get("management")),
        ("Productos asociados", context.get("associated_products")),
        ("Tipo", context.get("subtype")),
        ("Asunto", context.get("subject")),
        ("Observaciones", context.get("observations")),
        ("Elemento afectado", context.get("case_type")),
        ("Alimentador", context.get("feeder_name")),
        ("Subestación", context.get("substation")),
        ("Línea de subtransmisión", context.get("subtransmission_line")),
        ("Fecha de interrupción", context.get("interruption_date")),
        ("Fecha del documento", context.get("document_date")),
        ("Hora", context.get("document_time")),
        ("Funcionario", context.get("owner_name")),
    ]
    custom_labels = context.get("custom_labels") or {}
    for key, value in (context.get("extra_data") or {}).items():
        if key.endswith("__other"):
            continue
        label = custom_labels.get(key) or key.replace("_", " ").title()
        other = (context.get("extra_data") or {}).get(f"{key}__other")
        display = f"{text(value)}: {other}" if other else value
        labels.append((label, display))
    return labels


def template_for(event_type, context):
    event_titles = {
        "password_reset": "Recuperación de contraseña",
        "password_changed": "Contraseña actualizada",
        "user_created": "Cuenta creada en el sistema",
        "user_updated": "Cuenta actualizada",
        "document_created": "Documento registrado",
        "document_updated": "Documento actualizado",
        "document_deleted": "Documento eliminado",
        "backup_exported": "Copia de seguridad generada",
        "backup_restored": "Copia de seguridad restaurada",
    }
    subject = event_titles.get(event_type, "Notificación del sistema")
    if event_type.startswith("document_") and context.get("code"):
        subject = f"{subject}: {context['code']}"
    intro = "Se registró una actividad en el sistema."
    rows = []
    action_html = ""

    if event_type == "password_reset":
        intro = "Se recibió una solicitud para restablecer su contraseña."
        link = str(context.get("reset_link", ""))
        action_html = (
            f"<p style='text-align:center;margin:26px 0'><a href='{html.escape(link, quote=True)}' "
            "style='background:#0d6efd;color:#fff;text-decoration:none;padding:12px 22px;border-radius:7px;font-weight:700'>"
            "Restablecer contraseña</a></p>"
            "<p style='font-size:13px;color:#6b778c'>El enlace vence en 30 minutos. Si no solicitó este cambio, ignore el mensaje.</p>"
        )
    elif event_type == "password_changed":
        intro = "La contraseña de su cuenta fue modificada correctamente."
        rows = [("Usuario", context.get("name")), ("Correo", context.get("email"))]
    elif event_type == "user_created":
        intro = "Se creó una cuenta para usted en el sistema de control documental. Use la contraseña proporcionada por el administrador."
        rows = [("Nombre", context.get("name")), ("Correo", context.get("email")), ("Rol", context.get("role"))]
        if context.get("login_url"):
            action_html = f"<p style='text-align:center;margin:26px 0'><a href='{html.escape(str(context.get('login_url')), quote=True)}' style='background:#0d6efd;color:#fff;text-decoration:none;padding:12px 22px;border-radius:7px;font-weight:700'>Ingresar al sistema</a></p>"
    elif event_type == "user_updated":
        intro = "Los datos o permisos de su cuenta fueron actualizados por un administrador."
        rows = [("Nombre", context.get("name")), ("Correo", context.get("email")), ("Rol", context.get("role")), ("Estado activo", context.get("active")), ("Contraseña modificada", context.get("password_changed"))]
    elif event_type.startswith("document_"):
        verbs = {"document_created": "registrado", "document_updated": "actualizado", "document_deleted": "eliminado"}
        intro = f"El siguiente documento fue {verbs.get(event_type, 'procesado')} en el sistema."
        rows = document_rows(context)
    elif event_type == "backup_exported":
        intro = "Se generó una copia de seguridad completa desde el panel de administración."
        rows = [("Administrador", context.get("actor_name")), ("Fecha", context.get("created_at")), ("Bases incluidas", context.get("databases"))]
    elif event_type == "backup_restored":
        intro = "Se restauró una copia de seguridad completa. Las sesiones activas fueron invalidadas."
        rows = [("Administrador", context.get("actor_name")), ("Fecha", context.get("created_at")), ("Archivo", context.get("filename"))]

    body = f"""
    <!doctype html><html><body style="margin:0;background:#f4f7fb;font-family:Arial,sans-serif;color:#172b4d">
      <div style="max-width:700px;margin:28px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 18px rgba(23,43,77,.10)">
        <div style="background:#123b63;color:#fff;padding:22px 28px">
          <div style="font-size:20px;font-weight:700">{html.escape(SYSTEM_NAME)}</div>
          <div style="font-size:13px;opacity:.8;margin-top:4px">Notificación automática</div>
        </div>
        <div style="padding:28px">
          <h1 style="font-size:22px;margin:0 0 12px">{html.escape(subject)}</h1>
          <p style="line-height:1.6;color:#52606d">{html.escape(intro)}</p>
          {"<table style='width:100%;border-collapse:collapse;margin-top:18px'>" + table_rows(rows) + "</table>" if rows else ""}
          {action_html}
        </div>
        <div style="padding:16px 28px;background:#f7f9fc;color:#7a869a;font-size:12px">Este correo fue generado automáticamente. No responda a este mensaje.</div>
      </div>
    </body></html>
    """
    return subject, body


def send_email(recipient, subject, body):
    if not EMAIL_NOTIFICATIONS_ENABLED or not SMTP_SERVER:
        return "skipped", "SMTP no configurado o notificaciones deshabilitadas"
    msg = MIMEText(body, "html", "utf-8")
    sender = SMTP_FROM or SMTP_USER or "no-reply@example.com"
    msg["From"] = sender if "<" in sender else formataddr((SYSTEM_NAME, sender))
    msg["To"] = recipient
    msg["Subject"] = subject
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    return "sent", None


def process_notification(log_id, body_override=None):
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM notification_log WHERE id=%s FOR UPDATE", (log_id,))
        row = cur.fetchone()
        if not row:
            return None
        if row["event_type"] == "password_reset" and body_override is None:
            raise ValueError("Solicite un nuevo enlace de recuperación; los enlaces no se almacenan para reintento")
        _, generated_body = template_for(row["event_type"], row["context"] or {})
        body = body_override or generated_body
        try:
            status, error = send_email(row["recipient"], row["subject"], body)
        except Exception as exc:
            app.logger.exception("No se pudo enviar la notificación %s", log_id)
            status, error = "failed", str(exc)[:2000]
        cur.execute(
            "UPDATE notification_log SET status=%s,attempts=attempts+1,error_message=%s,sent_at=CASE WHEN %s='sent' THEN NOW() ELSE sent_at END WHERE id=%s RETURNING *",
            (status, error, status, log_id),
        )
        updated = cur.fetchone()
        db.commit()
        return updated



@app.get("/health")
def health():
    try:
        with conn() as db, db.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return jsonify(status="ok", smtp_configured=bool(SMTP_SERVER), enabled=EMAIL_NOTIFICATIONS_ENABLED)
    except Exception as exc:
        return jsonify(status="error", detail=str(exc)), 503


@app.post("/api/notifications")
def create_notification():
    denied = require_internal()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    recipient = str(data.get("recipient", "")).strip()
    event_type = str(data.get("event_type", "generic")).strip()[:80]
    context = data.get("context") or {}
    if "@" not in recipient or len(recipient) > 320:
        return jsonify(error="Destinatario inválido"), 400
    if not isinstance(context, dict):
        return jsonify(error="El contexto debe ser un objeto"), 400
    subject, body = template_for(event_type, context)
    stored_context = dict(context)
    stored_context.pop("reset_link", None)
    stored_context.pop("temporary_password", None)
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO notification_log(event_type,recipient,subject,status,context) VALUES(%s,%s,%s,'pending',%s) RETURNING id",
            (event_type, recipient, subject, Json(stored_context)),
        )
        log_id = cur.fetchone()["id"]
        db.commit()
    item = process_notification(log_id, body_override=body)
    return jsonify(json_ready(item)), 201


@app.get("/api/notifications")
def list_notifications():
    denied = require_internal(admin=True)
    if denied:
        return denied
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    status = request.args.get("status", "").strip()
    recipient = request.args.get("recipient", "").strip()
    clauses = ["1=1"]
    params = []
    if status:
        if status not in {"pending", "sent", "failed", "skipped"}:
            return jsonify(error="Estado inválido"), 400
        clauses.append("status=%s")
        params.append(status)
    if recipient:
        clauses.append("recipient ILIKE %s")
        params.append(f"%{recipient}%")
    where = " AND ".join(clauses)
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM notification_log WHERE {where}", params)
        total = cur.fetchone()["total"]
        cur.execute(
            f"SELECT id,event_type,recipient,subject,status,attempts,error_message,created_at,sent_at FROM notification_log WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        items = cur.fetchall()
    return jsonify(items=json_ready(items), total=total, page=page, per_page=per_page)


@app.post("/api/system-logs")
def create_system_log():
    denied = require_internal()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    event_type = str(data.get("event_type") or "SYSTEM_EVENT").strip()[:100]
    level = str(data.get("level") or "info").strip().lower()
    module = str(data.get("module") or "system").strip()[:80]
    actor_name = str(data.get("actor_name") or "").strip()[:200] or None
    actor_role = str(data.get("actor_role") or "").strip()[:50] or None
    ip_address = str(data.get("ip_address") or request.headers.get("X-Client-IP") or "").strip()[:100] or None
    detail = data.get("detail") or {}
    try:
        actor_user_id = int(data["actor_user_id"]) if data.get("actor_user_id") not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify(error="actor_user_id inválido"), 400
    if level not in {"info", "warning", "error"}:
        return jsonify(error="Nivel de log inválido"), 400
    if not module:
        return jsonify(error="Módulo requerido"), 400
    if not isinstance(detail, dict):
        return jsonify(error="El detalle debe ser un objeto"), 400
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO system_log(event_type,level,module,actor_user_id,actor_name,actor_role,ip_address,detail)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
            """,
            (event_type, level, module, actor_user_id, actor_name, actor_role, ip_address, Json(detail)),
        )
        item = cur.fetchone()
        db.commit()
    return jsonify(json_ready(item)), 201


@app.get("/api/system-logs")
def list_system_logs():
    denied = require_internal(admin=True)
    if denied:
        return denied
    page = max(request.args.get("page", 1, type=int), 1)
    per_raw = str(request.args.get("per_page", "25")).strip().lower()
    per_page = 1000 if per_raw == "all" else min(max(int(per_raw or 25), 1), 1000)
    level = request.args.get("level", "").strip().lower()
    module = request.args.get("module", "").strip()
    query = request.args.get("q", "").strip()
    clauses = ["1=1"]
    params = []
    if level:
        if level not in {"info", "warning", "error"}:
            return jsonify(error="Nivel inválido"), 400
        clauses.append("level=%s")
        params.append(level)
    if module:
        clauses.append("module=%s")
        params.append(module)
    if query:
        clauses.append("(event_type ILIKE %s OR COALESCE(actor_name,'') ILIKE %s OR detail::text ILIKE %s)")
        like = f"%{query}%"
        params.extend([like, like, like])
    where = " AND ".join(clauses)
    offset = (page - 1) * per_page
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM system_log WHERE {where}", params)
        total = cur.fetchone()["total"]
        cur.execute(
            f"""
            SELECT id,event_type,level,module,actor_user_id,actor_name,actor_role,ip_address,detail,created_at
            FROM system_log WHERE {where}
            ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s
            """,
            params + [per_page, offset],
        )
        items = cur.fetchall()
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE level='warning') AS warnings,
                   COUNT(*) FILTER (WHERE level='error') AS errors,
                   COUNT(*) FILTER (WHERE module='backup') AS backups,
                   COUNT(*) FILTER (WHERE event_type='LOGIN_SUCCESS') AS logins
            FROM system_log
            """
        )
        summary = cur.fetchone()
        cur.execute("SELECT DISTINCT module FROM system_log ORDER BY module")
        modules = [row["module"] for row in cur.fetchall()]
    return jsonify(items=json_ready(items), total=total, page=page, per_page=per_page, summary=json_ready(summary), modules=modules)


@app.post("/api/notifications/<int:log_id>/retry")
def retry_notification(log_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        item = process_notification(log_id)
    except ValueError as exc:
        return jsonify(error=str(exc)), 409
    if not item:
        return jsonify(error="Notificación no encontrada"), 404
    return jsonify(json_ready(item))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
