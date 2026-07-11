/**
 * Flow: hit /health/ready on every service.
 * No auth required — health endpoints are public.
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { BASE_URLS } from '../config.js';

export function healthFlow() {
  group('health checks', () => {
    for (const [name, url] of Object.entries(BASE_URLS)) {
      const res = http.get(`${url}/health/ready`, { tags: { service: name } });
      check(res, {
        [`${name} ready 200`]: (r) => r.status === 200,
        [`${name} status ok`]: (r) => {
          try {
            const s = JSON.parse(r.body).status;
            return s === 'healthy' || s === 'degraded';
          } catch {
            return false;
          }
        },
      });
    }
  });
}
