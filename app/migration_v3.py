
import os
import psycopg2
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

# Configuración de BD (Misma lógica que app.py)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    pg_host = os.getenv("POSTGRES_HOST", os.getenv("POSTGRES_HOSTNAME", "db"))
    pg_port = int(os.getenv("POSTGRES_PORT", "5432") or 5432)
    pg_db = os.getenv("POSTGRES_DB", "actas_db")
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
    DATABASE_URL = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

def apply_migration():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        logging.info("Conectado a la BD.")

        # Agregar columna nombre_alimentador a informes si no existe
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='informes' AND column_name='nombre_alimentador'")
        if not cur.fetchone():
            logging.info("Agregando 'nombre_alimentador' a informes")
            cur.execute("ALTER TABLE informes ADD COLUMN nombre_alimentador VARCHAR(255)")
        else:
            logging.info("'nombre_alimentador' ya existe en informes")

        conn.commit()
        logging.info("Migración completada exitosamente.")

    except Exception as e:
        logging.error(f"Error en la migración: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    apply_migration()
