/**
 * Flow: full lead lifecycle — create, read, update, list.
 *
 * Creates leads prefixed with LOADTEST- so they can be cleaned up.
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { BASE_URLS, testName } from '../config.js';

const API = BASE_URLS.execute;

export function leadCrudFlow(headers) {
  let leadId = null;

  group('lead_crud', () => {
    // ── Create ──────────────────────────────────────────────────
    const name = testName('lead');
    const createRes = http.post(
      `${API}/api/v1/core/leads`,
      JSON.stringify({
        nombre: name,
        telefono: `+569${Math.floor(10000000 + Math.random() * 89999999)}`,
        canal: 'WEB',
      }),
      { headers },
    );
    check(createRes, {
      'create lead 2xx': (r) => r.status >= 200 && r.status < 300,
      'create lead has id': (r) => {
        try {
          const body = JSON.parse(r.body);
          leadId = (body.data && body.data.id) || body.id || null;
          return !!leadId;
        } catch {
          return false;
        }
      },
    });

    if (!leadId) return;
    sleep(0.3);

    // ── Read ────────────────────────────────────────────────────
    const getRes = http.get(`${API}/api/v1/core/leads/${leadId}`, { headers });
    check(getRes, {
      'get lead 200': (r) => r.status === 200,
    });
    sleep(0.2);

    // ── Update estado ───────────────────────────────────────────
    const patchRes = http.patch(
      `${API}/api/v1/core/leads/${leadId}`,
      JSON.stringify({ estado: 'CONTACTADO' }),
      { headers },
    );
    check(patchRes, {
      'patch lead 200': (r) => r.status === 200,
    });
    sleep(0.2);

    // ── List ────────────────────────────────────────────────────
    const listRes = http.get(`${API}/api/v1/core/leads?page=1&page_size=20`, {
      headers,
    });
    check(listRes, {
      'list leads 200': (r) => r.status === 200,
      'list has data array': (r) => {
        try { return Array.isArray(JSON.parse(r.body).data); }
        catch { return false; }
      },
    });
  });
}
