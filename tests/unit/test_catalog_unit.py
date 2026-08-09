import pytest
from conftest import load_service

catalog = load_service("catalog_service_unit", "services/catalog_service/app.py")
pytestmark = pytest.mark.unit


def test_tree_preserves_categories_and_special_behaviour():
    rows = [
        {"id":1,"nombre":"Informes de atención","valor":"ATENCION","padre_id":None,"meta_data":None},
        {"id":2,"nombre":"Caso fortuito","valor":"CASO","padre_id":1,"meta_data":{"special":"CASO_FORTUITO"}},
    ]
    tree = catalog.build_tree(rows)
    assert tree[0]["children"][0]["special"] == "CASO_FORTUITO"


def test_field_key_is_generated_and_stable():
    assert catalog.slugify_field_key("Número de trámite") == "numero_de_tramite"
    current = {"document_type":"actas","field_key":"numero_de_tramite","field_type":"text","section_id":None}
    values = catalog.normalize_form_field({"label":"Código de trámite","field_type":"text"}, current=current)
    assert values[2] == "numero_de_tramite"


def test_all_visual_builder_field_types_are_supported():
    simple = ("text","textarea","number","date","datetime","time","email","tel","url","checkbox","yesno")
    for field_type in simple:
        values = catalog.normalize_form_field({"document_type":"actas","label":field_type,"field_type":field_type})
        assert values[4] == field_type
    for field_type in ("select","radio","multiselect","checkboxes"):
        values = catalog.normalize_form_field({"document_type":"informes","label":field_type,"field_type":field_type,"options":["A","B"],"allow_other":True})
        assert values[10] == ["A","B"] and values[11] is True


def test_subform_conditions_support_specific_answer_contains_and_any_answer():
    assert catalog.normalize_show_when({"field_key":"tipo_informe","operator":"equals","value":"Caso fortuito"})["operator"] == "equals"
    assert catalog.normalize_show_when({"field_key":"custom:areas","operator":"contains","value":"Técnica"})["operator"] == "contains"
    assert catalog.normalize_show_when({"field_key":"custom:novedad","operator":"not_empty","value":""}) == {"field_key":"custom:novedad","operator":"not_empty","value":""}


def test_options_are_deduplicated_and_required_for_choice_fields():
    assert catalog.normalize_options(["A","A"," B "]) == ["A","B"]
    with pytest.raises(ValueError, match="opción"):
        catalog.normalize_form_field({"document_type":"reportes","label":"Estado","field_type":"select","options":[]})
