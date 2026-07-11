FROM python:3.12-slim

WORKDIR /app

# System deps (asyncpg not needed — open_agent has no DB)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Shared package — placed so "from shared.X import Y" works
COPY shared/ /opt/shared/
ENV PYTHONPATH="/opt"

# Service dependencies
COPY open_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Service code
COPY --chown=appuser:appgroup open_agent/app ./app

USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
