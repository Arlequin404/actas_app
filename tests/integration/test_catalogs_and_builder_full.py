import uuid
import pytest
import requests

pytestmark = pytest.mark.integration


def test_all_seed_catalogs_exist_and_company_other_is_configured(urls, admin_headers):
    categories = ["EMPRESA","GESTION_INFORME","PRODUCTO_INFORME","GESTION_REPORTE","TIPO_REPORTE","PRODUCTO_REPORTE","TIPO_INFORME","GESTION_ACTA","PRODUCTO_ACTA","GESTION_COMISION","PRODUCTO_COMISION"]
    for category in categories:
        response = requests.get(f"{urls['catalogs']}/api/catalogs/{category}?include_inactive=1", headers=admin_headers, timeout=15)
        assert response.status_code == 200, f"{category}: {response.text}"
        assert isinstance(response.json()["items"], list) and response.json()["items"], category
    setting = requests.get(f"{urls['catalogs']}/api/settings/company_other", headers=admin_headers, timeout=15)
    assert setting.status_code == 200
    assert setting.json()["setting_value"]["enabled"] is True


def test_catalog_create_edit_hide_restore_and_purge(urls, admin_headers, run_id):
    name = f"Empresa CRUD {run_id}"
    created = requests.post(f"{urls['catalogs']}/api/catalogs", headers=admin_headers, json={"categoria":"EMPRESA","nombre":name,"orden":999,"meta_data":None}, timeout=15)
    assert created.status_code == 201, created.text
    item = created.json(); original_value = item["valor"]
    edited = requests.put(f"{urls['catalogs']}/api/catalogs/{item['id']}", headers=admin_headers, json={"nombre":name+" editada","orden":998,"activo":True}, timeout=15)
    assert edited.status_code == 200
    assert edited.json()["nombre"].endswith("editada") and edited.json()["valor"] == original_value
    hidden = requests.delete(f"{urls['catalogs']}/api/catalogs/{item['id']}", headers=admin_headers, timeout=15)
    assert hidden.status_code == 200 and hidden.json()["activo"] is False
    restored = requests.put(f"{urls['catalogs']}/api/catalogs/{item['id']}", headers=admin_headers, json={"nombre":name+" editada","activo":True,"orden":998}, timeout=15)
    assert restored.status_code == 200 and restored.json()["activo"] is True
    purged = requests.delete(f"{urls['catalogs']}/api/catalogs/{item['id']}/purge", headers=admin_headers, timeout=15)
    assert purged.status_code == 200, purged.text


def test_hierarchical_report_types_and_tree(urls, admin_headers, run_id):
    parent = requests.post(f"{urls['catalogs']}/api/catalogs", headers=admin_headers, json={"categoria":"TIPO_INFORME","nombre":f"Categoría {run_id}","orden":900}, timeout=15).json()
    child_resp = requests.post(f"{urls['catalogs']}/api/catalogs", headers=admin_headers, json={"categoria":"TIPO_INFORME","nombre":f"Respuesta {run_id}","padre_id":parent["id"],"meta_data":{"special":"CASO_FORTUITO"},"orden":1}, timeout=15)
    assert child_resp.status_code == 201, child_resp.text
    tree = requests.get(f"{urls['catalogs']}/api/catalogs/TIPO_INFORME/tree", headers=admin_headers, timeout=15).json()["items"]
    node = next(x for x in tree if x["id"] == parent["id"])
    assert node["children"][0]["special"] == "CASO_FORTUITO"


def test_visual_builder_sections_fields_subforms_clone_and_delete(urls, admin_headers, run_id):
    root = requests.post(f"{urls['catalogs']}/api/form-sections", headers=admin_headers, json={"document_type":"informes","title":f"Sección {run_id}","description":"Creada por pruebas","section_order":800,"show_when":{}}, timeout=15)
    assert root.status_code == 201, root.text
    root_item = root.json()
    field = requests.post(f"{urls['catalogs']}/api/form-fields", headers=admin_headers, json={"document_type":"informes","section_id":root_item["id"],"label":f"Tipo de atención {run_id}","field_type":"radio","options":["Normal","Especial"],"allow_other":True,"required":True,"field_order":1}, timeout=15)
    assert field.status_code == 201, field.text
    field_item = field.json()
    sub = requests.post(f"{urls['catalogs']}/api/form-sections", headers=admin_headers, json={"document_type":"informes","title":f"Detalle especial {run_id}","section_order":801,"show_when":{"field_key":f"custom:{field_item['field_key']}","operator":"equals","value":"Especial"}}, timeout=15)
    assert sub.status_code == 201, sub.text
    sub_item = sub.json()
    detail = requests.post(f"{urls['catalogs']}/api/form-fields", headers=admin_headers, json={"document_type":"informes","section_id":sub_item["id"],"label":"Fecha del detalle","field_type":"date","required":True}, timeout=15)
    assert detail.status_code == 201
    listed = requests.get(f"{urls['catalogs']}/api/form-sections/informes?include_inactive=1", headers=admin_headers, timeout=15).json()["items"]
    assert any(x["id"] == sub_item["id"] and x["show_when"]["value"] == "Especial" for x in listed)
    cloned = requests.post(f"{urls['catalogs']}/api/form-sections/{root_item['id']}/clone", headers=admin_headers, json={"targets":["reportes"]}, timeout=20)
    assert cloned.status_code == 200, cloned.text
    purge_without_cascade = requests.delete(f"{urls['catalogs']}/api/form-fields/{field_item['id']}/purge", headers=admin_headers, timeout=15)
    assert purge_without_cascade.status_code == 409 and purge_without_cascade.json()["requires_cascade"] is True
    purge = requests.delete(f"{urls['catalogs']}/api/form-fields/{field_item['id']}/purge?cascade=1", headers=admin_headers, timeout=20)
    assert purge.status_code == 200 and purge.json()["historical_data_preserved"] is True


def test_shortcut_crud(urls, admin_headers, run_id):
    created = requests.post(f"{urls['catalogs']}/api/form-shortcuts", headers=admin_headers, json={"label":f"Acceso {run_id}","description":"Prueba","document_type":"actas","preset_values":{"empresa":"Empresa X"},"shortcut_order":999}, timeout=15)
    assert created.status_code == 201, created.text
    item = created.json()
    updated = requests.put(f"{urls['catalogs']}/api/form-shortcuts/{item['id']}", headers=admin_headers, json={"label":f"Acceso editado {run_id}","description":"Editado","document_type":"actas","preset_values":{"empresa":"Empresa Y"},"active":True,"shortcut_order":998}, timeout=15)
    assert updated.status_code == 200 and updated.json()["preset_values"]["empresa"] == "Empresa Y"
    archived = requests.delete(f"{urls['catalogs']}/api/form-shortcuts/{item['id']}", headers=admin_headers, timeout=15)
    assert archived.status_code == 200 and archived.json()["active"] is False


def test_bulk_catalog_reorder_and_company_other_settings(urls, admin_headers, run_id):
    names = [f"Gestión lote {run_id} A", f"Gestión lote {run_id} B"]
    bulk = requests.post(f"{urls['catalogs']}/api/catalogs/bulk", headers=admin_headers,
        json={"categoria":"GESTION_ACTA","items":names,"orden_inicial":970,"incremento":10}, timeout=20)
    assert bulk.status_code == 201, bulk.text
    assert bulk.json()["created_count"] == 2
    ids = [item["id"] for item in bulk.json()["created"]]
    reorder = requests.post(f"{urls['catalogs']}/api/catalogs/reorder", headers=admin_headers,
        json={"categoria":"GESTION_ACTA","ids":list(reversed(ids))}, timeout=15)
    assert reorder.status_code == 200
    setting = requests.put(f"{urls['catalogs']}/api/settings/company_other", headers=admin_headers,
        json={"enabled":True,"label":"Otra empresa","prompt":"Escriba la empresa"}, timeout=15)
    assert setting.status_code == 200
    assert setting.json()["setting_value"] == {"enabled":True,"label":"Otra empresa","prompt":"Escriba la empresa"}
    # Se restaura la etiqueta esperada por las demás pruebas de interfaz.
    requests.put(f"{urls['catalogs']}/api/settings/company_other", headers=admin_headers,
        json={"enabled":True,"label":"Otros","prompt":"Especifique la empresa"}, timeout=15)
