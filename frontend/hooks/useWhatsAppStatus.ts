"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

interface QRResponse {
  qr_code: string;
  instance_name: string;
  status: string;
}

interface InstanceSettingsPayload {
  reject_call: boolean;
  always_online: boolean;
  read_messages: boolean;
}

interface InstanceSettingsResponse {
  success: boolean;
  instance_name: string;
}

interface UseWhatsAppStatusOptions {
  enabled?: boolean;
  refetchInterval?: number | false;
}

export function useWhatsAppStatus(options: UseWhatsAppStatusOptions = {}) {
  const { tenantId } = useAuth();
  const { enabled = true, refetchInterval = false } = options;

  return useQuery({
    queryKey: ["whatsapp-status", tenantId],
    queryFn: () => api.get<QRResponse>(`/qr/${tenantId}/status`, { service: "canales" }),
    enabled: Boolean(tenantId) && enabled,
    refetchInterval,
    retry: false,
    meta: { silent: true },
  });
}

export function useGenerateQR() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (phoneNumber?: string) =>
      api.post<QRResponse>(
        `/qr/${tenantId}`,
        phoneNumber ? { phone_number: phoneNumber } : {},
        { service: "canales" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
    onError: () => {
      notifications.show({
        title: "Error",
        message: "No se pudo generar el código QR",
        color: "red",
      });
    },
  });
}

export function useDisconnectWhatsApp() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.delete<{ status: string }>(`/qr/${tenantId}`, { service: "canales" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-status"] });
      notifications.show({
        title: "Desconectado",
        message: "WhatsApp desconectado correctamente. Puedes conectar otro número.",
        color: "blue",
      });
    },
    onError: () => {
      notifications.show({
        title: "Error",
        message: "No se pudo desconectar WhatsApp",
        color: "red",
      });
    },
  });
}

export function useConfigureInstance() {
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (payload: InstanceSettingsPayload) =>
      api.post<InstanceSettingsResponse>(`/whatsapp/instance/${tenantId}/settings`, payload, {
        service: "canales",
      }),
    onSuccess: () => {
      notifications.show({
        title: "Configurado",
        message: "Instancia WhatsApp configurada correctamente",
        color: "green",
      });
    },
    onError: () => {
      notifications.show({
        title: "Error",
        message: "No se pudo configurar la instancia",
        color: "red",
      });
    },
  });
}
