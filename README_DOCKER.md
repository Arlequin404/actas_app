# Actas App — Docker + InitDB

## Pasos rápidos
1. Copia `.env.example` a `.env` y ajusta si deseas.
2. Levanta todo:
   ```bash
   docker compose up -d --build
   ```
3. App: http://localhost:8080  
   PgAdmin: http://localhost:5050 (usa credenciales del `.env`).

## Base de datos
- La primera vez que se crea el volumen de Postgres, se ejecuta `initdb/02_schema.sql`
  y se crean tablas + usuario admin (`admin@actas.local` / `admin123`).

## Si ya tenías datos y NO quieres borrar el volumen
Aplica el esquema manualmente:
```bash
# En PowerShell:
Get-Content .\initdb\02_schema.sql | docker exec -i actas_db psql -U postgres -d actas_db
# En bash:
docker exec -i actas_db psql -U postgres -d actas_db < initdb/02_schema.sql
```

## Notas
- `config.py` toma credenciales desde variables de entorno.
- `app.py` ahora usa `get_conn()` para abrir conexión a demanda (evita fallas al bootear).
- Revisa seguridad de contraseñas: te recomiendo mover a bcrypt después.
