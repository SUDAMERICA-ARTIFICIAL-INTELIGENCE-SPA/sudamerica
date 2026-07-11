"use client";

import { SucursalesTab } from "@/components/configuracion/SucursalesTab";
import { TenantSettings } from "@/components/configuracion/TenantSettings";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/lib/auth";
import { Stack } from "@mantine/core";

export default function ConfiguracionPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN" || user?.role === "SUPERADMIN";

  return (
    <Stack gap="lg">
      <PageHeader title="Configuracion del Restaurant" />
      <TenantSettings />
      {isAdmin && <SucursalesTab />}
    </Stack>
  );
}
