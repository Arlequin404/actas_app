import os

# Configuración de base de datos (controlada por env; los valores por defecto funcionan con docker-compose)
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'actas_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'host': os.getenv('POSTGRES_HOST', 'db'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),    
}

# Clave secreta de Flask
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

# Configuración SMTP
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp')
SMTP_FROM   = os.getenv('SMTP_FROM', 'notificaciones@actas.com')
SMTP_PORT   = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER   = os.getenv('SMTP_USER', '')
SMTP_PASS   = os.getenv('SMTP_PASS', '')
SMTP_TLS    = os.getenv('SMTP_TLS', 'true').lower() == 'true'
