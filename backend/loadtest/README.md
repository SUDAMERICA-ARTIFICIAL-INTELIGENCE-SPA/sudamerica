# Load Testing (k6)

Load tests for the 6 Sudamérica AI microservices on Cloud Run.

## Install k6

```bash
# Windows (chocolatey)
choco install k6

# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

## Run scenarios

```bash
# Smoke test — quick sanity check after deploy (~30s)
k6 run backend/loadtest/scenarios/smoke.js

# Baseline — normal load, measure typical latency (~2 min)
k6 run backend/loadtest/scenarios/baseline.js

# Stress — find breaking point, ramp to 100 VUs (~5 min)
k6 run backend/loadtest/scenarios/stress.js

# Spike — cold start impact, instant 100 VUs (~1 min)
k6 run backend/loadtest/scenarios/spike.js
```

## Override URLs (local or staging)

```bash
k6 run -e API_EXECUTE_URL=http://localhost:8000 \
       -e AI_DIALER_URL=http://localhost:8001 \
       backend/loadtest/scenarios/smoke.js
```

All `BASE_URLS` in `config.js` can be overridden with `-e VAR=value`.

## Override credentials

```bash
k6 run -e TEST_EMAIL=test@example.com \
       -e TEST_PASSWORD=secret \
       backend/loadtest/scenarios/baseline.js
```

## Reading results

k6 prints a summary table with these key metrics:

| Metric | What to look for |
|--------|-----------------|
| `http_req_duration` p95 | > 10s = latency problem |
| `http_req_failed` | > 5% = error rate problem |
| `http_reqs` rate | plateau = throughput ceiling |
| `checks` | < 90% = functional failures |

## Scenarios

| Scenario | VUs | Duration | Purpose |
|----------|-----|----------|---------|
| smoke | 1 | 30s | Sanity check — everything responds |
| baseline | 10 | 2 min | Normal load — typical latency |
| stress | 10→100 | 5 min | Find breaking point |
| spike | 5→100 | ~1 min | Cold start impact |
| multi_tenant | configurable | configurable | Multi-tenant WhatsApp webhook (1000-tenant readiness) |

### multi_tenant

Simulates N restaurant tenants sending WhatsApp messages concurrently through
the canales-service webhook — the real hot path for scale. Each VU sticks to
one tenant (sticky routing).

```bash
# 50 tenants, 5 min (first gate before 1000):
k6 run \
  -e WEBHOOK_TOKEN=<from canales-service env> \
  -e TENANT_IDS=uuid1,uuid2,...,uuid50 \
  -e VUS=50 -e DURATION=5m \
  backend/loadtest/scenarios/multi_tenant.js

# 200 tenants (stress-test Cloud SQL pool after upgrade):
k6 run \
  -e WEBHOOK_TOKEN=... -e TENANT_IDS=... \
  -e VUS=200 -e DURATION=10m \
  backend/loadtest/scenarios/multi_tenant.js
```

Each tenant in `TENANT_IDS` must have a matching `evolution_instance` row
named `tenant-{uuid}`. For fresh fixtures create them via api-execute onboarding.

## Flows

| Flow | Services hit | Weight in baseline |
|------|-------------|-------------------|
| `dashboard.js` | api-execute (4 parallel GETs) | 40% |
| `lead_crud.js` | api-execute (create, read, update, list) | 30% |
| `chat_flow.js` | api-execute → ai-dialer (LLM) | 20% |
| `health.js` | all 6 services /health/ready | 10% |

## Cleanup

Test leads are created with the prefix `LOADTEST-`. To clean up:

```sql
DELETE FROM leads WHERE nombre LIKE 'LOADTEST-%';
```
