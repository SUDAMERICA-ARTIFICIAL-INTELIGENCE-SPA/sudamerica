"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import {
  useCreateSucursal,
  useDeactivateSucursal,
  useSucursales,
  useUpdateSucursal,
} from "@/hooks/useSucursales";
import { api } from "@/lib/api";
import type { Sucursal } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NativeSelect,
  NumberInput,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import {
  IconBuilding,
  IconCurrencyDollar,
  IconEdit,
  IconMap,
  IconMapPin,
  IconPhone,
  IconPlus,
  IconTrash,
  IconTruck,
  IconUsers,
  IconWorld,
} from "@tabler/icons-react";
import { useState } from "react";

const LATAM_COUNTRIES = [
  { value: "CL", label: "Chile" },
  { value: "AR", label: "Argentina" },
  { value: "PE", label: "Peru" },
  { value: "CO", label: "Colombia" },
  { value: "MX", label: "Mexico" },
  { value: "EC", label: "Ecuador" },
  { value: "UY", label: "Uruguay" },
  { value: "PY", label: "Paraguay" },
  { value: "BO", label: "Bolivia" },
  { value: "BR", label: "Brasil" },
  { value: "VE", label: "Venezuela" },
  { value: "CR", label: "Costa Rica" },
  { value: "PA", label: "Panama" },
  { value: "GT", label: "Guatemala" },
  { value: "DO", label: "Rep. Dominicana" },
];

interface SucursalFormValues {
  nombre: string;
  direccion: string;
  telefono: string;
  zona_delivery: string;
  ciudad: string;
  region: string;
  codigo_postal: string;
  pais: string;
  google_maps_url: string;
  costo_delivery: number | "";
  grupo_repartidores_jid: string;
  grupo_invite_link: string;
}

interface GrupoRepartidoresResolved {
  grupo_repartidores_jid: string | null;
}

function SucursalFormModal({
  opened,
  onClose,
  sucursal,
}: {
  opened: boolean;
  onClose: () => void;
  sucursal?: Sucursal | undefined;
}) {
  const createMutation = useCreateSucursal();
  const updateMutation = useUpdateSucursal();
  const isEdit = !!sucursal;

  const [grupoBusy, setGrupoBusy] = useState(false);
  const [grupoError, setGrupoError] = useState<string | null>(null);

  const form = useForm<SucursalFormValues>({
    initialValues: {
      nombre: sucursal?.nombre ?? "",
      direccion: sucursal?.direccion ?? "",
      telefono: sucursal?.telefono ?? "",
      zona_delivery: sucursal?.zona_delivery ?? "",
      ciudad: sucursal?.ciudad ?? "",
      region: sucursal?.region ?? "",
      codigo_postal: sucursal?.codigo_postal ?? "",
      pais: sucursal?.pais ?? "CL",
      google_maps_url: sucursal?.google_maps_url ?? "",
      costo_delivery: sucursal?.costo_delivery ?? "",
      grupo_repartidores_jid: sucursal?.grupo_repartidores_jid ?? "",
      grupo_invite_link: "",
    },
    validate: {
      nombre: (v) => (v.trim().length === 0 ? "Nombre es requerido" : null),
    },
  });

  const handleVincularGrupo = async () => {
    if (!isEdit || !sucursal) {
      setGrupoError("Guarda la sucursal primero antes de vincular el grupo.");
      return;
    }
    const link = form.values.grupo_invite_link.trim();
    if (!link) {
      setGrupoError("Pega el enlace del grupo de WhatsApp.");
      return;
    }
    setGrupoBusy(true);
    setGrupoError(null);
    try {
      const res = await api.post<GrupoRepartidoresResolved>(
        `/sucursales/${sucursal.id}/grupo-repartidores`,
        { invite_link: link },
      );
      if (res?.grupo_repartidores_jid) {
        form.setFieldValue("grupo_repartidores_jid", res.grupo_repartidores_jid);
        form.setFieldValue("grupo_invite_link", "");
      } else {
        setGrupoError("No se pudo obtener el JID del grupo.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al vincular el grupo";
      setGrupoError(msg);
    } finally {
      setGrupoBusy(false);
    }
  };

  const handleSubmit = (values: SucursalFormValues) => {
    const payload = {
      nombre: values.nombre.trim(),
      direccion: values.direccion.trim() || null,
      telefono: values.telefono.trim() || null,
      zona_delivery: values.zona_delivery.trim() || null,
      ciudad: values.ciudad.trim() || null,
      region: values.region.trim() || null,
      codigo_postal: values.codigo_postal.trim() || null,
      pais: values.pais,
      google_maps_url: values.google_maps_url.trim() || null,
      costo_delivery: typeof values.costo_delivery === "number" ? values.costo_delivery : 0,
      grupo_repartidores_jid: values.grupo_repartidores_jid.trim() || null,
    };

    if (isEdit) {
      updateMutation.mutate({ id: sucursal.id, ...payload }, { onSuccess: onClose });
    } else {
      createMutation.mutate(payload, { onSuccess: onClose });
    }
  };

  const loading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEdit ? "Editar Sucursal" : "Nueva Sucursal"}
      size="lg"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="sm">
          <TextInput
            label="Nombre"
            placeholder="Sucursal Centro"
            required
            {...form.getInputProps("nombre")}
          />
          <TextInput
            label="Direccion"
            placeholder="Av. Principal 123"
            leftSection={<IconMapPin size={16} />}
            {...form.getInputProps("direccion")}
          />
          <Group grow>
            <TextInput label="Ciudad" placeholder="Santiago" {...form.getInputProps("ciudad")} />
            <TextInput
              label="Region"
              placeholder="Region Metropolitana"
              {...form.getInputProps("region")}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Codigo postal"
              placeholder="8320000"
              {...form.getInputProps("codigo_postal")}
            />
            <NativeSelect
              label="Pais"
              data={LATAM_COUNTRIES}
              leftSection={<IconWorld size={16} />}
              {...form.getInputProps("pais")}
            />
          </Group>
          <TextInput
            label="Telefono"
            placeholder="+56 9 1234 5678"
            leftSection={<IconPhone size={16} />}
            {...form.getInputProps("telefono")}
          />
          <TextInput
            label="Google Maps URL"
            placeholder="https://maps.google.com/..."
            leftSection={<IconMap size={16} />}
            {...form.getInputProps("google_maps_url")}
          />
          <Textarea
            label="Zona de delivery"
            placeholder="Centro, Providencia, Las Condes..."
            {...form.getInputProps("zona_delivery")}
          />
          <NumberInput
            label="Costo de delivery ($)"
            placeholder="1500"
            min={0}
            leftSection={<IconCurrencyDollar size={16} />}
            value={form.values.costo_delivery}
            onChange={(val) =>
              form.setFieldValue("costo_delivery", typeof val === "number" ? val : "")
            }
          />
          <Stack gap="xs">
            <Text size="sm" fw={500}>
              Grupo de repartidores (WhatsApp)
            </Text>
            {form.values.grupo_repartidores_jid ? (
              <Group gap="xs">
                <Badge color="green" leftSection={<IconUsers size={12} />}>
                  Vinculado
                </Badge>
                <Text size="xs" c="dimmed" style={{ fontFamily: "monospace" }}>
                  {form.values.grupo_repartidores_jid}
                </Text>
                <Button
                  size="compact-xs"
                  variant="subtle"
                  color="red"
                  onClick={() => form.setFieldValue("grupo_repartidores_jid", "")}
                >
                  Quitar
                </Button>
              </Group>
            ) : null}
            <Group gap="xs" align="flex-end">
              <TextInput
                label={form.values.grupo_repartidores_jid ? "Cambiar grupo" : "Enlace del grupo"}
                placeholder="https://chat.whatsapp.com/XXXXX"
                leftSection={<IconUsers size={16} />}
                style={{ flex: 1 }}
                description={
                  isEdit
                    ? "El número del restaurante debe estar dentro del grupo."
                    : "Guarda la sucursal primero, luego vincula el grupo."
                }
                {...form.getInputProps("grupo_invite_link")}
              />
              <Button
                onClick={handleVincularGrupo}
                loading={grupoBusy}
                disabled={!isEdit || !form.values.grupo_invite_link.trim()}
                variant="light"
              >
                Vincular
              </Button>
            </Group>
            {grupoError ? (
              <Text size="xs" c="red">
                {grupoError}
              </Text>
            ) : null}
          </Stack>
          <Group justify="flex-end" mt="md">
            <Button variant="subtle" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={loading}>
              {isEdit ? "Guardar" : "Crear"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function SucursalCard({
  sucursal,
  onEdit,
}: {
  sucursal: Sucursal;
  onEdit: (s: Sucursal) => void;
}) {
  const deactivateMutation = useDeactivateSucursal();
  const locationParts = [sucursal.ciudad, sucursal.region].filter(Boolean);

  return (
    <Card withBorder padding="md" radius="md">
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <IconBuilding size={20} />
          <Text fw={600}>{sucursal.nombre}</Text>
        </Group>
        <Group gap={4}>
          {sucursal.es_principal && (
            <Badge size="sm" color="indigo" variant="light">
              Principal
            </Badge>
          )}
          <ActionIcon
            variant="subtle"
            size="sm"
            onClick={() => onEdit(sucursal)}
            aria-label={`Editar ${sucursal.nombre}`}
          >
            <IconEdit size={16} />
          </ActionIcon>
          {!sucursal.es_principal && (
            <ActionIcon
              variant="subtle"
              color="red"
              size="sm"
              loading={deactivateMutation.isPending}
              onClick={() => deactivateMutation.mutate(sucursal.id)}
              aria-label={`Desactivar ${sucursal.nombre}`}
            >
              <IconTrash size={16} />
            </ActionIcon>
          )}
        </Group>
      </Group>
      {sucursal.direccion && (
        <Text size="sm" c="dimmed">
          <IconMapPin size={14} style={{ verticalAlign: "middle" }} /> {sucursal.direccion}
        </Text>
      )}
      {locationParts.length > 0 && (
        <Text size="sm" c="dimmed">
          {locationParts.join(", ")}
          {sucursal.pais ? ` (${sucursal.pais})` : ""}
        </Text>
      )}
      {sucursal.telefono && (
        <Text size="sm" c="dimmed">
          <IconPhone size={14} style={{ verticalAlign: "middle" }} /> {sucursal.telefono}
        </Text>
      )}
      {sucursal.zona_delivery && (
        <Text size="sm" c="dimmed" mt={4}>
          <IconTruck size={14} style={{ verticalAlign: "middle" }} /> {sucursal.zona_delivery}
        </Text>
      )}
      {sucursal.costo_delivery > 0 && (
        <Text size="sm" c="dimmed" mt={2}>
          <IconCurrencyDollar size={14} style={{ verticalAlign: "middle" }} /> Delivery: $
          {sucursal.costo_delivery}
        </Text>
      )}
      {sucursal.google_maps_url && (
        <Text
          size="sm"
          c="indigo"
          mt={4}
          component="a"
          href={sucursal.google_maps_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <IconMap size={14} style={{ verticalAlign: "middle" }} /> Ver en mapa
        </Text>
      )}
    </Card>
  );
}

export function SucursalesTab() {
  const { data: sucursales, isLoading } = useSucursales();
  const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);
  const [editOpened, { open: openEdit, close: closeEdit }] = useDisclosure(false);
  const [editTarget, setEditTarget] = useState<Sucursal | undefined>();

  const handleEdit = (s: Sucursal) => {
    setEditTarget(s);
    openEdit();
  };

  return (
    <SectionCard
      title="Sucursales"
      action={
        <Button leftSection={<IconPlus size={16} />} onClick={openCreate}>
          Nueva Sucursal
        </Button>
      }
    >
      {isLoading ? (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <Skeleton height={120} />
          <Skeleton height={120} />
        </SimpleGrid>
      ) : sucursales && sucursales.length > 0 ? (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          {sucursales.map((s) => (
            <SucursalCard key={s.id} sucursal={s} onEdit={handleEdit} />
          ))}
        </SimpleGrid>
      ) : (
        <Card withBorder padding="xl" radius="md">
          <Stack align="center" gap="xs">
            <IconBuilding size={40} color="gray" />
            <Text c="dimmed">No hay sucursales configuradas. Crea tu primera sucursal.</Text>
          </Stack>
        </Card>
      )}

      <SucursalFormModal key="create" opened={createOpened} onClose={closeCreate} />
      <SucursalFormModal
        key={editTarget?.id ?? "edit"}
        opened={editOpened}
        onClose={closeEdit}
        sucursal={editTarget}
      />
    </SectionCard>
  );
}
