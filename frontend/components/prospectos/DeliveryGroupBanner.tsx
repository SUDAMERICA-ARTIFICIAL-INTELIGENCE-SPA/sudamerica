"use client";

import { useSucursales } from "@/hooks/useSucursales";
import { api } from "@/lib/api";
import type { Sucursal } from "@/lib/types";
import { useUiStore } from "@/stores/ui-store";
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconTruckDelivery, IconUsers } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

interface GrupoRepartidoresResolved {
  grupo_repartidores_jid: string | null;
}

export function DeliveryGroupBanner() {
  const { data: sucursalesRaw } = useSucursales();
  const { activeSucursalId } = useUiStore();
  const queryClient = useQueryClient();
  const [opened, { open, close }] = useDisclosure(false);

  const sucursales: Sucursal[] = useMemo(() => {
    if (!sucursalesRaw) return [];
    if (Array.isArray(sucursalesRaw))
      return sucursalesRaw.filter((s) => s.activo);
    const raw = sucursalesRaw as unknown as { data?: Sucursal[] };
    return (raw.data ?? []).filter((s) => s.activo);
  }, [sucursalesRaw]);

  const missingSucursales = useMemo(
    () => sucursales.filter((s) => !s.grupo_repartidores_jid),
    [sucursales],
  );

  const defaultSucursalId = useMemo(() => {
    if (activeSucursalId) {
      const active = sucursales.find((s) => s.id === activeSucursalId);
      if (active && !active.grupo_repartidores_jid) return active.id;
    }
    return missingSucursales[0]?.id ?? null;
  }, [activeSucursalId, sucursales, missingSucursales]);

  const [sucursalId, setSucursalId] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (sucursales.length === 0 || missingSucursales.length === 0) return null;

  const handleOpen = () => {
    setSucursalId(defaultSucursalId);
    setInviteLink("");
    setError(null);
    open();
  };

  const handleVincular = async () => {
    if (!sucursalId) {
      setError("Selecciona una sucursal.");
      return;
    }
    const link = inviteLink.trim();
    if (!link) {
      setError("Pega el enlace del grupo de WhatsApp.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<GrupoRepartidoresResolved>(
        `/sucursales/${sucursalId}/grupo-repartidores`,
        { invite_link: link },
      );
      if (res?.grupo_repartidores_jid) {
        notifications.show({
          color: "green",
          title: "Grupo vinculado",
          message:
            "Los repartidores ya pueden tomar pedidos desde el grupo de WhatsApp.",
        });
        queryClient.invalidateQueries({ queryKey: ["sucursales"] });
        close();
      } else {
        setError("No se pudo obtener el JID del grupo.");
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Error al vincular el grupo";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const sucursalOptions = missingSucursales.map((s) => ({
    value: s.id,
    label: s.nombre,
  }));

  const alertTitle =
    missingSucursales.length === sucursales.length
      ? "Configura tu grupo de repartidores"
      : `Falta vincular ${missingSucursales.length} sucursal${missingSucursales.length > 1 ? "es" : ""}`;

  return (
    <>
      <Alert
        color="orange"
        icon={<IconTruckDelivery size={18} />}
        title={alertTitle}
        styles={{ root: { flexShrink: 0 } }}
      >
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Text size="sm">
            Pega el enlace del grupo de WhatsApp donde avisas a tus repartidores
            y la IA podrá publicar los pedidos de delivery ahí.
          </Text>
          <Button
            size="xs"
            variant="white"
            color="orange"
            onClick={handleOpen}
            leftSection={<IconUsers size={14} />}
          >
            Vincular grupo
          </Button>
        </Group>
      </Alert>

      <Modal
        opened={opened}
        onClose={close}
        title="Vincular grupo de repartidores"
        size="md"
      >
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            El número de WhatsApp del restaurante debe estar{" "}
            <Text span fw={600}>
              dentro del grupo
            </Text>{" "}
            antes de vincularlo. La IA enviará los pedidos de delivery a este
            grupo para que los repartidores los tomen escribiendo{" "}
            <Badge size="sm" variant="light">
              TOMO
            </Badge>
            .
          </Text>
          {sucursalOptions.length > 1 ? (
            <Select
              label="Sucursal"
              data={sucursalOptions}
              value={sucursalId}
              onChange={setSucursalId}
              required
            />
          ) : null}
          <TextInput
            label="Enlace del grupo"
            placeholder="https://chat.whatsapp.com/XXXXX"
            leftSection={<IconUsers size={16} />}
            value={inviteLink}
            onChange={(e) => setInviteLink(e.currentTarget.value)}
            description="Abre WhatsApp → info del grupo → Enlace de invitación → Copiar"
          />
          {error ? (
            <Text size="xs" c="red">
              {error}
            </Text>
          ) : null}
          <Group justify="flex-end" mt="sm">
            <Button variant="subtle" onClick={close}>
              Cancelar
            </Button>
            <Button onClick={handleVincular} loading={busy}>
              Vincular
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
