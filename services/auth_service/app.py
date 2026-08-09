import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
import psycopg2
import requests
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
if len(INTERNAL_API_KEY) < 32:
    raise RuntimeError("INTERNAL_API_KEY debe tener al menos 32 caracteres")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "6"))
if MIN_PASSWORD_LENGTH < 6:
    raise RuntimeError("MIN_PASSWORD_LENGTH no puede ser menor que 6")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")


def conn():
    return psycopg2.connect(DATABASE_URL)


def require_internal(admin: bool = False):
    if not secrets.compare_digest(request.headers.get("X-Internal-Key", ""), INTERNAL_API_KEY):
        return jsonify(error="Acceso interno no autorizado"), 401
    if admin and request.headers.get("X-User-Role") != "admin":
        return jsonify(error="Se requiere rol administrador"), 403
    return None


def validate_role(value: str) -> str:
    role = (value or "usuario").strip().lower()
    if role not in {"usuario", "admin"}:
        raise ValueError("Rol inválido")
    return role


def validate_password(value: str):
    if len(value or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")


def send_notification(event_type: str, recipient: str, context: dict):
    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/api/notifications",
            headers={"X-Internal-Key": INTERNAL_API_KEY},
            json={"event_type": event_type, "recipient": recipient, "context": context},
            timeout=(4, 25),
        )
        if response.status_code >= 400:
            app.logger.warning("El servicio de notificaciones rechazó %s: %s", event_type, response.text[:500])
    except requests.RequestException:
        app.logger.exception("No se pudo contactar al servicio de notificaciones")



def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS usuarios (
      id SERIAL PRIMARY KEY,
      nombre VARCHAR(120) NOT NULL,
      email VARCHAR(120) NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      rol VARCHAR(20) NOT NULL DEFAULT 'usuario' CHECK (rol IN ('usuario','admin')),
      activo BOOLEAN NOT NULL DEFAULT TRUE,
      session_version INTEGER NOT NULL DEFAULT 1,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_email_lower ON usuarios (LOWER(email));
    CREATE TABLE IF NOT EXISTS password_resets (
      id BIGSERIAL PRIMARY KEY,
      email VARCHAR(120) NOT NULL,
      token_hash CHAR(64) UNIQUE NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL,
      used_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(LOWER(email));
    CREATE TABLE IF NOT EXISTS login_attempts (
      id BIGSERIAL PRIMARY KEY,
      email VARCHAR(120) NOT NULL,
      client_ip VARCHAR(64) NOT NULL,
      success BOOLEAN NOT NULL,
      attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup ON login_attempts(LOWER(email),client_ip,attempted_at DESC);
    CREATE TABLE IF NOT EXISTS audit_log (
      id BIGSERIAL PRIMARY KEY,
      actor_user_id INTEGER,
      action VARCHAR(80) NOT NULL,
      target_type VARCHAR(50),
      target_id VARCHAR(80),
      detail JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with conn() as db, db.cursor() as cur:
        cur.execute(schema)
        cur.execute("SELECT COUNT(*) FROM usuarios")
        has_users = cur.fetchone()[0] > 0
        if not has_users:
            if not ADMIN_PASSWORD:
                raise RuntimeError("ADMIN_PASSWORD es obligatorio para crear el primer administrador")
            validate_password(ADMIN_PASSWORD)
            cur.execute(
                "INSERT INTO usuarios(nombre,email,password_hash,rol) VALUES(%s,%s,%s,'admin')",
                (ADMIN_NAME, ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD)),
            )
        # ADMIN_PASSWORD solo se usa durante el primer arranque. En actualizaciones no se
        # valida ni reemplaza contraseñas existentes, aunque sean de una política anterior.
        db.commit()


@app.get("/health")
def health():
    try:
        with conn() as db, db.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return jsonify(status="ok")
    except Exception as exc:
        return jsonify(status="error", detail=str(exc)), 503


@app.post("/api/auth/login")
def login():
    denied = require_internal()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    client_ip = request.headers.get("X-Client-IP", "unknown")[:64]
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT COUNT(*) AS failures FROM login_attempts WHERE LOWER(email)=LOWER(%s) AND client_ip=%s AND success=FALSE AND attempted_at > NOW() - INTERVAL '15 minutes'",
            (email, client_ip),
        )
        if cur.fetchone()["failures"] >= 5:
            return jsonify(error="Demasiados intentos. Intente nuevamente en 15 minutos"), 429
        cur.execute("SELECT id,nombre,email,password_hash,rol,activo,session_version FROM usuarios WHERE LOWER(email)=LOWER(%s)", (email,))
        user = cur.fetchone()
        valid = bool(user and user["activo"] and check_password_hash(user["password_hash"], password))
        cur.execute("INSERT INTO login_attempts(email,client_ip,success) VALUES(%s,%s,%s)", (email, client_ip, valid))
        if valid:
            cur.execute("DELETE FROM login_attempts WHERE LOWER(email)=LOWER(%s) AND client_ip=%s AND success=FALSE", (email, client_ip))
        cur.execute("DELETE FROM login_attempts WHERE attempted_at < NOW() - INTERVAL '7 days'")
        db.commit()
    if not valid:
        return jsonify(error="Credenciales incorrectas"), 401
    user.pop("password_hash", None)
    return jsonify(user)


@app.get("/api/users/<int:user_id>")
def get_user(user_id):
    denied = require_internal()
    if denied:
        return denied
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id,nombre,email,rol,activo,session_version,created_at FROM usuarios WHERE id=%s", (user_id,))
        user = cur.fetchone()
    if not user:
        return jsonify(error="Usuario no encontrado"), 404
    return jsonify(user)


@app.get("/api/users/display-names")
def user_display_names():
    """Devuelve únicamente identificador y nombre para mostrar propietarios de documentos."""
    denied = require_internal()
    if denied:
        return denied
    ids = [int(x) for x in request.args.get("ids", "").split(",") if x.strip().isdigit()]
    if not ids:
        return jsonify(items=[])
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id,nombre FROM usuarios WHERE id = ANY(%s) ORDER BY nombre",
            (ids,),
        )
        users = cur.fetchall()
    return jsonify(items=users)


@app.get("/api/users")
def list_users():
    denied = require_internal(admin=True)
    if denied:
        return denied
    ids = [int(x) for x in request.args.get("ids", "").split(",") if x.strip().isdigit()]
    query = "SELECT id,nombre,email,rol,activo,session_version,created_at FROM usuarios"
    params = []
    if ids:
        query += " WHERE id = ANY(%s)"
        params.append(ids)
    query += " ORDER BY nombre"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return jsonify(items=rows)


@app.post("/api/users")
def create_user():
    denied = require_internal(admin=True)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        nombre = str(data.get("nombre", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        role = validate_role(data.get("rol", "usuario"))
        if not nombre or "@" not in email:
            raise ValueError("Nombre y correo válidos son obligatorios")
        validate_password(password)
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO usuarios(nombre,email,password_hash,rol) VALUES(%s,%s,%s,%s) RETURNING id,nombre,email,rol,activo,session_version",
                (nombre, email, generate_password_hash(password), role),
            )
            user = cur.fetchone()
            cur.execute("INSERT INTO audit_log(actor_user_id,action,target_type,target_id) VALUES(%s,'USER_CREATE','user',%s)", (request.headers.get("X-User-ID"), user["id"]))
            db.commit()
        send_notification(
            "user_created",
            user["email"],
            {"name": user["nombre"], "email": user["email"], "role": user["rol"], "login_url": APP_BASE_URL},
        )
        return jsonify(user), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="El correo ya está registrado"), 409
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.put("/api/users/<int:user_id>")
def update_user(user_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        nombre = str(data.get("nombre", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        role = validate_role(data.get("rol", "usuario"))
        active = bool(data.get("activo", True))
        password = str(data.get("password", ""))
        if not nombre or "@" not in email:
            raise ValueError("Nombre y correo válidos son obligatorios")
        actor_id = int(request.headers.get("X-User-ID", "0") or 0)
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT rol FROM usuarios WHERE id=%s FOR UPDATE", (user_id,))
            current = cur.fetchone()
            if not current:
                return jsonify(error="Usuario no encontrado"), 404
            if current["rol"] == "admin" and (role != "admin" or not active):
                cur.execute("SELECT COUNT(*) AS total FROM usuarios WHERE rol='admin' AND activo=TRUE")
                if cur.fetchone()["total"] <= 1:
                    return jsonify(error="No se puede desactivar o degradar al último administrador"), 409
            if password:
                validate_password(password)
                cur.execute(
                    "UPDATE usuarios SET nombre=%s,email=%s,rol=%s,activo=%s,password_hash=%s,session_version=session_version+1,updated_at=NOW() WHERE id=%s RETURNING id,nombre,email,rol,activo,session_version",
                    (nombre, email, role, active, generate_password_hash(password), user_id),
                )
            else:
                cur.execute(
                    "UPDATE usuarios SET nombre=%s,email=%s,rol=%s,activo=%s,session_version=session_version+1,updated_at=NOW() WHERE id=%s RETURNING id,nombre,email,rol,activo,session_version",
                    (nombre, email, role, active, user_id),
                )
            user = cur.fetchone()
            cur.execute("INSERT INTO audit_log(actor_user_id,action,target_type,target_id) VALUES(%s,'USER_UPDATE','user',%s)", (actor_id, user_id))
            db.commit()
        send_notification(
            "user_updated",
            user["email"],
            {"name": user["nombre"], "email": user["email"], "role": user["rol"], "active": user["activo"], "password_changed": bool(password)},
        )
        return jsonify(user)
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="El correo ya está registrado"), 409
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.delete("/api/users/<int:user_id>")
def delete_user(user_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    actor_id = int(request.headers.get("X-User-ID", "0") or 0)
    if actor_id == user_id:
        return jsonify(error="No puede eliminar su propio usuario"), 409
    with conn() as db, db.cursor() as cur:
        cur.execute("SELECT rol FROM usuarios WHERE id=%s FOR UPDATE", (user_id,))
        row = cur.fetchone()
        if not row:
            return jsonify(error="Usuario no encontrado"), 404
        if row[0] == "admin":
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol='admin' AND activo=TRUE")
            if cur.fetchone()[0] <= 1:
                return jsonify(error="No se puede eliminar al último administrador"), 409
        cur.execute("UPDATE usuarios SET activo=FALSE,session_version=session_version+1,updated_at=NOW() WHERE id=%s", (user_id,))
        cur.execute("INSERT INTO audit_log(actor_user_id,action,target_type,target_id) VALUES(%s,'USER_DEACTIVATE','user',%s)", (actor_id, user_id))
        db.commit()
    return jsonify(ok=True, deactivated=True)


@app.post("/api/auth/password-reset/request")
def request_reset():
    denied = require_internal()
    if denied:
        return denied
    email = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    token = None
    with conn() as db, db.cursor() as cur:
        cur.execute("SELECT 1 FROM usuarios WHERE LOWER(email)=LOWER(%s) AND activo=TRUE", (email,))
        if cur.fetchone():
            cur.execute("SELECT COUNT(*) FROM password_resets WHERE LOWER(email)=LOWER(%s) AND created_at > NOW() - INTERVAL '1 hour'", (email,))
            if cur.fetchone()[0] < 3:
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                cur.execute("UPDATE password_resets SET used_at=NOW() WHERE LOWER(email)=LOWER(%s) AND used_at IS NULL", (email,))
                cur.execute("INSERT INTO password_resets(email,token_hash,expires_at) VALUES(%s,%s,%s)", (email, token_hash, datetime.now(timezone.utc) + timedelta(minutes=30)))
                db.commit()
    if token:
        send_notification(
            "password_reset",
            email,
            {"reset_link": f"{APP_BASE_URL.rstrip('/')}/restablecer_contrasena/{token}"},
        )
    return jsonify(message="Si el correo está registrado, recibirá instrucciones")


@app.get("/api/auth/password-reset/<token>")
def validate_reset(token):
    denied = require_internal()
    if denied:
        return denied
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with conn() as db, db.cursor() as cur:
        cur.execute("SELECT 1 FROM password_resets WHERE token_hash=%s AND used_at IS NULL AND expires_at>NOW()", (token_hash,))
        valid = bool(cur.fetchone())
    return jsonify(valid=valid), (200 if valid else 404)


@app.post("/api/auth/password-reset/<token>")
def reset_password(token):
    denied = require_internal()
    if denied:
        return denied
    password = str((request.get_json(silent=True) or {}).get("password", ""))
    try:
        validate_password(password)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with conn() as db, db.cursor() as cur:
        cur.execute("SELECT id,email FROM password_resets WHERE token_hash=%s AND used_at IS NULL AND expires_at>NOW() FOR UPDATE", (token_hash,))
        row = cur.fetchone()
        if not row:
            return jsonify(error="El enlace es inválido o expiró"), 404
        cur.execute("UPDATE usuarios SET password_hash=%s,session_version=session_version+1,updated_at=NOW() WHERE LOWER(email)=LOWER(%s)", (generate_password_hash(password), row[1]))
        cur.execute("UPDATE password_resets SET used_at=NOW() WHERE id=%s", (row[0],))
        cur.execute("SELECT nombre,email FROM usuarios WHERE LOWER(email)=LOWER(%s)", (row[1],))
        user = cur.fetchone()
        db.commit()
    if user:
        send_notification("password_changed", user[1], {"name": user[0], "email": user[1]})
    return jsonify(ok=True)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
