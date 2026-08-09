# Cambios consolidados de la versión final

- Arquitectura por microservicios.
- Política de nuevas contraseñas configurable, mínimo seis caracteres.
- Las contraseñas existentes no se reemplazan ni se vuelven a validar durante una actualización.
- Roles `admin` y `usuario`.
- CRUD administrativo con desactivación y reactivación segura.
- Creación y edición documental mediante el mismo formulario.
- Diseñador de campos almacenado en PostgreSQL.
- Respuestas dinámicas en `JSONB` con texto, número, fecha, fecha/hora, correo, listas, radio, selección múltiple, confirmación, Sí/No y Otros.
- Clave y tipo de campo inmutables; ocultamiento sin pérdida histórica.
- Código documental `PREFIJO.NÚMERO.AÑO` y reinicio anual independiente por tipo.
- Conversión automática de códigos creados con el formato intermedio anterior.
- Servicio de correos HTML con registro de estado y reintentos.
- Notificaciones de usuarios, contraseñas, documentos y respaldos.
- Respaldo de `auth_db`, `documents_db`, `catalog_db` y `notifications_db`.
- Restauración compatible con respaldos `v1` anteriores.
- Exportación Excel con campos dinámicos y protección contra fórmulas.
- CSRF, CSP, hash de contraseñas, bloqueo de intentos y APIs internas protegidas.

## Editor visual V2
- Módulo general e independiente para empresas.
- CRUD visual de empresas con edición, ocultamiento y restauración.
- Vista previa sincronizada con los catálogos reales existentes.
- Acciones visibles de editar, ocultar y restaurar en cada opción.
- Corrección de ventanas modales superpuestas durante la edición.
- Copia y sincronización de secciones completas entre formularios.
