import os

# Database configuration (env-driven; defaults work with docker-compose)
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'actas_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'host': os.getenv('POSTGRES_HOST', 'db'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),    
}

# Flask secret key
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

# SMTP settings
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp')
SMTP_FROM   = os.getenv('SMTP_FROM', 'notificaciones@actas.com')
SMTP_PORT   = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER   = os.getenv('SMTP_USER', '')
SMTP_PASS   = os.getenv('SMTP_PASS', '')
SMTP_TLS    = os.getenv('SMTP_TLS', 'true').lower() == 'true'
