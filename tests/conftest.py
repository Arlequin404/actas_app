import importlib.util
import io
import os
import time
import uuid
from pathlib import Path

import psycopg2
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
for key, value in {
    "DATABASE_URL": "postgresql://unused:unused@localhost/unused",
    "INTERNAL_API_KEY": "a" * 64,
    "SECRET_KEY": "b" * 64,
    "ADMIN_PASSWORD": "Admin123",
    "PGPASSWORD": "unused",
    "MIN_PASSWORD_LENGTH": "6",
    "EMAIL_NOTIFICATIONS_ENABLED": "false",
}.items():
    os.environ.setdefault(key, value)


def load_service(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def wait_url(url, timeout=180):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                return response
            last = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.RequestException as exc:
            last = str(exc)
        time.sleep(2)
    raise AssertionError(f"Servicio no disponible: {url}. Último error: {last}")


@pytest.fixture(scope="session")
def urls():
    return {
        "web": os.getenv("BASE_URL", "http://web-gateway:8000"),
        "auth": os.getenv("AUTH_URL", "http://auth-service:8000"),
        "documents": os.getenv("DOCUMENT_URL", "http://document-service:8000"),
        "catalogs": os.getenv("CATALOG_URL", "http://catalog-service:8000"),
        "backup": os.getenv("BACKUP_URL", "http://backup-service:8000"),
        "notifications": os.getenv("NOTIFICATION_URL", "http://notification-service:8000"),
        "mailpit": os.getenv("MAILPIT_URL", "http://mailpit:8025"),
    }


@pytest.fixture(scope="session", autouse=True)
def stack_ready(request, urls):
    if "integration" not in str(request.config.invocation_params.args) and "e2e" not in str(request.config.invocation_params.args) and "destructive" not in str(request.config.invocation_params.args):
        return
    for key in ("auth", "documents", "catalogs", "backup", "notifications", "web"):
        wait_url(f"{urls[key]}/health")
    wait_url(f"{urls['mailpit']}/api/v1/info")


@pytest.fixture(scope="session")
def run_id():
    return uuid.uuid4().hex[:10]


@pytest.fixture(scope="session")
def internal_key():
    return os.environ["INTERNAL_API_KEY"]


@pytest.fixture(scope="session")
def admin_user(urls, internal_key):
    response = requests.post(
        f"{urls['auth']}/api/auth/login",
        headers={"X-Internal-Key": internal_key, "X-Client-IP": "test-admin"},
        json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]},
        timeout=20,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def admin_headers(internal_key, admin_user):
    return {
        "X-Internal-Key": internal_key,
        "X-User-ID": str(admin_user["id"]),
        "X-User-Role": "admin",
    }


@pytest.fixture(scope="session")
def create_user(urls, admin_headers, run_id):
    created = []
    def _create(prefix="usuario", role="usuario", password="Usuario2026"):
        email = f"{prefix}.{uuid.uuid4().hex[:8]}@test.local"
        response = requests.post(
            f"{urls['auth']}/api/users", headers=admin_headers,
            json={"nombre": f"{prefix.title()} {run_id}", "email": email, "password": password, "rol": role}, timeout=20,
        )
        assert response.status_code == 201, response.text
        item = response.json(); item["password"] = password
        created.append(item)
        return item
    return _create


@pytest.fixture(scope="session")
def normal_user(create_user):
    return create_user("funcionario", "usuario")


@pytest.fixture(scope="session")
def normal_headers(internal_key, normal_user):
    return {"X-Internal-Key": internal_key, "X-User-ID": str(normal_user["id"]), "X-User-Role": "usuario"}


@pytest.fixture
def base_document_payload(run_id):
    return {
        "empresa": f"Empresa pruebas {run_id}",
        "gestiones": "Gestión automatizada",
        "productos_asociados": "Producto automatizado",
        "asunto": f"Prueba automática {uuid.uuid4().hex[:8]}",
        "observaciones": "Documento generado por la suite completa de pruebas.",
        "custom_fields": {},
        "form_definition_snapshot": [],
    }


def db_connect(env_name):
    return psycopg2.connect(os.environ[env_name])


@pytest.fixture
def auth_db():
    db = db_connect("AUTH_DATABASE_URL")
    try: yield db
    finally: db.close()


@pytest.fixture
def document_db():
    db = db_connect("DOCUMENT_DATABASE_URL")
    try: yield db
    finally: db.close()


@pytest.fixture
def catalog_db():
    db = db_connect("CATALOG_DATABASE_URL")
    try: yield db
    finally: db.close()


@pytest.fixture
def notification_db():
    db = db_connect("NOTIFICATION_DATABASE_URL")
    try: yield db
    finally: db.close()


def mailpit_messages(urls):
    response = requests.get(f"{urls['mailpit']}/api/v1/messages", timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload.get("messages", payload.get("Messages", []))


def wait_for_mail(urls, recipient, subject_contains=None, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for message in mailpit_messages(urls):
            to_values = message.get("To") or message.get("to") or []
            joined = str(to_values)
            subject = message.get("Subject") or message.get("subject") or ""
            if recipient.lower() in joined.lower() and (not subject_contains or subject_contains.lower() in subject.lower()):
                return message
        time.sleep(1)
    raise AssertionError(f"No llegó correo para {recipient} con asunto {subject_contains!r}")


def choose_first(select_locator):
    options = select_locator.locator("option")
    for index in range(options.count()):
        value = options.nth(index).get_attribute("value") or ""
        if value:
            select_locator.select_option(index=index)
            return value
    raise AssertionError("No hay opciones seleccionables")
