# app.py
from flask import Flask, render_template, request, redirect, session, url_for, flash
from markupsafe import Markup
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import secrets
from flask import send_file
from io import BytesIO
from datetime import datetime
import pandas as pd

# ===============================
# Flask app
# ===============================
app = Flask(__name__)
app.debug = False



# ===============================
# Carga de entorno y configuración
# ===============================
load_dotenv()
APP_TZ = os.getenv("TZ", "America/Guayaquil")

# ===============================
# SMTP
# ===============================
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_TLS = str(os.getenv("SMTP_TLS", "true")).lower() in {"1", "true", "yes", "on"}
SMTP_FROM = os.getenv("SMTP_FROM", "")  # opcional (si no se pone, usa SMTP_USER)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")

# DB URL primero; fallback a POSTGRES_*
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    pg_host = os.getenv("POSTGRES_HOST", os.getenv("POSTGRES_HOSTNAME", "db"))
    pg_port = int(os.getenv("POSTGRES_PORT", "5432") or 5432)
    pg_db = os.getenv("POSTGRES_DB", "actas_db")
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
    DATABASE_URL = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

# ===============================
# Flask app
# ===============================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "please_change_me")

# ===============================
# Utilidades
# ===============================
def get_conn():
    """Nueva conexión por request (seguro para Gunicorn)."""
    return psycopg2.connect(DATABASE_URL)

def password_matches(db_password: str, provided: str) -> bool:
    return db_password == provided


def send_email(to_email: str, subject: str, html: str):
    if not SMTP_SERVER:
        print("[WARN] SMTP no configurado; no se envía correo.")
        return
    msg = MIMEText(html, "html", "utf-8")
    sender = SMTP_FROM or SMTP_USER or "no-reply@example.com"
    if "<" in sender and ">" in sender:
        # ya viene con "Nombre <correo>"
        msg["From"] = sender
    else:
        msg["From"] = formataddr(("Notificaciones", sender))
    msg["To"] = to_email
    msg["Subject"] = subject

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        if SMTP_TLS:
            server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def local_time_str(fecha, hora, tz_name=APP_TZ):
    """Convierte (fecha, hora) UTC a zona local y devuelve HH:MM:SS."""
    utc = pytz.utc
    local_tz = pytz.timezone(tz_name)
    dt_utc = datetime.combine(fecha, hora).replace(tzinfo=utc)
    dt_local = dt_utc.astimezone(local_tz)
    return dt_local.strftime("%H:%M:%S")

# ===============================
# Middlewares de sesión
# ===============================
def require_login():
    if not session.get("user_id"):
        flash("Inicia sesión primero.", "warning")
        return False
    return True

def require_admin():
    if not require_login():
        return False
    if session.get("rol") != "admin":
        flash("Acceso denegado", "danger")
        return False
    return True

# ===============================
# Rutas
# ===============================
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, nombre, rol, password FROM usuarios WHERE LOWER(email)=%s", (email,))
        row = cur.fetchone()

    if row and password_matches(row[3], password):
        session['user_id'] = row[0]
        session['nombre'] = row[1]
        session['rol'] = row[2]
        return redirect('/dashboard')

    flash("Correo o contraseña incorrecta", "danger")
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not require_login():
        return redirect('/')
    return render_template('dashboard.html', nombre=session['nombre'])

# ==============================================
# Exportar documentos (actas, informes, reportes)
# ==============================================
@app.route('/exportar_documentos/<tipo>', methods=['GET'])
def exportar_documentos(tipo):
    if not require_login():
        return redirect('/')

    if tipo not in ['actas', 'informes', 'reportes', 'comisiones']:
        flash("Tipo de documento no válido", "danger")
        return redirect('/dashboard')

    with get_conn() as conn:
        df = pd.read_sql_query(f"""
            SELECT d.id,
                   d.asunto,
                   d.observaciones,
                   d.fecha,
                   d.hora,
                   u.nombre AS funcionario
            FROM {tipo} d
            JOIN usuarios u ON u.id = d.id_usuario
            ORDER BY d.fecha DESC, d.hora DESC
        """, conn)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=tipo.capitalize())

    output.seek(0)
    filename = f"{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ===============================
# Recuperación de contraseña
# ===============================
@app.route('/recuperar_contrasena', methods=['GET'])
@app.route('/recuperar_contraseña', methods=['GET'], endpoint='recuperar_contraseña')
def recuperar_contrasena():
    return render_template('recuperar_contraseña.html')

@app.route('/enviar_recuperacion', methods=['POST'])
def enviar_recuperacion():
    email = request.form.get('email', '').strip().lower()
    if not email:
        flash("Ingresa tu correo.", "warning")
        return redirect('/recuperar_contrasena')

    # ¿Existe el usuario?
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM usuarios WHERE LOWER(email)=%s", (email,))
        exists = cur.fetchone() is not None

    if not exists:
        flash("Correo no registrado.", "warning")
        return redirect('/recuperar_contrasena')

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO password_resets (token, email, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (token) DO UPDATE SET email=EXCLUDED.email, expires_at=EXCLUDED.expires_at
        """, (token, email, expires_at))
        conn.commit()

    # construir URL con base conocida (APP_BASE_URL) para que funcione detrás de proxy
    reset_path = url_for('restablecer_contrasena', token=token)
    reset_url = APP_BASE_URL.rstrip('/') + reset_path

    html = f"""
    <p>Hola,</p>
    <p>Has solicitado cambiar tu contraseña. Haz clic en el siguiente enlace:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Este enlace expira en 1 hora.</p>
    """
    try:
        send_email(email, "Recuperación de contraseña", html)
        flash("Se ha enviado un enlace de recuperación al correo.", "success")
    except Exception as e:
        print("Error al enviar correo:", e)
        flash("Error al enviar el correo.", "danger")

    return redirect('/')

@app.route('/restablecer_contrasena/<token>', methods=['GET', 'POST'])
@app.route('/restablecer_contraseña/<token>', methods=['GET', 'POST'], endpoint='restablecer_contraseña')
def restablecer_contrasena(token):
    if request.method == 'POST':
        nueva = request.form.get('password', '')
        email = request.form.get('email', '').strip().lower()

        if not nueva or not email:
            flash("Completa los campos requeridos.", "warning")
            return redirect(request.url)

        # validar token
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT email, expires_at
                FROM password_resets
                WHERE token=%s
            """, (token,))
            row = cur.fetchone()

            if not row or row['email'].lower() != email or row['expires_at'] < datetime.utcnow():
                flash("Enlace inválido o expirado.", "danger")
                return redirect('/')

            # actualizar contraseña
            cur.execute("UPDATE usuarios SET password=%s WHERE LOWER(email)=%s", (nueva, email))

            # borrar token
            cur.execute("DELETE FROM password_resets WHERE token=%s", (token,))
            conn.commit()

        flash("Contraseña actualizada exitosamente.", "success")
        return redirect('/')

    # GET
    return render_template('restablecer_contraseña.html', token=token)

# ===============================
# Creación de documentos
# ===============================
@app.route('/crear/<tipo>', methods=['GET', 'POST'])
def crear(tipo):
    if not require_login():
        return redirect('/')

    if session.get('rol') not in ['usuario', 'admin']:
        return 'Acceso no autorizado'

    tipo = tipo.lower()

    # Mapeo seguro de tablas
    tablas_permitidas = {
        'actas': 'actas',
        'informes': 'informes',
        'reportes': 'reportes',
        'comisiones': 'comisiones'
    }

    if tipo not in tablas_permitidas:
        flash("Tipo de documento inválido.", "danger")
        return redirect('/dashboard')

    tabla = tablas_permitidas[tipo]

    if request.method == 'POST':
        asunto = request.form.get('asunto', '').strip()
        observaciones = request.form.get('observaciones', '').strip()

        if not asunto:
            flash("El asunto es obligatorio.", "warning")
            return redirect(request.url)

        # Hora local Ecuador
        timezone = pytz.timezone(APP_TZ)
        now = datetime.now(timezone)
        fecha = now.date()
        hora = now.time()

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {tabla} (asunto, observaciones, id_usuario, fecha, hora)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (asunto, observaciones, session['user_id'], fecha, hora))
            doc_id = cur.fetchone()[0]

            cur.execute(
                "SELECT email FROM usuarios WHERE id=%s",
                (session['user_id'],)
            )
            email_usuario = cur.fetchone()[0]
            conn.commit()

        hora_local = hora.strftime("%H:%M:%S")

        # Correo
        try:
            html = f"""
            <h3>Nuevo {tipo.capitalize()} registrado</h3>
            <p><b>Número:</b> {doc_id}</p>
            <p><b>Asunto:</b> {asunto}</p>
            <p><b>Observaciones:</b> {observaciones}</p>
            <p><b>Fecha:</b> {fecha}</p>
            <p><b>Hora:</b> {hora_local}</p>
            <p><b>Funcionario:</b> {session['nombre']}</p>
            """
            send_email(
                email_usuario,
                f"{tipo.capitalize()} creado: {asunto}",
                html
            )
        except Exception as e:
            print("Error al enviar correo:", e)

        # Toast
        flash(Markup(f"""
        <div class='toast-content'>
            <h5>{tipo.capitalize()} creado correctamente</h5>
            <p><b>ID:</b> {doc_id}</p>
            <p><b>Asunto:</b> {asunto}</p>
            <p><b>Fecha:</b> {fecha}</p>
            <p><b>Hora:</b> {hora_local}</p>
        </div>
        """), 'toast')

        return redirect('/dashboard')

    return render_template('formulario.html', tipo=tipo)



# ===============================
# Panel admin
# ===============================
@app.route('/admin')
def admin():
    if not require_admin():
        return redirect('/')
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, nombre, email, rol FROM usuarios ORDER BY id")
        usuarios = cur.fetchall()
    return render_template('admin.html', usuarios=usuarios)

@app.route('/admin/documentos')
def admin_documentos():
    if not require_admin():
        return redirect('/')

    with get_conn() as conn, conn.cursor() as cur:
        # ACTAS
        cur.execute("""
            SELECT a.id, a.asunto, a.fecha,
                   TO_CHAR(a.hora, 'HH24:MI:SS'),
                   u.nombre
            FROM actas a
            JOIN usuarios u ON u.id = a.id_usuario
            ORDER BY a.id DESC
        """)
        actas = cur.fetchall()

        # INFORMES
        cur.execute("""
            SELECT i.id, i.asunto, i.fecha,
                   TO_CHAR(i.hora, 'HH24:MI:SS'),
                   u.nombre
            FROM informes i
            JOIN usuarios u ON u.id = i.id_usuario
            ORDER BY i.id DESC
        """)
        informes = cur.fetchall()

        # REPORTES
        cur.execute("""
            SELECT r.id, r.asunto, r.fecha,
                   TO_CHAR(r.hora, 'HH24:MI:SS'),
                   u.nombre
            FROM reportes r
            JOIN usuarios u ON u.id = r.id_usuario
            ORDER BY r.id DESC
        """)
        reportes = cur.fetchall()

        # COMISIONES
        cur.execute("""
            SELECT c.id, c.asunto, c.fecha,
                   TO_CHAR(c.hora, 'HH24:MI:SS'),
                   u.nombre
            FROM comisiones c
            JOIN usuarios u ON u.id = c.id_usuario
            ORDER BY c.id DESC
        """)
        comisiones = cur.fetchall()

    return render_template(
        'admin_documentos.html',
        actas=actas,
        informes=informes,
        reportes=reportes,
        comisiones=comisiones
    )


@app.route('/eliminar/<tipo>/<int:id>')
def eliminar_documento(tipo, id):
    if not require_admin():
        return redirect('/')

    tipo = tipo.lower()
    if tipo not in ['actas', 'informes', 'reportes', 'comisiones']:
        flash("Tipo de documento inválido.", "danger")
        return redirect('/admin/documentos')

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"DELETE FROM {tipo} WHERE id=%s", (id,))
        conn.commit()

    flash(f'{tipo.capitalize()} ID {id} eliminado correctamente.', 'danger')
    return redirect('/admin/documentos')

# ===============================
# CRUD usuarios (admin)
# ===============================
@app.route('/admin/usuarios/crear', methods=['GET', 'POST'])
def crear_usuario():
    if not require_admin():
        return redirect('/')

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        rol = request.form.get('rol', 'usuario')

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (nombre, email, password, rol)
                VALUES (%s, %s, %s, %s)
            """, (nombre, email, password, rol))  # Se guarda en texto plano
            conn.commit()


        flash("Usuario creado exitosamente", "success")
        return redirect('/admin')

    return render_template('form_usuario.html', modo="Crear", usuario=None)

@app.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if not require_admin():
        return redirect('/')

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        rol = request.form.get('rol', 'usuario')

        with get_conn() as conn, conn.cursor() as cur:
            if password:
                cur.execute("""
                    UPDATE usuarios
                    SET nombre=%s, email=%s, password=%s, rol=%s
                    WHERE id=%s
                """, (nombre, email, password, rol, id))
            else:
                cur.execute("""
                    UPDATE usuarios
                    SET nombre=%s, email=%s, rol=%s
                    WHERE id=%s
                """, (nombre, email, rol, id))
            conn.commit()

        flash("Usuario actualizado", "info")
        return redirect('/admin')

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT nombre, email, password, rol FROM usuarios WHERE id=%s", (id,))
        usuario = cur.fetchone()

    if not usuario:
        flash("Usuario no encontrado.", "warning")
        return redirect('/admin')

    return render_template('form_usuario.html', modo="Editar", usuario=usuario, id=id)

@app.route('/admin/usuarios/eliminar/<int:id>')
def eliminar_usuario(id):
    if not require_admin():
        return redirect('/')

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM usuarios WHERE id=%s", (id,))
        conn.commit()

    flash("Usuario eliminado", "danger")
    return redirect('/admin')

# ===============================
# Listados para usuario
# ===============================
@app.route('/mis_documentos')
def mis_documentos():
    if not require_login():
        return redirect('/')

    with get_conn() as conn, conn.cursor() as cur:

        cur.execute("""
            SELECT a.id, a.asunto, a.observaciones, a.fecha,
                   TO_CHAR(a.hora, 'HH24:MI:SS'), u.nombre
            FROM actas a
            JOIN usuarios u ON a.id_usuario = u.id
            ORDER BY a.id DESC
        """)
        actas = cur.fetchall()

        cur.execute("""
            SELECT i.id, i.asunto, i.observaciones, i.fecha,
                   TO_CHAR(i.hora, 'HH24:MI:SS'), u.nombre
            FROM informes i
            JOIN usuarios u ON i.id_usuario = u.id
            ORDER BY i.id DESC
        """)
        informes = cur.fetchall()

        cur.execute("""
            SELECT r.id, r.asunto, r.observaciones, r.fecha,
                   TO_CHAR(r.hora, 'HH24:MI:SS'), u.nombre
            FROM reportes r
            JOIN usuarios u ON r.id_usuario = u.id
            ORDER BY r.id DESC
        """)
        reportes = cur.fetchall()

        cur.execute("""
            SELECT c.id, c.asunto, c.observaciones, c.fecha,
                   TO_CHAR(c.hora, 'HH24:MI:SS'), u.nombre
            FROM comisiones c
            JOIN usuarios u ON c.id_usuario = u.id
            ORDER BY c.id DESC
        """)
        comisiones = cur.fetchall()

    return render_template(
        'mis_documentos.html',
        actas=actas,
        informes=informes,
        reportes=reportes,
        comisiones=comisiones
    )


# ===============================
# Utilidad CLI (opcional)
# ===============================
def crear_usuario_directo(nombre, email, password, rol):
    """Utilidad para crear un usuario desde consola usando la misma config."""
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO usuarios (nombre, email, password, rol) VALUES (%s, %s, %s, %s) RETURNING *",
            (nombre, email.lower(), password, rol)
        )
        row = cur.fetchone()
        conn.commit()
        return dict(row)

# ===============================
# Main
# ===============================
if __name__ == '__main__':
    # En desarrollo local: flask built-in; en Docker se usa Gunicorn (CMD del contenedor)
    app.run(host='0.0.0.0', port=8000, debug=True)
