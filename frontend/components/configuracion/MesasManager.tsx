"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import {
  useCreateMesa,
  useDeleteMesa,
  useMesas,
  useRegenerateMesaQr,
  useUpdateMesa,
} from "@/hooks/useMesas";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useSucursales } from "@/hooks/useSucursales";
import { getMesaQrUrl } from "@/lib/api";
import { RUBRO_DEFAULT, plural } from "@/lib/rubros";
import type { Mesa, Sucursal } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  CopyButton,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconCheck,
  IconCopy,
  IconDownload,
  IconEdit,
  IconPlus,
  IconPrinter,
  IconQrcode,
  IconRefresh,
  IconTrash,
} from "@tabler/icons-react";
import { QRCodeCanvas } from "qrcode.react";
import { useCallback, useMemo, useRef, useState } from "react";

interface MesaFormState {
  numero: number | "";
  nombre: string;
  capacidad: number | "";
  sucursal_id: string | null;
}

const INITIAL_FORM: MesaFormState = {
  numero: "",
  nombre: "",
  capacidad: "",
  sucursal_id: null,
};

function MesaTable({
  mesas,
  recursoLower,
  recursosPluralLower,
  onOpenQr,
  onOpenEdit,
  onOpenDelete,
}: {
  mesas: Mesa[];
  recursoLower: string;
  recursosPluralLower: string;
  onOpenQr: (mesa: Mesa) => void;
  onOpenEdit: (mesa: Mesa) => void;
  onOpenDelete: (mesa: Mesa) => void;
}) {
  if (mesas.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="md" size="sm">
        Sin {recursosPluralLower} en esta sucursal. Agrega la primera.
      </Text>
    );
  }

  return (
    <Table striped highlightOnHover>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Numero</Table.Th>
          <Table.Th>Nombre</Table.Th>
          <Table.Th style={{ textAlign: "right" }}>Capacidad</Table.Th>
          <Table.Th>QR</Table.Th>
          <Table.Th style={{ width: 100 }}>Acciones</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {mesas.map((mesa) => (
          <Table.Tr key={mesa.id}>
            <Table.Td fw={600}>{mesa.numero}</Table.Td>
            <Table.Td>{mesa.nombre ?? "-"}</Table.Td>
            <Table.Td className="num-tabular">{mesa.capacidad} personas</Table.Td>
            <Table.Td>
              <Tooltip label="Ver QR" withArrow>
                <ActionIcon
                  variant="subtle"
                  color="violet"
                  size="sm"
                  onClick={() => onOpenQr(mesa)}
                  aria-label={`Ver QR ${recursoLower} ${mesa.numero}`}
                >
                  <IconQrcode size={16} />
                </ActionIcon>
              </Tooltip>
            </Table.Td>
            <Table.Td>
              <Group gap={4}>
                <Tooltip label="Editar" withArrow>
                  <ActionIcon
                    variant="subtle"
                    color="blue"
                    size="sm"
                    onClick={() => onOpenEdit(mesa)}
                    aria-label={`Editar ${recursoLower} ${mesa.numero}`}
                  >
                    <IconEdit size={16} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Eliminar" withArrow>
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    size="sm"
                    onClick={() => onOpenDelete(mesa)}
                    aria-label={`Eliminar ${recursoLower} ${mesa.numero}`}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

export function MesasManager() {
  const { data: mesas, isLoading: mesasLoading } = useMesas();
  const { data: sucursalesRaw, isLoading: sucursalesLoading } = useSucursales();
  const createMesa = useCreateMesa();
  const updateMesa = useUpdateMesa();
  const deleteMesa = useDeleteMesa();
  const regenerateQr = useRegenerateMesaQr();

  // Rubro-aware labels (fail-safe to restaurante → "Mesa"/"mesa"/"mesas", byte-identical).
  const rubro = useRubroLabels();
  const recurso = rubro.labels.recurso;
  const recursoLower = recurso.toLowerCase();
  const recursosPlural = plural(recurso);
  const recursosPluralLower = recursosPlural.toLowerCase();
  const tituloRecursos = rubro.key === RUBRO_DEFAULT ? "Mesas del Restaurante" : recursosPlural;

  const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);
  const [editOpened, { open: openEdit, close: closeEdit }] = useDisclosure(false);
  const [deleteOpened, { open: openDelete, close: closeDelete }] = useDisclosure(false);
  const [qrOpened, { open: openQr, close: closeQr }] = useDisclosure(false);

  const [form, setForm] = useState<MesaFormState>(INITIAL_FORM);
  const [editingMesa, setEditingMesa] = useState<Mesa | null>(null);
  const [deletingMesa, setDeletingMesa] = useState<Mesa | null>(null);
  const [qrMesa, setQrMesa] = useState<Mesa | null>(null);

  const qrCanvasRef = useRef<HTMLDivElement>(null);

  const sucursales: Sucursal[] = useMemo(() => {
    if (!sucursalesRaw) return [];
    // Handle both array and paginated response
    if (Array.isArray(sucursalesRaw)) return sucursalesRaw.filter((s) => s.activo);
    const raw = sucursalesRaw as unknown as { data?: Sucursal[] };
    return (raw.data ?? []).filter((s) => s.activo);
  }, [sucursalesRaw]);

  const hasSucursales = sucursales.length > 0;
  const isMultiSucursal = sucursales.length > 1;

  const activeMesas = useMemo(() => (mesas ?? []).filter((m) => m.activo), [mesas]);

  // Group mesas by sucursal_id
  const mesasBySucursal = useMemo(() => {
    const map = new Map<string | null, Mesa[]>();
    for (const mesa of activeMesas) {
      const key = mesa.sucursal_id ?? null;
      const list = map.get(key) ?? [];
      list.push(mesa);
      map.set(key, list);
    }
    return map;
  }, [activeMesas]);

  const sucursalOptions = useMemo(
    () => sucursales.map((s) => ({ value: s.id, label: s.nombre })),
    [sucursales],
  );

  const resetForm = useCallback(() => {
    setForm(INITIAL_FORM);
    setEditingMesa(null);
    setDeletingMesa(null);
  }, []);

  const handleCreate = useCallback(() => {
    if (form.numero === "" || form.capacidad === "") return;
    createMesa.mutate(
      {
        numero: form.numero,
        nombre: form.nombre || null,
        capacidad: form.capacidad,
        sucursal_id: form.sucursal_id,
      },
      {
        onSuccess: () => {
          resetForm();
          closeCreate();
        },
      },
    );
  }, [form, createMesa, resetForm, closeCreate]);

  const handleEdit = useCallback(() => {
    if (!editingMesa || form.numero === "" || form.capacidad === "") return;
    updateMesa.mutate(
      {
        id: editingMesa.id,
        dto: {
          nombre: form.nombre || null,
          ...(typeof form.capacidad === "number" ? { capacidad: form.capacidad } : {}),
        },
      },
      {
        onSuccess: () => {
          resetForm();
          closeEdit();
        },
      },
    );
  }, [editingMesa, form, updateMesa, resetForm, closeEdit]);

  const handleDelete = useCallback(() => {
    if (!deletingMesa) return;
    deleteMesa.mutate(deletingMesa.id, {
      onSuccess: () => {
        resetForm();
        closeDelete();
      },
    });
  }, [deletingMesa, deleteMesa, resetForm, closeDelete]);

  const openEditModal = useCallback(
    (mesa: Mesa) => {
      setEditingMesa(mesa);
      setForm({
        numero: mesa.numero,
        nombre: mesa.nombre ?? "",
        capacidad: mesa.capacidad,
        sucursal_id: mesa.sucursal_id ?? null,
      });
      openEdit();
    },
    [openEdit],
  );

  const openDeleteModal = useCallback(
    (mesa: Mesa) => {
      setDeletingMesa(mesa);
      openDelete();
    },
    [openDelete],
  );

  const openQrModal = useCallback(
    (mesa: Mesa) => {
      setQrMesa(mesa);
      openQr();
    },
    [openQr],
  );

  const openCreateForSucursal = useCallback(
    (sucursalId: string | null) => {
      resetForm();
      setForm((prev) => ({ ...prev, sucursal_id: sucursalId }));
      openCreate();
    },
    [resetForm, openCreate],
  );

  const handleRegenerateQr = useCallback(() => {
    if (!qrMesa) return;
    regenerateQr.mutate(qrMesa.id, {
      onSuccess: (res) => {
        const updated = (res as { data?: Mesa })?.data;
        if (updated) setQrMesa(updated);
      },
    });
  }, [qrMesa, regenerateQr]);

  const handleDownloadQr = useCallback(() => {
    const canvas = qrCanvasRef.current?.querySelector("canvas");
    if (!canvas || !qrMesa) return;
    const link = document.createElement("a");
    link.download = `${recursoLower}-${qrMesa.numero}-qr.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }, [qrMesa, recursoLower]);

  const handlePrintQr = useCallback(() => {
    const canvas = qrCanvasRef.current?.querySelector("canvas");
    if (!canvas || !qrMesa) return;
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(`
      <html><head><title>QR ${recurso} ${qrMesa.numero}</title>
      <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;
      min-height:100vh;margin:0;font-family:system-ui}h2{margin:0 0 1rem}</style></head>
      <body><h2>${recurso} ${qrMesa.numero}${qrMesa.nombre ? ` - ${qrMesa.nombre}` : ""}</h2>
      <img src="${canvas.toDataURL("image/png")}" width="300" height="300"/>
      <script>setTimeout(()=>{window.print();window.close()},300)<\/script></body></html>
    `);
    win.document.close();
  }, [qrMesa, recurso]);

  if (mesasLoading || sucursalesLoading) {
    return (
      <Paper p="lg" radius="md" withBorder>
        <Stack gap="md">
          <Skeleton height={28} width={200} />
          <Skeleton height={200} />
        </Stack>
      </Paper>
    );
  }

  const qrUrl = qrMesa ? getMesaQrUrl(qrMesa.qr_token) : "";

  // Render a sucursal box with its mesas
  const renderSucursalBox = (sucursal: Sucursal | null, sucursalId: string | null) => {
    const sucursalMesas = mesasBySucursal.get(sucursalId) ?? [];
    const title = sucursal ? sucursal.nombre : "Sin sucursal asignada";
    const address = sucursal?.direccion;

    return (
      <SectionCard
        key={sucursalId ?? "none"}
        title={title}
        {...(address ? { subtitle: address } : {})}
        noBodyPadding
        action={
          <Group gap="xs" wrap="nowrap">
            {sucursal?.es_principal && (
              <Badge size="xs" variant="light" color="blue">
                Principal
              </Badge>
            )}
            <Badge size="xs" variant="light" color="gray">
              {sucursalMesas.length}{" "}
              {sucursalMesas.length === 1 ? recursoLower : recursosPluralLower}
            </Badge>
            <Button
              leftSection={<IconPlus size={14} />}
              size="xs"
              variant="light"
              onClick={() => openCreateForSucursal(sucursalId)}
            >
              Agregar {recurso}
            </Button>
          </Group>
        }
      >
        <MesaTable
          mesas={sucursalMesas}
          recursoLower={recursoLower}
          recursosPluralLower={recursosPluralLower}
          onOpenQr={openQrModal}
          onOpenEdit={openEditModal}
          onOpenDelete={openDeleteModal}
        />
      </SectionCard>
    );
  };

  return (
    <>
      <Stack gap="lg">
        {/* If multi-sucursal: one box per sucursal */}
        {isMultiSucursal ? (
          <>
            {sucursales.map((s) => renderSucursalBox(s, s.id))}
            {/* Show unassigned mesas if any */}
            {mesasBySucursal.has(null) && renderSucursalBox(null, null)}
          </>
        ) : hasSucursales && sucursales[0] ? (
          /* Single sucursal: one box with sucursal name */
          renderSucursalBox(sucursales[0], sucursales[0].id)
        ) : (
          /* No sucursales: flat view */
          <SectionCard
            title={tituloRecursos}
            noBodyPadding
            action={
              <Button
                leftSection={<IconPlus size={16} />}
                size="sm"
                onClick={() => openCreateForSucursal(null)}
              >
                Agregar {recurso}
              </Button>
            }
          >
            <MesaTable
              mesas={activeMesas}
              recursoLower={recursoLower}
              recursosPluralLower={recursosPluralLower}
              onOpenQr={openQrModal}
              onOpenEdit={openEditModal}
              onOpenDelete={openDeleteModal}
            />
          </SectionCard>
        )}
      </Stack>

      {/* Create Modal */}
      <Modal
        opened={createOpened}
        onClose={() => {
          resetForm();
          closeCreate();
        }}
        title={`Agregar ${recurso}`}
        centered
      >
        <Stack gap="md">
          {isMultiSucursal && (
            <Select
              label="Sucursal"
              data={sucursalOptions}
              value={form.sucursal_id}
              onChange={(val) => setForm((prev) => ({ ...prev, sucursal_id: val }))}
              required
            />
          )}
          <NumberInput
            label={`Numero de ${recursoLower}`}
            placeholder="1"
            min={1}
            required
            value={form.numero}
            onChange={(val) =>
              setForm((prev) => ({
                ...prev,
                numero: typeof val === "number" ? val : "",
              }))
            }
          />
          <TextInput
            label="Nombre (opcional)"
            placeholder="Terraza 1, VIP, Barra..."
            value={form.nombre}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                nombre: e?.currentTarget?.value ?? "",
              }))
            }
          />
          <NumberInput
            label="Capacidad (personas)"
            placeholder="4"
            min={1}
            required
            value={form.capacidad}
            onChange={(val) =>
              setForm((prev) => ({
                ...prev,
                capacidad: typeof val === "number" ? val : "",
              }))
            }
          />
          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={() => {
                resetForm();
                closeCreate();
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleCreate}
              loading={createMesa.isPending}
              disabled={form.numero === "" || form.capacidad === ""}
            >
              Crear {recurso}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Edit Modal */}
      <Modal
        opened={editOpened}
        onClose={() => {
          resetForm();
          closeEdit();
        }}
        title={`Editar ${recurso} ${editingMesa?.numero ?? ""}`}
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Nombre (opcional)"
            placeholder="Terraza 1, VIP, Barra..."
            value={form.nombre}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                nombre: e?.currentTarget?.value ?? "",
              }))
            }
          />
          <NumberInput
            label="Capacidad (personas)"
            min={1}
            required
            value={form.capacidad}
            onChange={(val) =>
              setForm((prev) => ({
                ...prev,
                capacidad: typeof val === "number" ? val : "",
              }))
            }
          />
          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={() => {
                resetForm();
                closeEdit();
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleEdit}
              loading={updateMesa.isPending}
              disabled={typeof form.capacidad !== "number"}
            >
              Guardar Cambios
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        opened={deleteOpened}
        onClose={() => {
          resetForm();
          closeDelete();
        }}
        title="Confirmar Eliminacion"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text>
            Estas seguro de eliminar la {recursoLower}{" "}
            <Text span fw={700}>
              #{deletingMesa?.numero}
            </Text>
            {deletingMesa?.nombre ? ` (${deletingMesa.nombre})` : ""}? Esta accion no se puede
            deshacer.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={() => {
                resetForm();
                closeDelete();
              }}
            >
              Cancelar
            </Button>
            <Button color="red" onClick={handleDelete} loading={deleteMesa.isPending}>
              Eliminar
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* QR Code Modal */}
      <Modal
        opened={qrOpened}
        onClose={() => {
          setQrMesa(null);
          closeQr();
        }}
        title={`QR ${recurso} ${qrMesa?.numero ?? ""}${qrMesa?.nombre ? ` - ${qrMesa.nombre}` : ""}`}
        centered
        size="md"
      >
        {qrMesa && (
          <Stack gap="md" align="center">
            <div ref={qrCanvasRef}>
              <QRCodeCanvas value={qrUrl} size={256} level="H" includeMargin />
            </div>

            <TextInput
              value={qrUrl}
              readOnly
              styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
              w="100%"
              aria-label="URL del QR"
            />

            <Group gap="sm">
              <CopyButton value={qrUrl}>
                {({ copied, copy }) => (
                  <Button
                    variant="light"
                    leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                    color={copied ? "teal" : "blue"}
                    onClick={copy}
                  >
                    {copied ? "Copiado" : "Copiar enlace"}
                  </Button>
                )}
              </CopyButton>

              <Button
                variant="light"
                leftSection={<IconDownload size={16} />}
                onClick={handleDownloadQr}
              >
                Descargar PNG
              </Button>

              <Button
                variant="light"
                leftSection={<IconPrinter size={16} />}
                onClick={handlePrintQr}
              >
                Imprimir
              </Button>
            </Group>

            <Button
              variant="subtle"
              color="orange"
              leftSection={<IconRefresh size={16} />}
              onClick={handleRegenerateQr}
              loading={regenerateQr.isPending}
              size="xs"
            >
              Regenerar QR (invalida el anterior)
            </Button>
          </Stack>
        )}
      </Modal>
    </>
  );
}
