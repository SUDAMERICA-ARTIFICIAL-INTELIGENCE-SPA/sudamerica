/**
 * Shared configuration for all k6 load test scripts.
 *
 * Override any URL via environment variables:
 *   k6 run -e API_EXECUTE_URL=http://localhost:8000 scenarios/smoke.js
 */

export const BASE_URLS = {
  execute:
    __ENV.API_EXECUTE_URL ||
    'https://api-execute-456595931835.us-central1.run.app',
  dialer:
    __ENV.AI_DIALER_URL ||
    'https://ai-dialer-456595931835.us-central1.run.app',
  callback:
    __ENV.CALLBACK_URL ||
    'https://callback-manual-456595931835.us-central1.run.app',
  tasks:
    __ENV.TASKS_URL ||
    'https://tasks-456595931835.us-central1.run.app',
  canales:
    __ENV.CANALES_URL ||
    'https://canales-service-456595931835.us-central1.run.app',
  agent:
    __ENV.AGENT_URL ||
    'https://open-agent-456595931835.us-central1.run.app',
};

export const CREDENTIALS = {
  email: __ENV.TEST_EMAIL || 'admin@sudamerica.ai',
  password: __ENV.TEST_PASSWORD || 'Sudamérica2026Prod',
};

/** Prefix for test data so it can be filtered/cleaned. */
export const TEST_PREFIX = 'LOADTEST';

/** Generate a unique test name with timestamp. */
export function testName(label) {
  return `${TEST_PREFIX}-${label}-${Date.now()}`;
}
