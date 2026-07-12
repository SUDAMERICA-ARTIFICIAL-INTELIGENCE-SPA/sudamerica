/**
 * Flow: simulate Evolution API -> canales-service webhook for one tenant.
 *
 * Hits the real hot path used in production: WhatsApp message ingress.
 * Triggers the full pipeline canales-service -> api-execute -> open_agent -> LLM -> sendText.
 *
 * Required env vars:
 *   WEBHOOK_TOKEN    — shared token from canales-service env
 *   TENANT_IDS       — comma-separated tenant UUIDs (must have evolution_instance rows)
 *
 * Optional:
 *   PHONE_PREFIX     — default "5691" (CL mobile); used to build unique JIDs
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { BASE_URLS } from '../config.js';

const CANALES = BASE_URLS.canales;
const WEBHOOK_TOKEN = __ENV.WEBHOOK_TOKEN || '';
const TENANT_IDS = (__ENV.TENANT_IDS || '').split(',').filter(Boolean);
const PHONE_PREFIX = __ENV.PHONE_PREFIX || '5691';

const MESSAGES = [
  'Hola, cual es el horario?',
  'Tienen pizza vegetariana?',
  'Cuanto cuesta el combo familiar?',
  'Puedo reservar una mesa para 4 a las 20:30?',
  'Hacen delivery a Providencia?',
  'Cuales son los metodos de pago?',
  'Necesito la direccion exacta del local',
  'El menu del dia incluye postre?',
  'Pueden traer cubiertos extra?',
  'Tienen opciones sin gluten?',
];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Picks a tenant deterministically from VU id so each VU consistently
 * simulates one "restaurant" (sticky tenant = realistic multi-tenant load).
 */
function pickTenant(vu) {
  if (TENANT_IDS.length === 0) {
    throw new Error('TENANT_IDS env var is required (comma-separated UUIDs)');
  }
  return TENANT_IDS[vu % TENANT_IDS.length];
}

function buildJid(vu, iteration) {
  // 8 unique digits per VU/iteration combo -> distinct conversations
  const suffix = String((vu * 10000 + iteration) % 100000000).padStart(8, '0');
  return `${PHONE_PREFIX}${suffix}@s.whatsapp.net`;
}

export function whatsappWebhookFlow(vu, iteration) {
  if (!WEBHOOK_TOKEN) {
    throw new Error('WEBHOOK_TOKEN env var is required');
  }
  const tenantId = pickTenant(vu);
  const jid = buildJid(vu, iteration);
  const message = pick(MESSAGES);
  const msgId = `LOADTEST-${vu}-${iteration}-${Date.now()}`;

  const payload = {
    event: 'messages.upsert',
    instance: `tenant-${tenantId}`,
    data: {
      key: {
        remoteJid: jid,
        fromMe: false,
        id: msgId,
      },
      message: { conversation: message },
      messageType: 'conversation',
      messageTimestamp: Math.floor(Date.now() / 1000),
      pushName: `LoadTest-${vu}`,
      source: 'android',
      status: 'DELIVERY_ACK',
    },
  };

  group('whatsapp_webhook', () => {
    const res = http.post(
      `${CANALES}/api/v1/canales/webhook/whatsapp?token=${WEBHOOK_TOKEN}`,
      JSON.stringify(payload),
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: '60s',
        tags: { flow: 'whatsapp_webhook', tenant: tenantId },
      },
    );

    check(res, {
      'webhook accepted (2xx)': (r) => r.status >= 200 && r.status < 300,
    });
  });
}
