#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# Sudamérica AI — External Application Load Balancer with path-based routing
# Creates a single HTTPS entry point that routes to Cloud Run services.
#
# Prerequisites:
#   - gcloud CLI authenticated with project owner permissions
#   - Cloud Run services already deployed
#   - APIs enabled: compute.googleapis.com, run.googleapis.com
#
# Usage:
#   chmod +x infra/setup-gateway-lb.sh
#   ./infra/setup-gateway-lb.sh
#
# After running:
#   1. Point your DNS (e.g. api.sudamerica.com) to the reserved IP
#   2. Wait ~15 min for the managed SSL cert to provision
#   3. Rebuild frontend with: NEXT_PUBLIC_API_GATEWAY=https://api.sudamerica.com
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT="sudamerica-prod"
REGION="us-central1"
LB_NAME="sudamerica-gateway"
DOMAIN="api.sudamerica.com"   # <-- Change to your actual domain

# Cloud Run service names (must match deployed services)
# ai-dialer was removed in the refoundation: its user-facing IA endpoints moved to
# api_execute (/api/v1/core/ai/*). open-agent stays internal (service-to-service),
# not fronted by this LB.
SERVICES=(api-execute callback-manual tasks canales-service)

echo "==> Enabling required APIs..."
gcloud services enable compute.googleapis.com --project="$PROJECT"

# ── 1. Reserve a global static IP ────────────────────────────────────
echo "==> Reserving static IP..."
gcloud compute addresses create "${LB_NAME}-ip" \
  --global \
  --project="$PROJECT" 2>/dev/null || echo "    (IP already exists)"

IP=$(gcloud compute addresses describe "${LB_NAME}-ip" \
  --global --project="$PROJECT" --format="get(address)")
echo "    Static IP: $IP  (point DNS A record for $DOMAIN here)"

# ── 2. Create Serverless NEGs (one per Cloud Run service) ────────────
echo "==> Creating Serverless NEGs..."
for SVC in "${SERVICES[@]}"; do
  gcloud compute network-endpoint-groups create "neg-${SVC}" \
    --region="$REGION" \
    --network-endpoint-type=serverless \
    --cloud-run-service="$SVC" \
    --project="$PROJECT" 2>/dev/null || echo "    neg-${SVC} already exists"
done

# ── 3. Create backend services (one per NEG) ─────────────────────────
echo "==> Creating backend services..."
for SVC in "${SERVICES[@]}"; do
  gcloud compute backend-services create "bs-${SVC}" \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project="$PROJECT" 2>/dev/null || echo "    bs-${SVC} already exists"

  gcloud compute backend-services add-backend "bs-${SVC}" \
    --global \
    --network-endpoint-group="neg-${SVC}" \
    --network-endpoint-group-region="$REGION" \
    --project="$PROJECT" 2>/dev/null || echo "    backend already attached"
done

# ── 4. Create URL Map (path-based routing) ───────────────────────────
echo "==> Creating URL Map..."

# Default service = api-execute (handles /api/v1/core/*, /api/v1/admin/*, /api/v1/public/*)
cat > /tmp/sudamerica-url-map.yaml <<'URLMAP'
name: sudamerica-gateway-url-map
defaultService: projects/sudamerica-prod/global/backendServices/bs-api-execute
hostRules:
  - hosts: ["*"]
    pathMatcher: all-paths
pathMatchers:
  - name: all-paths
    defaultService: projects/sudamerica-prod/global/backendServices/bs-api-execute
    routeRules:
      # api-execute WebSocket: /ws/kds/
      - priority: 20
        matchRules:
          - prefixMatch: /ws/kds/
        routeAction:
          weightedBackendServices:
            - backendService: projects/sudamerica-prod/global/backendServices/bs-api-execute
              weight: 100
      # callback-manual: /api/v1/reviews/*
      - priority: 40
        matchRules:
          - prefixMatch: /api/v1/reviews/
        routeAction:
          weightedBackendServices:
            - backendService: projects/sudamerica-prod/global/backendServices/bs-callback-manual
              weight: 100
      # tasks: /api/v1/tasks/*
      - priority: 50
        matchRules:
          - prefixMatch: /api/v1/tasks/
        routeAction:
          weightedBackendServices:
            - backendService: projects/sudamerica-prod/global/backendServices/bs-tasks
              weight: 100
      # canales-service: /api/v1/canales/*
      - priority: 60
        matchRules:
          - prefixMatch: /api/v1/canales/
        routeAction:
          weightedBackendServices:
            - backendService: projects/sudamerica-prod/global/backendServices/bs-canales-service
              weight: 100
URLMAP

gcloud compute url-maps import "${LB_NAME}-url-map" \
  --source=/tmp/sudamerica-url-map.yaml \
  --global \
  --project="$PROJECT" 2>/dev/null || \
gcloud compute url-maps import "${LB_NAME}-url-map" \
  --source=/tmp/sudamerica-url-map.yaml \
  --global \
  --project="$PROJECT" \
  --quiet

echo "    URL Map created/updated"

# ── 5. Create managed SSL certificate ────────────────────────────────
echo "==> Creating managed SSL certificate for $DOMAIN..."
gcloud compute ssl-certificates create "${LB_NAME}-cert" \
  --domains="$DOMAIN" \
  --global \
  --project="$PROJECT" 2>/dev/null || echo "    cert already exists"

# ── 6. Create HTTPS target proxy ─────────────────────────────────────
echo "==> Creating HTTPS proxy..."
gcloud compute target-https-proxies create "${LB_NAME}-https-proxy" \
  --url-map="${LB_NAME}-url-map" \
  --ssl-certificates="${LB_NAME}-cert" \
  --global \
  --project="$PROJECT" 2>/dev/null || echo "    proxy already exists"

# ── 7. Create forwarding rule (binds IP + port 443 to proxy) ─────────
echo "==> Creating forwarding rule..."
gcloud compute forwarding-rules create "${LB_NAME}-https-rule" \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --network-tier=PREMIUM \
  --address="${LB_NAME}-ip" \
  --target-https-proxy="${LB_NAME}-https-proxy" \
  --global \
  --ports=443 \
  --project="$PROJECT" 2>/dev/null || echo "    rule already exists"

# ── 8. (Optional) HTTP → HTTPS redirect ──────────────────────────────
echo "==> Creating HTTP→HTTPS redirect..."
gcloud compute url-maps create "${LB_NAME}-http-redirect" \
  --default-url-redirect-action=HTTPS_REDIRECT \
  --project="$PROJECT" 2>/dev/null || true

gcloud compute target-http-proxies create "${LB_NAME}-http-proxy" \
  --url-map="${LB_NAME}-http-redirect" \
  --global \
  --project="$PROJECT" 2>/dev/null || true

gcloud compute forwarding-rules create "${LB_NAME}-http-rule" \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --network-tier=PREMIUM \
  --address="${LB_NAME}-ip" \
  --target-http-proxy="${LB_NAME}-http-proxy" \
  --global \
  --ports=80 \
  --project="$PROJECT" 2>/dev/null || true

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Load Balancer setup complete!"
echo "============================================"
echo ""
echo "  Static IP:  $IP"
echo "  Domain:     $DOMAIN"
echo ""
echo "  Next steps:"
echo "  1. Add DNS A record:  $DOMAIN → $IP"
echo "  2. Wait ~15 min for SSL cert provisioning"
echo "  3. Rebuild frontend with:"
echo "     NEXT_PUBLIC_API_GATEWAY=https://$DOMAIN"
echo "  4. Verify: curl https://$DOMAIN/api/v1/core/health"
echo ""
echo "  URL Map routing:"
echo "    /api/v1/core/*    → api-execute"
echo "    /api/v1/admin/*   → api-execute"
echo "    /api/v1/public/*  → api-execute"
echo "    /ws/kds/*         → api-execute"
echo "    /api/v1/reviews/* → callback-manual"
echo "    /api/v1/tasks/*   → tasks"
echo "    /api/v1/canales/* → canales-service"
echo ""
