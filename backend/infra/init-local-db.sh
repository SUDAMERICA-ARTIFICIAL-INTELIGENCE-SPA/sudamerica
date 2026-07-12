#!/bin/sh
# Local-only Postgres bootstrap for docker compose.
#
# Runs once, on the FIRST init of an empty pgdata volume (the official postgres
# entrypoint executes files in /docker-entrypoint-initdb.d/ in name order — this
# file is 000_ so it runs before anything else). It applies the FULL canonical
# raw-SQL schema chain from infra/ in numeric order.
#
# Why the whole chain (not just 001/002/003, and not alembic): columns the app
# reads live in later migrations — e.g. agente_config.debounce_seconds is defined
# ONLY in infra/012 and is NOT in the alembic history. The infra chain is the
# complete, canonical local schema; its later files are idempotent catch-ups
# (ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS), safe to apply in order
# on a fresh database.
#
# The glob is restricted to /infra/[0-9]*.sql so non-schema files (README.md,
# PRE_DEPLOY.md, and especially setup-gateway-lb.sh — a GCP script) are ignored.
set -e

echo "[init-local-db] applying infra/*.sql chain to ${POSTGRES_DB} as ${POSTGRES_USER}"
for f in /infra/[0-9]*.sql; do
  echo "[init-local-db] -> $f"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
done
echo "[init-local-db] schema chain applied."
