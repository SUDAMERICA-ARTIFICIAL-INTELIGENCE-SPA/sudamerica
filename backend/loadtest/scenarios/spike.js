/**
 * Spike test — measure cold start impact.
 *
 * Quiet baseline → instant spike to 100 VUs → sustain → cool down.
 *   k6 run backend/loadtest/scenarios/spike.js
 *
 * Cloud Run scales from 0 (or min-instances). First requests hit cold
 * starts (~2-5s penalty). This test measures how long the spike takes
 * to stabilize and what error rate occurs during scale-up.
 */

import { sleep } from 'k6';
import { login } from '../auth.js';
import { healthFlow } from '../flows/health.js';
import { dashboardFlow } from '../flows/dashboard.js';
import { leadCrudFlow } from '../flows/lead_crud.js';

export const options = {
  stages: [
    { duration: '10s', target: 5 },     // quiet baseline
    { duration: '5s', target: 100 },    // instant spike
    { duration: '30s', target: 100 },   // sustain peak
    { duration: '10s', target: 5 },     // back to normal
  ],
  thresholds: {
    http_req_duration: ['p(95)<15000'],  // p95 < 15s (cold starts)
  },
};

export function setup() {
  return login();
}

export default function (data) {
  if (!data.token) {
    healthFlow();
    sleep(1);
    return;
  }

  // Mix of light and medium flows — no chat (LLM) to isolate infra latency
  const roll = Math.random();
  if (roll < 0.5) {
    dashboardFlow(data.headers);
  } else if (roll < 0.85) {
    leadCrudFlow(data.headers);
  } else {
    healthFlow();
  }

  sleep(0.5);
}
