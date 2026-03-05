
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

        # 1. Agregar columnas si no existen
        # Usamos una verificación segura.
        tables = ['actas', 'comisiones']
        for table in tables:
            logging.info(f"Verificando {table}...")
            # Verificar gestiones
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='gestiones'")
            if not cur.fetchone():
                logging.info(f"Agregando 'gestiones' a {table}")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN gestiones VARCHAR(255)")
            else:
                logging.info(f"'gestiones' ya existe en {table}")
            
            # Verificar productos_asociados
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='productos_asociados'")
            if not cur.fetchone():
                logging.info(f"Agregando 'productos_asociados' a {table}")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN productos_asociados VARCHAR(255)")
            else:
                logging.info(f"'productos_asociados' ya existe en {table}")

        # 2. Insertar nuevos catálogos
        # Podemos leer las partes relevantes del archivo SQL o incluirlas aquí. Incluir es más seguro para coincidir con la lógica.
        
        # Nuevas Categorías
        new_data = [
            # GESTION_ACTA
            ('GESTION_ACTA', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
            ('GESTION_ACTA', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
            ('GESTION_ACTA', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
            ('GESTION_ACTA', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
            ('GESTION_ACTA', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
            ('GESTION_ACTA', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
            ('GESTION_ACTA', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
            ('GESTION_ACTA', 'Otros', 'Otros', 999),

            # PRODUCTO_ACTA
            ('PRODUCTO_ACTA', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
            ('PRODUCTO_ACTA', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
            ('PRODUCTO_ACTA', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
            ('PRODUCTO_ACTA', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
            ('PRODUCTO_ACTA', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
            ('PRODUCTO_ACTA', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
            ('PRODUCTO_ACTA', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
            ('PRODUCTO_ACTA', 'Otros', 'Otros', 999),

            # GESTION_COMISION
            ('GESTION_COMISION', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
            ('GESTION_COMISION', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
            ('GESTION_COMISION', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
            ('GESTION_COMISION', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
            ('GESTION_COMISION', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
            ('GESTION_COMISION', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
            ('GESTION_COMISION', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
            ('GESTION_COMISION', 'Otros', 'Otros', 999),

            # PRODUCTO_COMISION
            ('PRODUCTO_COMISION', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
            ('PRODUCTO_COMISION', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
            ('PRODUCTO_COMISION', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
            ('PRODUCTO_COMISION', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
            ('PRODUCTO_COMISION', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
            ('PRODUCTO_COMISION', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
            ('PRODUCTO_COMISION', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
            ('PRODUCTO_COMISION', 'Otros', 'Otros', 999)
        ]

        logging.info("Verificando catálogos...")
        for cat, name, val, order in new_data:
            # Verificar si existe (por categoría y nombre)
            cur.execute("SELECT 1 FROM catalogos WHERE categoria=%s AND nombre=%s", (cat, name))
            if not cur.fetchone():
                cur.execute("INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES (%s, %s, %s, %s)", (cat, name, val, order))
        
        conn.commit()
        logging.info("Migración completada exitosamente.")

    except Exception as e:
        logging.error(f"Error en la migración: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    apply_migration()
