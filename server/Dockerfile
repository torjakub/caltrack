FROM python:3.12-slim

# Enables the insecure-default-JWT-secret startup check in app/main.py.
ENV ENVIRONMENT=production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data \
    && useradd --system --uid 1000 caltrack \
    && chown -R caltrack:caltrack /app /data
USER caltrack

# The bind-mounted ./data must be writable by uid 1000 (see docker-compose.yml).
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
