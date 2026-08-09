from conftest import load_service


catalog = load_service("catalog_service_app", "services/catalog_service/app.py")


def test_build_tree_preserves_hierarchy_and_special_flag():
    rows = [
        {"id": 1, "nombre": "Raíz", "valor": "R", "padre_id": None, "meta_data": None},
        {"id": 2, "nombre": "Hijo", "valor": "H", "padre_id": 1, "meta_data": {"special": "CASO_FORTUITO"}},
    ]
    tree = catalog.build_tree(rows)
    assert tree[0]["value"] == "R"
    assert tree[0]["children"][0]["special"] == "CASO_FORTUITO"


def test_slugify_dynamic_field_key():
    assert catalog.slugify_field_key("Número de trámite") == "numero_de_tramite"


def test_dynamic_select_requires_options():
    try:
        catalog.normalize_form_field({
            "document_type": "actas",
            "label": "Estado",
            "field_type": "select",
            "options": [],
        })
    except ValueError as exc:
        assert "opción" in str(exc).lower()
    else:
        raise AssertionError("Se esperaba una validación por opciones vacías")


def test_new_dynamic_field_types_are_supported():
    for field_type in ("time", "tel", "url"):
        values = catalog.normalize_form_field({
            "document_type": "actas",
            "label": f"Campo {field_type}",
            "field_type": field_type,
        })
        assert values[3] == field_type


def test_checkbox_group_requires_options_and_supports_other():
    values = catalog.normalize_form_field({
        "document_type": "reportes",
        "label": "Áreas responsables",
        "field_type": "checkboxes",
        "options": ["Técnica", "Jurídica"],
        "allow_other": True,
    })
    assert values[3] == "checkboxes"
    assert values[9] == ["Técnica", "Jurídica"]
    assert values[10] is True


def test_parse_bool_handles_json_and_text_values():
    assert catalog.parse_bool(True) is True
    assert catalog.parse_bool("false") is False
    assert catalog.parse_bool("sí") is True
