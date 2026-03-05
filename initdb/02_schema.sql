-- =========================
-- USUARIOS
-- =========================
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'usuario',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================
-- FUNCIÓN CONTADOR ANUAL
-- =========================
CREATE OR REPLACE FUNCTION generar_numero_anual()
RETURNS TRIGGER AS $$
BEGIN
    NEW.anio := EXTRACT(YEAR FROM CURRENT_DATE);

    EXECUTE format(
        'SELECT COALESCE(MAX(numero), 0) + 1 FROM %I WHERE anio = $1',
        TG_TABLE_NAME
    )
    INTO NEW.numero
    USING NEW.anio;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- FUNCIÓN GENERAR CÓDIGO (prefijo + numero + año)
-- =========================
CREATE OR REPLACE FUNCTION generar_codigo_documento()
RETURNS TRIGGER AS $$
DECLARE
    prefijo TEXT;
BEGIN
    IF TG_TABLE_NAME = 'informes' THEN
        prefijo := 'INF.DTCD';
    ELSIF TG_TABLE_NAME = 'actas' THEN
        prefijo := 'ACTAS.DTCD';
    ELSIF TG_TABLE_NAME = 'reportes' THEN
        prefijo := 'REP.DTCD';
    ELSIF TG_TABLE_NAME = 'comisiones' THEN
        prefijo := 'CMS.DTCD';
    ELSE
        prefijo := UPPER(TG_TABLE_NAME);
    END IF;

    NEW.codigo := prefijo || '.' || LPAD(NEW.numero::text, 3, '0') || '.' || NEW.anio;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- ACTAS
-- =========================
CREATE TABLE IF NOT EXISTS actas (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    codigo VARCHAR(30),
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa VARCHAR(200),
    
    -- NUEVO
    gestiones VARCHAR(255),
    productos_asociados VARCHAR(255),

    asunto VARCHAR(255) NOT NULL,
    observaciones TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (numero, anio),
    UNIQUE (codigo)
);

CREATE TRIGGER trg_actas_numero
BEFORE INSERT ON actas
FOR EACH ROW
EXECUTE FUNCTION generar_numero_anual();

CREATE TRIGGER trg_actas_codigo
BEFORE INSERT ON actas
FOR EACH ROW
EXECUTE FUNCTION generar_codigo_documento();

-- =========================
-- INFORMES
-- =========================
CREATE TABLE IF NOT EXISTS informes (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    codigo VARCHAR(30),
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa VARCHAR(200),
    tipo_informe VARCHAR(150),

    -- NUEVO (siempre en el formulario)
    gestiones VARCHAR(255),
    productos_asociados VARCHAR(255),

    asunto VARCHAR(255) NOT NULL,
    observaciones TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,

    -- =========================
    -- CAMPOS (SOLO SI tipo_informe = 'CASO FORTUITO')
    -- =========================
    caso_tipo VARCHAR(60),
    nombre_alimentador VARCHAR(200),
    alimentador_subestacion VARCHAR(200),
    linea_subtransmision_nombre VARCHAR(200),
    fecha_interrupcion DATE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (numero, anio),
    UNIQUE (codigo)
);

CREATE TRIGGER trg_informes_numero
BEFORE INSERT ON informes
FOR EACH ROW
EXECUTE FUNCTION generar_numero_anual();

CREATE TRIGGER trg_informes_codigo
BEFORE INSERT ON informes
FOR EACH ROW
EXECUTE FUNCTION generar_codigo_documento();

-- =========================
-- REPORTES
-- =========================
CREATE TABLE IF NOT EXISTS reportes (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    codigo VARCHAR(30),
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa VARCHAR(200),

    -- tipo de reporte
    tipo_reporte VARCHAR(150),

    -- NUEVO (siempre en el formulario)
    gestiones VARCHAR(255),
    productos_asociados VARCHAR(255),

    asunto VARCHAR(255) NOT NULL,
    observaciones TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (numero, anio),
    UNIQUE (codigo)
);

CREATE TRIGGER trg_reportes_numero
BEFORE INSERT ON reportes
FOR EACH ROW
EXECUTE FUNCTION generar_numero_anual();

CREATE TRIGGER trg_reportes_codigo
BEFORE INSERT ON reportes
FOR EACH ROW
EXECUTE FUNCTION generar_codigo_documento();

-- =========================
-- COMISIONES
-- =========================
CREATE TABLE IF NOT EXISTS comisiones (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    codigo VARCHAR(30),
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa VARCHAR(200),
    
    -- NUEVO
    gestiones VARCHAR(255),
    productos_asociados VARCHAR(255),

    asunto VARCHAR(255) NOT NULL,
    observaciones TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (numero, anio),
    UNIQUE (codigo)
);

CREATE TRIGGER trg_comisiones_numero
BEFORE INSERT ON comisiones
FOR EACH ROW
EXECUTE FUNCTION generar_numero_anual();

CREATE TRIGGER trg_comisiones_codigo
BEFORE INSERT ON comisiones
FOR EACH ROW
EXECUTE FUNCTION generar_codigo_documento();

-- =========================
-- PASSWORD RESET
-- =========================
CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =========================
-- ADMIN POR DEFECTO
-- =========================
INSERT INTO usuarios (nombre, email, password, rol)
VALUES ('William Lopez', 'william.lopez@arconel.gob.ec', 'Ecuador.2025', 'admin')
ON CONFLICT (email) DO NOTHING;
