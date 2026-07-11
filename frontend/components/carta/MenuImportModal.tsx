"use client";

import { useMenuImport, type MenuImportResult } from "@/hooks/useMenuImport";
import {
  useMenuImportUrl,
  type MenuImportUrlResult,
} from "@/hooks/useMenuImportUrl";
import {
  useMenuImportPreview,
  useMenuImportConfirm,
} from "@/hooks/useMenuImportPreview";
import { useCategorias } from "@/hooks/useCategorias";
import type {
  MenuImportPreviewItem,
  MenuImportConfirmResult,
} from "@/lib/types";
import {
  ActionIcon,
  Alert,
  Autocomplete,
  Badge,
  Button,
  Checkbox,
  Group,
  List,
  Modal,
  NumberInput,
  ScrollArea,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  rem,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { Dropzone } from "@mantine/dropzone";
import {
  IconCheck,
  IconFileSpreadsheet,
  IconLink,
  IconPhoto,
  IconPlus,
  IconTrash,
  IconUpload,
  IconWorldWww,
  IconX,
} from "@tabler/icons-react";
import { useRef, useState } from "react";

const ACCEPTED_MIME = [
  "text/csv",
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/webp",
];

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

type ModalStep = "upload" | "review" | "result";

interface ReviewFormValues {
  items: MenuImportPreviewItem[];
  set_as_official_pdf: boolean;
}

export function MenuImportModal({
  opened,
  onClose,
  onImportComplete,
}: {
  opened: boolean;
  onClose: () => void;
  onImportComplete?: () => void;
}) {
  // Legacy direct import (backward compat for URL import)
  const { mutate: importUrl, isPending: urlPending } = useMenuImportUrl();

  // New preview/confirm workflow
  const { mutate: preview, isPending: previewPending } =
    useMenuImportPreview();
  const { mutate: confirm, isPending: confirmPending } =
    useMenuImportConfirm();

  // Categorias for the review Select dropdown
  const { data: categorias } = useCategorias();

  const [step, setStep] = useState<ModalStep>("upload");
  const [importId, setImportId] = useState<string | null>(null);
  const [sourceType, setSourceType] = useState<string | null>(null);
  const [result, setResult] = useState<MenuImportConfirmResult | null>(null);
  const [urlResult, setUrlResult] = useState<
    (MenuImportResult & { images_uploaded?: number }) | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [urlValue, setUrlValue] = useState("");
  const openRef = useRef<() => void>(null);

  const form = useForm<ReviewFormValues>({
    initialValues: { items: [], set_as_official_pdf: false },
  });

  // ── Handlers ──

  function handleDrop(files: File[]) {
    const file = files[0];
    if (!file) return;
    setError(null);

    preview(file, {
      onSuccess: (data) => {
        setImportId(data.import_id);
        setSourceType(data.source_type);
        form.setFieldValue(
          "items",
          data.items.map((it) => ({
            nombre: it.nombre,
            descripcion: it.descripcion ?? null,
            precio: it.precio,
            categoria: it.categoria,
          })),
        );
        form.setFieldValue("set_as_official_pdf", false);
        setStep("review");
      },
      onError: (err) => setError(err.message || "Error al extraer items"),
    });
  }

  function handleUrlImport() {
    const url = urlValue.trim();
    if (!url) return;
    setError(null);

    importUrl(url, {
      onSuccess: (data) => {
        setUrlResult(
          data as MenuImportResult & { images_uploaded?: number },
        );
        setStep("result");
      },
      onError: (err) =>
        setError(err.message || "Error al importar desde URL"),
    });
  }

  function handleConfirm() {
    if (!importId) return;
    setError(null);

    confirm(
      {
        import_id: importId,
        items: form.values.items,
        set_as_official_pdf: form.values.set_as_official_pdf,
      },
      {
        onSuccess: (data) => {
          setResult(data);
          setStep("result");
        },
        onError: (err) => setError(err.message || "Error al confirmar"),
      },
    );
  }

  function handleAddRow() {
    form.insertListItem("items", {
      nombre: "",
      descripcion: null,
      precio: 0,
      categoria: "General",
    });
  }

  function handleClose() {
    setStep("upload");
    setResult(null);
    setUrlResult(null);
    setError(null);
    setUrlValue("");
    setImportId(null);
    setSourceType(null);
    form.reset();
    onClose();
  }

  function handleFinish() {
    onImportComplete?.();
    handleClose();
  }

  // Build unique category options from extracted items + existing DB categories
  const categoryOptions = (() => {
    const set = new Set<string>();
    for (const item of form.values.items) {
      if (item.categoria) set.add(item.categoria);
    }
    if (categorias) {
      for (const c of categorias) {
        set.add(c.nombre);
      }
    }
    return Array.from(set)
      .sort()
      .map((c) => ({ value: c, label: c }));
  })();

  const isPending = previewPending || urlPending;
  const showOfficialCheckbox = sourceType === "PDF";

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        step === "review"
          ? "Revisar items extraidos"
          : step === "result"
            ? "Importacion completada"
            : "Importar Menu"
      }
      size={step === "review" ? "xl" : "lg"}
      radius="md"
    >
      {/* ── STEP 1: UPLOAD ── */}
      {step === "upload" && (
        <Stack gap="md">
          <Text fz="sm" c="dimmed">
            Importa tu carta desde un archivo o desde la URL de tu sitio web.
            La IA extraera los platos automaticamente.
          </Text>

          <Tabs defaultValue="archivo" radius="md">
            <Tabs.List>
              <Tabs.Tab
                value="archivo"
                leftSection={<IconFileSpreadsheet size={14} />}
              >
                Archivo
              </Tabs.Tab>
              <Tabs.Tab
                value="url"
                leftSection={<IconWorldWww size={14} />}
              >
                Desde URL
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="archivo" pt="md">
              <Dropzone
                onDrop={handleDrop}
                onReject={() =>
                  setError(
                    "Archivo no valido. Usa CSV, PDF o imagen (PNG, JPG, WebP).",
                  )
                }
                maxSize={MAX_SIZE}
                accept={ACCEPTED_MIME}
                multiple={false}
                loading={previewPending}
                openRef={openRef}
                radius="md"
              >
                <Group
                  justify="center"
                  gap="xl"
                  mih={120}
                  style={{ pointerEvents: "none" }}
                >
                  <Dropzone.Accept>
                    <IconUpload
                      style={{
                        width: rem(52),
                        height: rem(52),
                        color: "var(--mantine-color-indigo-6)",
                      }}
                      stroke={1.5}
                    />
                  </Dropzone.Accept>
                  <Dropzone.Reject>
                    <IconX
                      style={{
                        width: rem(52),
                        height: rem(52),
                        color: "var(--mantine-color-red-6)",
                      }}
                      stroke={1.5}
                    />
                  </Dropzone.Reject>
                  <Dropzone.Idle>
                    <IconFileSpreadsheet
                      style={{
                        width: rem(52),
                        height: rem(52),
                        color: "var(--mantine-color-dimmed)",
                      }}
                      stroke={1.5}
                    />
                  </Dropzone.Idle>

                  <Stack gap={4}>
                    <Text fz="md" fw={500} inline>
                      Arrastra tu archivo aqui o haz clic
                    </Text>
                    <Text fz="xs" c="dimmed" inline>
                      CSV, PDF, PNG, JPG, WebP — max 10 MB
                    </Text>
                  </Stack>
                </Group>
              </Dropzone>

              {previewPending && (
                <Text fz="xs" c="dimmed" ta="center" mt="sm">
                  Extrayendo platos con IA... esto puede tomar unos segundos.
                </Text>
              )}
            </Tabs.Panel>

            <Tabs.Panel value="url" pt="md">
              <Stack gap="sm">
                <Text fz="sm" c="dimmed">
                  Pega la URL de la carta de tu restaurante. La IA visitara la
                  pagina, extraera los platos con sus precios y categorias, y
                  descargara las imagenes automaticamente.
                </Text>
                <TextInput
                  placeholder="https://www.mirestaurante.cl/carta"
                  leftSection={<IconLink size={16} />}
                  value={urlValue}
                  onChange={(e) => setUrlValue(e.currentTarget.value)}
                  radius="md"
                  disabled={urlPending}
                />
                <Button
                  onClick={handleUrlImport}
                  loading={urlPending}
                  disabled={!urlValue.trim() || urlPending}
                  color="indigo"
                  radius="md"
                  leftSection={<IconWorldWww size={16} />}
                >
                  Importar desde web
                </Button>
                {urlPending && (
                  <Text fz="xs" c="dimmed" ta="center">
                    Esto puede tomar 15-30 segundos. La IA esta analizando la
                    pagina...
                  </Text>
                )}
              </Stack>
            </Tabs.Panel>
          </Tabs>

          {error && (
            <Alert color="red" icon={<IconX size={16} />} radius="md">
              {error}
            </Alert>
          )}

          <Group justify="flex-end">
            <Button variant="subtle" color="gray" onClick={handleClose}>
              Cancelar
            </Button>
          </Group>
        </Stack>
      )}

      {/* ── STEP 2: REVIEW ── */}
      {step === "review" && (
        <Stack gap="md">
          <Group justify="space-between">
            <Text fz="sm" c="dimmed">
              Revisa y corrige los items extraidos antes de guardarlos.
            </Text>
            <Badge size="sm" variant="light">
              {form.values.items.length} items
            </Badge>
          </Group>

          <ScrollArea h={400} offsetScrollbars>
            <Table
              striped
              highlightOnHover
              withTableBorder
              horizontalSpacing="xs"
              verticalSpacing={6}
              fz="sm"
            >
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Nombre</Table.Th>
                  <Table.Th>Descripcion</Table.Th>
                  <Table.Th style={{ width: 100 }}>Precio</Table.Th>
                  <Table.Th style={{ width: 160 }}>Categoria</Table.Th>
                  <Table.Th style={{ width: 40 }} />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {form.values.items.map((item, index) => (
                  <Table.Tr key={index}>
                    <Table.Td>
                      <TextInput
                        size="xs"
                        variant="unstyled"
                        placeholder="Nombre del plato"
                        {...form.getInputProps(`items.${index}.nombre`)}
                      />
                    </Table.Td>
                    <Table.Td>
                      <TextInput
                        size="xs"
                        variant="unstyled"
                        placeholder="Descripcion"
                        value={item.descripcion ?? ""}
                        onChange={(e) =>
                          form.setFieldValue(
                            `items.${index}.descripcion`,
                            e.currentTarget.value || null,
                          )
                        }
                      />
                    </Table.Td>
                    <Table.Td>
                      <NumberInput
                        size="xs"
                        variant="unstyled"
                        min={0}
                        hideControls
                        prefix="$"
                        thousandSeparator="."
                        decimalSeparator=","
                        {...form.getInputProps(`items.${index}.precio`)}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Autocomplete
                        size="xs"
                        variant="unstyled"
                        data={categoryOptions.map((c) => c.value)}
                        placeholder="Categoria"
                        {...form.getInputProps(`items.${index}.categoria`)}
                      />
                    </Table.Td>
                    <Table.Td>
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="red"
                        onClick={() => form.removeListItem("items", index)}
                        disabled={form.values.items.length <= 1}
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={handleAddRow}
          >
            Agregar plato
          </Button>

          {showOfficialCheckbox && (
            <Checkbox
              label="Usar este PDF como menu oficial para WhatsApp"
              description="Cuando un cliente pida el menu, se le enviara este PDF"
              {...form.getInputProps("set_as_official_pdf", {
                type: "checkbox",
              })}
            />
          )}

          {error && (
            <Alert color="red" icon={<IconX size={16} />} radius="md">
              {error}
            </Alert>
          )}

          <Group justify="flex-end">
            <Button
              variant="subtle"
              color="gray"
              onClick={() => {
                setStep("upload");
                setError(null);
              }}
            >
              Volver
            </Button>
            <Button
              color="indigo"
              onClick={handleConfirm}
              loading={confirmPending}
              disabled={
                form.values.items.length === 0 ||
                form.values.items.every((i) => !i.nombre.trim())
              }
            >
              Confirmar importacion
            </Button>
          </Group>
        </Stack>
      )}

      {/* ── STEP 3: RESULT ── */}
      {step === "result" && (
        <Stack gap="md">
          {/* Result from preview/confirm flow */}
          {result && (
            <Alert
              color={result.errors.length > 0 ? "yellow" : "green"}
              icon={<IconCheck size={16} />}
              radius="md"
              title="Importacion completada"
            >
              <List size="sm" spacing={4}>
                <List.Item>
                  <strong>{result.created}</strong> platos creados
                </List.Item>
                <List.Item>
                  <strong>{result.categories_created}</strong> secciones
                  nuevas
                </List.Item>
                <List.Item>
                  Version <strong>v{result.version}</strong> del menu
                </List.Item>
              </List>
              {result.errors.length > 0 && (
                <Text fz="xs" c="red" mt="xs">
                  Errores: {result.errors.join(", ")}
                </Text>
              )}
            </Alert>
          )}

          {/* Result from URL import (legacy direct flow) */}
          {urlResult && (
            <Alert
              color={urlResult.errors.length > 0 ? "yellow" : "green"}
              icon={<IconCheck size={16} />}
              radius="md"
              title="Importacion completada"
            >
              <List size="sm" spacing={4}>
                <List.Item>
                  <strong>{urlResult.created}</strong> platos creados
                </List.Item>
                <List.Item>
                  <strong>{urlResult.categories_created}</strong> secciones
                  nuevas
                </List.Item>
                {urlResult.images_uploaded !== undefined &&
                  urlResult.images_uploaded > 0 && (
                    <List.Item>
                      <strong>{urlResult.images_uploaded}</strong> imagenes
                      descargadas
                    </List.Item>
                  )}
              </List>
              {urlResult.errors.length > 0 && (
                <Text fz="xs" c="red" mt="xs">
                  Errores: {urlResult.errors.join(", ")}
                </Text>
              )}
            </Alert>
          )}

          <Group justify="flex-end" gap="sm">
            <Button
              variant="light"
              color="indigo"
              leftSection={<IconPhoto size={16} />}
              onClick={handleFinish}
            >
              Agregar imagenes a platos
            </Button>
            <Button variant="subtle" color="gray" onClick={handleClose}>
              Cerrar
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
