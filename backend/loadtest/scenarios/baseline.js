/**
 * Baseline test — normal load to measure typical latency.
 *
 * 10 VUs, 2 minutes. Simulates ~10 concurrent users.
 *   k6 run backend/loadtest/scenarios/baseline.js
 *
 * Traffic mix:
 *   40% dashboard  — most common action
 *   30% lead CRUD  — sales team activity
 *   20% chat       — AI pipeline (heavy)
 *   10% health     — monitoring
 */

import { sleep } from 'k6';
import { login } from '../auth.js';
import { healthFlow } from '../flows/health.js';
import { leadCrudFlow } from '../flows/lead_crud.js';
import { chatFlow } from '../flows/chat_flow.js';
import { dashboardFlow } from '../flows/dashboard.js';

export const options = {
  vus: 10,
  duration: '2m',
  thresholds: {
    http_req_failed: ['rate<0.05'],        // <5% errors
    http_req_duration: ['p(95)<10000'],    // p95 < 10s
    checks: ['rate>0.90'],                 // >90% checks pass
  },
};

export function setup() {
  return login();
}

export default function (data) {
  if (!data.token) {
    healthFlow();
    sleep(2);
    return;
  }

  const roll = Math.random();
  if (roll < 0.4) {
    dashboardFlow(data.headers);
  } else if (roll < 0.7) {
    leadCrudFlow(data.headers);
  } else if (roll < 0.9) {
    chatFlow(data.headers);
  } else {
    healthFlow();
  }

  sleep(1 + Math.random() * 2); // 1-3s think time
}
