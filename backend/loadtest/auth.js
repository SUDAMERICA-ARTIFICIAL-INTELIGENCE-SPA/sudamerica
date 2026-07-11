/**
 * Authentication helper — logs in once and returns reusable headers.
 *
 * Usage in setup():
 *   import { login } from '../auth.js';
 *   export function setup() { return login(); }
 *   export default function (data) { ... use data.headers ... }
 */

import http from 'k6/http';
import { check } from 'k6';
import { BASE_URLS, CREDENTIALS } from './config.js';

/**
 * Authenticate against api-execute and return auth context.
 * Returns { token, tenantId, headers } or fails the test.
 */
export function login() {
  const res = http.post(
    `${BASE_URLS.execute}/api/v1/core/auth/login`,
    JSON.stringify({
      email: CREDENTIALS.email,
      password: CREDENTIALS.password,
    }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  const ok = check(res, {
    'login status 200': (r) => r.status === 200,
    'login has access_token': (r) => {
      try { return !!JSON.parse(r.body).access_token; }
      catch { return false; }
    },
  });

  if (!ok) {
    console.error(`Login failed: ${res.status} ${res.body}`);
    return { token: null, tenantId: null, headers: {} };
  }

  const body = JSON.parse(res.body);
  return {
    token: body.access_token,
    tenantId: body.tenant_id || null,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${body.access_token}`,
    },
  };
}
