import pytest
from conftest import load_service

doc = load_service("document_service_unit", "services/document_service/app.py")
pytestmark = pytest.mark.unit


def test_codes_use_original_format_and_independent_prefixes():
    assert doc.code_for("informes", 2026, 7) == "INF.DTCD.007.2026"
    assert doc.code_for("actas", 2027, 1) == "ACTAS.DTCD.001.2027"
    assert doc.code_for("reportes", 2026, 2) == "REP.DTCD.002.2026"
    assert doc.code_for("comisiones", 2026, 3) == "CMS.DTCD.003.2026"


def test_payload_validation_for_every_document_type():
    base = {"empresa":"Empresa","gestiones":"Gestión","productos_asociados":"Producto","asunto":"Asunto"}
    assert doc.validate_payload("actas", base)["subtype"] is None
    assert doc.validate_payload("comisiones", base)["subtype"] is None
    assert doc.validate_payload("reportes", {**base,"tipo_reporte":"Seguimiento"})["subtype"] == "Seguimiento"
    assert doc.validate_payload("informes", {**base,"tipo_informe":"Técnico"})["subtype"] == "Técnico"


def test_case_fortuito_legacy_fields_are_validated_when_present():
    base = {"empresa":"Empresa","gestiones":"Gestión","productos_asociados":"Producto","asunto":"Asunto","tipo_informe":"Informe de caso fortuito"}
    result = doc.validate_payload("informes", {**base,"caso_tipo":"ALIMENTADOR","fecha_interrupcion":"2026-08-01","nombre_alimentador":"A-01","alimentador_subestacion":"SE Norte"})
    assert result["case_type"] == "ALIMENTADOR"
    with pytest.raises(ValueError, match="fecha"):
        doc.validate_payload("informes", {**base,"fecha_interrupcion":"01/08/2026"})


def test_custom_jsonb_fields_support_all_expected_value_shapes():
    result = doc.validate_custom_fields({"texto":"Dato","numero":4.5,"booleano":True,"lista":["A","B"],"vacio":None})
    assert result == {"texto":"Dato","numero":4.5,"booleano":True,"lista":["A","B"],"vacio":""}
    with pytest.raises(ValueError, match="clave"):
        doc.validate_custom_fields({"clave inválida":"x"})


def test_excel_formula_injection_is_neutralized():
    for value in ("=SUM(1,1)", "+1+1", "-2+3", "@CMD"):
        assert doc.excel_safe(value).startswith("'")
    assert doc.excel_safe("Texto normal") == "Texto normal"


def test_allocate_number_supports_real_dict_cursor_shape():
    class FakeCursor:
        def execute(self, *args, **kwargs):
            return None
        def fetchone(self):
            return {"allocated_number": 7}
    assert doc.allocate_number(FakeCursor(), "actas", 2026) == 7
