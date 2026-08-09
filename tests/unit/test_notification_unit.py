from conftest import load_service
import pytest

notification = load_service("notification_service_unit", "services/notification_service/app.py")
pytestmark = pytest.mark.unit


def test_document_email_uses_html_template_and_escapes_user_content():
    subject, body = notification.template_for("document_created", {
        "document_label":"Informe", "code":"INF.DTCD.001.2026", "company":"<script>alert(1)</script>",
        "management":"Gestión", "associated_products":"Producto", "subject":"Asunto",
    })
    assert "INF.DTCD.001.2026" in body
    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert subject == "Documento registrado: INF.DTCD.001.2026"


def test_password_reset_secret_is_not_part_of_stored_context_contract():
    _, body = notification.template_for("password_reset", {"reset_link":"http://example/reset/token"})
    assert "http://example/reset/token" in body
