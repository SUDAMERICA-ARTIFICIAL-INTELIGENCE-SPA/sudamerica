/**
 * Flow: send a message through the AI pipeline.
 *
 * Hits api-execute /ai/process-message which orchestrates LLM generation
 * via open_agent (pipeline: api-execute -> open_agent -> LLM).
 * This is the heaviest flow (LLM latency) — expect 3-15s responses.
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { BASE_URLS } from '../config.js';

const API = BASE_URLS.execute;

const MESSAGES = [
  'Hola, quiero ver el menu',
  'Cuanto cuesta la pizza margarita?',
  'Tienen delivery a Las Condes?',
  'Quiero hacer un pedido para llevar',
  'Cuales son los horarios de atencion?',
  'Hay opciones vegetarianas?',
  'Me pueden dar el numero de telefono?',
  'Quiero reservar una mesa para 4 personas',
];

function randomMessage() {
  return MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
}

export function chatFlow(headers) {
  group('chat_flow', () => {
    const res = http.post(
      `${API}/api/v1/core/ai/process-message`,
      JSON.stringify({
        message: randomMessage(),
        canal: 'WEB',
      }),
      { headers, timeout: '30s' },
    );

    check(res, {
      'chat 200': (r) => r.status === 200,
      'chat has response': (r) => {
        try {
          const body = JSON.parse(r.body);
          return !!(body.response || body.reply || body.message);
        } catch {
          return false;
        }
      },
    });

    sleep(1);
  });
}
