"use client";

import { AUTH_TOKENS_UPDATED_EVENT, getGatewayOrigin } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

function resolveWebSocketBase(): string {
  // Gateway mode: derive wss:// from the single HTTPS gateway origin
  const gateway = getGatewayOrigin();
  if (gateway) {
    return gateway.replace(/^http/, "ws").replace(/\/+$/, "");
  }

  const explicit = process.env.NEXT_PUBLIC_WS_DIALER?.trim();
  if (explicit && explicit !== "undefined" && explicit !== "null") {
    return explicit.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const { hostname } = window.location;
    if (hostname.startsWith("frontend-") && hostname.endsWith(".run.app")) {
      return `wss://ai-dialer${hostname.slice("frontend".length)}`;
    }
  }

  return "ws://localhost:8001";
}

const WS_BASE = resolveWebSocketBase();
const MAX_RECONNECT_DELAY = 30_000;
const BASE_RECONNECT_DELAY = 2_000;

function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;
    const raw = parts[1];
    if (!raw) return true;
    const padded = raw.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(padded)) as { exp?: number };
    if (typeof payload.exp !== "number") return false;
    return payload.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}

interface WsMessage {
  type: "new_message" | "thread_update" | "ping";
  lead_id: string | null;
}

/**
 * Real-time WebSocket for conversation updates.
 *
 * Security note: the JWT is passed as a query parameter because the browser
 * WebSocket API does not support custom headers. The connection uses wss://
 * in production so the token is encrypted in transit. A future backend change
 * can move auth to a post-connect handshake message.
 */
export function useConversationWebSocket() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  const tenantIdRef = useRef(tenantId);
  const queryClientRef = useRef(queryClient);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  const retriesRef = useRef(0);
  const lastTokenRef = useRef<string | null>(null);
  const errorShownRef = useRef(false);

  tenantIdRef.current = tenantId;
  queryClientRef.current = queryClient;

  useEffect(() => {
    function getReconnectDelay(): number {
      return Math.min(
        BASE_RECONNECT_DELAY * 2 ** retriesRef.current,
        MAX_RECONNECT_DELAY,
      );
    }

    function showConnectionWarning(message: string) {
      if (errorShownRef.current) return;
      errorShownRef.current = true;
      notifications.show({
        title: "Tiempo real desconectado",
        message,
        color: "yellow",
      });
    }

    function scheduleReconnect() {
      retriesRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(connect, getReconnectDelay());
    }

    function connect() {
      const tid = tenantIdRef.current;
      if (!tid) return;

      const token = localStorage.getItem("access_token");
      if (!token) return;
      if (isTokenExpired(token)) {
        // Don't spam reconnects with a stale token. The REST layer will refresh
        // on the next authenticated call and fire AUTH_TOKENS_UPDATED_EVENT,
        // which re-invokes connect() via handleTokenUpdate.
        return;
      }
      lastTokenRef.current = token;

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const ws = new WebSocket(`${WS_BASE}/ws/${tid}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        retriesRef.current = 0;
        errorShownRef.current = false;
        queryClientRef.current.invalidateQueries({
          queryKey: ["conversation-messages"],
        });
        queryClientRef.current.invalidateQueries({
          queryKey: ["conversation-threads"],
        });
      };

      ws.onmessage = (event) => {
        if (typeof event.data !== "string") return;

        try {
          const data = JSON.parse(event.data) as WsMessage;

          if (data.type === "ping") return;

          if (data.type === "new_message" && data.lead_id) {
            queryClientRef.current.invalidateQueries({
              queryKey: ["conversation-messages", data.lead_id],
            });
            queryClientRef.current.invalidateQueries({
              queryKey: ["conversation-threads"],
            });
          }

          if (data.type === "thread_update") {
            queryClientRef.current.invalidateQueries({
              queryKey: ["conversation-threads"],
            });
            if (data.lead_id) {
              queryClientRef.current.invalidateQueries({
                queryKey: ["conversation-messages", data.lead_id],
              });
            }
          }
        } catch {
          // Ignore malformed frames.
        }
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        if (intentionalCloseRef.current) return;

        if (event.code === 4401 || event.code === 1008) {
          showConnectionWarning("La sesi\u00f3n del canal en tiempo real expir\u00f3. Reintentando conexi\u00f3n.");
        } else {
          showConnectionWarning("La conexi\u00f3n en tiempo real se perdi\u00f3. Reintentando.");
        }
        scheduleReconnect();
      };

      ws.onerror = () => {
        showConnectionWarning("No se pudo mantener la conexi\u00f3n en tiempo real.");
        ws.close();
      };
    }

    function handleTokenUpdate() {
      const tid = tenantIdRef.current;
      if (!tid) return;

      const nextToken = localStorage.getItem("access_token");
      if (!nextToken || nextToken === lastTokenRef.current) return;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      retriesRef.current = 0;
      connect();
    }

    intentionalCloseRef.current = false;
    retriesRef.current = 0;
    window.addEventListener(AUTH_TOKENS_UPDATED_EVENT, handleTokenUpdate);
    connect();

    return () => {
      intentionalCloseRef.current = true;
      window.removeEventListener(AUTH_TOKENS_UPDATED_EVENT, handleTokenUpdate);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [tenantId]);
}
