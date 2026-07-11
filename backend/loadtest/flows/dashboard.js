/**
 * Flow: simulate a user opening the dashboard.
 *
 * Fires parallel requests like the frontend does on page load:
 * metrics, products, leads, ventas.
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { BASE_URLS } from '../config.js';

const API = BASE_URLS.execute;

export function dashboardFlow(headers) {
  group('dashboard', () => {
    const responses = http.batch([
      ['GET', `${API}/api/v1/core/metricas/dashboard`, null, { headers }],
      ['GET', `${API}/api/v1/core/productos?page=1&page_size=50`, null, { headers }],
      ['GET', `${API}/api/v1/core/leads?page=1&page_size=20`, null, { headers }],
      ['GET', `${API}/api/v1/core/ventas?page=1&page_size=20`, null, { headers }],
    ]);

    check(responses[0], {
      'metricas 200': (r) => r.status === 200,
    });
    check(responses[1], {
      'productos 200': (r) => r.status === 200,
    });
    check(responses[2], {
      'leads 200': (r) => r.status === 200,
    });
    check(responses[3], {
      'ventas 200': (r) => r.status === 200,
    });
  });
}
