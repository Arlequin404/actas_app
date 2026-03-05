# Manual de Usuario - Sistema de Gestión de Actas, Informes y Reportes

Este manual proporciona una guía detallada sobre el uso y funcionamiento del sistema de gestión de documentos. El sistema está diseñado para facilitar la creación, administración y exportación de Actas, Informes, Reportes y Comisiones.

---

## 1. Acceso al Sistema

### 1.1 Inicio de Sesión
Para acceder al sistema, ingrese sus credenciales en la página de inicio:
*   **Correo Electrónico**: Su dirección de correo institucional.
*   **Contraseña**: Su clave personal de acceso.

### 1.2 Recuperación de Contraseña
Si ha olvidado su contraseña:
1. Haga clic en **"¿Olvidaste tu contraseña?"** en la pantalla de login.
2. Ingrese su correo electrónico registrado.
3. Recibirá un enlace de restablecimiento por correo (válido por 1 hora).

---

## 2. Panel Principal (Dashboard)

Una vez iniciada la sesión, verá el Dashboard con tarjetas de acceso rápido:
*   **Botones Coloridos**: Acceso directo para la creación de los 4 tipos de documentos.
*   **Mis Documentos**: Lista rápida de los documentos creados por usted.
*   **Administración** (Solo para perfiles Admin): Acceso a la gestión de usuarios, control total de documentos y configuración de catálogos.

---

## 3. Creación de Documentos

El sistema cuenta con un flujo estandarizado para la creación de registros:

### 3.1 Pasos Comunes
1. Seleccione la **Empresa** relacionada.
2. Complete la **Gestión** y el **Producto Asociado** (estas listas son dinámicas y dependen del tipo de documento).
3. Escriba el **Asunto** (obligatorio) y las **Observaciones**.
4. Haga clic en **"Guardar Documento"**.

### 3.2 Manejo de la opción "Otros"
Si una opción no se encuentra en las listas desplegables:
1. Seleccione la opción **"Otros"** al final de la lista.
2. Aparecerá un cuadro de texto adicional donde deberá escribir el valor personalizado.
3. El sistema guardará este texto automáticamente.

### 3.3 Sección Especial: Caso Fortuito (Solo en Informes)
Si el informe es de tipo **"Caso Fortuito"**, se habilitará una sección adicional obligatoria:
*   **Tipo de Caso**: Seleccione si es "Alimentador" o "Línea de Subtransmisión".
*   **Causa Principal**: Seleccione de la lista o use "Otros".
*   **Datos Técnicos**: Nombre del alimentador/línea, subestación, fecha y hora de la interrupción.

---

## 4. Gestión y Administración

### 4.1 Visualización de Documentos
En la sección **"Todos los Docs"** (Admin) o **"Mis Documentos"** (Usuario), los registros se presentan en tablas organizadas por pestañas.
*   Los documentos están ordenados cronológicamente (los más recientes primero).
*   Se genera un código automático siguiendo el formato: `TIPO.DTCD.####.2026`.

### 4.2 Edición y Eliminación
*   **Editar**: Permite modificar cualquier campo de un documento ya guardado. El formulario se cargará con toda la información existente, incluyendo los valores de "Otros".
*   **Eliminar**: Borra el registro de forma permanente (requiere confirmación).

### 4.3 Exportación a Excel
En el panel de administración, cada pestaña cuenta con un botón **"📥 Exportar [Tipo]"**.
*   Genera un archivo `.xlsx` con formato profesional.
*   Incluye todos los campos, incluyendo los detalles técnicos de casos fortuitos.

---

## 5. Configuración del Sistema (Solo Administradores)

### 5.1 Gestión de Usuarios
Acceso desde el Dashboard → **Usuarios**:
*   Crear nuevos usuarios.
*   Asignar roles (**admin** para control total, **usuario** para registro básico).
*   Cambiar contraseñas.

### 5.2 Gestión de Catálogos
Acceso desde el Dashboard → **Configuración**:
*   Permite editar las listas desplegables de todo el sistema.
*   Puede agregar nuevas Empresas, Gestiones, Productos y Tipos de Reporte sin necesidad de programar.
*   **Estructura Jerárquica**: Los "Tipos de Informe" pueden tener hasta 3 niveles de profundidad para una clasificación exacta.

---

## 6. Soporte Técnico

Si experimenta problemas con el sistema o necesita ayuda adicional:
*   Verifique su conexión a internet.
*   Asegúrese de que todos los campos requeridos (marcados con `*` o mensaje de validación) estén llenos.
*   Contacte al administrador del sistema en caso de errores de acceso.

---
*Manual generado el: 06 de Febrero de 2026*
