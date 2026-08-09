> **V7:** el servicio de respaldos usa herramientas PostgreSQL 16, igual que el servidor. Esto corrige el error `unrecognized configuration parameter "transaction_timeout"` durante la restauración.

# ARCONEL — Sistema de Control de Documentos por microservicios

Versión final consolidada del proyecto. Mantiene actas, informes, reportes y comisiones, pero separa autenticación, documentos, catálogos, notificaciones, respaldos e interfaz.

## Servicios

| Servicio | Base/función |
|---|---|
| `web-gateway` | Interfaz, sesiones, CSRF y permisos. |
| `auth-service` | Usuarios, roles, acceso y recuperación de contraseña (`auth_db`). |
| `document-service` | CRUD, correlativos y Excel (`documents_db`). |
| `catalog-service` | Catálogos y diseñador de formularios (`catalog_db`). |
| `notification-service` | Correos HTML y trazabilidad de envíos (`notifications_db`). |
| `backup-service` | Copia y restauración de las cuatro bases. |
| `migration-tool` | Migración opcional desde el monolito. |

Solo el gateway publica el puerto `8080`.

## Primera instalación

```powershell
python scripts\create_env.py --admin-email "correo@empresa.com"
docker compose up -d --build
```

Abra `http://localhost:8080`. La contraseña inicial aparece al ejecutar `create_env.py`.

La longitud mínima es configurable y queda en seis caracteres por compatibilidad:

```env
MIN_PASSWORD_LENGTH=6
```

## Actualizar una instalación que ya tiene datos

1. Haga una copia desde **Administración → Respaldos**.
2. Copie su `.env` actual a esta carpeta.
3. Detenga los contenedores sin borrar volúmenes:

```powershell
docker compose down --remove-orphans
```

4. Levante la versión final:

```powershell
docker compose up -d --build --force-recreate
```

5. Compruebe:

```powershell
docker compose ps
docker compose logs --tail=100 auth-service catalog-service document-service notification-service web-gateway
```

**No use `docker compose down -v`**, porque `-v` elimina PostgreSQL.

## Numeración documental

El formato es:

```text
PREFIJO.NÚMERO.AÑO
```

Ejemplos:

```text
ACTAS.DTCD.001.2026
INF.DTCD.001.2026
REP.DTCD.001.2026
CMS.DTCD.001.2026
```

El contador se administra por tipo de documento y año. Al iniciar 2027 vuelve automáticamente a `001` para cada tipo. La inicialización también corrige códigos creados por ediciones anteriores con el año en la mitad.

## Roles y usuarios

- `admin`: acceso completo a usuarios, documentos, catálogos, formularios, notificaciones y respaldos.
- `usuario`: crea, consulta y edita sus propios documentos.

El administrador puede crear, editar, cambiar rol, cambiar contraseña, desactivar y reactivar usuarios. La desactivación conserva documentos e historial. No se puede desactivar al último administrador ni al usuario administrador que está usando la sesión.

Las contraseñas se guardan con hash; nunca en texto plano.

## Formularios dinámicos

Desde **Administración → Diseñador de formularios** se pueden agregar:

- Texto corto y largo.
- Número.
- Fecha.
- Fecha y hora.
- Correo.
- Lista desplegable.
- Opción única.
- Selección múltiple.
- Casilla de confirmación.
- Sí/No.
- Opción **Otros** con respuesta manual.

La definición se guarda en `catalog_db.form_fields`. Las respuestas se guardan dentro de PostgreSQL en `documents_db.documents.extra_data` de tipo `JSONB`; no son archivos JSON externos.

La clave interna y el tipo quedan bloqueados después de crear un campo. Se puede cambiar la etiqueta, ayuda, obligatoriedad, opciones, orden y visibilidad. Ocultar un campo no elimina respuestas históricas. Crear y editar documentos usan la misma plantilla.

## Correos

El `notification-service` conserva la estructura HTML y registra cada intento como enviado, fallido u omitido. Se generan notificaciones para:

- Creación y actualización de usuarios.
- Recuperación y cambio de contraseña.
- Creación, edición y eliminación de documentos.
- Generación y restauración de respaldos.

Configuración:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=correo@gmail.com
SMTP_PASS=CONTRASENA_DE_APLICACION
SMTP_TLS=true
SMTP_FROM=ARCONEL <correo@gmail.com>
EMAIL_NOTIFICATIONS_ENABLED=true
```

Si SMTP no está configurado, la operación principal continúa y el envío queda como `Omitido` en **Administración → Notificaciones**.

## Copias de seguridad

El archivo `.tar.gz` administrativo contiene:

```text
manifest.json
auth_db.dump
documents_db.dump
catalog_db.dump
notifications_db.dump
```

Por tanto, incluye usuarios, documentos, respuestas JSONB, definición de campos, catálogos y trazabilidad de correos. La restauración se prueba primero en bases temporales. También se aceptan respaldos `v1` anteriores que contienen las tres bases principales.

## Excel

Los campos dinámicos se agregan como columnas. Los valores que podrían interpretarse como fórmulas se neutralizan antes de generar el archivo.

## Validación

```powershell
python scripts\check_project.py
```

Valida Python, plantillas Jinja y `docker-compose.yml`.

## pgAdmin opcional

```powershell
docker compose --profile tools up -d pgadmin
```

Abra `http://localhost:5050`; el host de PostgreSQL es `db`.

## Editor visual de formularios

Esta versión unifica catálogos, preguntas y subformularios en **Administración → Editor visual de formularios**. Consulte `CONSTRUCTOR_VISUAL.md` y `ACTUALIZACION_CONSTRUCTOR_VISUAL.md`.

## Constructor visual V3

El administrador puede editar todas las respuestas directamente desde la vista del formulario, crear subformularios condicionados para cualquier opción y eliminar elementos de forma segura. La opción especial **Otros** de Empresas se administra en una pantalla independiente. Consulte `MEJORAS_CONSTRUCTOR_VISUAL_V3.md`.


## Pruebas automatizadas completas

La versión incluye pruebas unitarias, integración real con PostgreSQL, pruebas de interfaz con Playwright, correos con Mailpit y restauración de respaldos en un volumen aislado.

En Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1
```

Consulte `PRUEBAS_COMPLETAS.md` para la matriz y los reportes generados.

## Compatibilidad de respaldos

Las nuevas copias completas se descargan como `.tar.gz` porque la arquitectura utiliza cuatro bases PostgreSQL. Desde la V9, el administrador también puede importar respaldos `.sql` generados por la versión monolítica anterior. Consulte `COMPATIBILIDAD_RESPALDOS_SQL_V9.md`.

## V13: OneDrive y logs

Consulte `RESPALDOS_AUTOMATICOS_ONEDRIVE_Y_LOGS_V13.md` para activar las copias automáticas diarias en una carpeta sincronizada por OneDrive Desktop y usar la nueva pestaña administrativa de Logs y reportes.


## V15: Google Drive

La integración de nube fue corregida para Google Drive. Consulte `CORRECCION_GOOGLE_DRIVE_V15.md`.

## Google Drive directo (V16)

La integración de respaldos ya no depende de Google Drive para ordenadores ni de una ruta local. Consulte `GOOGLE_DRIVE_DIRECTO_V16.md` para configurar OAuth 2.0 y subir los `.tar.gz` directamente a la nube mediante Google Drive API.


## V17 — Google Drive OAuth PKCE
Se corrigió la persistencia y reutilización del `code_verifier` durante el callback OAuth de Google Drive.
