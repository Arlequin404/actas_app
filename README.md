# 📄 Sistema de Gestión de Actas, Informes y Reportes (actas_app)

![Versión](https://img.shields.io/badge/versión-2.1.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-green.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.3-lightgrey.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)
![Docker](https://img.shields.io/badge/Docker-enabled-blue.svg)

Una solución integral y moderna diseñada para la administración, creación y exportación de documentos técnicos y administrativos. Este sistema optimiza el flujo de trabajo para la generación de **Actas, Informes (incluyendo Casos Fortuitos), Reportes y Comisiones**.

---

## 🚀 Características Principales

### 📁 Gestión de Documentos
- **Flujo Estandarizado**: Creación intuitiva de documentos con campos personalizados según el tipo.
- **Numeración Automática e Inteligente**: Generación de correlativos automáticos con capacidad de edición manual en registros existentes.
- **Sección Especial de Casos Fortuitos**: Campos técnicos específicos para reportes de fallas en alimentadores y líneas de subtransmisión.
- **Exportación Profesional**: Generación de reportes en formato Excel (.xlsx) con estilos aplicados.

### ⚙️ Administración Avanzada
- **Catálogos Dinámicos**: Gestión de Empresas, Gestiones, Productos y Tipos de Reporte desde la interfaz administrativa, sin necesidad de tocar código.
- **Control de Usuarios**: Sistema de roles (Admin/Usuario) con gestión de perfiles y seguridad mejorada.
- **Seguridad en Acciones**: Modales de confirmación para eliminaciones críticas.

### 🛡️ Respaldo y Seguridad
- **Copia de Seguridad Automatizada**: Sistema de backups diarios de la base de datos PostgreSQL.
- **Compresión y Retención**: Almacenamiento local comprimido (.sql.gz) con política de rotación de 30 días.
- **Sincronización en la Nube**: Integración con `rclone` para subir respaldos automáticamente a Google Drive.
- **Disparador Manual**: Opción para ejecutar respaldos inmediatos desde el panel de administración.

---

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.12 + Flask
- **Base de Datos**: PostgreSQL 16
- **ORM**: SQLAlchemy
- **Frontend**: HTML5, CSS3 (Vanilla + Custom Components), JavaScript (ES6+)
- **Infraestructura**: Docker & Docker Compose
- **Backups**: Scripts Bash + pg_dump + Rclone

---

## 📦 Instalación y Despliegue

### Requisitos Previos
- Docker y Docker Compose instalados.
- Archivo `.env` configurado (ver `.env.example`).

### Pasos Rápidos
1. **Clonar el repositorio**:
   ```bash
   git clone <url-del-repositorio>
   cd actas_app
   ```

2. **Levantar los servicios**:
   ```bash
   docker-compose up -d --build
   ```

3. **Acceder a la aplicación**:
   - Web: `http://localhost:8080`
   - pgAdmin: `http://localhost:5050` (Credenciales en `.env`)

---

## 📂 Estructura del Proyecto

```text
actas_app/
├── app/               # Código fuente de la aplicación Flask
│   ├── static/        # Archivos estáticos (CSS, JS, Imágenes)
│   ├── templates/     # Plantillas Jinja2
│   ├── models.py      # Definición de modelos SQLAlchemy
│   └── app.py         # Punto de entrada y rutas
├── initdb/            # Scripts de inicialización de la DB
├── backups/           # Directorio local de respaldos (generado automáticamente)
├── Dockerfile         # Configuración de imagen Docker para el Web
└── docker-compose.yml # Orquestación de servicios
```

---

## ✨ Últimas Actualizaciones

- ✅ **Sistema de Backups**: Implementación de copias de seguridad automáticas y manuales con subida a la nube.
- ✅ **Gestión de "Otros"**: Nueva funcionalidad en selectores para permitir entradas manuales si la opción no existe.
- ✅ **Seguridad UI**: Implementación de modales de confirmación para borrado de usuarios y documentos.
- ✅ **Flexibilidad en Numeración**: Permiso para modificar el número correlativo al editar documentos existentes.

---
*Desarrollado con ❤️ para la gestión eficiente de información.*
