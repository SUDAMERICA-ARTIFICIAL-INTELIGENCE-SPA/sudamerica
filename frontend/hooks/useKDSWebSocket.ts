"use client";

import { getGatewayOrigin } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

/** KDS event types sent by the backend WebSocket. */
interface KDSEvent {
  type: "comanda_created" | "comanda_updated" | "comanda_deleted" | "ping";
  data?: Record<string, unknown>;
}

/**
 * Resolve the WebSocket origin for api_execute.
 *
 * Resolution order:
 * 1. NEXT_PUBLIC_API_GATEWAY (single gateway — LB routes /ws/kds/* to api-execute)
 * 2. Explicit NEXT_PUBLIC_API_EXECUTE env var
 * 3. Infer Cloud Run origin from current hostname
 * 4. Fallback to localhost:8000
 *
 * Then convert http(s) to ws(s).
 */
function getKDSWebSocketUrl(tenantId: string, accessToken: string): string {
  let origin: string;

  const gateway = getGatewayOrigin();
  if (gateway) {
    origin = gateway;
  } else {
    const explicit = process.env.NEXT_PUBLIC_API_EXECUTE?.trim();
    if (explicit && explicit !== "undefined" && explicit !== "null") {
      origin = explicit.replace(/\/+$/, "");
    } else if (
      typeof window !== "undefined" &&
      window.location.hostname.startsWith("frontend-") &&
      window.location.hostname.endsWith(".run.app")
    ) {
      const { hostname, protocol } = window.location;
      origin = `${protocol}//api-execute${hostname.slice("frontend".length)}`;
    } else {
      origin = "http://localhost:8000";
    }
  }

  // Convert http(s) -> ws(s)
  const wsOrigin = origin.replace(/^http/, "ws");
  return `${wsOrigin}/ws/kds/${tenantId}?token=${encodeURIComponent(accessToken)}`;
}

const MAX_BACKOFF_MS = 30_000;
const BASE_BACKOFF_MS = 1_000;

export function useKDSWebSocket(): { isConnected: boolean } {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const unmountedRef = useRef(false);

  const onNewComanda = useCallback(() => {
    // Dispatch a custom event so KDSBoard can play audio / flash
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("kds:new-comanda"));
    }
  }, []);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const accessToken =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;

    if (!tenantId || !accessToken) return;

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    const url = getKDSWebSocketUrl(tenantId, accessToken);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmountedRef.current) return;
      setIsConnected(true);
      attemptRef.current = 0; // Reset backoff on successful connection
    };

    ws.onmessage = (event) => {
      if (unmountedRef.current) return;
      try {
        const parsed = JSON.parse(event.data) as KDSEvent;
        if (parsed.type === "ping") return; // Ignore keepalive pings

        // Invalidate all comanda queries so TanStack Query refetches
        void queryClient.invalidateQueries({ queryKey: ["comandas"] });

        if (parsed.type === "comanda_created") {
          onNewComanda();
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setIsConnected(false);
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      // onerror is always followed by onclose, so reconnect logic lives there
    };
  }, [tenantId, queryClient, onNewComanda]);

  const scheduleReconnect = useCallback(() => {
    if (unmountedRef.current) return;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);

    const delay = Math.min(
      BASE_BACKOFF_MS * 2 ** attemptRef.current,
      MAX_BACKOFF_MS,
    );
    attemptRef.current += 1;

    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;
      connect();
    }, delay);
  }, [connect]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [connect]);

  return { isConnected };
}
