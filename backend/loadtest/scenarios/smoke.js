/**
 * Smoke test — quick sanity check that everything responds.
 *
 * 1 VU, 30 seconds. Run after every deploy.
 *   k6 run backend/loadtest/scenarios/smoke.js
 */

import { sleep } from 'k6';
import { login } from '../auth.js';
import { healthFlow } from '../flows/health.js';
import { leadCrudFlow } from '../flows/lead_crud.js';
import { dashboardFlow } from '../flows/dashboard.js';

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],       // <1% errors
    http_req_duration: ['p(95)<5000'],    // p95 < 5s
    checks: ['rate>0.95'],                // >95% checks pass
  },
};

export function setup() {
  return login();
}

export default function (data) {
  healthFlow();
  sleep(0.5);

  if (data.token) {
    leadCrudFlow(data.headers);
    sleep(0.5);
    dashboardFlow(data.headers);
  }

  sleep(1);
}
