import re
import uuid
import pytest
import requests
from playwright.sync_api import expect
from conftest import choose_first

pytestmark = pytest.mark.e2e


def fill_acta_base(page, subject):
    choose_first(page.locator("#empresa"))
    choose_first(page.locator("#gestiones"))
    choose_first(page.locator("#productos_asociados"))
    page.locator("#asunto").fill(subject)
    page.locator("#observaciones").fill("Prueba completa desde navegador")


def test_create_and_edit_document_use_same_form(admin_page, urls, admin_headers, run_id):
    page = admin_page
    subject = f"Acta UI {run_id} {uuid.uuid4().hex[:5]}"
    page.goto(urls["web"] + "/crear/actas")
    fill_acta_base(page, subject)
    page.get_by_role("button", name=re.compile("Guardar documento", re.I)).click()
    expect(page).to_have_url(re.compile(r"/admin/documentos"))
    expect(page.get_by_text(re.compile("creado correctamente"))).to_be_visible()
    data = requests.get(f"{urls['documents']}/api/documents/actas?per_page=all", headers=admin_headers, timeout=20).json()["items"]
    item = next(x for x in data if x["subject"] == subject)
    page.goto(f"{urls['web']}/admin/editar/actas/{item['id']}")
    expect(page.locator("#asunto")).to_have_value(subject)
    new_subject = subject + " editada"
    page.locator("#asunto").fill(new_subject)
    page.get_by_role("button", name=re.compile("Actualizar documento", re.I)).click()
    expect(page.get_by_text("Documento actualizado correctamente.")).to_be_visible()
    updated = requests.get(f"{urls['documents']}/api/documents/actas/{item['id']}", headers=admin_headers, timeout=15).json()
    assert updated["subject"] == new_subject


def test_company_other_displays_manual_text_field(admin_page, urls):
    page = admin_page
    page.goto(urls["web"] + "/crear/actas")
    company = page.locator("#empresa")
    labels = company.locator("option").all_text_contents()
    assert any(x.strip().lower() == "otros" for x in labels), labels
    company.select_option(label="Otros")
    expect(page.locator("#empresa_otro_div")).to_be_visible()
    expect(page.locator("#empresa_otro")).to_be_editable()


def test_normal_user_sees_documents_created_by_other_users(normal_page, urls, admin_headers, run_id, base_document_payload):
    subject = f"Documento global visible {run_id} {uuid.uuid4().hex[:5]}"
    response = requests.post(
        f"{urls['documents']}/api/documents/actas",
        headers=admin_headers,
        json={**base_document_payload, "asunto": subject},
        timeout=20,
    )
    assert response.status_code == 201, response.text
    page = normal_page
    page.goto(urls["web"] + "/mis_documentos?tab=actas&per_page=all")
    expect(page.get_by_text(subject, exact=True)).to_be_visible()
    row = page.locator("tr", has_text=subject)
    expect(row.get_by_text("Solo lectura", exact=True)).to_be_visible()


def test_admin_can_edit_document_created_by_normal_user(admin_page, urls, normal_headers, run_id, base_document_payload):
    subject = f"Documento de usuario editable por admin {run_id} {uuid.uuid4().hex[:5]}"
    response = requests.post(
        f"{urls['documents']}/api/documents/actas",
        headers=normal_headers,
        json={**base_document_payload, "asunto": subject},
        timeout=20,
    )
    assert response.status_code == 201, response.text
    item = response.json()

    page = admin_page
    page.goto(urls["web"] + "/mis_documentos?tab=actas&per_page=all")
    row = page.locator("tr", has_text=subject)
    expect(row).to_be_visible()
    expect(row.get_by_role("link", name=re.compile("Editar", re.I))).to_be_visible()
    expect(row.get_by_text("Solo lectura", exact=True)).to_have_count(0)

    page.goto(f"{urls['web']}/admin/editar/actas/{item['id']}")
    expect(page.locator("#asunto")).to_have_value(subject)
    updated_subject = subject + " actualizado por admin"
    page.locator("#asunto").fill(updated_subject)
    page.get_by_role("button", name=re.compile("Actualizar documento", re.I)).click()
    expect(page.get_by_text("Documento actualizado correctamente.")).to_be_visible()
