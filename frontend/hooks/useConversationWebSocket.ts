"use client";

/**
 * Real-time conversation updates via WebSocket — INTENTIONALLY DISABLED.
 *
 * The WebSocket used to connect to the ai-dialer service
 * (`ws://localhost:8001` / `wss://ai-dialer…`), which no longer exists after the
 * refoundation. api_execute does not (yet) expose a `/ws` endpoint, so this hook
 * is a deliberate no-op instead of dialing a dead host. The conversation viewer
 * stays fresh through react-query polling: threads every 15s and messages every
 * 5s (see `useConversationThreads` / `useConversationMessages`).
 *
 * TODO(paso3+): if a WebSocket is added to api_execute under
 * `/api/v1/core/ai/ws/{tenant_id}` (reconciling close codes 4401/1008 with the
 * old client), restore the connect / reconnect / token-refresh logic here and
 * derive the `wss://` base from the api_execute origin — do NOT reintroduce the
 * `ws://localhost:8001` / `wss://ai-dialer` fallbacks.
 */
export function useConversationWebSocket(): void {
  // No-op: polling in the conversation hooks keeps the viewer up to date.
}
