import pytest
from conftest import load_service


doc = load_service("document_service_app", "services/document_service/app.py")


def test_document_code_is_consistent():
    assert doc.code_for("informes", 2026, 7) == "INF.DTCD.007.2026"
    assert doc.code_for("actas", 2026, 12) == "ACTAS.DTCD.012.2026"


def test_case_fortuito_requires_technical_fields():
    payload = {
        "empresa": "Empresa",
        "gestiones": "Gestión",
        "productos_asociados": "Producto",
        "asunto": "Interrupción",
        "tipo_informe": "Informe de caso fortuito",
        "caso_tipo": "ALIMENTADOR",
        "fecha_interrupcion": "2026-07-31",
        "nombre_alimentador": "A-01",
        "alimentador_subestacion": "SE Norte",
    }
    result = doc.validate_payload("informes", payload)
    assert result["case_type"] == "ALIMENTADOR"
    assert result["feeder_name"] == "A-01"


def test_case_fortuito_rejects_missing_date():
    with pytest.raises(ValueError, match="fecha de interrupción"):
        doc.validate_payload("informes", {
            "empresa": "Empresa", "gestiones": "Gestión",
            "productos_asociados": "Producto", "asunto": "Interrupción",
            "tipo_informe": "Caso fortuito", "caso_tipo": "ALIMENTADOR",
            "nombre_alimentador": "A-01", "alimentador_subestacion": "SE Norte",
        })


def test_excel_formula_is_neutralized():
    assert doc.excel_safe("=HYPERLINK(\"x\")").startswith("'")
    assert doc.excel_safe("Texto normal") == "Texto normal"


def test_custom_fields_accept_supported_values():
    result = doc.validate_custom_fields({
        "numero_tramite": "TRM-001",
        "requiere_revision": True,
        "cantidad": 3,
        "areas": ["Técnica", "Jurídica"],
    })
    assert result["numero_tramite"] == "TRM-001"
    assert result["requiere_revision"] is True
    assert result["cantidad"] == 3
    assert result["areas"] == ["Técnica", "Jurídica"]


def test_custom_fields_reject_invalid_key():
    with pytest.raises(ValueError, match="clave"):
        doc.validate_custom_fields({"campo con espacios": "x"})
