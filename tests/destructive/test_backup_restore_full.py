import io
import time
import uuid

import pytest
import requests
from conftest import wait_url

pytestmark = pytest.mark.destructive


def test_backup_restore_recovers_catalogs_users_documents_dynamic_fields_and_notifications(urls, admin_headers, internal_key):
    suffix = uuid.uuid4().hex[:8]
    before_name = f"Empresa antes respaldo {suffix}"
    after_name = f"Empresa después respaldo {suffix}"

    before = requests.post(f"{urls['catalogs']}/api/catalogs", headers=admin_headers,
        json={"categoria":"EMPRESA","nombre":before_name,"orden":990}, timeout=20)
    assert before.status_code == 201, before.text

    backup = requests.get(f"{urls['backup']}/api/backups/export", headers=admin_headers, timeout=120)
    assert backup.status_code == 200, backup.text

    after = requests.post(f"{urls['catalogs']}/api/catalogs", headers=admin_headers,
        json={"categoria":"EMPRESA","nombre":after_name,"orden":991}, timeout=20)
    assert after.status_code == 201, after.text

    restored = requests.post(
        f"{urls['backup']}/api/backups/import", headers=admin_headers,
        files={"backup":("prueba-restauracion.tar.gz", io.BytesIO(backup.content), "application/gzip")}, timeout=240,
    )
    assert restored.status_code == 200, restored.text

    for key in ("auth","documents","catalogs","backup","notifications","web"):
        wait_url(f"{urls[key]}/health", timeout=180)

    items = requests.get(f"{urls['catalogs']}/api/catalogs/EMPRESA?include_inactive=1", headers=admin_headers, timeout=20).json()["items"]
    names = {item["nombre"] for item in items}
    assert before_name in names
    assert after_name not in names

    login = requests.post(
        f"{urls['auth']}/api/auth/login",
        headers={"X-Internal-Key":internal_key,"X-Client-IP":"post-restore"},
        json={"email":__import__('os').environ["ADMIN_EMAIL"],"password":__import__('os').environ["ADMIN_PASSWORD"]}, timeout=20,
    )
    assert login.status_code == 200, login.text

    fields = requests.get(f"{urls['catalogs']}/api/form-fields/informes?include_inactive=1", headers=admin_headers, timeout=20)
    assert fields.status_code == 200 and len(fields.json()["items"]) >= 5
    docs = requests.get(f"{urls['documents']}/api/documents/actas?per_page=all", headers=admin_headers, timeout=20)
    assert docs.status_code == 200 and docs.json()["total"] > 0
    notifications = requests.get(f"{urls['notifications']}/api/notifications", headers=admin_headers, timeout=20)
    assert notifications.status_code == 200 and notifications.json()["total"] > 0


def test_legacy_plain_sql_backup_is_migrated_to_microservices(urls, admin_headers, internal_key):
    legacy_sql = b"""--
-- PostgreSQL database dump
--
\\restrict legacytest
SET statement_timeout = 0;
SET transaction_timeout = 0;
CREATE TABLE public.usuarios (
  id integer, nombre varchar(120), email varchar(120), password varchar(255),
  rol varchar(20), created_at timestamp without time zone
);
CREATE TABLE public.catalogos (
  id integer, categoria varchar(50), nombre varchar(500), valor varchar(500),
  padre_id integer, activo boolean, orden integer, meta_data jsonb
);
CREATE TABLE public.actas (
  id integer, numero integer, anio integer, codigo varchar(50), id_usuario integer,
  empresa varchar(200), gestiones varchar(500), productos_asociados varchar(1000),
  asunto varchar(255), observaciones text, fecha date, hora time without time zone,
  created_at timestamp without time zone
);
CREATE TABLE public.informes (
  id integer, numero integer, anio integer, codigo varchar(50), id_usuario integer,
  empresa varchar(200), gestiones varchar(500), productos_asociados varchar(1000),
  asunto varchar(255), observaciones text, fecha date, hora time without time zone,
  created_at timestamp without time zone, tipo_informe varchar(300), caso_tipo varchar(60),
  nombre_alimentador varchar(200), alimentador_subestacion varchar(200),
  linea_subtransmision_nombre varchar(200), fecha_interrupcion date
);
CREATE TABLE public.reportes (
  id integer, numero integer, anio integer, codigo varchar(50), id_usuario integer,
  empresa varchar(200), gestiones varchar(500), productos_asociados varchar(1000),
  asunto varchar(255), observaciones text, fecha date, hora time without time zone,
  created_at timestamp without time zone, tipo_reporte varchar(300)
);
CREATE TABLE public.comisiones (
  id integer, numero integer, anio integer, codigo varchar(50), id_usuario integer,
  empresa varchar(200), gestiones varchar(500), productos_asociados varchar(1000),
  asunto varchar(255), observaciones text, fecha date, hora time without time zone,
  created_at timestamp without time zone
);
INSERT INTO public.usuarios VALUES
  (1,'Administrador anterior','legacy.admin@test.local','Legacy2026','admin','2026-08-03 08:00:00');
INSERT INTO public.catalogos VALUES
  (1,'EMPRESA','Empresa anterior','Empresa anterior',NULL,TRUE,1,NULL),
  (2,'GESTION_INFORME','Gestion informe','Gestion informe',NULL,TRUE,1,NULL),
  (3,'PRODUCTO_INFORME','Producto informe','Producto informe',NULL,TRUE,1,NULL),
  (4,'GESTION_REPORTE','Gestion reporte','Gestion reporte',NULL,TRUE,1,NULL),
  (5,'TIPO_REPORTE','Tipo reporte','Tipo reporte',NULL,TRUE,1,NULL),
  (6,'PRODUCTO_REPORTE','Producto reporte','Producto reporte',NULL,TRUE,1,NULL),
  (7,'TIPO_INFORME','Tipo informe','Tipo informe',NULL,TRUE,1,NULL),
  (8,'GESTION_ACTA','Gestion acta','Gestion acta',NULL,TRUE,1,NULL),
  (9,'PRODUCTO_ACTA','Producto acta','Producto acta',NULL,TRUE,1,NULL),
  (10,'GESTION_COMISION','Gestion comision','Gestion comision',NULL,TRUE,1,NULL),
  (11,'PRODUCTO_COMISION','Producto comision','Producto comision',NULL,TRUE,1,NULL);
INSERT INTO public.actas VALUES
  (1,1,2026,'ACTAS.DTCD.001.2026',1,'Empresa anterior','Gestion acta','Producto acta',
   'Acta recuperada desde SQL','Prueba de compatibilidad','2026-08-03','08:30:00','2026-08-03 08:30:00');
\\unrestrict legacytest
"""

    restored = requests.post(
        f"{urls['backup']}/api/backups/import",
        headers=admin_headers,
        files={"backup": ("respaldo_anterior.sql", io.BytesIO(legacy_sql), "application/sql")},
        timeout=240,
    )
    assert restored.status_code == 200, restored.text
    payload = restored.json()
    assert payload["format"] == "legacy-sql"
    assert payload["migrated"]["users"] == 1
    assert payload["migrated"]["documents"] == 1

    for key in ("auth", "documents", "catalogs", "backup", "notifications", "web"):
        wait_url(f"{urls[key]}/health", timeout=180)

    login = requests.post(
        f"{urls['auth']}/api/auth/login",
        headers={"X-Internal-Key": internal_key, "X-Client-IP": "legacy-restore"},
        json={"email": "legacy.admin@test.local", "password": "Legacy2026"},
        timeout=20,
    )
    assert login.status_code == 200, login.text
    legacy_admin = login.json()
    legacy_headers = {
        "X-Internal-Key": internal_key,
        "X-User-ID": str(legacy_admin["id"]),
        "X-User-Role": "admin",
    }

    documents = requests.get(
        f"{urls['documents']}/api/documents/actas?per_page=all",
        headers=legacy_headers,
        timeout=20,
    )
    assert documents.status_code == 200, documents.text
    assert documents.json()["total"] == 1
    assert documents.json()["items"][0]["subject"] == "Acta recuperada desde SQL"

    catalogs = requests.get(
        f"{urls['catalogs']}/api/catalogs/EMPRESA?include_inactive=1",
        headers=legacy_headers,
        timeout=20,
    )
    assert catalogs.status_code == 200, catalogs.text
    assert any(item["nombre"] == "Empresa anterior" for item in catalogs.json()["items"])
