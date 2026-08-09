import argparse
import secrets
import string
from pathlib import Path


def password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@%_-"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in value) and any(c.isupper() for c in value) and any(c.isdigit() for c in value):
            return value


def main():
    parser = argparse.ArgumentParser(description="Genera un archivo .env seguro")
    parser.add_argument("--admin-email", default="admin@example.com")
    parser.add_argument("--admin-name", default="Administrador del sistema")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / ".env"
    if target.exists() and not args.force:
        raise SystemExit(".env ya existe. Use --force para reemplazarlo.")
    admin_password = password(20)
    content = f"""POSTGRES_USER=actas_admin
POSTGRES_PASSWORD={secrets.token_urlsafe(32)}
SECRET_KEY={secrets.token_hex(32)}
INTERNAL_API_KEY={secrets.token_hex(32)}

ADMIN_NAME={args.admin_name}
ADMIN_EMAIL={args.admin_email}
ADMIN_PASSWORD={admin_password}
MIN_PASSWORD_LENGTH=6

TZ=America/Guayaquil
WEB_PORT=8080
APP_BASE_URL=http://localhost:8080
SESSION_COOKIE_SECURE=false
MAX_BACKUP_UPLOAD_BYTES=104857600
MAX_BACKUP_EXTRACTED_BYTES=524288000

SMTP_SERVER=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_TLS=true
SMTP_FROM=
EMAIL_NOTIFICATIONS_ENABLED=true
SYSTEM_NAME="ARCONEL - Control de Documentos"

PGADMIN_DEFAULT_EMAIL={args.admin_email}
PGADMIN_DEFAULT_PASSWORD={password(20)}
PGADMIN_PORT=5050
"""
    target.write_text(content, encoding="utf-8")
    print(f"Archivo creado: {target}")
    print(f"Usuario administrador: {args.admin_email}")
    print(f"Contraseña inicial: {admin_password}")
    print("Guarde esta contraseña y cámbiela después del primer acceso.")


if __name__ == "__main__":
    main()
