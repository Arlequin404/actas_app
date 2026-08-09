import argparse
import os
import sys
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from werkzeug.security import generate_password_hash

PREFIXES = {
    "actas": "ACTAS.DTCD",
    "informes": "INF.DTCD",
    "reportes": "REP.DTCD",
    "comisiones": "CMS.DTCD",
}


def password_hash(value: str) -> str:
    value = value or ""
    if value.startswith(("scrypt:", "pbkdf2:")):
        return value
    return generate_password_hash(value)


def connect(url):
    return psycopg2.connect(url)


def migrate_users(old, auth):
    with old.cursor(cursor_factory=RealDictCursor) as src, auth.cursor() as dst:
        src.execute("SELECT id,nombre,email,password,rol,created_at FROM usuarios ORDER BY id")
        users = src.fetchall()
        if not any(user.get("rol") == "admin" for user in users):
            raise RuntimeError("La base de datos de origen no contiene al menos un usuario administrador")
        dst.execute("TRUNCATE usuarios RESTART IDENTITY CASCADE")
        for user in users:
            dst.execute(
                """
                INSERT INTO usuarios(id,nombre,email,password_hash,rol,activo,session_version,created_at,updated_at)
                VALUES(%s,%s,%s,%s,%s,TRUE,1,%s,%s)
                """,
                (
                    user["id"], user["nombre"], user["email"].lower(),
                    password_hash(user["password"]),
                    user["rol"] if user["rol"] in {"usuario", "admin"} else "usuario",
                    user["created_at"], user["created_at"],
                ),
            )
        dst.execute("SELECT setval(pg_get_serial_sequence('usuarios','id'), COALESCE((SELECT MAX(id) FROM usuarios),1), TRUE)")
    auth.commit()
    return len(users)


def migrate_catalogs(old, catalogs):
    with old.cursor(cursor_factory=RealDictCursor) as src:
        src.execute("SELECT id,categoria,nombre,valor,padre_id,activo,orden,meta_data FROM catalogos ORDER BY id")
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
                    key = (row["categoria"], mapped_parent or 0, row["nombre"].strip().casefold())
                    if key in unique_keys:
                        id_map[item_id] = unique_keys[key]
                        skipped_duplicates += 1
                    else:
                        dst.execute(
                            """
                            INSERT INTO catalogos(id,categoria,nombre,valor,padre_id,activo,orden,meta_data)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (row["id"], row["categoria"], row["nombre"], row["valor"], mapped_parent, row["activo"], row["orden"], Json(row["meta_data"]) if row["meta_data"] is not None else None),
                        )
                        id_map[item_id] = row["id"]
                        unique_keys[key] = row["id"]
                        inserted += 1
                    del pending[item_id]
                    progress = True
            if not progress:
                raise RuntimeError("No se pudo reconstruir la jerarquía de catálogos: hay padres inexistentes o ciclos")
        dst.execute("SELECT setval(pg_get_serial_sequence('catalogos','id'), COALESCE((SELECT MAX(id) FROM catalogos),1), TRUE)")
    catalogs.commit()
    return inserted, skipped_duplicates


def source_rows(old, table):
    common = "id,numero,anio,id_usuario,empresa,gestiones,productos_asociados,asunto,observaciones,fecha,hora,created_at"
    if table == "informes":
        fields = common + ",tipo_informe,caso_tipo,nombre_alimentador,alimentador_subestacion,linea_subtransmision_nombre,fecha_interrupcion"
    elif table == "reportes":
        fields = common + ",tipo_reporte"
    else:
        fields = common
    with old.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT {fields} FROM {table} ORDER BY anio,numero,id")
        return cur.fetchall()


def migrate_documents(old, documents):
    total = 0
    counters = defaultdict(int)
    with documents.cursor() as dst:
        dst.execute("TRUNCATE documents,document_counters RESTART IDENTITY CASCADE")
        for table in ("actas", "informes", "reportes", "comisiones"):
            for row in source_rows(old, table):
                subtype = row.get("tipo_informe") if table == "informes" else row.get("tipo_reporte") if table == "reportes" else None
                code = f"{PREFIXES[table]}.{row['numero']:03d}.{row['anio']}"
                dst.execute(
                    """
                    INSERT INTO documents(
                      document_type,number,year,code,user_id,company,management,associated_products,
                      subtype,subject,observations,case_type,feeder_name,substation,subtransmission_line,
                      interruption_date,document_date,document_time,created_at,updated_at,legacy_table,legacy_id
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        table, row["numero"], row["anio"], code, row["id_usuario"],
                        row["empresa"] or "No especificado",
                        row["gestiones"] or "No especificado",
                        row["productos_asociados"] or "No especificado",
                        subtype, row["asunto"], row["observaciones"], row.get("caso_tipo"),
                        row.get("nombre_alimentador"), row.get("alimentador_subestacion"),
                        row.get("linea_subtransmision_nombre"), row.get("fecha_interrupcion"),
                        row["fecha"], row["hora"], row["created_at"], row["created_at"], table, row["id"],
                    ),
                )
                counters[(table, row["anio"])] = max(counters[(table, row["anio"])], row["numero"] + 1)
                total += 1
        for (table, year), next_number in counters.items():
            dst.execute(
                "INSERT INTO document_counters(document_type,year,next_number) VALUES(%s,%s,%s)",
                (table, year, next_number),
            )
    documents.commit()
    return total


def main():
    parser = argparse.ArgumentParser(description="Migra la base monolítica a las tres bases de microservicios")
    parser.add_argument("--old", default=os.getenv("OLD_DATABASE_URL"), help="URL de la base monolítica")
    parser.add_argument("--auth", default=os.getenv("AUTH_DATABASE_URL"), help="URL de auth_db")
    parser.add_argument("--documents", default=os.getenv("DOCUMENT_DATABASE_URL"), help="URL de documents_db")
    parser.add_argument("--catalogs", default=os.getenv("CATALOG_DATABASE_URL"), help="URL de catalog_db")
    parser.add_argument("--confirm", action="store_true", help="Confirma que los destinos pueden vaciarse")
    args = parser.parse_args()
    if not all((args.old, args.auth, args.documents, args.catalogs)):
        parser.error("Debe proporcionar las cuatro URL de conexión")
    if not args.confirm:
        parser.error("La migración reemplaza los datos destino. Ejecute con --confirm")

    old = connect(args.old)
    auth = connect(args.auth)
    docs = connect(args.documents)
    cats = connect(args.catalogs)
    try:
        user_count = migrate_users(old, auth)
        catalog_count, duplicate_catalogs = migrate_catalogs(old, cats)
        document_count = migrate_documents(old, docs)
    except Exception:
        auth.rollback(); docs.rollback(); cats.rollback()
        raise
    finally:
        old.close(); auth.close(); docs.close(); cats.close()
    print(
        f"Migración completada: {user_count} usuarios, {catalog_count} catálogos "
        f"({duplicate_catalogs} duplicados omitidos) y {document_count} documentos."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
