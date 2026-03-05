-- =========================
-- CATALOGOS (Opciones dinámicas)
-- =========================
CREATE TABLE IF NOT EXISTS catalogos (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL, -- 'EMPRESA', 'GESTION_INFORME', 'TIPO_INFORME', etc.
    nombre VARCHAR(500) NOT NULL,
    valor VARCHAR(500), -- Opcional, por si difiere del nombre
    padre_id INTEGER REFERENCES catalogos(id) ON DELETE CASCADE,
    activo BOOLEAN DEFAULT TRUE,
    orden INTEGER DEFAULT 0,
    meta_data JSONB -- Para flags especiales como 'CASO_FORTUITO', 'OTROS', etc.
);

-- Índices para búsqueda rápida
CREATE INDEX idx_catalogos_categoria ON catalogos(categoria);
CREATE INDEX idx_catalogos_padre ON catalogos(padre_id);

-- ========================================================
-- DATOS INICIALES
-- ========================================================

-- 1. EMPRESAS (categoría = 'EMPRESA')
-- Grupo: CNEL EP
INSERT INTO catalogos (categoria, nombre, orden) VALUES 
('EMPRESA', 'CNEL EP Unidad de Negocio Bolívar', 10),
('EMPRESA', 'CNEL EP Unidad de Negocio El Oro', 20),
('EMPRESA', 'CNEL EP Unidad de Negocio Esmeraldas', 30),
('EMPRESA', 'CNEL EP Unidad de Negocio Guayaquil', 40),
('EMPRESA', 'CNEL EP Unidad de Negocio Guayas Los Ríos', 50),
('EMPRESA', 'CNEL EP Unidad de Negocio Los Ríos', 60),
('EMPRESA', 'CNEL EP Unidad de Negocio Manabí', 70),
('EMPRESA', 'CNEL EP Unidad de Negocio Milagro', 80),
('EMPRESA', 'CNEL EP Unidad de Negocio Santa Elena', 90),
('EMPRESA', 'CNEL EP Unidad de Negocio Santo Domingo', 100),
('EMPRESA', 'CNEL EP Unidad de Negocio Sucumbíos', 110);

-- Grupo: Empresas Eléctricas
INSERT INTO catalogos (categoria, nombre, orden) VALUES 
('EMPRESA', 'Empresa Eléctrica Ambato Regional Centro Norte S.A.', 120),
('EMPRESA', 'Empresa Eléctrica Azogues C.A.', 130),
('EMPRESA', 'Empresa Eléctrica Regional Centro Sur C.A.', 140),
('EMPRESA', 'Empresa Eléctrica Provincial Cotopaxi S.A.', 150),
('EMPRESA', 'Empresa Eléctrica Provincial Galápagos S.A.', 160),
('EMPRESA', 'Empresa Eléctrica Quito S.A.', 170),
('EMPRESA', 'Empresa Eléctrica Regional Norte S.A.', 180),
('EMPRESA', 'Empresa Eléctrica Riobamba S.A.', 190),
('EMPRESA', 'Empresa Eléctrica Regional del Sur S.A.', 200);


-- 2. GESTIONES (INFORMES) (categoría = 'GESTION_INFORME')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('GESTION_INFORME', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
('GESTION_INFORME', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
('GESTION_INFORME', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
('GESTION_INFORME', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
('GESTION_INFORME', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
('GESTION_INFORME', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
('GESTION_INFORME', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
('GESTION_INFORME', 'Otros', 'Otros', 999);


-- 3. PRODUCTOS ASOCIADOS (INFORMES) (categoría = 'PRODUCTO_INFORME')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('PRODUCTO_INFORME', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
('PRODUCTO_INFORME', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
('PRODUCTO_INFORME', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
('PRODUCTO_INFORME', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
('PRODUCTO_INFORME', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
('PRODUCTO_INFORME', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
('PRODUCTO_INFORME', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
('PRODUCTO_INFORME', 'Otros', 'Otros', 999);


-- 4. GESTIONES (REPORTES) (categoria = 'GESTION_REPORTE')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('GESTION_REPORTE', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
('GESTION_REPORTE', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
('GESTION_REPORTE', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
('GESTION_REPORTE', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
('GESTION_REPORTE', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
('GESTION_REPORTE', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
('GESTION_REPORTE', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
('GESTION_REPORTE', 'Otros', 'Otros', 999);


-- 5. TIPO DE REPORTE (categoria = 'TIPO_REPORTE')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('TIPO_REPORTE', '1. Calidad de Servicio Técnico', 'Calidad de Servicio Técnico', 10),
('TIPO_REPORTE', '2. Calidad de Producto', 'Calidad de Producto', 20),
('TIPO_REPORTE', '3. Campañas de medición', 'Campañas de medición', 30),
('TIPO_REPORTE', '4. SGDA', 'SGDA', 40),
('TIPO_REPORTE', '5. CGD', 'CGD', 50),
('TIPO_REPORTE', '6. GEE', 'GEE', 60),
('TIPO_REPORTE', '7. Avance de Ejecución de Costos', 'Avance de Ejecución de Costos', 70),
('TIPO_REPORTE', '8. Otros', 'Otros', 999);


-- 6. PRODUCTOS ASOCIADOS (REPORTES) (categoria = 'PRODUCTO_REPORTE')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('PRODUCTO_REPORTE', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
('PRODUCTO_REPORTE', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
('PRODUCTO_REPORTE', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
('PRODUCTO_REPORTE', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
('PRODUCTO_REPORTE', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
('PRODUCTO_REPORTE', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
('PRODUCTO_REPORTE', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
('PRODUCTO_REPORTE', 'Otros', 'Otros', 999);


-- 7. TIPO DE INFORME (JERÁRQUICO) (categoría = 'TIPO_INFORME')
DO $$
DECLARE
    id_root INTEGER;
    id_l2 INTEGER;
    id_l3 INTEGER;
BEGIN
    -- 7.1. Informe Control de la Calidad
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '1. Informe Control de la Calidad', 'Informe Control de la Calidad', 10) RETURNING id INTO id_root;
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES 
        ('TIPO_INFORME', 'Producto', 'Producto', id_root, 10),
        ('TIPO_INFORME', 'Servicio técnico', 'Servicio técnico', id_root, 20);

    -- 7.2. Informe de control técnico de ejecución de mantenimientos
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '2. Informe de control técnico de ejecución de mantenimientos', 'Informe de control técnico de ejecución de mantenimientos', 20);

    -- 7.3. Informe de inspección
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '3. Informe de inspección', 'Informe de inspección', 30) RETURNING id INTO id_root;
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES ('TIPO_INFORME', 'Mantenimientos', 'Mantenimientos', id_root, 10);
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES ('TIPO_INFORME', 'Calidad', 'Calidad', id_root, 20);
        
        -- Proyectos de Expansión (Level 2 -> Level 3)
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES ('TIPO_INFORME', 'Proyectos de Expansión', 'Proyectos de Expansión', id_root, 30) RETURNING id INTO id_l2;
            INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES 
            ('TIPO_INFORME', 'Via tarifa', 'Via tarifa', id_l2, 10),
            ('TIPO_INFORME', 'Recursos propios', 'Recursos propios', id_l2, 20),
            ('TIPO_INFORME', 'Excepcionalidad de obras', 'Excepcionalidad de obras', id_l2, 30);
            
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES ('TIPO_INFORME', 'S. Alumbrado Publico', 'S. Alumbrado Publico', id_root, 40);
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES ('TIPO_INFORME', 'SGDA', 'SGDA', id_root, 50);
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES ('TIPO_INFORME', 'GEE', 'GEE', id_root, 60);

    -- 7.4. Informe de Evaluación a la ejecución presupuestaria de Mantenimientos
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '4. Informe de Evaluación a la ejecución presupuestaria de Mantenimientos', 'Informe de Evaluación a la ejecución presupuestaria de Mantenimientos', 40);

    -- 7.5. Informe de control de la información técnica...
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '5. Informe de control de la información técnica de emisión de factibilidades de conexión para trámites de SGDA, CGD y GEE.', 'Informe de control de la información técnica de emisión de factibilidades de conexión para trámites de SGDA, CGD y GEE.', 50);

    -- 7.6. Informe de seguimiento y control de Proyectos Nacionales
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '6. Informe de seguimiento y control de Proyectos Nacionales', 'Informe de seguimiento y control de Proyectos Nacionales', 60) RETURNING id INTO id_root;
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES 
        ('TIPO_INFORME', 'Información contenida en el sistema GIS', 'Información contenida en el sistema GIS', id_root, 10),
        ('TIPO_INFORME', 'Estado de situación del sistema ADMS-SCADA', 'Estado de situación del sistema ADMS-SCADA', id_root, 20),
        ('TIPO_INFORME', 'Calidad de información del sistema ADMS-SCADA', 'Calidad de información del sistema ADMS-SCADA', id_root, 30);

    -- 7.7. Informes técnicos operativos...
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '7. Informes técnicos operativos de atención de reclamos de SGDA y CGD', 'Informes técnicos operativos de atención de reclamos de SGDA y CGD', 70);

    -- 7.8. CASO FORTUITO (Bandera Especial)
    INSERT INTO catalogos (categoria, nombre, valor, orden, meta_data) VALUES ('TIPO_INFORME', '8. Informes de la atención de solicitudes de interrupciones por eventos de fuerza mayor o caso fortuito', 'Informes de la atención de solicitudes de interrupciones por eventos de fuerza mayor o caso fortuito', 80, '{"special": "CASO_FORTUITO"}');

    -- 7.9. Informe de Evaluación a la ejecución presupuestaria de Proyectos calificados
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '9. Informe de Evaluación a la ejecución presupuestaria de Proyectos calificados', 'Informe de Evaluación a la ejecución presupuestaria de Proyectos calificados', 90);

    -- 7.10. Informe de Control Técnico a la Ejecución de proyectos
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '10. Informe de Control Técnico a la Ejecución de proyectos', 'Informe de Control Técnico a la Ejecución de proyectos', 100);

    -- 7.11. Informe de Evaluación a la ejecución presupuestaria
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '11. Informe de Evaluación a la ejecución presupuestaria', 'Informe de Evaluación a la ejecución presupuestaria', 110);

    -- 7.12. Informe o reporte técnico procesos de sanción
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '12. Informe o reporte técnico procesos de sanción', 'Informe o reporte técnico procesos de sanción', 120) RETURNING id INTO id_root;
        INSERT INTO catalogos (categoria, nombre, valor, padre_id, orden) VALUES 
        ('TIPO_INFORME', 'Informe de seguimiento sanciones', 'Informe de seguimiento sanciones', id_root, 10),
        ('TIPO_INFORME', 'Informe de notificación de incumplimientos normativos o contractuales', 'Informe de notificación de incumplimientos normativos o contractuales', id_root, 20),
        ('TIPO_INFORME', 'Informe de análisis de descargos', 'Informe de análisis de descargos', id_root, 30),
        ('TIPO_INFORME', 'Informe de recurso de apelación o de revisión', 'Informe de recurso de apelación o de revisión', id_root, 40);

    -- 7.13. Informe de revisión de proyectos de Regulación o mejora regulatoria
    INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES ('TIPO_INFORME', '13. Informe de revisión de proyectos de Regulación o mejora regulatoria', 'Informe de revisión de proyectos de Regulación o mejora regulatoria', 130);

    -- 7.14. Otros
    INSERT INTO catalogos (categoria, nombre, valor, orden, meta_data) VALUES ('TIPO_INFORME', '14. Otros', 'Otros', 999, '{"special": "OTROS"}');
END $$;




-- ========================================================
-- NUEVOS CATALOGOS (ACTAS Y COMISIONES)
-- ========================================================

-- 9. GESTIONES (ACTAS) (categoria = 'GESTION_ACTA')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('GESTION_ACTA', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
('GESTION_ACTA', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
('GESTION_ACTA', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
('GESTION_ACTA', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
('GESTION_ACTA', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
('GESTION_ACTA', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
('GESTION_ACTA', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
('GESTION_ACTA', 'Otros', 'Otros', 999);

-- 10. PRODUCTOS ASOCIADOS (ACTAS) (categoria = 'PRODUCTO_ACTA')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('PRODUCTO_ACTA', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
('PRODUCTO_ACTA', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
('PRODUCTO_ACTA', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
('PRODUCTO_ACTA', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
('PRODUCTO_ACTA', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
('PRODUCTO_ACTA', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
('PRODUCTO_ACTA', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
('PRODUCTO_ACTA', 'Otros', 'Otros', 999);


-- 11. GESTIONES (COMISIONES) (categoria = 'GESTION_COMISION')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('GESTION_COMISION', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
('GESTION_COMISION', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
('GESTION_COMISION', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
('GESTION_COMISION', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
('GESTION_COMISION', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
('GESTION_COMISION', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
('GESTION_COMISION', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
('GESTION_COMISION', 'Otros', 'Otros', 999);

-- 12. PRODUCTOS ASOCIADOS (COMISIONES) (categoria = 'PRODUCTO_COMISION')
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('PRODUCTO_COMISION', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
('PRODUCTO_COMISION', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
('PRODUCTO_COMISION', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
('PRODUCTO_COMISION', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
('PRODUCTO_COMISION', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
('PRODUCTO_COMISION', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
('PRODUCTO_COMISION', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
('PRODUCTO_COMISION', 'Otros', 'Otros', 999);
