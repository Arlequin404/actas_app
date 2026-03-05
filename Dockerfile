# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario ANTES
RUN useradd -ms /bin/bash appuser

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Copiar código
COPY app /app

# 🔑 DAR PERMISOS CORRECTOS
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "300", "app:app"]
