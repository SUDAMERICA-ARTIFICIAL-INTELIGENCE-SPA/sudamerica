/**
 * Multi-tenant WhatsApp scenario — simulates N tenants sending messages
 * concurrently via the canales-service webhook (the real 1000-restaurant path).
 *
 * Each VU sticks to one tenant (sticky routing), mimicking real restaurants
 * receiving messages from their own customers.
 *
 * USAGE (example: 100 tenants, ~1 msg/sec each, 5 min):
 *   k6 run \
 *     -e WEBHOOK_TOKEN=ad2d7b12... \
 *     -e TENANT_IDS=uuid1,uuid2,...,uuid100 \
 *     -e VUS=100 \
 *     -e DURATION=5m \
 *     backend/loadtest/scenarios/multi_tenant.js
 *
 * The TENANT_IDS must exist in prod DB with matching evolution_instance rows
 * named "tenant-{uuid}". For staging, create fixture tenants first.
 *
 * GOAL: validate capacity for 1000 tenants. Start at 50, ramp to 200, then 500.
 *       Watch for: p95 latency, http_req_failed, Cloud SQL CPU/conns, ai-dialer 429s.
 */

import { sleep } from 'k6';
import { whatsappWebhookFlow } from '../flows/whatsapp_webhook.js';

const VUS = parseInt(__ENV.VUS || '50', 10);
const DURATION = __ENV.DURATION || '5m';
const THINK_MIN = parseFloat(__ENV.THINK_MIN || '2');  // min seconds between messages
const THINK_MAX = parseFloat(__ENV.THINK_MAX || '8');  // max seconds between messages

export const options = {
  scenarios: {
    multi_tenant: {
      executor: 'ramping-vus',
      startVUs: Math.max(1, Math.floor(VUS / 10)),
      stages: [
        { duration: '30s', target: Math.floor(VUS / 2) },  // warm up to half
        { duration: '30s', target: VUS },                   // ramp to full
        { duration: DURATION, target: VUS },                // hold
        { duration: '30s', target: 0 },                     // ramp down
      ],
      gracefulRampDown: '20s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],           // <5% errors overall
    http_req_duration: ['p(95)<15000'],       // p95 under 15s (LLM-bound)
    'http_req_duration{flow:whatsapp_webhook}': ['p(99)<30000'],
    checks: ['rate>0.95'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  whatsappWebhookFlow(__VU, __ITER);
  sleep(THINK_MIN + Math.random() * (THINK_MAX - THINK_MIN));
}

export function handleSummary(data) {
  const trends = data.metrics.http_req_duration;
  const p = (k) => (trends.values[k] || 0).toFixed(0);
  const failed = (data.metrics.http_req_failed.values.rate * 100).toFixed(2);
  const reqs = data.metrics.http_reqs.values.count;
  const rate = (data.metrics.http_reqs.values.rate).toFixed(2);

  const summary = `
==========================================
Multi-tenant load test results
==========================================
VUs:              ${VUS}
Duration:         ${DURATION}
Requests:         ${reqs} (${rate} req/s)
Failed:           ${failed}%
Latency (ms):
  median          ${p('med')}
  p95             ${p('p(95)')}
  p99             ${p('p(99)')}
  max             ${p('max')}
==========================================
`;
  return {
    stdout: summary,
    'loadtest-results.json': JSON.stringify(data, null, 2),
  };
}
