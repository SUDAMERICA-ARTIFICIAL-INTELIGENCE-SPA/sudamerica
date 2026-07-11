#!/bin/bash
set -euo pipefail

# NOTE: ai-dialer is intentionally NOT part of this monorepo (removed in the
# Sudamérica refoundation). This script deploys the ported services only.

PROJECT_ID="melodic-nature-484617-e6"
REGION="us-central1"
REPO="sudamerica"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"
CLOUDSQL_INSTANCE="${PROJECT_ID}:${REGION}:sudamerica-db"
EVOLUTION_DB_NAME="${EVOLUTION_DB_NAME:-evolution_db}"
EVOLUTION_API_KEY="${EVOLUTION_API_KEY:-$(openssl rand -hex 32)}"

build_evolution_database_uri() {
  local database_url="$1"
  local database_name="$2"
  local credentials
  local socket_path

  credentials="$(printf '%s' "${database_url}" | sed -E 's#^postgresql\+asyncpg://([^@]+)@.*#\1#')"
  socket_path="$(printf '%s' "${database_url}" | sed -n 's/.*host=\([^&]*\).*/\1/p')"

  if [ -z "${credentials}" ] || [ -z "${socket_path}" ]; then
    echo "ERROR: Could not derive Evolution DATABASE_CONNECTION_URI from DATABASE_URL." >&2
    exit 1
  fi

  printf 'postgresql://%s@localhost/%s?host=%s&schema=public' \
    "${credentials}" \
    "${database_name}" \
    "${socket_path}"
}

# --- Required env vars (pass via env or they'll be prompted) ---
JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"
DATABASE_URL="${DATABASE_URL:-}"

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL is required."
  echo "  export DATABASE_URL='postgresql+asyncpg://user:pass@host:5432/sudamerica'"
  echo "  Then re-run this script."
  exit 1
fi

echo "=== Config ==="
echo "  Project:  ${PROJECT_ID}"
echo "  Region:   ${REGION}"
echo "  Registry: ${REGISTRY}"
echo "  DB:       ${DATABASE_URL%%@*}@***"
echo ""

# --- Step 1: Enable APIs & Create Artifact Registry ---
echo "=== Step 1: Enable APIs & Artifact Registry ==="
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project ${PROJECT_ID}

gcloud artifacts repositories create ${REPO} \
  --repository-format=docker \
  --location=${REGION} \
  --project=${PROJECT_ID} 2>/dev/null || echo "  Repository already exists"

# --- Step 2: Build backend images ---
echo ""
echo "=== Step 2: Build backend images (Cloud Build) ==="
cd backend
gcloud builds submit \
  --config cloudbuild.yaml \
  --project ${PROJECT_ID} \
  --substitutions "SHORT_SHA=$(git rev-parse --short HEAD)" \
  --timeout 900
cd ..

# --- Step 3: Deploy backend services ---
echo ""
echo "=== Step 3: Deploy backend services ==="

COMMON_ENV="JWT_SECRET_KEY=${JWT_SECRET_KEY},DATABASE_URL=${DATABASE_URL},LOG_LEVEL=INFO"
EVOLUTION_DATABASE_URI="$(build_evolution_database_uri "${DATABASE_URL}" "${EVOLUTION_DB_NAME}")"

for SVC in api-execute callback-manual tasks canales-service; do
  echo "  Deploying ${SVC}..."
  gcloud run deploy ${SVC} \
    --image ${REGISTRY}/${SVC}:latest \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "${COMMON_ENV}" \
    --quiet
done

echo "  Deploying evolution-api..."
gcloud run deploy evolution-api \
  --image ${REGISTRY}/evolution-api:latest \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 1 \
  --no-cpu-throttling \
  --timeout 300 \
  --add-cloudsql-instances ${CLOUDSQL_INSTANCE} \
  --set-env-vars "^|^SERVER_NAME=evolution|SERVER_TYPE=http|SERVER_PORT=8080|SERVER_URL=https://evolution-api-pending.run.app|CORS_ORIGIN=*|AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}|AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true|DATABASE_PROVIDER=postgresql|DATABASE_CONNECTION_URI=${EVOLUTION_DATABASE_URI}|DATABASE_CONNECTION_CLIENT_NAME=evolution_exchange|DATABASE_SAVE_DATA_INSTANCE=true|DATABASE_SAVE_DATA_NEW_MESSAGE=true|DATABASE_SAVE_MESSAGE_UPDATE=true|DATABASE_SAVE_DATA_CONTACTS=true|DATABASE_SAVE_DATA_CHATS=true|DATABASE_SAVE_DATA_LABELS=true|DATABASE_SAVE_DATA_HISTORIC=true|CACHE_REDIS_ENABLED=false|CACHE_LOCAL_ENABLED=true|WEBSOCKET_ENABLED=true|WEBSOCKET_GLOBAL_EVENTS=true|WEBHOOK_GLOBAL_ENABLED=false|DEL_INSTANCE=false|LOG_LEVEL=ERROR,WARN,DEBUG,INFO,LOG,WEBHOOKS,WEBSOCKET|CONFIG_SESSION_PHONE_CLIENT=Evolution API|CONFIG_SESSION_PHONE_NAME=Chrome|QRCODE_LIMIT=30" \
  --quiet

# --- Step 4: Get service URLs ---
echo ""
echo "=== Step 4: Get service URLs ==="
API_EXECUTE_URL=$(gcloud run services describe api-execute --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
CALLBACK_URL=$(gcloud run services describe callback-manual --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
TASKS_URL=$(gcloud run services describe tasks --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
CANALES_URL=$(gcloud run services describe canales-service --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
EVOLUTION_URL=$(gcloud run services describe evolution-api --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')

echo "  api-execute:     ${API_EXECUTE_URL}"
echo "  callback-manual: ${CALLBACK_URL}"
echo "  tasks:           ${TASKS_URL}"
echo "  canales-service: ${CANALES_URL}"
echo "  evolution-api:   ${EVOLUTION_URL}"

# --- Step 5: Wire inter-service URLs ---
echo ""
echo "=== Step 5: Wire inter-service env vars ==="

# api-execute → CALLBACK, TASKS
gcloud run services update api-execute \
  --region ${REGION} --project ${PROJECT_ID} \
  --update-env-vars "SERVICE_CALLBACK_URL=${CALLBACK_URL},SERVICE_TASKS_URL=${TASKS_URL},FRONTEND_URL=https://frontend-pending.run.app" \
  --quiet

# callback-manual → TASKS
gcloud run services update callback-manual \
  --region ${REGION} --project ${PROJECT_ID} \
  --update-env-vars "SERVICE_TASKS_URL=${TASKS_URL},FRONTEND_URL=https://frontend-pending.run.app" \
  --quiet

# tasks → API_EXECUTE
gcloud run services update tasks \
  --region ${REGION} --project ${PROJECT_ID} \
  --update-env-vars "FRONTEND_URL=https://frontend-pending.run.app" \
  --quiet

gcloud run services update canales-service \
  --region ${REGION} --project ${PROJECT_ID} \
  --update-env-vars "^|^SERVICE_API_EXECUTE_URL=${API_EXECUTE_URL}|EVOLUTION_WEBHOOK_URL=${CANALES_URL}/api/v1/canales/webhook/whatsapp|EVOLUTION_API_URL=${EVOLUTION_URL}|EVOLUTION_API_KEY=${EVOLUTION_API_KEY}|FRONTEND_URL=https://frontend-pending.run.app" \
  --quiet

gcloud run services update evolution-api \
  --region ${REGION} --project ${PROJECT_ID} \
  --update-env-vars "SERVER_URL=${EVOLUTION_URL}" \
  --quiet

# --- Step 6: Build frontend with backend URLs baked in ---
echo ""
echo "=== Step 6: Build & deploy frontend ==="
cd frontend

# Cloud Build with build args for NEXT_PUBLIC vars
cat > /tmp/cloudbuild-frontend.yaml <<CBEOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_EXECUTE=${API_EXECUTE_URL}'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_CALLBACK=${CALLBACK_URL}'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_CANALES=${CANALES_URL}'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_TASKS=${TASKS_URL}'
      - '-t'
      - '${REGISTRY}/frontend:latest'
      - '.'
images:
  - '${REGISTRY}/frontend:latest'
options:
  logging: CLOUD_LOGGING_ONLY
CBEOF

gcloud builds submit \
  --config /tmp/cloudbuild-frontend.yaml \
  --project ${PROJECT_ID} \
  --timeout 900

gcloud run deploy frontend \
  --image ${REGISTRY}/frontend:latest \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars "NODE_ENV=production" \
  --quiet

cd ..

FRONTEND_URL=$(gcloud run services describe frontend --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')

# --- Step 7: Update FRONTEND_URL on backends ---
echo ""
echo "=== Step 7: Update FRONTEND_URL on all backends ==="
for SVC in api-execute callback-manual tasks canales-service; do
  gcloud run services update ${SVC} \
    --region ${REGION} --project ${PROJECT_ID} \
    --update-env-vars "FRONTEND_URL=${FRONTEND_URL}" \
    --quiet
done

# --- Done ---
echo ""
echo "============================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================"
echo ""
echo "Service URLs:"
echo "  Frontend:        ${FRONTEND_URL}"
echo "  api-execute:     ${API_EXECUTE_URL}"
echo "  callback-manual: ${CALLBACK_URL}"
echo "  tasks:           ${TASKS_URL}"
echo "  canales-service: ${CANALES_URL}"
echo "  evolution-api:   ${EVOLUTION_URL}"
echo ""
echo "Optional secrets to set later:"
echo "  api-execute:   STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET"
echo "  callback:      OPENAI_API_KEY (Whisper)"
echo "  tasks:         SMTP_*"
echo "  canales:       usa evolution-api en Cloud Run"
echo ""
echo "Example:"
echo "  gcloud run services update api-execute --region ${REGION} --project ${PROJECT_ID} \\"
echo "    --update-env-vars 'STRIPE_SECRET_KEY=sk_live_xxx'"
