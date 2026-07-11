FROM python:3.12-slim

WORKDIR /app

# System deps (asyncpg, psycopg2, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Shared package — placed so "from shared.X import Y" works
COPY shared/ /opt/shared/
ENV PYTHONPATH="/opt"

# Service dependencies
COPY callback_manual/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Service code
COPY --chown=appuser:appgroup callback_manual/app ./app

USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
