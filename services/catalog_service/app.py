import os
import re
import secrets
import unicodedata
from pathlib import Path

import psycopg2
from flask import Flask, jsonify, request
from psycopg2.extras import Json, RealDictCursor

app = Flask(__name__)
DATABASE_URL = os.environ["DATABASE_URL"]
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
if len(INTERNAL_API_KEY) < 32:
    raise RuntimeError("INTERNAL_API_KEY debe tener al menos 32 caracteres")

ALLOWED_CATEGORIES = {
    "EMPRESA", "GESTION_INFORME", "PRODUCTO_INFORME", "GESTION_REPORTE",
    "TIPO_REPORTE", "PRODUCTO_REPORTE", "TIPO_INFORME",
    "GESTION_ACTA", "PRODUCTO_ACTA", "GESTION_COMISION", "PRODUCTO_COMISION"
}
FORM_DOC_TYPES = {"actas", "informes", "reportes", "comisiones"}
FORM_FIELD_TYPES = {
    "text", "textarea", "number", "date", "datetime", "time", "email", "tel", "url",
    "select", "radio", "multiselect", "checkboxes", "checkbox", "yesno"
}


def conn():
    return psycopg2.connect(DATABASE_URL)


def require_internal(admin=False):
    if not secrets.compare_digest(request.headers.get("X-Internal-Key", ""), INTERNAL_API_KEY):
        return jsonify(error="Acceso interno no autorizado"), 401
    if admin and request.headers.get("X-User-Role") != "admin":
        return jsonify(error="Se requiere rol administrador"), 403
    return None


def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS catalogos (
      id SERIAL PRIMARY KEY,
      categoria VARCHAR(50) NOT NULL,
      nombre VARCHAR(500) NOT NULL,
      valor VARCHAR(500),
      padre_id INTEGER REFERENCES catalogos(id) ON DELETE RESTRICT,
      activo BOOLEAN NOT NULL DEFAULT TRUE,
      orden INTEGER NOT NULL DEFAULT 0,
      meta_data JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_catalogos_categoria ON catalogos(categoria,activo,orden);
    CREATE INDEX IF NOT EXISTS idx_catalogos_padre ON catalogos(padre_id);
    CREATE UNIQUE INDEX IF NOT EXISTS uq_catalogos_categoria_padre_nombre
      ON catalogos(categoria,COALESCE(padre_id,0),LOWER(nombre));

    CREATE TABLE IF NOT EXISTS form_sections (
      id SERIAL PRIMARY KEY,
      document_type VARCHAR(20) NOT NULL CHECK(document_type IN ('actas','informes','reportes','comisiones')),
      section_key VARCHAR(80) NOT NULL,
      title VARCHAR(150) NOT NULL,
      description VARCHAR(500),
      icon VARCHAR(50) NOT NULL DEFAULT 'bi-ui-checks-grid',
      active BOOLEAN NOT NULL DEFAULT TRUE,
      section_order INTEGER NOT NULL DEFAULT 0,
      show_when JSONB NOT NULL DEFAULT '{}'::jsonb,
      settings JSONB NOT NULL DEFAULT '{}'::jsonb,
      archived_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(document_type, section_key)
    );
    CREATE INDEX IF NOT EXISTS idx_form_sections_document
      ON form_sections(document_type, active, section_order, id);

    CREATE TABLE IF NOT EXISTS form_shortcuts (
      id SERIAL PRIMARY KEY,
      label VARCHAR(120) NOT NULL,
      description VARCHAR(300),
      icon VARCHAR(50) NOT NULL DEFAULT 'bi-file-earmark-plus',
      document_type VARCHAR(20) NOT NULL CHECK(document_type IN ('actas','informes','reportes','comisiones')),
      preset_values JSONB NOT NULL DEFAULT '{}'::jsonb,
      active BOOLEAN NOT NULL DEFAULT TRUE,
      shortcut_order INTEGER NOT NULL DEFAULT 0,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_form_shortcuts_active
      ON form_shortcuts(active, shortcut_order, id);

    CREATE TABLE IF NOT EXISTS form_settings (
      setting_key VARCHAR(80) PRIMARY KEY,
      setting_value JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS form_fields (
      id SERIAL PRIMARY KEY,
      document_type VARCHAR(20) NOT NULL CHECK(document_type IN ('actas','informes','reportes','comisiones')),
      section_id INTEGER REFERENCES form_sections(id) ON DELETE SET NULL,
      field_key VARCHAR(80) NOT NULL,
      label VARCHAR(120) NOT NULL,
      field_type VARCHAR(20) NOT NULL,
      placeholder VARCHAR(200),
      help_text VARCHAR(500),
      required BOOLEAN NOT NULL DEFAULT FALSE,
      active BOOLEAN NOT NULL DEFAULT TRUE,
      field_order INTEGER NOT NULL DEFAULT 0,
      options JSONB NOT NULL DEFAULT '[]'::jsonb,
      allow_other BOOLEAN NOT NULL DEFAULT FALSE,
      settings JSONB NOT NULL DEFAULT '{}'::jsonb,
      archived_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(document_type, field_key)
    );
    ALTER TABLE form_fields ADD COLUMN IF NOT EXISTS section_id INTEGER REFERENCES form_sections(id) ON DELETE SET NULL;
    ALTER TABLE form_fields ADD COLUMN IF NOT EXISTS allow_other BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE form_fields ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}'::jsonb;
    ALTER TABLE form_fields ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
    ALTER TABLE form_fields DROP CONSTRAINT IF EXISTS form_fields_field_type_check;
    ALTER TABLE form_fields ADD CONSTRAINT form_fields_field_type_check
      CHECK(field_type IN ('text','textarea','number','date','datetime','time','email','tel','url','select','radio','multiselect','checkboxes','checkbox','yesno'));
    CREATE INDEX IF NOT EXISTS idx_form_fields_document
      ON form_fields(document_type, active, field_order, id);
    """
    with conn() as db, db.cursor() as cur:
        cur.execute(schema)
        cur.execute("SELECT COUNT(*) FROM catalogos")
        if cur.fetchone()[0] == 0:
            seed = Path(__file__).with_name("seed_catalogs.sql").read_text(encoding="utf-8")
            cur.execute(seed)
        cur.execute(
            """
            INSERT INTO form_sections(document_type,section_key,title,description,icon,section_order,show_when,settings)
            VALUES('informes','caso_fortuito_adicional','Información adicional del caso fortuito',
                   'Preguntas complementarias que aparecen únicamente al seleccionar el informe de caso fortuito.',
                   'bi-exclamation-triangle',60,
                   '{"field_key":"tipo_informe","operator":"contains","value":"caso fortuito"}'::jsonb,
                   '{"system_section":"case_fortuito"}'::jsonb)
            ON CONFLICT(document_type,section_key) DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO form_sections(document_type,section_key,title,description,icon,section_order,show_when)
            VALUES
              ('informes','caso_fortuito_alimentador','Datos del alimentador','Complete estos datos cuando el elemento afectado sea un alimentador.','bi-lightning-charge',61,
               '{"field_key":"custom:elemento_afectado","operator":"equals","value":"ALIMENTADOR"}'::jsonb),
              ('informes','caso_fortuito_lineas','Datos de la línea de subtransmisión','Complete estos datos cuando el elemento afectado sea una línea de subtransmisión.','bi-bezier2',62,
               '{"field_key":"custom:elemento_afectado","operator":"equals","value":"LINEAS DE SUBTRANSMISION"}'::jsonb)
            ON CONFLICT(document_type,section_key) DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO form_fields(document_type,section_id,field_key,label,field_type,required,active,field_order,options,allow_other,settings)
            VALUES
              ('informes',(SELECT id FROM form_sections WHERE document_type='informes' AND section_key='caso_fortuito_adicional'),
               'elemento_afectado','Elemento afectado','select',TRUE,TRUE,10,
               '["ALIMENTADOR","LINEAS DE SUBTRANSMISION"]'::jsonb,FALSE,'{"legacy_target":"case_type"}'::jsonb),
              ('informes',(SELECT id FROM form_sections WHERE document_type='informes' AND section_key='caso_fortuito_adicional'),
               'fecha_interrupcion','Fecha de interrupción','date',TRUE,TRUE,20,'[]'::jsonb,FALSE,'{"legacy_target":"interruption_date"}'::jsonb),
              ('informes',(SELECT id FROM form_sections WHERE document_type='informes' AND section_key='caso_fortuito_alimentador'),
               'nombre_alimentador','Alimentador','text',TRUE,TRUE,10,'[]'::jsonb,FALSE,'{"legacy_target":"feeder_name"}'::jsonb),
              ('informes',(SELECT id FROM form_sections WHERE document_type='informes' AND section_key='caso_fortuito_alimentador'),
               'alimentador_subestacion','Subestación','text',TRUE,TRUE,20,'[]'::jsonb,FALSE,'{"legacy_target":"substation"}'::jsonb),
              ('informes',(SELECT id FROM form_sections WHERE document_type='informes' AND section_key='caso_fortuito_lineas'),
               'linea_subtransmision_nombre','Línea de subtransmisión','text',TRUE,TRUE,10,'[]'::jsonb,FALSE,'{"legacy_target":"subtransmission_line"}'::jsonb)
            ON CONFLICT(document_type,field_key) DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO form_settings(setting_key,setting_value)
            VALUES('company_other', '{"enabled":true,"label":"Otros","prompt":"Especifique la empresa"}'::jsonb)
            ON CONFLICT(setting_key) DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO form_shortcuts(label,description,icon,document_type,preset_values,shortcut_order)
            SELECT 'Casos fortuitos','Abra directamente el formulario de informe para registrar un evento de fuerza mayor o caso fortuito.',
                   'bi-exclamation-triangle','informes',
                   jsonb_build_object('tipo_informe',valor),50
            FROM catalogos
            WHERE categoria='TIPO_INFORME' AND meta_data->>'special'='CASO_FORTUITO'
              AND NOT EXISTS (SELECT 1 FROM form_shortcuts WHERE label='Casos fortuitos')
            LIMIT 1
            """
        )
        db.commit()


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def normalize_payload(data, item_id=None, current=None):
    category = str((current or {}).get("categoria") or data.get("categoria", "")).strip().upper()
    name = str(data.get("nombre", "")).strip()
    # El identificador interno se genera al crear la opción y queda estable al editarla.
    if current:
        value = current.get("valor") or current.get("nombre") or name
    else:
        requested_value = str(data.get("valor", "")).strip()
        value = requested_value or name
    parent_id = data.get("padre_id") if "padre_id" in data else (current or {}).get("padre_id")
    parent_id = parent_id or None
    order = int(data.get("orden", (current or {}).get("orden", 0)) or 0)
    active = parse_bool(data.get("activo"), (current or {}).get("activo", True))
    metadata = data.get("meta_data") if "meta_data" in data else (current or {}).get("meta_data")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("Categoría inválida")
    if not name:
        raise ValueError("El nombre es obligatorio")
    if len(name) > 500 or (value and len(value) > 500):
        raise ValueError("Nombre o valor demasiado largo")
    if parent_id:
        if category != "TIPO_INFORME":
            raise ValueError("Solo los tipos de informe pueden tener una categoría superior")
        parent_id = int(parent_id)
        if item_id and parent_id == item_id:
            raise ValueError("Un elemento no puede ser su propio padre")
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id,categoria,padre_id FROM catalogos WHERE id=%s", (parent_id,))
            parent = cur.fetchone()
            if not parent:
                raise ValueError("La categoría superior no existe")
            if parent["categoria"] != category:
                raise ValueError("La categoría superior debe pertenecer a la misma lista")
            current_parent = parent
            visited = set()
            parent_depth = 1
            while current_parent and current_parent["padre_id"]:
                if current_parent["id"] in visited:
                    raise ValueError("La jerarquía existente contiene un ciclo")
                visited.add(current_parent["id"])
                if item_id and current_parent["padre_id"] == item_id:
                    raise ValueError("La relación produciría un ciclo")
                cur.execute("SELECT id,padre_id FROM catalogos WHERE id=%s", (current_parent["padre_id"],))
                current_parent = cur.fetchone()
                parent_depth += 1
            subtree_height = 1
            if item_id:
                cur.execute(
                    """
                    WITH RECURSIVE descendants AS (
                      SELECT id,1 AS depth FROM catalogos WHERE id=%s
                      UNION ALL
                      SELECT child.id,parent.depth+1
                      FROM catalogos child JOIN descendants parent ON child.padre_id=parent.id
                    ) SELECT COALESCE(MAX(depth),1) FROM descendants
                    """,
                    (item_id,),
                )
                subtree_height = int(cur.fetchone()[0] or 1)
            if parent_depth + subtree_height > 3:
                raise ValueError("La jerarquía admite máximo tres niveles")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("Los metadatos deben ser un objeto JSON")
    if metadata:
        special = str(metadata.get("special", "")).strip().upper()
        if special not in {"", "OTROS", "CASO_FORTUITO"}:
            raise ValueError("El comportamiento especial no es válido")
        if special == "CASO_FORTUITO" and category != "TIPO_INFORME":
            raise ValueError("Caso fortuito solo puede configurarse en tipos de informe")
        metadata = {"special": special} if special else None
    return category, name, value, parent_id, order, active, metadata


def build_tree(items, parent_id=None):
    children = []
    for item in [x for x in items if x["padre_id"] == parent_id]:
        node = {
            "id": item["id"],
            "label": item["nombre"],
            "value": item["valor"] or item["nombre"],
        }
        if item.get("meta_data") and item["meta_data"].get("special"):
            node["special"] = item["meta_data"]["special"]
        nested = build_tree(items, item["id"])
        if nested:
            node["children"] = nested
        children.append(node)
    return children


def slugify_field_key(label):
    normalized = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_").lower()
    if not key:
        key = "campo"
    if key[0].isdigit():
        key = f"campo_{key}"
    return key[:70]


def normalize_options(raw):
    if raw in (None, ""):
        return []
    if isinstance(raw, str):
        raw = raw.splitlines()
    if not isinstance(raw, list):
        raise ValueError("Las opciones deben enviarse como una lista")
    result = []
    for item in raw:
        text = str(item).strip()
        if text and text not in result:
            if len(text) > 120:
                raise ValueError("Cada opción puede tener máximo 120 caracteres")
            result.append(text)
    if len(result) > 100:
        raise ValueError("Un campo puede contener máximo 100 opciones")
    return result


def normalize_form_field(data, current=None):
    doc_type = str((current or {}).get("document_type") or data.get("document_type") or "").strip().lower()
    label = str(data.get("label", "")).strip()
    field_type = str(data.get("field_type") or (current or {}).get("field_type") or "text").strip().lower()
    placeholder = str(data.get("placeholder", "")).strip() or None
    help_text = str(data.get("help_text", "")).strip() or None
    required = parse_bool(data.get("required"), False)
    active = parse_bool(data.get("active"), True)
    field_order = int(data.get("field_order", 0) or 0)
    section_id = data.get("section_id") if "section_id" in data else (current or {}).get("section_id")
    section_id = int(section_id) if section_id not in (None, "") else None
    options = normalize_options(data.get("options"))
    allow_other = parse_bool(data.get("allow_other"), False)
    settings = data.get("settings") or {}

    if doc_type not in FORM_DOC_TYPES:
        raise ValueError("Tipo de documento inválido")
    if not label:
        raise ValueError("El nombre visible del campo es obligatorio")
    if len(label) > 120:
        raise ValueError("El nombre del campo puede tener máximo 120 caracteres")
    if field_type not in FORM_FIELD_TYPES:
        raise ValueError("Tipo de campo inválido")
    if placeholder and len(placeholder) > 200:
        raise ValueError("El texto de ejemplo puede tener máximo 200 caracteres")
    if help_text and len(help_text) > 500:
        raise ValueError("La ayuda puede tener máximo 500 caracteres")
    option_types = {"select", "radio", "multiselect", "checkboxes"}
    if field_type in option_types and not options:
        raise ValueError("Los campos de opciones deben tener al menos una opción")
    if field_type not in option_types:
        options = []
        allow_other = False
    if not isinstance(settings, dict):
        raise ValueError("La configuración avanzada debe ser un objeto")
    if section_id:
        with conn() as db, db.cursor() as cur:
            cur.execute("SELECT 1 FROM form_sections WHERE id=%s AND document_type=%s", (section_id, doc_type))
            if not cur.fetchone():
                raise ValueError("La sección seleccionada no pertenece a este formulario")

    field_key = (current or {}).get("field_key")
    requested_key = str(data.get("field_key", "")).strip().lower()
    if not field_key:
        field_key = requested_key or slugify_field_key(label)
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", field_key):
        raise ValueError("La clave interna del campo no es válida")
    return doc_type, section_id, field_key, label, field_type, placeholder, help_text, required, active, field_order, options, allow_other, settings


def normalize_show_when(raw):
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise ValueError("La condición debe ser un objeto")
    field_key = str(raw.get("field_key", "")).strip()
    operator = str(raw.get("operator", "equals")).strip().lower()
    value = str(raw.get("value", "")).strip()
    if not field_key and not value:
        return {}
    if not field_key:
        raise ValueError("La condición debe indicar la pregunta que la activa")
    if operator != "not_empty" and not value:
        raise ValueError("La condición debe indicar la respuesta que la activa")
    if not re.fullmatch(r"[a-z][a-z0-9_:]{0,99}", field_key):
        raise ValueError("El campo de la condición no es válido")
    if operator not in {"equals", "contains", "not_empty"}:
        raise ValueError("Operador de condición inválido")
    return {"field_key": field_key, "operator": operator, "value": "" if operator == "not_empty" else value}


def normalize_section(data, current=None):
    doc_type = str((current or {}).get("document_type") or data.get("document_type") or "").strip().lower()
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip() or None
    icon = str(data.get("icon", "bi-ui-checks-grid")).strip() or "bi-ui-checks-grid"
    active = parse_bool(data.get("active"), True)
    section_order = int(data.get("section_order", 0) or 0)
    show_when = normalize_show_when(data.get("show_when"))
    settings = data.get("settings") or {}
    if doc_type not in FORM_DOC_TYPES:
        raise ValueError("Tipo de documento inválido")
    if not title:
        raise ValueError("El título de la sección es obligatorio")
    if len(title) > 150 or (description and len(description) > 500):
        raise ValueError("El título o la descripción son demasiado extensos")
    if not re.fullmatch(r"bi-[a-z0-9-]{1,45}", icon):
        icon = "bi-ui-checks-grid"
    if not isinstance(settings, dict):
        raise ValueError("La configuración de la sección debe ser un objeto")
    section_key = (current or {}).get("section_key")
    if not section_key:
        section_key = slugify_field_key(str(data.get("section_key") or title))
    return doc_type, section_key, title, description, icon, active, section_order, show_when, settings


def normalize_shortcut(data, current=None):
    label = str(data.get("label", "")).strip()
    description = str(data.get("description", "")).strip() or None
    icon = str(data.get("icon", "bi-file-earmark-plus")).strip() or "bi-file-earmark-plus"
    doc_type = str((current or {}).get("document_type") or data.get("document_type") or "").strip().lower()
    preset_values = data.get("preset_values") or {}
    active = parse_bool(data.get("active"), True)
    shortcut_order = int(data.get("shortcut_order", 0) or 0)
    if not label or len(label) > 120:
        raise ValueError("El nombre del acceso es obligatorio y puede tener máximo 120 caracteres")
    if description and len(description) > 300:
        raise ValueError("La descripción puede tener máximo 300 caracteres")
    if doc_type not in FORM_DOC_TYPES:
        raise ValueError("Tipo de documento inválido")
    if not isinstance(preset_values, dict):
        raise ValueError("Los valores preseleccionados deben ser un objeto")
    if not re.fullmatch(r"bi-[a-z0-9-]{1,45}", icon):
        icon = "bi-file-earmark-plus"
    return label, description, icon, doc_type, preset_values, active, shortcut_order


def next_available_key(cur, doc_type, base_key):
    key = base_key
    suffix = 2
    while True:
        cur.execute("SELECT 1 FROM form_fields WHERE document_type=%s AND field_key=%s", (doc_type, key))
        if not cur.fetchone():
            return key
        tail = f"_{suffix}"
        key = f"{base_key[:80-len(tail)]}{tail}"
        suffix += 1


@app.get("/health")
def health():
    try:
        with conn() as db, db.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return jsonify(status="ok")
    except Exception as exc:
        return jsonify(status="error", detail=str(exc)), 503


@app.get("/api/catalogs/<category>")
def list_catalog(category):
    denied = require_internal()
    if denied:
        return denied
    category = category.upper()
    if category not in ALLOWED_CATEGORIES:
        return jsonify(error="Categoría inválida"), 400
    include_inactive = request.args.get("include_inactive") == "1" and request.headers.get("X-User-Role") == "admin"
    query = "SELECT id,categoria,nombre,valor,padre_id,activo,orden,meta_data FROM catalogos WHERE categoria=%s"
    if not include_inactive:
        query += " AND activo=TRUE"
    query += " ORDER BY orden,nombre"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (category,))
        rows = cur.fetchall()
    return jsonify(items=rows)


@app.get("/api/catalogs/<category>/tree")
def catalog_tree(category):
    denied = require_internal()
    if denied:
        return denied
    category = category.upper()
    if category not in ALLOWED_CATEGORIES:
        return jsonify(error="Categoría inválida"), 400
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id,nombre,valor,padre_id,meta_data FROM catalogos WHERE categoria=%s AND activo=TRUE ORDER BY orden,nombre", (category,))
        rows = cur.fetchall()
    return jsonify(items=build_tree(rows))


@app.post("/api/catalogs")
def create_catalog():
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        values = normalize_payload(request.get_json(silent=True) or {})
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO catalogos(categoria,nombre,valor,padre_id,orden,activo,meta_data) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id,categoria,nombre,valor,padre_id,orden,activo,meta_data",
                values[:-1] + (Json(values[-1]) if values[-1] is not None else None,),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="Ya existe un elemento con ese nombre en la categoría"), 409
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.put("/api/catalogs/<int:item_id>")
def update_catalog(item_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        data = request.get_json(silent=True) or {}
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM catalogos WHERE id=%s FOR UPDATE", (item_id,))
            current = cur.fetchone()
            if not current:
                return jsonify(error="Elemento no encontrado"), 404
            values = normalize_payload(data, item_id=item_id, current=current)
            cur.execute(
                """
                UPDATE catalogos SET categoria=%s,nombre=%s,valor=%s,padre_id=%s,orden=%s,activo=%s,meta_data=%s,updated_at=NOW()
                WHERE id=%s RETURNING id,categoria,nombre,valor,padre_id,orden,activo,meta_data
                """,
                values[:-1] + (Json(values[-1]) if values[-1] is not None else None, item_id),
            )
            item = cur.fetchone()
            if not item:
                return jsonify(error="Elemento no encontrado"), 404
            db.commit()
        return jsonify(item)
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="Ya existe un elemento con ese nombre en la categoría"), 409
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.delete("/api/catalogs/<int:item_id>")
def archive_catalog(item_id):
    """Oculta una opción sin borrar documentos históricos ni relaciones jerárquicas."""
    denied = require_internal(admin=True)
    if denied:
        return denied
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "UPDATE catalogos SET activo=FALSE,updated_at=NOW() WHERE id=%s RETURNING id,categoria,nombre,valor,padre_id,activo,orden,meta_data",
            (item_id,),
        )
        item = cur.fetchone()
        if not item:
            return jsonify(error="Elemento no encontrado"), 404
        db.commit()
    return jsonify(item)


def collect_section_tree(cur, initial_ids):
    """Obtiene secciones condicionadas anidadas y sus preguntas para borrado seguro."""
    section_ids = {int(value) for value in initial_ids if value is not None}
    pending = set(section_ids)
    field_ids = set()
    while pending:
        batch = list(pending)
        pending.clear()
        cur.execute("SELECT id,field_key FROM form_fields WHERE section_id=ANY(%s)", (batch,))
        rows = cur.fetchall()
        field_ids.update(row["id"] for row in rows)
        condition_keys = [f"custom:{row['field_key']}" for row in rows]
        if condition_keys:
            cur.execute("SELECT id FROM form_sections WHERE show_when->>'field_key'=ANY(%s)", (condition_keys,))
            for row in cur.fetchall():
                if row["id"] not in section_ids:
                    section_ids.add(row["id"])
                    pending.add(row["id"])
    return sorted(section_ids), sorted(field_ids)


def delete_section_tree(cur, initial_ids):
    section_ids, field_ids = collect_section_tree(cur, initial_ids)
    if section_ids:
        cur.execute("DELETE FROM form_fields WHERE section_id=ANY(%s)", (section_ids,))
        cur.execute("DELETE FROM form_sections WHERE id=ANY(%s)", (section_ids,))
    return len(section_ids), len(field_ids)


def catalog_field_key(category):
    return {
        "EMPRESA": "empresa",
        "GESTION_INFORME": "gestiones", "GESTION_REPORTE": "gestiones",
        "GESTION_ACTA": "gestiones", "GESTION_COMISION": "gestiones",
        "PRODUCTO_INFORME": "productos_asociados", "PRODUCTO_REPORTE": "productos_asociados",
        "PRODUCTO_ACTA": "productos_asociados", "PRODUCTO_COMISION": "productos_asociados",
        "TIPO_INFORME": "tipo_informe", "TIPO_REPORTE": "tipo_reporte",
    }.get(category)


@app.delete("/api/catalogs/<int:item_id>/purge")
def purge_catalog(item_id):
    """Elimina una opción del diseñador. Los valores ya guardados en documentos permanecen intactos."""
    denied = require_internal(admin=True)
    if denied:
        return denied
    cascade = request.args.get("cascade") == "1"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM catalogos WHERE id=%s FOR UPDATE", (item_id,))
        item = cur.fetchone()
        if not item:
            return jsonify(error="Elemento no encontrado"), 404
        cur.execute(
            """
            WITH RECURSIVE descendants AS (
              SELECT id,nombre,valor,padre_id,0 AS depth FROM catalogos WHERE id=%s
              UNION ALL
              SELECT c.id,c.nombre,c.valor,c.padre_id,d.depth+1
              FROM catalogos c JOIN descendants d ON c.padre_id=d.id
            ) SELECT * FROM descendants ORDER BY depth DESC,id DESC
            """,
            (item_id,),
        )
        descendants = cur.fetchall()
        deleted_values = {str(row.get("valor") or row.get("nombre") or "").strip().lower() for row in descendants}
        field_key = catalog_field_key(item["categoria"])
        linked_sections = []
        if field_key and deleted_values:
            cur.execute("SELECT id,title,show_when FROM form_sections WHERE show_when->>'field_key'=%s", (field_key,))
            for section in cur.fetchall():
                condition = section.get("show_when") or {}
                expected = str(condition.get("value") or "").strip().lower()
                if condition.get("operator") == "contains":
                    related = any(expected and expected in deleted_value for deleted_value in deleted_values)
                else:
                    related = expected in deleted_values
                if related:
                    linked_sections.append(section)
        children_count = max(len(descendants) - 1, 0)
        if (children_count or linked_sections) and not cascade:
            return jsonify(
                error="Esta opción tiene elementos relacionados",
                requires_cascade=True,
                children=children_count,
                linked_sections=[{"id": row["id"], "title": row["title"]} for row in linked_sections],
            ), 409
        removed_sections, removed_fields = delete_section_tree(cur, [row["id"] for row in linked_sections]) if linked_sections else (0, 0)
        for row in descendants:
            cur.execute("DELETE FROM catalogos WHERE id=%s", (row["id"],))
        db.commit()
    return jsonify(ok=True, deleted_options=len(descendants), deleted_sections=removed_sections, deleted_fields=removed_fields,
                   historical_data_preserved=True)


@app.get("/api/settings/<setting_key>")
def get_setting(setting_key):
    denied = require_internal()
    if denied:
        return denied
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT setting_key,setting_value,updated_at FROM form_settings WHERE setting_key=%s", (setting_key,))
        item = cur.fetchone()
    if not item:
        return jsonify(error="Configuración no encontrada"), 404
    return jsonify(item)


@app.put("/api/settings/<setting_key>")
def update_setting(setting_key):
    denied = require_internal(admin=True)
    if denied:
        return denied
    value = request.get_json(silent=True) or {}
    if not isinstance(value, dict):
        return jsonify(error="La configuración debe ser un objeto"), 400
    if setting_key == "company_other":
        value = {
            "enabled": parse_bool(value.get("enabled"), True),
            "label": str(value.get("label") or "Otros").strip()[:80] or "Otros",
            "prompt": str(value.get("prompt") or "Especifique la empresa").strip()[:160] or "Especifique la empresa",
        }
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO form_settings(setting_key,setting_value,updated_at) VALUES(%s,%s,NOW())
            ON CONFLICT(setting_key) DO UPDATE SET setting_value=EXCLUDED.setting_value,updated_at=NOW()
            RETURNING setting_key,setting_value,updated_at
            """,
            (setting_key, Json(value)),
        )
        item = cur.fetchone()
        db.commit()
    return jsonify(item)


@app.post("/api/catalogs/bulk")
def bulk_create_catalogs():
    """Crea varias opciones en una sola operación y omite duplicados existentes."""
    denied = require_internal(admin=True)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    category = str(data.get("categoria", "")).strip().upper()
    raw_items = data.get("items") or []
    if category not in ALLOWED_CATEGORIES:
        return jsonify(error="Categoría inválida"), 400
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify(error="Debe enviar al menos una opción"), 400
    if len(raw_items) > 200:
        return jsonify(error="Puede agregar máximo 200 opciones por operación"), 400

    common_parent = data.get("padre_id") or None
    common_special = str(data.get("special", "")).strip().upper() or None
    start_order = int(data.get("orden_inicial", 10) or 10)
    step = max(int(data.get("incremento", 10) or 10), 1)
    created, skipped = [], []
    try:
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            for index, raw in enumerate(raw_items):
                item = raw if isinstance(raw, dict) else {"nombre": str(raw)}
                payload = {
                    "categoria": category,
                    "nombre": item.get("nombre", ""),
                    "valor": item.get("valor", ""),
                    "padre_id": item.get("padre_id", common_parent),
                    "orden": item.get("orden", start_order + index * step),
                    "activo": item.get("activo", True),
                    "meta_data": item.get("meta_data") or ({"special": common_special} if common_special else None),
                }
                values = normalize_payload(payload)
                cur.execute(
                    "SELECT id,nombre FROM catalogos WHERE categoria=%s AND COALESCE(padre_id,0)=COALESCE(%s,0) AND LOWER(nombre)=LOWER(%s)",
                    (values[0], values[3], values[1]),
                )
                duplicate = cur.fetchone()
                if duplicate:
                    skipped.append({"nombre": values[1], "reason": "duplicado", "id": duplicate["id"]})
                    continue
                cur.execute(
                    "INSERT INTO catalogos(categoria,nombre,valor,padre_id,orden,activo,meta_data) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id,categoria,nombre,valor,padre_id,orden,activo,meta_data",
                    values[:-1] + (Json(values[-1]) if values[-1] is not None else None,),
                )
                created.append(cur.fetchone())
            db.commit()
        return jsonify(created=created, skipped=skipped, created_count=len(created), skipped_count=len(skipped)), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.post("/api/catalogs/reorder")
def reorder_catalogs():
    denied = require_internal(admin=True)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    category = str(data.get("categoria", "")).strip().upper()
    ids = data.get("ids") or []
    if category not in ALLOWED_CATEGORIES or not isinstance(ids, list):
        return jsonify(error="Datos de ordenamiento inválidos"), 400
    try:
        ids = [int(value) for value in ids]
    except (TypeError, ValueError):
        return jsonify(error="Lista de opciones inválida"), 400
    if len(ids) != len(set(ids)):
        return jsonify(error="La lista contiene identificadores repetidos"), 400
    with conn() as db, db.cursor() as cur:
        cur.execute("SELECT id FROM catalogos WHERE categoria=%s AND id=ANY(%s)", (category, ids))
        found = {row[0] for row in cur.fetchall()}
        if found != set(ids):
            return jsonify(error="Una o más opciones no pertenecen al catálogo seleccionado"), 400
        for index, item_id in enumerate(ids, 1):
            cur.execute("UPDATE catalogos SET orden=%s,updated_at=NOW() WHERE id=%s", (index * 10, item_id))
        db.commit()
    return jsonify(ok=True)


@app.get("/api/form-sections/<doc_type>")
def list_form_sections(doc_type):
    denied = require_internal()
    if denied:
        return denied
    doc_type = doc_type.lower()
    if doc_type not in FORM_DOC_TYPES:
        return jsonify(error="Tipo de documento inválido"), 400
    include_inactive = request.args.get("include_inactive") == "1" and request.headers.get("X-User-Role") == "admin"
    query = "SELECT id,document_type,section_key,title,description,icon,active,section_order,show_when,settings,archived_at FROM form_sections WHERE document_type=%s"
    if not include_inactive:
        query += " AND active=TRUE"
    query += " ORDER BY section_order,id"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (doc_type,))
        rows = cur.fetchall()
    return jsonify(items=rows)


@app.post("/api/form-sections")
def create_form_section():
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        values = normalize_section(request.get_json(silent=True) or {})
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            base = values[1]
            key = base
            suffix = 2
            while True:
                cur.execute("SELECT 1 FROM form_sections WHERE document_type=%s AND section_key=%s", (values[0], key))
                if not cur.fetchone():
                    break
                tail = f"_{suffix}"
                key = f"{base[:80-len(tail)]}{tail}"
                suffix += 1
            cur.execute(
                """
                INSERT INTO form_sections(document_type,section_key,title,description,icon,active,section_order,show_when,settings)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id,document_type,section_key,title,description,icon,active,section_order,show_when,settings,archived_at
                """,
                (values[0], key, values[2], values[3], values[4], values[5], values[6], Json(values[7]), Json(values[8])),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.put("/api/form-sections/<int:section_id>")
def update_form_section(section_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        data = request.get_json(silent=True) or {}
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM form_sections WHERE id=%s FOR UPDATE", (section_id,))
            current = cur.fetchone()
            if not current:
                return jsonify(error="Sección no encontrada"), 404
            values = normalize_section(data, current=current)
            cur.execute(
                """
                UPDATE form_sections SET title=%s,description=%s,icon=%s,active=%s,section_order=%s,
                    show_when=%s,settings=%s,
                    archived_at=CASE WHEN %s THEN NULL ELSE COALESCE(archived_at,NOW()) END,updated_at=NOW()
                WHERE id=%s
                RETURNING id,document_type,section_key,title,description,icon,active,section_order,show_when,settings,archived_at
                """,
                (values[2], values[3], values[4], values[5], values[6], Json(values[7]), Json(values[8]), values[5], section_id),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.delete("/api/form-sections/<int:section_id>")
def archive_form_section(section_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "UPDATE form_sections SET active=FALSE,archived_at=COALESCE(archived_at,NOW()),updated_at=NOW() WHERE id=%s RETURNING id,document_type,section_key,title,active,archived_at",
            (section_id,),
        )
        item = cur.fetchone()
        if not item:
            return jsonify(error="Sección no encontrada"), 404
        db.commit()
    return jsonify(item)

@app.delete("/api/form-sections/<int:section_id>/purge")
def purge_form_section(section_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    cascade = request.args.get("cascade") == "1"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM form_sections WHERE id=%s FOR UPDATE", (section_id,))
        section = cur.fetchone()
        if not section:
            return jsonify(error="Sección no encontrada"), 404
        cur.execute("SELECT id,label FROM form_fields WHERE section_id=%s ORDER BY field_order,id", (section_id,))
        children = cur.fetchall()
        tree_sections, tree_fields = collect_section_tree(cur, [section_id])
        nested_count = max(len(tree_sections) - 1, 0)
        if (children or nested_count) and not cascade:
            return jsonify(error="La sección todavía contiene preguntas o subformularios", requires_cascade=True,
                           fields=[{"id": row["id"], "label": row["label"]} for row in children],
                           nested_sections=nested_count), 409
        removed_sections, removed_fields = delete_section_tree(cur, [section_id])
        db.commit()
    return jsonify(ok=True, deleted_section=section_id, deleted_sections=removed_sections, deleted_fields=removed_fields,
                   historical_data_preserved=True)


@app.post("/api/form-sections/<int:section_id>/clone")
def clone_form_section(section_id):
    """Copia o sincroniza una sección completa y sus preguntas en otros formularios."""
    denied = require_internal(admin=True)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    raw_targets = data.get("targets") or []
    if not isinstance(raw_targets, list):
        return jsonify(error="Los formularios de destino son inválidos"), 400
    targets = []
    for value in raw_targets:
        target = str(value).strip().lower()
        if target in FORM_DOC_TYPES and target not in targets:
            targets.append(target)
    if not targets:
        return jsonify(error="Seleccione al menos un formulario de destino"), 400

    allowed_system_conditions = {
        "actas": {"empresa", "gestiones", "productos_asociados"},
        "informes": {"empresa", "gestiones", "productos_asociados", "tipo_informe"},
        "reportes": {"empresa", "gestiones", "productos_asociados", "tipo_reporte"},
        "comisiones": {"empresa", "gestiones", "productos_asociados"},
    }
    results, warnings = [], []
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM form_sections WHERE id=%s", (section_id,))
        source = cur.fetchone()
        if not source:
            return jsonify(error="Sección no encontrada"), 404
        cur.execute("SELECT * FROM form_fields WHERE section_id=%s ORDER BY field_order,id", (section_id,))
        source_fields = cur.fetchall()

        for target in targets:
            if target == source["document_type"]:
                continue
            condition = dict(source.get("show_when") or {})
            condition_key = str(condition.get("field_key", ""))
            if condition_key and not condition_key.startswith("custom:") and condition_key not in allowed_system_conditions[target]:
                warnings.append(f"La condición de '{source['title']}' no existe en {target}; la copia quedará siempre visible.")
                condition = {}
            settings = dict(source.get("settings") or {})
            settings["copied_from_document_type"] = source["document_type"]
            settings["copied_from_section_key"] = source["section_key"]
            cur.execute(
                """
                INSERT INTO form_sections(document_type,section_key,title,description,icon,active,section_order,show_when,settings,archived_at)
                VALUES(%s,%s,%s,%s,%s,TRUE,%s,%s,%s,NULL)
                ON CONFLICT(document_type,section_key) DO UPDATE SET
                  title=EXCLUDED.title,description=EXCLUDED.description,icon=EXCLUDED.icon,active=TRUE,
                  section_order=EXCLUDED.section_order,show_when=EXCLUDED.show_when,settings=EXCLUDED.settings,
                  archived_at=NULL,updated_at=NOW()
                RETURNING id,document_type,section_key,title
                """,
                (target, source["section_key"], source["title"], source.get("description"), source.get("icon") or "bi-ui-checks-grid",
                 source.get("section_order") or 0, Json(condition), Json(settings)),
            )
            target_section = cur.fetchone()
            for field in source_fields:
                field_settings = dict(field.get("settings") or {})
                field_settings["copied_from_document_type"] = source["document_type"]
                field_settings["copied_from_field_key"] = field["field_key"]
                if target != "informes":
                    field_settings.pop("legacy_target", None)
                cur.execute(
                    """
                    INSERT INTO form_fields(document_type,section_id,field_key,label,field_type,placeholder,help_text,
                                            required,active,field_order,options,allow_other,settings,archived_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)
                    ON CONFLICT(document_type,field_key) DO UPDATE SET
                      section_id=EXCLUDED.section_id,label=EXCLUDED.label,field_type=EXCLUDED.field_type,
                      placeholder=EXCLUDED.placeholder,help_text=EXCLUDED.help_text,required=EXCLUDED.required,
                      active=EXCLUDED.active,field_order=EXCLUDED.field_order,options=EXCLUDED.options,
                      allow_other=EXCLUDED.allow_other,settings=EXCLUDED.settings,archived_at=NULL,updated_at=NOW()
                    """,
                    (target, target_section["id"], field["field_key"], field["label"], field["field_type"],
                     field.get("placeholder"), field.get("help_text"), field.get("required", False),
                     field.get("active", True), field.get("field_order") or 0, Json(field.get("options") or []),
                     field.get("allow_other", False), Json(field_settings)),
                )
            results.append({"document_type": target, "section_id": target_section["id"], "fields": len(source_fields)})
        db.commit()
    return jsonify(items=results, warnings=warnings)


@app.get("/api/form-fields/<doc_type>")
def list_form_fields(doc_type):
    denied = require_internal()
    if denied:
        return denied
    doc_type = doc_type.lower()
    if doc_type not in FORM_DOC_TYPES:
        return jsonify(error="Tipo de documento inválido"), 400
    include_inactive = request.args.get("include_inactive") == "1" and request.headers.get("X-User-Role") == "admin"
    query = "SELECT id,document_type,section_id,field_key,label,field_type,placeholder,help_text,required,active,field_order,options,allow_other,settings,archived_at FROM form_fields WHERE document_type=%s"
    if not include_inactive:
        query += " AND active=TRUE"
    query += " ORDER BY field_order,id"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (doc_type,))
        rows = cur.fetchall()
    return jsonify(items=rows)


@app.post("/api/form-fields")
def create_form_field():
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        data = request.get_json(silent=True) or {}
        values = list(normalize_form_field(data))
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            values[2] = next_available_key(cur, values[0], values[2])
            cur.execute(
                """
                INSERT INTO form_fields(document_type,section_id,field_key,label,field_type,placeholder,help_text,required,active,field_order,options,allow_other,settings)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id,document_type,section_id,field_key,label,field_type,placeholder,help_text,required,active,field_order,options,allow_other,settings,archived_at
                """,
                tuple(values[:10]) + (Json(values[10]), values[11], Json(values[12])),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="Ya existe un campo con esa clave"), 409


@app.put("/api/form-fields/<int:field_id>")
def update_form_field(field_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        data = request.get_json(silent=True) or {}
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM form_fields WHERE id=%s FOR UPDATE", (field_id,))
            current = cur.fetchone()
            if not current:
                return jsonify(error="Campo no encontrado"), 404
            values = normalize_form_field(data, current=current)
            cur.execute(
                """
                UPDATE form_fields SET document_type=%s,section_id=%s,field_key=%s,label=%s,field_type=%s,
                    placeholder=%s,help_text=%s,required=%s,active=%s,field_order=%s,options=%s,allow_other=%s,settings=%s,
                    archived_at=CASE WHEN %s THEN NULL ELSE COALESCE(archived_at,NOW()) END,updated_at=NOW()
                WHERE id=%s
                RETURNING id,document_type,section_id,field_key,label,field_type,placeholder,help_text,required,active,field_order,options,allow_other,settings,archived_at
                """,
                tuple(values[:10]) + (Json(values[10]), values[11], Json(values[12]), values[8], field_id),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="Ya existe un campo con esa clave"), 409


@app.delete("/api/form-fields/<int:field_id>")
def archive_form_field(field_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "UPDATE form_fields SET active=FALSE,archived_at=COALESCE(archived_at,NOW()),updated_at=NOW() WHERE id=%s RETURNING id,document_type,section_id,field_key,label,active,archived_at",
            (field_id,),
        )
        item = cur.fetchone()
        if not item:
            return jsonify(error="Campo no encontrado"), 404
        db.commit()
    return jsonify(item)


@app.delete("/api/form-fields/<int:field_id>/purge")
def purge_form_field(field_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    cascade = request.args.get("cascade") == "1"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM form_fields WHERE id=%s FOR UPDATE", (field_id,))
        field = cur.fetchone()
        if not field:
            return jsonify(error="Pregunta no encontrada"), 404
        condition_key = f"custom:{field['field_key']}"
        cur.execute("SELECT id,title FROM form_sections WHERE show_when->>'field_key'=%s", (condition_key,))
        linked = cur.fetchall()
        if linked and not cascade:
            return jsonify(error="Esta pregunta activa uno o más subformularios", requires_cascade=True,
                           linked_sections=[{"id": row["id"], "title": row["title"]} for row in linked]), 409
        removed_sections, removed_fields = delete_section_tree(cur, [row["id"] for row in linked]) if linked else (0, 0)
        cur.execute("DELETE FROM form_fields WHERE id=%s", (field_id,))
        db.commit()
    return jsonify(ok=True, deleted_field=field_id, deleted_sections=removed_sections, deleted_nested_fields=removed_fields,
                   historical_data_preserved=True)


@app.post("/api/form-fields/reorder")
def reorder_form_fields():
    denied = require_internal(admin=True)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    doc_type = str(data.get("document_type", "")).lower()
    ids = data.get("ids") or []
    if doc_type not in FORM_DOC_TYPES or not isinstance(ids, list):
        return jsonify(error="Datos de ordenamiento inválidos"), 400
    try:
        ids = [int(value) for value in ids]
    except (TypeError, ValueError):
        return jsonify(error="Lista de campos inválida"), 400
    with conn() as db, db.cursor() as cur:
        for order, field_id in enumerate(ids, 1):
            cur.execute(
                "UPDATE form_fields SET field_order=%s,updated_at=NOW() WHERE id=%s AND document_type=%s",
                (order, field_id, doc_type),
            )
        db.commit()
    return jsonify(ok=True)


@app.get("/api/form-shortcuts")
def list_form_shortcuts():
    denied = require_internal()
    if denied:
        return denied
    include_inactive = request.args.get("include_inactive") == "1" and request.headers.get("X-User-Role") == "admin"
    query = "SELECT id,label,description,icon,document_type,preset_values,active,shortcut_order FROM form_shortcuts"
    if not include_inactive:
        query += " WHERE active=TRUE"
    query += " ORDER BY shortcut_order,id"
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        items = cur.fetchall()
    return jsonify(items=items)


@app.post("/api/form-shortcuts")
def create_form_shortcut():
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        values = normalize_shortcut(request.get_json(silent=True) or {})
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO form_shortcuts(label,description,icon,document_type,preset_values,active,shortcut_order)
                VALUES(%s,%s,%s,%s,%s,%s,%s)
                RETURNING id,label,description,icon,document_type,preset_values,active,shortcut_order
                """,
                values[:4] + (Json(values[4]), values[5], values[6]),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.put("/api/form-shortcuts/<int:shortcut_id>")
def update_form_shortcut(shortcut_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    try:
        data = request.get_json(silent=True) or {}
        with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM form_shortcuts WHERE id=%s FOR UPDATE", (shortcut_id,))
            current = cur.fetchone()
            if not current:
                return jsonify(error="Acceso no encontrado"), 404
            values = normalize_shortcut(data, current=current)
            cur.execute(
                """
                UPDATE form_shortcuts SET label=%s,description=%s,icon=%s,document_type=%s,preset_values=%s,active=%s,shortcut_order=%s,updated_at=NOW()
                WHERE id=%s RETURNING id,label,description,icon,document_type,preset_values,active,shortcut_order
                """,
                values[:4] + (Json(values[4]), values[5], values[6], shortcut_id),
            )
            item = cur.fetchone()
            db.commit()
        return jsonify(item)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.delete("/api/form-shortcuts/<int:shortcut_id>")
def archive_form_shortcut(shortcut_id):
    denied = require_internal(admin=True)
    if denied:
        return denied
    with conn() as db, db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("UPDATE form_shortcuts SET active=FALSE,updated_at=NOW() WHERE id=%s RETURNING id,label,active", (shortcut_id,))
        item = cur.fetchone()
        if not item:
            return jsonify(error="Acceso no encontrado"), 404
        db.commit()
    return jsonify(item)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
