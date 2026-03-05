# 📄 Sistema de Gestión de Documentos – ACTAS APP

Aplicación web desarrollada en **Flask + PostgreSQL** para la **gestión, control y trazabilidad de documentos institucionales**, específicamente:

- ✅ Actas  
- ✅ Informes (incluye Casos Fortuitos)  
- ✅ Reportes  
- ✅ Comisiones  

El sistema permite **crear, editar, listar, exportar y administrar documentos**, con control de usuarios y roles, generación automática de códigos y soporte para flujos administrativos reales.

---

## 🚀 Características principales

- 🔐 Autenticación de usuarios (roles: usuario / admin)
- 📑 Gestión completa de documentos:
  - Actas
  - Informes (con Gestiones, Productos Asociados y Caso Fortuito)
  - Reportes
  - Comisiones
- 🧾 Generación automática de:
  - Número anual
  - Código institucional (ej. `INF-DTCD-001-2026`)
- 🧠 Formularios dinámicos:
  - Campos que aparecen según selección
  - Opción **“Otros”** con campo de texto libre
- ⚡ Caso Fortuito con validaciones estrictas
- 📊 Exportación a Excel por tipo de documento
- 🧑‍💼 Panel de administración
- 🐳 Dockerizado (listo para desarrollo y despliegue)
- 🗄️ PostgreSQL como base de datos
- 📬 Envío de correo al crear documentos (opcional)

---

## 🛠️ Tecnologías usadas

- **Backend:** Python 3.12, Flask  
- **Base de datos:** PostgreSQL  
- **Frontend:** Jinja2, Bootstrap 5, JavaScript  
- **Contenedores:** Docker, Docker Compose  
- **Exportación:** Pandas + OpenPyXL  
- **Servidor:** Gunicorn  

---

## 📂 Estructura del proyecto

actas_app/
│
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
│
├── templates/
│ ├── base.html
│ ├── login.html
│ ├── dashboard.html
│ ├── formulario.html
│ ├── admin.html
│ ├── admin_documentos.html
│ ├── mis_documentos.html
│
├── static/
│ ├── css/
│ └── js/
│
└── sql/
└── schema.sql


---

## 🧑‍💻 Roles del sistema

### 👤 Usuario
- Crear documentos
- Ver sus documentos
- Exportar documentos
- Recibir notificaciones por correo

### 🛡️ Administrador
- Todas las funciones del usuario
- Editar y eliminar cualquier documento
- Ver todos los documentos
- Gestionar usuarios

---

## 🗄️ Base de datos

El sistema utiliza **PostgreSQL** con:

- Triggers para:
  - Numeración automática anual
  - Generación de código institucional
- Soporte para:
  - Caso Fortuito
  - Gestiones
  - Productos asociados
- Integridad referencial con usuarios

Archivo principal:

Construir y levantar contenedores
docker-compose up --build

Usuario administrador por defecto

Email: william.lopez@arconel.gob.ec
Rol: admin
