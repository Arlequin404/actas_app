from pathlib import Path
import pytest
from conftest import ROOT, load_service

gateway = load_service("web_gateway_unit", "services/web_gateway/app.py")
pytestmark = pytest.mark.unit


def test_login_has_csrf_and_security_headers():
    client = gateway.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert client.post("/login", data={"email":"x@test.local","password":"123456"}).status_code == 400


def test_dark_mode_is_synchronized_with_bootstrap_and_persisted():
    base = (ROOT / "services/web_gateway/templates/base.html").read_text(encoding="utf-8")
    css = (ROOT / "services/web_gateway/static/styles.css").read_text(encoding="utf-8")
    assert 'data-bs-theme' in base
    assert "localStorage.setItem('theme', 'dark')" in base
    for selector in (".form-control", ".form-select", ".modal-content", ".dropdown-menu", ".table"):
        assert selector in css
