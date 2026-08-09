import re
import uuid
import pytest
import requests
from playwright.sync_api import expect
from conftest import choose_first

pytestmark = pytest.mark.e2e


def test_any_answer_can_open_a_nested_form(admin_page, urls, admin_headers, run_id):
    suffix = uuid.uuid4().hex[:6]
    root_resp = requests.post(f"{urls['catalogs']}/api/form-sections", headers=admin_headers, json={"document_type":"actas","title":f"Sección disparadora {suffix}","section_order":950,"show_when":{}}, timeout=15)
    assert root_resp.status_code == 201, root_resp.text
    root = root_resp.json()
    field_resp = requests.post(f"{urls['catalogs']}/api/form-fields", headers=admin_headers, json={"document_type":"actas","section_id":root["id"],"label":f"¿Existe novedad? {suffix}","field_type":"text","field_order":1}, timeout=15)
    assert field_resp.status_code == 201, field_resp.text
    field = field_resp.json()
    nested_resp = requests.post(f"{urls['catalogs']}/api/form-sections", headers=admin_headers, json={"document_type":"actas","title":f"Detalles de novedad {suffix}","section_order":951,"show_when":{"field_key":f"custom:{field['field_key']}","operator":"not_empty","value":""}}, timeout=15)
    assert nested_resp.status_code == 201, nested_resp.text
    nested = nested_resp.json()
    detail_resp = requests.post(f"{urls['catalogs']}/api/form-fields", headers=admin_headers, json={"document_type":"actas","section_id":nested["id"],"label":f"Fecha de novedad {suffix}","field_type":"date","required":True,"field_order":1}, timeout=15)
    assert detail_resp.status_code == 201, detail_resp.text
    detail = detail_resp.json()

    page = admin_page
    page.goto(urls["web"] + "/crear/actas")
    trigger = page.locator(f"#custom_{field['field_key']}")
    nested_section = page.locator(f"[data-section-key='{nested['section_key']}']")
    expect(trigger).to_be_visible()
    expect(nested_section).to_be_hidden()
    trigger.fill("Sí existe una novedad")
    trigger.dispatch_event("input")
    expect(nested_section).to_be_visible()
    expect(page.locator(f"#custom_{detail['field_key']}")).to_be_visible()


def test_visual_editor_shows_current_options_and_edit_controls(admin_page, urls):
    page = admin_page
    page.goto(urls["web"] + "/admin/campos")
    expect(page.get_by_role("heading", name=re.compile("Constructor visual de formularios", re.I))).to_be_visible()
    expect(page.locator("#documentBuilderTabs")).to_be_visible()
    expect(page.locator("#documentBuilderTabs").get_by_text(re.compile("Informes|Actas", re.I)).first).to_be_visible()
    # La interfaz debe exponer acciones de agregar y no depender de editar valores internos manualmente.
    assert page.get_by_text(re.compile(r"Agregar|Nueva|\+", re.I)).count() > 0
    assert page.get_by_text("Valor interno", exact=True).count() == 0
