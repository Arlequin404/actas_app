import hashlib
import fcntl
import json
import os
import re
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests
from flask import Flask, after_this_request, jsonify, request, send_file
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build as google_build
from googleapiclient.http import MediaFileUpload
from psycopg2 import sql
from psycopg2.extras import Json, RealDictCursor
from werkzeug.security import generate_password_hash

app = Flask(__name__)
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
if len(INTERNAL_API_KEY) < 32:
    raise RuntimeError("INTERNAL_API_KEY debe tener al menos 32 caracteres")
PGHOST = os.getenv("PGHOST", "db")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.environ["PGPASSWORD"]
DATABASES = [
    x.strip()
    for x in os.getenv(
        "BACKUP_DATABASES",
        "auth_db,documents_db,catalog_db,notifications_db",
    ).split(",")
    if x.strip()
]
if (
    not DATABASES
    or len(set(DATABASES)) != len(DATABASES)
    or any(
        not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", name)
        for name in DATABASES
    )
):
    raise RuntimeError("BACKUP_DATABASES contiene nombres de base de datos inválidos")
MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_BACKUP_UPLOAD_BYTES", str(100 * 1024 * 1024))
)
MAX_EXTRACTED_BYTES = int(
    os.getenv("MAX_BACKUP_EXTRACTED_BYTES", str(MAX_UPLOAD_BYTES * 5))
)
GOOGLE_DRIVE_CLIENT_ID = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "").strip()
GOOGLE_DRIVE_CLIENT_SECRET = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "").strip()
GOOGLE_DRIVE_FOLDER_PATH = os.getenv("GOOGLE_DRIVE_FOLDER_PATH", "ARCONEL Respaldos/Actas").strip().strip("/") or "ARCONEL Respaldos/Actas"
GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GOOGLE_DRIVE_TOKEN_FILE = Path(os.getenv("GOOGLE_DRIVE_TOKEN_FILE", "/backup-state/google-drive-token.json"))
GOOGLE_DRIVE_META_FILE = Path(os.getenv("GOOGLE_DRIVE_META_FILE", "/backup-state/google-drive-meta.json"))
GOOGLE_DRIVE_OAUTH_STATE_FILE = Path(os.getenv("GOOGLE_DRIVE_OAUTH_STATE_FILE", "/backup-state/google-drive-oauth-state.json"))
GOOGLE_DRIVE_OAUTH_CONFIGURED = bool(GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET)
BACKUP_STATUS_FILE = Path(os.getenv("BACKUP_STATUS_FILE", "/backup-state/status.json"))
BACKUP_SCHEDULER_STATUS_FILE = Path(os.getenv("BACKUP_SCHEDULER_STATUS_FILE", "/backup-state/scheduler.json"))
BACKUP_LOCK_FILE = Path(os.getenv("BACKUP_LOCK_FILE", "/backup-state/backup.lock"))
BACKUP_RETENTION_DAYS = max(int(os.getenv("BACKUP_RETENTION_DAYS", "30")), 1)
AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
AUTO_BACKUP_TIME = os.getenv("AUTO_BACKUP_TIME", "02:00")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")
LEGACY_REQUIRED_TABLES = {
    "usuarios",
    "catalogos",
    "actas",
    "informes",
    "reportes",
    "comisiones",
}
LEGACY_PREFIXES = {
    "actas": "ACTAS.DTCD",
    "informes": "INF.DTCD",
    "reportes": "REP.DTCD",
    "comisiones": "CMS.DTCD",
}


def require_admin():
    if not secrets.compare_digest(
        request.headers.get("X-Internal-Key", ""), INTERNAL_API_KEY
    ):
        return jsonify(error="Acceso interno no autorizado"), 401
    if request.headers.get("X-User-Role") != "admin":
        return jsonify(error="Se requiere rol administrador"), 403
    return None


def command_env(password=None):
    result = os.environ.copy()
    result["PGPASSWORD"] = PGPASSWORD if password is None else password
    return result


def run(command, password=None):
    return subprocess.run(
        command,
        env=command_env(password),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def db_conn(database, *, user=None, password=None):
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        user=user or PGUSER,
        password=PGPASSWORD if password is None else password,
        dbname=database,
    )


def maintenance_conn():
    return db_conn("postgres")


def maintenance_cursor():
    connection = maintenance_conn()
    connection.autocommit = True
    return connection, connection.cursor()


def database_exists(cur, database):
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,))
    return cur.fetchone() is not None


def role_exists(cur, role_name):
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role_name,))
    return cur.fetchone() is not None


def drop_database_force(database):
    connection, cur = maintenance_cursor()
    try:
        if database_exists(cur, database):
            cur.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    sql.Identifier(database)
                )
            )
    finally:
        cur.close()
        connection.close()


def drop_role(role_name):
    connection, cur = maintenance_cursor()
    try:
        if role_exists(cur, role_name):
            cur.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role_name)))
    finally:
        cur.close()
        connection.close()


def postgres_client_major():
    output = run(["pg_restore", "--version"]).stdout
    match = re.search(r"\b(\d+)(?:\.\d+)?\b", output)
    if not match:
        raise RuntimeError(
            f"No fue posible identificar la versión de pg_restore: {output.strip()}"
        )
    return int(match.group(1))


def postgres_server_major():
    with maintenance_conn() as db, db.cursor() as cur:
        cur.execute("SHOW server_version_num")
        return int(cur.fetchone()[0]) // 10000


def save_upload(uploaded, destination):
    total = 0
    with destination.open("wb") as target:
        while True:
            chunk = uploaded.stream.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise ValueError("El respaldo supera el tamaño permitido")
            target.write(chunk)
    if total == 0:
        raise ValueError("El archivo de respaldo está vacío")
    return total


def create_safety_dumps(temp_dir, databases):
    dumps = {}
    for database in databases:
        path = temp_dir / f"{database}.before_restore.dump"
        run(
            [
                "pg_dump",
                "-h",
                PGHOST,
                "-p",
                PGPORT,
                "-U",
                PGUSER,
                "-Fc",
                "--no-owner",
                "--no-acl",
                "-f",
                str(path),
                database,
            ]
        )
        dumps[database] = path
    return dumps


def restore_safety_dumps(safety_dumps):
    errors = []
    for database, safety_path in safety_dumps.items():
        if not safety_path.exists():
            continue
        try:
            run(
                [
                    "pg_restore",
                    "-h",
                    PGHOST,
                    "-p",
                    PGPORT,
                    "-U",
                    PGUSER,
                    "--clean",
                    "--if-exists",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--no-acl",
                    "-d",
                    database,
                    str(safety_path),
                ]
            )
        except Exception as exc:
            errors.append(f"{database}: {exc}")
            app.logger.exception("No se pudo revertir la base %s", database)
    return errors


def extract_microservices_archive(archive, temp_dir):
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            names = {member.name for member in members}
            if "manifest.json" not in names:
                raise ValueError("El respaldo no contiene manifiesto")
            if any(
                not member.isfile() or Path(member.name).name != member.name
                for member in members
            ):
                raise ValueError("El archivo contiene rutas no permitidas")
            if any(
                name not in {"manifest.json", "adapted.sql"}
                and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}\.dump", name)
                for name in names
            ):
                raise ValueError("El respaldo contiene archivos no reconocidos")
            if sum(member.size for member in members) > MAX_EXTRACTED_BYTES:
                raise OverflowError(
                    "El contenido descomprimido supera el tamaño permitido"
                )

            # Python 3.11 no acepta extractall(filter="data"). Se extraen solo
            # archivos regulares con nombres planos ya validados.
            for member in members:
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError("El archivo de respaldo no es válido")
                destination = temp_dir / member.name
                written = 0
                with source, destination.open("xb") as target:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > member.size:
                            raise ValueError("El archivo de respaldo no es válido")
                        target.write(chunk)
                if written != member.size:
                    raise ValueError("El archivo de respaldo está incompleto")
            return names
    except (tarfile.TarError, OSError) as exc:
        raise ValueError("El archivo de respaldo no es válido") from exc


def restore_adapted_sql_archive(names, manifest, temp_dir):
    expected = {"manifest.json", "adapted.sql"}
    if names != expected:
        raise ValueError(
            "El paquete adaptado no contiene exactamente manifest.json y adapted.sql"
        )
    declared_databases = manifest.get("databases")
    if not isinstance(declared_databases, list) or set(declared_databases) != set(DATABASES):
        raise ValueError("El paquete adaptado no corresponde a las bases configuradas")

    sql_path = temp_dir / "adapted.sql"
    declared_hash = str(manifest.get("sha256", "")).lower()
    actual_hash = hashlib.sha256(sql_path.read_bytes()).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", declared_hash) or declared_hash != actual_hash:
        raise ValueError("La integridad del archivo SQL adaptado no es válida")

    safety_dumps = create_safety_dumps(temp_dir, DATABASES)
    try:
        run(
            [
                "psql",
                "-h",
                PGHOST,
                "-p",
                PGPORT,
                "-U",
                PGUSER,
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-d",
                "postgres",
                "-f",
                str(sql_path),
            ]
        )

        with db_conn("auth_db") as db, db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM usuarios")
            users = cur.fetchone()[0]
        with db_conn("catalog_db") as db, db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM catalogos")
            catalogs = cur.fetchone()[0]
        with db_conn("documents_db") as db, db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents")
            documents = cur.fetchone()[0]

        expected_counts = manifest.get("counts") or {}
        checks = {
            "users": users,
            "catalogs": catalogs,
            "documents": documents,
        }
        for key, actual in checks.items():
            expected_value = expected_counts.get(key)
            if expected_value is not None and int(expected_value) != actual:
                raise RuntimeError(
                    f"La importación de {key} quedó incompleta: {actual} de {expected_value}"
                )

        return {
            "ok": True,
            "format": "adapted-sql-tar.gz",
            "message": "Base adaptada importada correctamente",
            "imported": checks,
        }
    except Exception:
        rollback_errors = restore_safety_dumps(safety_dumps)
        if rollback_errors:
            raise RuntimeError(
                "La importación falló y la reversión automática no pudo completarse: "
                + "; ".join(rollback_errors)
            )
        raise


def restore_microservices_backup(archive, temp_dir):
    names = extract_microservices_archive(archive, temp_dir)
    try:
        manifest = json.loads(
            (temp_dir / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("El manifiesto del respaldo no es válido") from exc

    if manifest.get("format") == "actas-adapted-sql-backup-v1":
        return restore_adapted_sql_archive(names, manifest, temp_dir)

    if manifest.get("format") not in {
        "actas-microservices-backup-v1",
        "actas-microservices-backup-v2",
    }:
        raise ValueError("El respaldo pertenece a una versión no compatible")

    restore_databases = manifest.get("databases")
    required_core = {"auth_db", "documents_db", "catalog_db"}
    if not isinstance(restore_databases, list) or not required_core.issubset(
        restore_databases
    ):
        raise ValueError("El respaldo no contiene las bases principales")
    if any(database not in DATABASES for database in restore_databases):
        raise ValueError(
            "El respaldo contiene bases no configuradas en esta instalación"
        )
    expected = {
        "manifest.json",
        *{f"{database}.dump" for database in restore_databases},
    }
    if names != expected:
        raise ValueError(
            "El respaldo no contiene exactamente los archivos declarados"
        )

    suffix = uuid.uuid4().hex[:8]
    validation_databases = {
        db: f"{db}_validation_{suffix}" for db in restore_databases
    }
    safety_dumps = {}
    restored_databases = []

    try:
        for database, validation_db in validation_databases.items():
            connection, cur = maintenance_cursor()
            try:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(validation_db)
                    )
                )
            finally:
                cur.close()
                connection.close()
            try:
                run(
                    [
                        "pg_restore",
                        "-h",
                        PGHOST,
                        "-p",
                        PGPORT,
                        "-U",
                        PGUSER,
                        "--exit-on-error",
                        "--no-owner",
                        "--no-acl",
                        "-d",
                        validation_db,
                        str(temp_dir / f"{database}.dump"),
                    ]
                )
                with db_conn(validation_db) as verify_conn, verify_conn.cursor() as verify_cur:
                    verify_cur.execute("SELECT 1")
                    verify_cur.fetchone()
            finally:
                drop_database_force(validation_db)

        safety_dumps = create_safety_dumps(temp_dir, restore_databases)

        for database in restore_databases:
            run(
                [
                    "pg_restore",
                    "-h",
                    PGHOST,
                    "-p",
                    PGPORT,
                    "-U",
                    PGUSER,
                    "--clean",
                    "--if-exists",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--no-acl",
                    "-d",
                    database,
                    str(temp_dir / f"{database}.dump"),
                ]
            )
            restored_databases.append(database)

        return {
            "ok": True,
            "format": "tar.gz",
            "message": "Respaldo completo restaurado correctamente",
        }
    except Exception:
        # Si una restauración ya alcanzó alguna base activa, se recuperan todas
        # las bases incluidas desde la copia interna previa.
        if safety_dumps and restored_databases:
            rollback_errors = restore_safety_dumps(safety_dumps)
            if rollback_errors:
                raise RuntimeError(
                    "La restauración falló y la reversión automática no pudo completarse: "
                    + "; ".join(rollback_errors)
                )
        raise
    finally:
        for validation_db in validation_databases.values():
            try:
                drop_database_force(validation_db)
            except Exception:
                app.logger.exception(
                    "No se pudo eliminar la base temporal %s", validation_db
                )


def normalize_legacy_sql_text(text):
    if "\x00" in text:
        raise ValueError("El respaldo SQL contiene bytes no permitidos")
    if "PostgreSQL database dump" not in text[:4096]:
        raise ValueError("El archivo .sql no parece un respaldo de PostgreSQL")

    normalized = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        # pg_dump 17 agrega estas directivas y transaction_timeout. El cliente
        # PostgreSQL 16 no las reconoce, aunque el contenido del dump sí sea
        # compatible con el servidor 16.
        if stripped.startswith("\\restrict ") or stripped.startswith(
            "\\unrestrict "
        ):
            continue
        if stripped.startswith("\\") and stripped != "\\.":
            raise ValueError("El respaldo SQL contiene un comando psql no permitido")
        if stripped == "SET transaction_timeout = 0;":
            continue
        normalized.append(line)
    return "".join(normalized)


def normalize_legacy_sql_file(source, destination):
    try:
        raw = source.read_bytes()
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("El respaldo SQL debe estar codificado en UTF-8") from exc
    normalized = normalize_legacy_sql_text(text)
    destination.write_text(normalized, encoding="utf-8", newline="\n")


def legacy_password_hash(value):
    value = str(value or "")
    if value.startswith(("scrypt:", "pbkdf2:")):
        return value
    return generate_password_hash(value)


def validate_legacy_database(connection):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        missing = LEGACY_REQUIRED_TABLES - tables
        if missing:
            raise ValueError(
                "El respaldo SQL no corresponde al proyecto anterior. Faltan: "
                + ", ".join(sorted(missing))
            )

        required_columns = {
            "usuarios": {"id", "nombre", "email", "password", "rol", "created_at"},
            "catalogos": {
                "id",
                "categoria",
                "nombre",
                "valor",
                "padre_id",
                "activo",
                "orden",
                "meta_data",
            },
            "actas": {
                "id",
                "numero",
                "anio",
                "id_usuario",
                "empresa",
                "gestiones",
                "productos_asociados",
                "asunto",
                "fecha",
                "hora",
                "created_at",
            },
        }
        for table_name, expected in required_columns.items():
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                """,
                (table_name,),
            )
            columns = {row[0] for row in cur.fetchall()}
            missing_columns = expected - columns
            if missing_columns:
                raise ValueError(
                    f"La tabla {table_name} del respaldo SQL es incompatible. "
                    f"Faltan columnas: {', '.join(sorted(missing_columns))}"
                )

        cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol='admin'")
        if cur.fetchone()[0] < 1:
            raise ValueError(
                "El respaldo SQL no contiene ningún usuario administrador"
            )


def migrate_legacy_users(old, auth):
    with old.cursor(cursor_factory=RealDictCursor) as src, auth.cursor() as dst:
        src.execute(
            "SELECT id,nombre,email,password,rol,created_at FROM usuarios ORDER BY id"
        )
        users = src.fetchall()
        dst.execute(
            "TRUNCATE usuarios,password_resets,login_attempts,audit_log RESTART IDENTITY CASCADE"
        )
        for user in users:
            dst.execute(
                """
                INSERT INTO usuarios(
                    id,nombre,email,password_hash,rol,activo,session_version,
                    created_at,updated_at
                ) VALUES(%s,%s,%s,%s,%s,TRUE,1,%s,%s)
                """,
                (
                    user["id"],
                    user["nombre"],
                    user["email"].strip().lower(),
                    legacy_password_hash(user["password"]),
                    user["rol"] if user["rol"] in {"usuario", "admin"} else "usuario",
                    user["created_at"],
                    user["created_at"],
                ),
            )
        dst.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('usuarios','id'),
                GREATEST(COALESCE((SELECT MAX(id) FROM usuarios),1),1),
                EXISTS(SELECT 1 FROM usuarios)
            )
            """
        )
    return len(users)


def migrate_legacy_catalogs(old, catalogs):
    with old.cursor(cursor_factory=RealDictCursor) as src:
        src.execute(
            "SELECT id,categoria,nombre,valor,padre_id,activo,orden,meta_data "
            "FROM catalogos ORDER BY id"
        )
        pending = {row["id"]: row for row in src.fetchall()}

    with catalogs.cursor() as dst:
        dst.execute("TRUNCATE catalogos RESTART IDENTITY CASCADE")
        id_map = {}
        unique_keys = {}
        inserted = 0
        skipped_duplicates = 0
        while pending:
            progress = False
            for item_id, row in list(pending.items()):
                if row["padre_id"] is None or row["padre_id"] in id_map:
                    mapped_parent = id_map.get(row["padre_id"])
                    key = (
                        row["categoria"],
                        mapped_parent or 0,
                        row["nombre"].strip().casefold(),
                    )
                    if key in unique_keys:
                        id_map[item_id] = unique_keys[key]
                        skipped_duplicates += 1
                    else:
                        metadata = row["meta_data"]
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except json.JSONDecodeError:
                                metadata = {"legacy_value": metadata}
                        dst.execute(
                            """
                            INSERT INTO catalogos(
                                id,categoria,nombre,valor,padre_id,activo,orden,
                                meta_data,created_at,updated_at
                            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                            """,
                            (
                                row["id"],
                                row["categoria"],
                                row["nombre"],
                                row["valor"],
                                mapped_parent,
                                row["activo"],
                                row["orden"],
                                Json(metadata) if metadata is not None else None,
                            ),
                        )
                        id_map[item_id] = row["id"]
                        unique_keys[key] = row["id"]
                        inserted += 1
                    del pending[item_id]
                    progress = True
            if not progress:
                raise ValueError(
                    "No se pudo reconstruir la jerarquía de catálogos del respaldo SQL"
                )
        dst.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('catalogos','id'),
                GREATEST(COALESCE((SELECT MAX(id) FROM catalogos),1),1),
                EXISTS(SELECT 1 FROM catalogos)
            )
            """
        )
    return inserted, skipped_duplicates


def legacy_source_rows(old, table):
    common = (
        "id,numero,anio,id_usuario,empresa,gestiones,productos_asociados,"
        "asunto,observaciones,fecha,hora,created_at"
    )
    if table == "informes":
        fields = (
            common
            + ",tipo_informe,caso_tipo,nombre_alimentador,"
            "alimentador_subestacion,linea_subtransmision_nombre,fecha_interrupcion"
        )
    elif table == "reportes":
        fields = common + ",tipo_reporte"
    else:
        fields = common
    with old.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            sql.SQL("SELECT {} FROM {} ORDER BY anio,numero,id").format(
                sql.SQL(fields), sql.Identifier(table)
            )
        )
        return cur.fetchall()


def migrate_legacy_documents(old, documents):
    total = 0
    counters = defaultdict(int)
    with documents.cursor() as dst:
        dst.execute(
            "TRUNCATE documents,document_counters,audit_log RESTART IDENTITY CASCADE"
        )
        for table in ("actas", "informes", "reportes", "comisiones"):
            for row in legacy_source_rows(old, table):
                subtype = (
                    row.get("tipo_informe")
                    if table == "informes"
                    else row.get("tipo_reporte")
                    if table == "reportes"
                    else None
                )
                code = f"{LEGACY_PREFIXES[table]}.{row['numero']:03d}.{row['anio']}"
                dst.execute(
                    """
                    INSERT INTO documents(
                        document_type,number,year,code,user_id,company,management,
                        associated_products,subtype,subject,observations,case_type,
                        feeder_name,substation,subtransmission_line,interruption_date,
                        document_date,document_time,created_at,updated_at,
                        legacy_table,legacy_id,extra_data,form_definition_snapshot
                    ) VALUES(
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,'{}'::jsonb,'[]'::jsonb
                    )
                    """,
                    (
                        table,
                        row["numero"],
                        row["anio"],
                        code,
                        row["id_usuario"],
                        row["empresa"] or "No especificado",
                        row["gestiones"] or "No especificado",
                        row["productos_asociados"] or "No especificado",
                        subtype,
                        row["asunto"] or "Sin asunto",
                        row["observaciones"],
                        row.get("caso_tipo"),
                        row.get("nombre_alimentador"),
                        row.get("alimentador_subestacion"),
                        row.get("linea_subtransmision_nombre"),
                        row.get("fecha_interrupcion"),
                        row["fecha"],
                        row["hora"],
                        row["created_at"],
                        row["created_at"],
                        table,
                        row["id"],
                    ),
                )
                counters[(table, row["anio"])] = max(
                    counters[(table, row["anio"])], row["numero"] + 1
                )
                total += 1
        for (table, year), next_number in counters.items():
            dst.execute(
                "INSERT INTO document_counters(document_type,year,next_number) "
                "VALUES(%s,%s,%s)",
                (table, year, next_number),
            )
    return total


def migrate_legacy_notifications(notifications):
    with notifications.cursor() as cur:
        cur.execute("TRUNCATE notification_log RESTART IDENTITY")


def import_legacy_sql(source_path, temp_dir):
    normalized_path = temp_dir / "legacy.normalized.sql"
    normalize_legacy_sql_file(source_path, normalized_path)

    suffix = uuid.uuid4().hex[:10]
    legacy_db = f"legacy_import_{suffix}"
    legacy_role = f"legacy_loader_{suffix}"
    legacy_password = secrets.token_urlsafe(32)
    safety_dumps = {}
    connections = []
    sandbox_created = False

    try:
        connection, cur = maintenance_cursor()
        try:
            cur.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOINHERIT"
                ).format(
                    sql.Identifier(legacy_role), sql.Literal(legacy_password)
                )
            )
            cur.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(legacy_db), sql.Identifier(legacy_role)
                )
            )
            sandbox_created = True
        finally:
            cur.close()
            connection.close()

        run(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                PGHOST,
                "-p",
                PGPORT,
                "-U",
                legacy_role,
                "-d",
                legacy_db,
                "-f",
                str(normalized_path),
            ],
            password=legacy_password,
        )

        old = db_conn(legacy_db, user=legacy_role, password=legacy_password)
        connections = [old]
        validate_legacy_database(old)

        safety_dumps = create_safety_dumps(temp_dir, DATABASES)
        auth = db_conn("auth_db")
        documents = db_conn("documents_db")
        catalogs = db_conn("catalog_db")
        notifications = db_conn("notifications_db")
        connections.extend([auth, documents, catalogs, notifications])

        user_count = migrate_legacy_users(old, auth)
        catalog_count, duplicate_catalogs = migrate_legacy_catalogs(old, catalogs)
        document_count = migrate_legacy_documents(old, documents)
        migrate_legacy_notifications(notifications)

        # Cada base trabaja dentro de una transacción. Se conserva además una
        # copia interna completa para recuperar el estado anterior si un commit
        # posterior fallara de forma excepcional.
        for target in (auth, documents, catalogs, notifications):
            target.commit()

        return {
            "ok": True,
            "format": "legacy-sql",
            "message": "Respaldo SQL anterior migrado correctamente",
            "migrated": {
                "users": user_count,
                "catalogs": catalog_count,
                "duplicate_catalogs_skipped": duplicate_catalogs,
                "documents": document_count,
            },
        }
    except Exception:
        for target in connections:
            try:
                target.rollback()
            except Exception:
                pass
        for target in connections:
            try:
                target.close()
            except Exception:
                pass
        connections = []
        if safety_dumps:
            rollback_errors = restore_safety_dumps(safety_dumps)
            if rollback_errors:
                raise RuntimeError(
                    "La migración SQL falló y la reversión automática no pudo completarse: "
                    + "; ".join(rollback_errors)
                )
        raise
    finally:
        for target in connections:
            try:
                target.close()
            except Exception:
                pass
        if sandbox_created:
            try:
                drop_database_force(legacy_db)
            except Exception:
                app.logger.exception("No se pudo eliminar la base temporal %s", legacy_db)
        try:
            drop_role(legacy_role)
        except Exception:
            app.logger.exception("No se pudo eliminar el rol temporal %s", legacy_role)


def create_backup_archive(temp_dir):
    temp_dir = Path(temp_dir)
    archive = temp_dir / (
        "actas_microservices_"
        + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        + ".tar.gz"
    )
    manifest = {
        "format": "actas-microservices-backup-v2",
        "app_version": "3.1.0",
        "schema_version": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "databases": DATABASES,
    }
    for database in DATABASES:
        dump_path = temp_dir / f"{database}.dump"
        run([
            "pg_dump", "-h", PGHOST, "-p", PGPORT, "-U", PGUSER,
            "-Fc", "--no-owner", "--no-acl", "-f", str(dump_path), database,
        ])
    (temp_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(temp_dir / "manifest.json", arcname="manifest.json")
        for database in DATABASES:
            tar.add(temp_dir / f"{database}.dump", arcname=f"{database}.dump")
    return archive


def write_backup_status(**updates):
    BACKUP_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        if BACKUP_STATUS_FILE.exists():
            data = json.loads(BACKUP_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    data.update(updates)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    temp = BACKUP_STATUS_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(BACKUP_STATUS_FILE)
    return data


def read_backup_status():
    try:
        return json.loads(BACKUP_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def system_log(event_type, level="info", detail=None, actor_name=None, actor_user_id=None, actor_role="admin"):
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/api/system-logs",
            headers={"X-Internal-Key": INTERNAL_API_KEY, "X-User-Role": "admin"},
            json={
                "event_type": event_type, "level": level, "module": "backup",
                "actor_user_id": actor_user_id, "actor_name": actor_name,
                "actor_role": actor_role, "detail": detail or {},
            },
            timeout=10,
        )
    except requests.RequestException:
        app.logger.exception("No fue posible registrar el evento de respaldo")


def _google_client_config():
    if not GOOGLE_DRIVE_OAUTH_CONFIGURED:
        raise RuntimeError(
            "Google Drive API no está configurado. Defina GOOGLE_DRIVE_CLIENT_ID y GOOGLE_DRIVE_CLIENT_SECRET."
        )
    return {
        "web": {
            "client_id": GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": GOOGLE_DRIVE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _write_private_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_google_credentials(credentials):
    payload = json.loads(credentials.to_json())
    # Asegura que el archivo persistente conserve los datos necesarios para renovar el token.
    payload["client_id"] = GOOGLE_DRIVE_CLIENT_ID
    payload["client_secret"] = GOOGLE_DRIVE_CLIENT_SECRET
    payload["token_uri"] = "https://oauth2.googleapis.com/token"
    payload["scopes"] = [GOOGLE_DRIVE_SCOPE]
    _write_private_json(GOOGLE_DRIVE_TOKEN_FILE, payload)


def _load_google_credentials():
    if not GOOGLE_DRIVE_OAUTH_CONFIGURED:
        raise RuntimeError(
            "Google Drive API no está configurado. Defina GOOGLE_DRIVE_CLIENT_ID y GOOGLE_DRIVE_CLIENT_SECRET."
        )
    if not GOOGLE_DRIVE_TOKEN_FILE.exists():
        raise RuntimeError("Google Drive todavía no está conectado. Conecte la cuenta desde Administración > Respaldos.")
    try:
        credentials = Credentials.from_authorized_user_file(
            str(GOOGLE_DRIVE_TOKEN_FILE), [GOOGLE_DRIVE_SCOPE]
        )
    except Exception as exc:
        raise RuntimeError("Las credenciales guardadas de Google Drive no son válidas; vuelva a conectar la cuenta.") from exc
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(GoogleAuthRequest())
                _save_google_credentials(credentials)
            except Exception as exc:
                raise RuntimeError("No fue posible renovar el acceso a Google Drive; vuelva a conectar la cuenta.") from exc
        else:
            raise RuntimeError("Google Drive requiere volver a conectar la cuenta.")
    return credentials


def _google_drive_service():
    return google_build(
        "drive", "v3", credentials=_load_google_credentials(), cache_discovery=False
    )


def _safe_drive_folder_parts():
    parts = [part.strip() for part in GOOGLE_DRIVE_FOLDER_PATH.replace("\\", "/").split("/") if part.strip()]
    if not parts or any(part in {".", ".."} for part in parts):
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_PATH no es válido")
    return parts


def _drive_query_value(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _find_or_create_drive_folder(service, name, parent_id):
    safe_name = _drive_query_value(name)
    safe_parent = _drive_query_value(parent_id)
    query = (
        f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{safe_parent}' in parents and trashed = false"
    )
    response = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id,name)",
        pageSize=10,
    ).execute()
    items = response.get("files", [])
    if items:
        return items[0]["id"]
    created = service.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id,name",
    ).execute()
    return created["id"]


def _ensure_drive_backup_folder(service):
    parent_id = "root"
    for part in _safe_drive_folder_parts():
        parent_id = _find_or_create_drive_folder(service, part, parent_id)
    return parent_id


def _upload_to_drive(service, local_path, folder_id, mimetype):
    media = MediaFileUpload(
        str(local_path), mimetype=mimetype, resumable=True, chunksize=5 * 1024 * 1024
    )
    return service.files().create(
        body={"name": local_path.name, "parents": [folder_id]},
        media_body=media,
        fields="id,name,size,createdTime,webViewLink",
    ).execute()


def cleanup_old_google_drive_backups(service, folder_id):
    cutoff = datetime.now(timezone.utc).timestamp() - BACKUP_RETENTION_DAYS * 86400
    removed = 0
    page_token = None
    query = f"'{_drive_query_value(folder_id)}' in parents and trashed = false"
    while True:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken,files(id,name,createdTime)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        for item in response.get("files", []):
            name = item.get("name", "")
            if not (name.startswith("actas_microservices_") and (name.endswith(".tar.gz") or name.endswith(".tar.gz.sha256"))):
                continue
            try:
                created = datetime.fromisoformat(item.get("createdTime", "").replace("Z", "+00:00")).timestamp()
            except (TypeError, ValueError):
                continue
            if created < cutoff:
                service.files().delete(fileId=item["id"]).execute()
                removed += 1
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return removed


def google_drive_connected():
    return GOOGLE_DRIVE_OAUTH_CONFIGURED and GOOGLE_DRIVE_TOKEN_FILE.exists()


def google_drive_auth_url(redirect_uri):
    _google_client_config()
    state = secrets.token_urlsafe(32)
    # PKCE: el mismo code_verifier debe sobrevivir al viaje navegador -> Google -> callback.
    # Se persiste únicamente durante los 10 minutos de validez del intento OAuth.
    code_verifier = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc).timestamp() + 600
    _write_private_json(
        GOOGLE_DRIVE_OAUTH_STATE_FILE,
        {
            "state": state,
            "redirect_uri": redirect_uri,
            "expires_at": expires_at,
            "code_verifier": code_verifier,
        },
    )
    flow = Flow.from_client_config(
        _google_client_config(),
        scopes=[GOOGLE_DRIVE_SCOPE],
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = redirect_uri
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url


def finish_google_drive_oauth(code, state, redirect_uri):
    pending = _read_json(GOOGLE_DRIVE_OAUTH_STATE_FILE)
    if not pending:
        raise ValueError("La autorización de Google Drive expiró; inicie la conexión nuevamente.")
    if pending.get("state") != state or pending.get("redirect_uri") != redirect_uri:
        raise ValueError("La respuesta de Google Drive no coincide con la autorización iniciada.")
    if float(pending.get("expires_at") or 0) < datetime.now(timezone.utc).timestamp():
        GOOGLE_DRIVE_OAUTH_STATE_FILE.unlink(missing_ok=True)
        raise ValueError("La autorización de Google Drive expiró; inicie la conexión nuevamente.")
    code_verifier = str(pending.get("code_verifier") or "").strip()
    if not code_verifier:
        GOOGLE_DRIVE_OAUTH_STATE_FILE.unlink(missing_ok=True)
        raise ValueError(
            "La autorización de Google Drive fue iniciada con una versión anterior. Pulse Conectar mi Google Drive nuevamente."
        )
    flow = Flow.from_client_config(
        _google_client_config(),
        scopes=[GOOGLE_DRIVE_SCOPE],
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code)
    credentials = flow.credentials
    if not credentials.refresh_token and GOOGLE_DRIVE_TOKEN_FILE.exists():
        previous = _read_json(GOOGLE_DRIVE_TOKEN_FILE)
        if previous.get("refresh_token"):
            credentials.refresh_token = previous["refresh_token"]
    if not credentials.refresh_token:
        raise RuntimeError(
            "Google no entregó un token de renovación. Revocar el acceso previo a la aplicación y volver a conectar Google Drive."
        )
    _save_google_credentials(credentials)
    service = google_build("drive", "v3", credentials=credentials, cache_discovery=False)
    about = service.about().get(fields="user(displayName,emailAddress)").execute().get("user", {})
    folder_id = _ensure_drive_backup_folder(service)
    meta = {
        "email": about.get("emailAddress"),
        "display_name": about.get("displayName"),
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "folder_path": GOOGLE_DRIVE_FOLDER_PATH,
        "folder_id": folder_id,
    }
    _write_private_json(GOOGLE_DRIVE_META_FILE, meta)
    GOOGLE_DRIVE_OAUTH_STATE_FILE.unlink(missing_ok=True)
    system_log("GOOGLE_DRIVE_CONNECTED", detail={"email": meta.get("email"), "folder_path": GOOGLE_DRIVE_FOLDER_PATH})
    return meta


def disconnect_google_drive():
    token_data = _read_json(GOOGLE_DRIVE_TOKEN_FILE)
    token = token_data.get("refresh_token") or token_data.get("token")
    if token:
        try:
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
        except requests.RequestException:
            app.logger.warning("No se pudo revocar el token remoto de Google Drive; se eliminará la copia local del token")
    GOOGLE_DRIVE_TOKEN_FILE.unlink(missing_ok=True)
    GOOGLE_DRIVE_META_FILE.unlink(missing_ok=True)
    GOOGLE_DRIVE_OAUTH_STATE_FILE.unlink(missing_ok=True)
    system_log("GOOGLE_DRIVE_DISCONNECTED", detail={})


def store_backup_in_google_drive(actor_name="Respaldo automático", actor_user_id=None):
    if not GOOGLE_DRIVE_OAUTH_CONFIGURED:
        raise RuntimeError(
            "Google Drive API no está configurado. Defina GOOGLE_DRIVE_CLIENT_ID y GOOGLE_DRIVE_CLIENT_SECRET."
        )
    if not google_drive_connected():
        raise RuntimeError("Google Drive no está conectado. Conecte la cuenta desde Administración > Respaldos.")
    BACKUP_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with BACKUP_LOCK_FILE.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Ya existe una copia de seguridad en ejecución") from exc
        temp_dir = Path(tempfile.mkdtemp(prefix="actas_google_drive_api_"))
        write_backup_status(state="running", last_attempt=datetime.now(timezone.utc).isoformat(), error=None)
        try:
            archive = create_backup_archive(temp_dir)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            checksum = Path(str(archive) + ".sha256")
            checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
            service = _google_drive_service()
            folder_id = _ensure_drive_backup_folder(service)
            uploaded = _upload_to_drive(service, archive, folder_id, "application/gzip")
            checksum_uploaded = _upload_to_drive(service, checksum, folder_id, "text/plain")
            removed = cleanup_old_google_drive_backups(service, folder_id)
            meta = _read_json(GOOGLE_DRIVE_META_FILE)
            status = write_backup_status(
                state="success",
                last_success=datetime.now(timezone.utc).isoformat(),
                filename=archive.name,
                size_bytes=archive.stat().st_size,
                sha256=digest,
                target_dir=f"Google Drive / {GOOGLE_DRIVE_FOLDER_PATH}",
                drive_file_id=uploaded.get("id"),
                drive_web_view_link=uploaded.get("webViewLink"),
                checksum_file_id=checksum_uploaded.get("id"),
                account_email=meta.get("email"),
                retention_days=BACKUP_RETENTION_DAYS,
                removed_by_retention=removed,
                error=None,
            )
            system_log(
                "AUTO_BACKUP_SUCCESS" if actor_user_id is None else "GOOGLE_DRIVE_BACKUP_SUCCESS",
                detail={
                    "filename": archive.name,
                    "size_bytes": archive.stat().st_size,
                    "target_dir": f"Google Drive / {GOOGLE_DRIVE_FOLDER_PATH}",
                    "drive_file_id": uploaded.get("id"),
                    "sha256": digest,
                },
                actor_name=actor_name,
                actor_user_id=actor_user_id,
            )
            return status
        except Exception as exc:
            write_backup_status(
                state="error",
                error=str(exc)[:1000],
                last_failure=datetime.now(timezone.utc).isoformat(),
            )
            system_log(
                "AUTO_BACKUP_FAILED" if actor_user_id is None else "GOOGLE_DRIVE_BACKUP_FAILED",
                level="error",
                detail={"error": str(exc)[:1000], "target_dir": f"Google Drive / {GOOGLE_DRIVE_FOLDER_PATH}"},
                actor_name=actor_name,
                actor_user_id=actor_user_id,
            )
            raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


@app.get("/health")
def health():
    try:
        client_major = postgres_client_major()
        server_major = postgres_server_major()
        if client_major != server_major:
            return (
                jsonify(
                    status="error",
                    detail="Las versiones mayores de pg_restore y PostgreSQL no coinciden",
                    postgres_client_major=client_major,
                    postgres_server_major=server_major,
                ),
                503,
            )
        return jsonify(
            status="ok",
            postgres_client_major=client_major,
            postgres_server_major=server_major,
            accepted_backup_formats=[".tar.gz", ".sql"],
        )
    except Exception as exc:
        return jsonify(status="error", detail=str(exc)), 503


@app.get("/api/backups/export")
def export_backup():
    denied = require_admin()
    if denied:
        return denied
    temp_dir = Path(tempfile.mkdtemp(prefix="actas_backup_"))
    try:
        archive = create_backup_archive(temp_dir)

        @after_this_request
        def cleanup(response):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return response

        return send_file(archive, as_attachment=True, download_name=archive.name, mimetype="application/gzip", max_age=0)
    except subprocess.CalledProcessError as exc:
        app.logger.error("Fallo de pg_dump: %s", exc.stderr)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error="No fue posible generar el respaldo"), 500
    except Exception:
        app.logger.exception("Fallo inesperado al generar el respaldo")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error="No fue posible generar el respaldo"), 500


@app.get("/api/backups/status")
def backup_status():
    denied = require_admin()
    if denied:
        return denied
    meta = _read_json(GOOGLE_DRIVE_META_FILE)
    return jsonify(
        auto_enabled=AUTO_BACKUP_ENABLED,
        auto_time=AUTO_BACKUP_TIME,
        retention_days=BACKUP_RETENTION_DAYS,
        oauth_client_configured=GOOGLE_DRIVE_OAUTH_CONFIGURED,
        drive_configured=google_drive_connected(),
        drive_connected=google_drive_connected(),
        account_email=meta.get("email"),
        account_name=meta.get("display_name"),
        target_dir=(f"Google Drive / {GOOGLE_DRIVE_FOLDER_PATH}" if google_drive_connected() else None),
        folder_path=GOOGLE_DRIVE_FOLDER_PATH,
        status=read_backup_status(),
        scheduler=(json.loads(BACKUP_SCHEDULER_STATUS_FILE.read_text(encoding="utf-8")) if BACKUP_SCHEDULER_STATUS_FILE.exists() else {}),
    )


@app.post("/api/google-drive/auth-url")
def google_drive_oauth_url_endpoint():
    denied = require_admin()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    redirect_uri = str(data.get("redirect_uri") or "").strip()
    if not redirect_uri.startswith(("http://", "https://")):
        return jsonify(error="redirect_uri inválido"), 400
    try:
        return jsonify(auth_url=google_drive_auth_url(redirect_uri))
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 409
    except Exception as exc:
        app.logger.exception("No fue posible iniciar OAuth con Google Drive")
        return jsonify(error=f"No fue posible iniciar la conexión con Google Drive: {str(exc)[:300]}"), 500


@app.post("/api/google-drive/oauth-callback")
def google_drive_oauth_callback_endpoint():
    denied = require_admin()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or "").strip()
    state = str(data.get("state") or "").strip()
    redirect_uri = str(data.get("redirect_uri") or "").strip()
    if not code or not state or not redirect_uri:
        return jsonify(error="Respuesta OAuth incompleta"), 400
    try:
        return jsonify(ok=True, account=finish_google_drive_oauth(code, state, redirect_uri))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        app.logger.exception("No fue posible completar OAuth con Google Drive")
        return jsonify(error=f"No fue posible conectar Google Drive: {str(exc)[:300]}"), 500


@app.post("/api/google-drive/disconnect")
def google_drive_disconnect_endpoint():
    denied = require_admin()
    if denied:
        return denied
    disconnect_google_drive()
    return jsonify(ok=True)


@app.post("/api/backups/google-drive")
@app.post("/api/backups/onedrive")  # alias heredado
def backup_to_google_drive():
    denied = require_admin()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    actor_name = str(data.get("actor_name") or "Administrador").strip()[:200]
    actor_user_id = data.get("actor_user_id")
    try:
        actor_user_id = int(actor_user_id) if actor_user_id not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify(error="actor_user_id inválido"), 400
    try:
        return jsonify(
            ok=True,
            status=store_backup_in_google_drive(
                actor_name=actor_name, actor_user_id=actor_user_id
            ),
        )
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 409
    except Exception as exc:
        app.logger.exception("No fue posible subir el respaldo directamente a Google Drive")
        return jsonify(error=f"No fue posible subir el respaldo a Google Drive: {str(exc)[:300]}"), 500


@app.post("/api/backups/import")
def import_backup():
    denied = require_admin()
    if denied:
        return denied
    uploaded = request.files.get("backup")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Debe seleccionar un respaldo"), 400

    filename = Path(uploaded.filename).name.lower()
    is_sql = filename.endswith(".sql")
    is_archive = filename.endswith(".tar.gz") or filename.endswith(".tgz")
    if not is_sql and not is_archive:
        return jsonify(error="Solo se permiten respaldos .tar.gz o .sql"), 400

    temp_dir = Path(tempfile.mkdtemp(prefix="actas_restore_"))
    destination = temp_dir / ("upload.sql" if is_sql else "upload.tar.gz")
    try:
        try:
            save_upload(uploaded, destination)
        except ValueError as exc:
            status = 413 if "tamaño" in str(exc) else 400
            return jsonify(error=str(exc)), status

        if is_sql:
            try:
                result = import_legacy_sql(destination, temp_dir)
                return jsonify(result)
            except ValueError as exc:
                return jsonify(error=str(exc)), 400
            except subprocess.CalledProcessError as exc:
                app.logger.error("Comando de migración SQL fallido: %s", exc.stderr)
                return (
                    jsonify(
                        error="No fue posible importar el respaldo SQL anterior; se conservaron las bases actuales"
                    ),
                    500,
                )
            except Exception:
                app.logger.exception("Migración de respaldo SQL fallida")
                return (
                    jsonify(
                        error="La importación SQL falló y se conservaron las bases actuales"
                    ),
                    500,
                )

        try:
            result = restore_microservices_backup(destination, temp_dir)
            return jsonify(result)
        except OverflowError as exc:
            return jsonify(error=str(exc)), 413
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except subprocess.CalledProcessError as exc:
            app.logger.error("Comando de restauración fallido: %s", exc.stderr)
            return (
                jsonify(
                    error="La restauración falló y se conservaron las bases originales"
                ),
                500,
            )
        except Exception:
            app.logger.exception("Restauración fallida")
            return (
                jsonify(
                    error="La restauración falló y se conservaron las bases originales"
                ),
                500,
            )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
