from conftest import load_service


gateway = load_service("web_gateway_app", "services/web_gateway/app.py")


def test_login_form_contains_csrf_and_security_headers():
    client = gateway.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_post_without_csrf_is_rejected_before_service_call():
    client = gateway.app.test_client()
    response = client.post("/login", data={"email": "x@example.com", "password": "invalid"})
    assert response.status_code == 400
