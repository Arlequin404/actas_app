# El servicio de respaldos debe usar exactamente la misma versión mayor de
# pg_dump/pg_restore que el servidor PostgreSQL. Al heredar de postgres:16,
# evitamos que Debian instale automáticamente un cliente 17/18 incompatible.
FROM postgres:16-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv curl \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY services/backup_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/backup_service/ ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /backup-state \
    && chown -R appuser:appuser /app /opt/venv /backup-state

# Quita el entrypoint del contenedor oficial de PostgreSQL. Este contenedor
# solo aporta las herramientas cliente v16; no inicia otro servidor.
ENTRYPOINT []
USER appuser
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
