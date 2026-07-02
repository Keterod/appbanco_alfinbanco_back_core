# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependencias del sistema para compilar psycopg2 (binary ya incluye
# la mayoria, pero dejamos libpq para conexiones SSL robustas).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render asigna el puerto en la variable PORT.
EXPOSE 8003

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8003}"]
