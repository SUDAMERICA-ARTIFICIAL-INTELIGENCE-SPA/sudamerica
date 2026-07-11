"use client";

import { api } from "@/lib/api";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery } from "@tanstack/react-query";

interface BillingCheckoutResponse {
  checkout_url: string;
  target_plan: string;
  provider: string;
}

export interface BillingUsage {
  plan: string;
  leads_used: number;
  leads_limit: number;
  users_used: number;
  users_limit: number;
  subscription_active: boolean;
  grace_until: string | null;
}

export function useBillingUsage() {
  return useQuery({
    queryKey: ["billing-usage"],
    queryFn: () => api.get<BillingUsage>("/billing/usage"),
  });
}

export function useCreateBillingCheckout() {
  return useMutation({
    mutationFn: (plan: "PLUS" | "PRO") =>
      api.post<BillingCheckoutResponse>("/billing/create-checkout", { plan }),
    onError: (error: Error) => {
      notifications.show({
        color: "red",
        title: "No se pudo iniciar el pago",
        message: error.message,
      });
    },
  });
}
