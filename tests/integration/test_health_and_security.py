import pytest
import requests

pytestmark = pytest.mark.integration


def test_every_service_and_gateway_is_healthy(urls):
    for name in ("auth","documents","catalogs","backup","notifications"):
        response = requests.get(f"{urls[name]}/health", timeout=15)
        assert response.status_code == 200, f"{name}: {response.text}"
        payload = response.json()
        assert payload["status"] == "ok"
        if name == "backup":
            assert payload["postgres_client_major"] == payload["postgres_server_major"] == 16
    gateway = requests.get(f"{urls['web']}/health", timeout=20)
    assert gateway.status_code == 200, gateway.text
    assert all(gateway.json()["services"].values())


def test_internal_apis_reject_missing_key_and_admin_operations_reject_user_role(urls, internal_key, normal_headers):
    assert requests.get(f"{urls['auth']}/api/users", timeout=10).status_code == 401
    assert requests.get(f"{urls['catalogs']}/api/catalogs/EMPRESA", timeout=10).status_code == 401
    assert requests.get(f"{urls['documents']}/api/documents/actas", timeout=10).status_code == 401
    assert requests.get(f"{urls['backup']}/api/backups/export", headers=normal_headers, timeout=10).status_code == 403
    assert requests.post(f"{urls['auth']}/api/users", headers=normal_headers, json={}, timeout=10).status_code == 403


def test_gateway_csrf_and_role_boundaries(urls, normal_user):
    session = requests.Session()
    page = session.get(f"{urls['web']}/", timeout=15)
    assert page.status_code == 200 and 'name="csrf_token"' in page.text
    assert session.post(f"{urls['web']}/login", data={"email":normal_user["email"],"password":normal_user["password"]}, timeout=15).status_code == 400
