
-- 1. Schema Changes
ALTER TABLE actas ADD COLUMN IF NOT EXISTS gestiones VARCHAR(255);
ALTER TABLE actas ADD COLUMN IF NOT EXISTS productos_asociados VARCHAR(255);
ALTER TABLE comisiones ADD COLUMN IF NOT EXISTS gestiones VARCHAR(255);
ALTER TABLE comisiones ADD COLUMN IF NOT EXISTS productos_asociados VARCHAR(255);

-- 2. New Data
-- 9. GESTIONES (ACTAS)
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('GESTION_ACTA', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
('GESTION_ACTA', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
('GESTION_ACTA', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
('GESTION_ACTA', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
('GESTION_ACTA', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
('GESTION_ACTA', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
('GESTION_ACTA', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
('GESTION_ACTA', 'Otros', 'Otros', 999);

-- 10. PRODUCTOS ASOCIADOS (ACTAS)
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('PRODUCTO_ACTA', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
('PRODUCTO_ACTA', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
('PRODUCTO_ACTA', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
('PRODUCTO_ACTA', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
('PRODUCTO_ACTA', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
('PRODUCTO_ACTA', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
('PRODUCTO_ACTA', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
('PRODUCTO_ACTA', 'Otros', 'Otros', 999);

-- 11. GESTIONES (COMISIONES)
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('GESTION_COMISION', '1. Gestión de control técnico a la operación y mantenimiento del SPEE', 'Gestión de control técnico a la operación y mantenimiento del SPEE', 10),
('GESTION_COMISION', '2. Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 'Gestión de control técnico a la expansión del SPEE, SAPG y SCVE.', 20),
('GESTION_COMISION', '3. Gestión de control técnico al SAPG y SCVE.', 'Gestión de control técnico al SAPG y SCVE.', 30),
('GESTION_COMISION', '4. Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 'Gestión de control económico financiero a la operación y mantenimiento del SPEE.', 40),
('GESTION_COMISION', '5. Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 'Gestión de control económico financiero a la expansión SPEE, SAPG y SCVE.', 50),
('GESTION_COMISION', '6. Gestión de control económico financiero al SAPG y SCVE.', 'Gestión de control económico financiero al SAPG y SCVE.', 60),
('GESTION_COMISION', '7. Gestión de control a los sistemas nacionales de información de distribución.', 'Gestión de control a los sistemas nacionales de información de distribución.', 70),
('GESTION_COMISION', 'Otros', 'Otros', 999);

-- 12. PRODUCTOS ASOCIADOS (COMISIONES)
INSERT INTO catalogos (categoria, nombre, valor, orden) VALUES
('PRODUCTO_COMISION', '1. Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 'Informes técnicos de control sobre operación y mantenimiento para procesos de sanciones y multas por incumplimientos normativos en la distribución de energía eléctrica.', 10),
('PRODUCTO_COMISION', '2. Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 'Reportes de sanciones y multas emitidas mediante resolución por infracciones técnicas en la operación y mantenimiento de la distribución eléctrica.', 20),
('PRODUCTO_COMISION', '3. Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 'Informes de control técnico a empresas distribuidoras sobre la operación y mantenimiento de la infraestructura de subtransmisión y distribución, en cumplimiento de la normativa vigente.', 30),
('PRODUCTO_COMISION', '4. Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico de la operación de la infraestructura de subtransmisión y distribución.', 40),
('PRODUCTO_COMISION', '5. Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 'Informes de seguimiento a las acciones de control técnico del mantenimiento de la infraestructura de subtransmisión y distribución.', 50),
('PRODUCTO_COMISION', '6. Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 'Informes técnicos para procesos de suspensión o intervención de empresas distribuidoras, evaluando el cumplimiento normativo en operación y mantenimiento.', 60),
('PRODUCTO_COMISION', '7. Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 'Informes técnicos con recomendaciones, observaciones y propuestas de nuevas regulaciones, reformas o actualizaciones relacionadas con la operación y mantenimiento de la distribución eléctrica.', 70),
('PRODUCTO_COMISION', 'Otros', 'Otros', 999);
