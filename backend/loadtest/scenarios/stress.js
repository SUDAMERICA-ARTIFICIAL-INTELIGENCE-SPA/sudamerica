/**
 * Stress test — ramp up to find the breaking point.
 *
 * 10 → 50 → 100 VUs over 5 minutes.
 *   k6 run backend/loadtest/scenarios/stress.js
 *
 * Look for: where error rate crosses 5%, where p95 exceeds 10s.
 */

import { sleep } from 'k6';
import { login } from '../auth.js';
import { healthFlow } from '../flows/health.js';
import { leadCrudFlow } from '../flows/lead_crud.js';
import { chatFlow } from '../flows/chat_flow.js';
import { dashboardFlow } from '../flows/dashboard.js';

export const options = {
  stages: [
    { duration: '1m', target: 10 },    // warm up
    { duration: '2m', target: 50 },    // ramp to 50
    { duration: '1m', target: 100 },   // push to 100
    { duration: '1m', target: 0 },     // cool down
  ],
  thresholds: {
    http_req_failed: ['rate<0.10'],       // <10% acceptable under stress
    http_req_duration: ['p(99)<30000'],   // p99 < 30s
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

  sleep(0.5 + Math.random()); // 0.5-1.5s think time (faster pace)
}
