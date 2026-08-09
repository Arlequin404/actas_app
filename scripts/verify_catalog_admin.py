"""Verifica que el administrador cubra todas las categorías y tipos de campo."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_APP = ROOT / "services/catalog_service/app.py"
GATEWAY_APP = ROOT / "services/web_gateway/app.py"
CATALOG_TEMPLATE = ROOT / "services/web_gateway/templates/admin_configuracion.html"
FORM_TEMPLATE = ROOT / "services/web_gateway/templates/formulario.html"


def literal_assignment(path: Path, variable: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"No se encontró {variable} en {path}")


allowed_categories = set(literal_assignment(CATALOG_APP, "ALLOWED_CATEGORIES"))
ui_categories = set(re.findall(r"key:'([A-Z_]+)'", CATALOG_TEMPLATE.read_text(encoding="utf-8")))
assert allowed_categories == ui_categories, (
    f"Categorías sin interfaz: {sorted(allowed_categories-ui_categories)}; "
    f"categorías inválidas en interfaz: {sorted(ui_categories-allowed_categories)}"
)

backend_types = set(literal_assignment(CATALOG_APP, "FORM_FIELD_TYPES"))
frontend_labels = set(literal_assignment(GATEWAY_APP, "FIELD_TYPE_LABELS"))
assert backend_types == frontend_labels, (
    f"Tipos sin etiqueta: {sorted(backend_types-frontend_labels)}; "
    f"etiquetas sin soporte: {sorted(frontend_labels-backend_types)}"
)

form_text = FORM_TEMPLATE.read_text(encoding="utf-8")
required_markers = {
    "text": "else 'text'",
    "textarea": "field.field_type == 'textarea'",
    "number": "field.field_type == 'number'",
    "date": "field.field_type == 'date'",
    "datetime": "field.field_type == 'datetime'",
    "time": "field.field_type == 'time'",
    "email": "field.field_type == 'email'",
    "tel": "field.field_type == 'tel'",
    "url": "field.field_type == 'url'",
    "select": "field.field_type == 'select'",
    "radio": "field.field_type == 'radio'",
    "multiselect": "field.field_type == 'multiselect'",
    "checkboxes": "field.field_type == 'checkboxes'",
    "checkbox": "field.field_type == 'checkbox'",
    "yesno": "field.field_type == 'yesno'",
}
missing = [field_type for field_type, marker in required_markers.items() if marker not in form_text]
assert not missing, f"Tipos sin renderizado en formulario: {missing}"

catalog_text = CATALOG_APP.read_text(encoding="utf-8")
for endpoint in ('/api/catalogs/bulk', '/api/catalogs/reorder'):
    assert endpoint in catalog_text, f"Falta endpoint {endpoint}"

print(
    f"Verificación correcta: {len(allowed_categories)} catálogos editables y "
    f"{len(backend_types)} tipos de campo disponibles."
)
