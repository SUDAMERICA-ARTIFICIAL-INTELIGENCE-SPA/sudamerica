"use client";

import { ImageUploadDrawer } from "@/components/carta/ImageUploadDrawer";
import { MenuImportModal } from "@/components/carta/MenuImportModal";
import { ModifierEditor } from "@/components/carta/ModifierEditor";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useCategorias } from "@/hooks/useCategorias";
import { useCreateProducto, useProductos, useUpdateProducto } from "@/hooks/useProductos";
import type { CreateProductoDto, UpdateProductoDto } from "@/hooks/useProductos";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useDeleteProductImage, useUploadProductImage } from "@/hooks/useUploadProductImage";
import { RUBRO_DEFAULT, plural } from "@/lib/rubros";
import type { Producto } from "@/lib/types";
import type { Categoria } from "@/lib/types";
import {
  Accordion,
  Badge,
  Button,
  Card,
  FileButton,
  Group,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import {
  IconCategory,
  IconEdit,
  IconFileUpload,
  IconPackage,
  IconPhoto,
  IconPlus,
  IconToolsKitchen2,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";

/** Unidades de venta (módulo precio_medida): el precio del producto es por esta unidad. */
const UNIDADES_VENTA = [
  { value: "unidad", label: "Por unidad" },
  { value: "kg", label: "Por kilo ($/kg)" },
  { value: "g", label: "Por gramo ($/g)" },
  { value: "m2", label: "Por metro cuadrado ($/m2)" },
  { value: "m", label: "Por metro ($/m)" },
  { value: "litro", label: "Por litro ($/litro)" },
  { value: "hora", label: "Por hora ($/hora)" },
];

function ProductoForm({
  opened,
  onClose,
  producto,
}: {
  opened: boolean;
  onClose: () => void;
  producto: Producto | null;
}) {
  const isEdit = !!producto;
  const { mutate: create, isPending: creating } = useCreateProducto();
  const { mutate: update, isPending: updating } = useUpdateProducto();
  const { mutate: uploadImage, isPending: uploading } = useUploadProductImage();
  const { mutate: deleteImage } = useDeleteProductImage();
  const { data: categorias } = useCategorias();
  const rubro = useRubroLabels();

  const isDefault = rubro.key === RUBRO_DEFAULT;
  const itemLabel = isDefault ? "Plato" : rubro.labels.item;
  const itemLower = isDefault ? "plato" : rubro.labels.item.toLowerCase();
  const categoriaLabel = isDefault ? "Seccion de Carta" : rubro.labels.categoria;
  const categoriaAria = isDefault ? "Seccion de carta" : rubro.labels.categoria;
  const conPrecioMedida = rubro.precioMedida ?? false;

  const form = useForm({
    initialValues: {
      nombre: "",
      descripcion: "",
      precio: "" as string | number,
      costo: "" as string | number,
      stock: "" as string | number,
      unidad_venta: "unidad",
      categoria_id: "",
    },
    validate: {
      nombre: (v) => (v.trim().length < 2 ? "Mínimo 2 caracteres" : null),
      precio: (v) => (Number(v) <= 0 ? "El precio debe ser mayor a 0" : null),
      costo: (v) => (v !== "" && Number(v) < 0 ? "El costo no puede ser negativo" : null),
    },
  });

  useEffect(() => {
    if (producto) {
      form.setValues({
        nombre: producto.nombre,
        descripcion: producto.descripcion ?? "",
        precio: producto.precio,
        costo: producto.costo ?? "",
        stock: producto.stock ?? "",
        unidad_venta: producto.unidad_venta ?? "unidad",
        categoria_id: producto.categoria_id ?? "",
      });
    } else {
      form.reset();
    }
  }, [producto, opened]);

  function handleSubmit(values: typeof form.values) {
    const dto: CreateProductoDto = {
      nombre: values.nombre.trim(),
      precio: Number(values.precio),
      ...(values.costo !== "" ? { costo: Number(values.costo) } : {}),
      ...(values.stock !== "" ? { stock: Number(values.stock) } : {}),
      ...(values.descripcion ? { descripcion: values.descripcion.trim() } : {}),
      ...(values.categoria_id ? { categoria_id: values.categoria_id } : {}),
      // Módulo precio_medida OFF (restaurante) → campo ausente, payload byte-idéntico.
      ...(conPrecioMedida ? { unidad_venta: values.unidad_venta } : {}),
    };

    if (isEdit) {
      update(
        { id: producto.id, dto: dto as UpdateProductoDto },
        {
          onSuccess: () => {
            form.reset();
            onClose();
          },
        },
      );
    } else {
      create(dto, {
        onSuccess: () => {
          form.reset();
          onClose();
        },
      });
    }
  }

  const catList =
    (categorias as { data?: Array<{ id: string; nombre: string }> })?.data ?? categorias ?? [];
  const catOptions = Array.isArray(catList)
    ? catList.map((c: { id: string; nombre: string }) => ({
        value: c.id,
        label: c.nombre,
      }))
    : [];

  function handleImageUpload(file: File | null) {
    if (file && producto) {
      uploadImage({ productoId: producto.id, file });
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEdit ? `Editar ${itemLabel}` : `Nuevo ${itemLabel}`}
      size="md"
      radius="md"
      centered={false}
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          {/* ── Imagen del plato (arriba, visible siempre en edit) ── */}
          {isEdit && producto && (
            <Stack gap="xs">
              <Text fz="sm" fw={500}>
                {`Imagen del ${itemLower}`}
              </Text>
              {producto.imagen_url ? (
                <Group gap="sm" align="center">
                  <img
                    src={producto.imagen_url}
                    alt={producto.nombre}
                    style={{
                      width: 80,
                      height: 80,
                      borderRadius: 8,
                      objectFit: "cover",
                    }}
                  />
                  <Stack gap={4}>
                    <FileButton
                      accept="image/png,image/jpeg,image/webp"
                      onChange={handleImageUpload}
                    >
                      {(props) => (
                        <Button
                          {...props}
                          size="xs"
                          variant="light"
                          color="indigo"
                          loading={uploading}
                          leftSection={<IconPhoto size={14} />}
                        >
                          Cambiar
                        </Button>
                      )}
                    </FileButton>
                    <Button
                      size="xs"
                      variant="light"
                      color="red"
                      leftSection={<IconTrash size={14} />}
                      onClick={() => deleteImage(producto.id)}
                    >
                      Eliminar
                    </Button>
                  </Stack>
                </Group>
              ) : (
                <FileButton accept="image/png,image/jpeg,image/webp" onChange={handleImageUpload}>
                  {(props) => (
                    <Button
                      {...props}
                      variant="light"
                      color="indigo"
                      loading={uploading}
                      leftSection={<IconUpload size={16} />}
                      radius="md"
                      fullWidth
                    >
                      Subir imagen (PNG, JPG, WebP)
                    </Button>
                  )}
                </FileButton>
              )}
            </Stack>
          )}

          <TextInput
            label={`Nombre del ${itemLower}`}
            placeholder="Hamburguesa Clásica"
            required
            radius="md"
            aria-label={`Nombre del ${itemLower}`}
            {...form.getInputProps("nombre")}
          />
          <Textarea
            label="Descripción"
            placeholder="Ingredientes, preparación..."
            rows={3}
            radius="md"
            aria-label="Descripción"
            {...form.getInputProps("descripcion")}
          />
          <Group grow gap="sm">
            <NumberInput
              label="Precio de venta"
              placeholder="0"
              min={0}
              decimalScale={0}
              prefix="$"
              required
              radius="md"
              aria-label="Precio de venta"
              {...form.getInputProps("precio")}
            />
            <NumberInput
              label="Costo"
              placeholder="0"
              min={0}
              decimalScale={0}
              prefix="$"
              radius="md"
              aria-label="Costo del producto"
              description="Para calcular food cost y margen"
              {...form.getInputProps("costo")}
            />
          </Group>
          <Group grow gap="sm">
            <NumberInput
              label="Stock"
              placeholder="0"
              min={0}
              decimalScale={0}
              radius="md"
              aria-label="Stock disponible"
              description="Se descuenta al entregar pedidos"
              {...form.getInputProps("stock")}
            />
            <Select
              label={categoriaLabel}
              placeholder="Sin seccion"
              data={catOptions}
              clearable
              radius="md"
              aria-label={categoriaAria}
              {...form.getInputProps("categoria_id")}
            />
          </Group>
          {conPrecioMedida && (
            <Select
              label="Unidad de venta"
              description="El precio corresponde a esta unidad (p. ej. $/kg)"
              data={UNIDADES_VENTA}
              allowDeselect={false}
              radius="md"
              aria-label="Unidad de venta"
              {...form.getInputProps("unidad_venta")}
            />
          )}

          {!isEdit && (
            <Text fz="xs" c="dimmed" ta="center">
              {isDefault
                ? "Guarda el plato primero para agregar una imagen."
                : `Guarda el ${itemLower} primero para agregar una imagen.`}
            </Text>
          )}

          <Group justify="flex-end" gap="sm" mt="xs">
            <Button variant="subtle" color="gray" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={creating || updating} color="indigo" radius="md">
              {isEdit ? "Guardar" : `Crear ${itemLabel}`}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function CartaTab() {
  const { data, isLoading } = useProductos({ page: 1, page_size: 100 });
  const { data: categorias } = useCategorias();
  const { mutate: updateProducto } = useUpdateProducto();
  const rubro = useRubroLabels();
  const isDefault = rubro.key === RUBRO_DEFAULT;
  const itemLabel = isDefault ? "Plato" : rubro.labels.item;
  const itemLower = isDefault ? "plato" : rubro.labels.item.toLowerCase();
  const itemsPlural = isDefault ? "Platos" : plural(rubro.labels.item);
  const [formOpened, setFormOpened] = useState(false);
  const [editing, setEditing] = useState<Producto | null>(null);
  const [importOpened, setImportOpened] = useState(false);
  const [imageDrawerOpened, setImageDrawerOpened] = useState(false);

  function handleToggleDisponible(p: Producto) {
    updateProducto({ id: p.id, dto: { disponible: p.disponible === false } });
  }

  const productos = data?.data ?? [];
  const catList: Categoria[] = Array.isArray(categorias) ? categorias : [];

  // Group products by category
  const grouped = useMemo(() => {
    const catMap = new Map<string, { nombre: string; items: Producto[] }>();
    const sinCategoria: Producto[] = [];

    // Build category name lookup
    const catNames = new Map<string, string>();
    for (const c of catList) {
      catNames.set(c.id, c.nombre);
    }

    for (const p of productos) {
      if (!p.categoria_id) {
        sinCategoria.push(p);
        continue;
      }
      const existing = catMap.get(p.categoria_id);
      if (existing) {
        existing.items.push(p);
      } else {
        catMap.set(p.categoria_id, {
          nombre: catNames.get(p.categoria_id) ?? "Sin sección",
          items: [p],
        });
      }
    }

    const sections = Array.from(catMap.entries()).map(([id, val]) => ({
      id,
      nombre: val.nombre,
      items: val.items,
    }));

    if (sinCategoria.length > 0) {
      sections.push({ id: "__sin_seccion__", nombre: "Sin sección", items: sinCategoria });
    }

    return sections;
  }, [productos, catList]);

  // All section IDs open by default
  const allSectionIds = useMemo(() => grouped.map((s) => s.id), [grouped]);

  function handleClose() {
    setFormOpened(false);
    setEditing(null);
  }

  return (
    <Stack gap="lg">
      <SectionCard
        title={`${itemsPlural} & Items`}
        action={
          <>
            <Button
              leftSection={<IconFileUpload size={16} />}
              variant="light"
              color="indigo"
              onClick={() => setImportOpened(true)}
              radius="md"
              aria-label="Importar menú"
            >
              Importar Menú
            </Button>
            <Button
              leftSection={<IconPlus size={16} />}
              color="indigo"
              onClick={() => {
                setEditing(null);
                setFormOpened(true);
              }}
              radius="md"
              aria-label={`Agregar ${itemLower}`}
            >
              {`Nuevo ${itemLabel}`}
            </Button>
          </>
        }
      >
        {isLoading ? (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={`skel-${i}`} height={100} radius="md" />
            ))}
          </SimpleGrid>
        ) : productos.length === 0 ? (
          <EmptyState
            title={
              isDefault
                ? "No hay platos en la carta. Agrega tu primer plato."
                : `No hay ${itemsPlural.toLowerCase()} en el catálogo. Agrega tu primer ${itemLower}.`
            }
          />
        ) : grouped.length <= 1 ? (
          /* Flat view if only one or no categories */
          <SectionItems
            items={productos}
            onEdit={(prod) => {
              setEditing(prod);
              setFormOpened(true);
            }}
            onToggleDisponible={handleToggleDisponible}
          />
        ) : (
          /* Grouped view with accordion sections */
          <Accordion
            multiple
            defaultValue={allSectionIds}
            variant="separated"
            radius="md"
            styles={{
              item: { borderColor: "var(--mantine-color-default-border)" },
            }}
          >
            {grouped.map((section) => (
              <Accordion.Item key={section.id} value={section.id}>
                <Accordion.Control>
                  <Group gap="sm">
                    <IconCategory size={18} style={{ opacity: 0.6 }} />
                    <Text fw={600} fz="md">
                      {section.nombre}
                    </Text>
                    <Badge size="sm" variant="light" color="gray">
                      {section.items.length}
                    </Badge>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <SectionItems
                    items={section.items}
                    onEdit={(prod) => {
                      setEditing(prod);
                      setFormOpened(true);
                    }}
                    onToggleDisponible={handleToggleDisponible}
                  />
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        )}
      </SectionCard>

      <ProductoForm opened={formOpened} onClose={handleClose} producto={editing} />
      <MenuImportModal
        opened={importOpened}
        onClose={() => setImportOpened(false)}
        onImportComplete={() => setImageDrawerOpened(true)}
      />
      <ImageUploadDrawer
        opened={imageDrawerOpened}
        onClose={() => setImageDrawerOpened(false)}
        productos={productos}
      />
    </Stack>
  );
}

// ─── Variant Detection ─────────────────────────────────────────────────────

const VARIANT_SEPARATOR = / - /;

interface VariantGroup {
  baseName: string;
  descripcion: string | null;
  variants: { label: string; producto: Producto }[];
}

/** Groups products by base name when they have " - Variant" suffixes. */
function groupVariants(items: Producto[]): (Producto | VariantGroup)[] {
  const groups = new Map<
    string,
    { desc: string | null; variants: { label: string; producto: Producto }[] }
  >();
  const standalone: Producto[] = [];

  for (const p of items) {
    const match = p.nombre.match(VARIANT_SEPARATOR);
    if (match && match.index !== undefined) {
      const baseName = p.nombre.slice(0, match.index).trim();
      const variantLabel = p.nombre.slice(match.index + match[0].length).trim();
      const existing = groups.get(baseName);
      if (existing) {
        existing.variants.push({ label: variantLabel, producto: p });
      } else {
        groups.set(baseName, {
          desc: p.descripcion,
          variants: [{ label: variantLabel, producto: p }],
        });
      }
    } else {
      standalone.push(p);
    }
  }

  const result: (Producto | VariantGroup)[] = [];

  // Groups with 2+ variants become VariantGroup; singles go back to standalone
  for (const [baseName, g] of groups) {
    if (g.variants.length >= 2) {
      result.push({ baseName, descripcion: g.desc, variants: g.variants });
    } else {
      standalone.push(g.variants[0]!.producto);
    }
  }

  // Add standalone cards at the end
  for (const p of standalone) {
    result.push(p);
  }

  return result;
}

function isVariantGroup(item: Producto | VariantGroup): item is VariantGroup {
  return "baseName" in item;
}

// ─── Display Components ────────────────────────────────────────────────────

function SectionItems({
  items,
  onEdit,
  onToggleDisponible,
}: {
  items: Producto[];
  onEdit: (p: Producto) => void;
  onToggleDisponible: (p: Producto) => void;
}) {
  const display = useMemo(() => groupVariants(items), [items]);

  return (
    <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
      {display.map((item) =>
        isVariantGroup(item) ? (
          <VariantGroupCard
            key={item.baseName}
            group={item}
            onEdit={onEdit}
            onToggleDisponible={onToggleDisponible}
          />
        ) : (
          <ProductoCard
            key={item.id}
            producto={item}
            onEdit={onEdit}
            onToggleDisponible={onToggleDisponible}
          />
        ),
      )}
    </SimpleGrid>
  );
}

function VariantGroupCard({
  group,
  onEdit,
  onToggleDisponible,
}: {
  group: VariantGroup;
  onEdit: (p: Producto) => void;
  onToggleDisponible: (p: Producto) => void;
}) {
  return (
    <Card radius="md" p="sm" withBorder>
      <Stack gap={6}>
        <Text fw={700} fz={15}>
          {group.baseName}
        </Text>
        {group.descripcion && (
          <Text fz={12} c="dimmed" lineClamp={2}>
            {group.descripcion}
          </Text>
        )}
        <Table
          horizontalSpacing={6}
          verticalSpacing={4}
          fz="sm"
          styles={{ table: { marginTop: 4 } }}
        >
          <Table.Tbody>
            {group.variants.map((v) => {
              const noDisp = v.producto.disponible === false;
              return (
                <Table.Tr key={v.producto.id} style={noDisp ? { opacity: 0.5 } : undefined}>
                  <Table.Td style={{ paddingLeft: 0 }}>
                    <Group gap={4} wrap="nowrap">
                      <Switch
                        size="xs"
                        checked={v.producto.disponible !== false}
                        onChange={() => onToggleDisponible(v.producto)}
                        aria-label={`Disponibilidad ${v.producto.nombre}`}
                      />
                      {v.producto.imagen_url && (
                        <img
                          src={v.producto.imagen_url}
                          alt={v.producto.nombre}
                          style={{ width: 28, height: 28, borderRadius: 4, objectFit: "cover" }}
                        />
                      )}
                      <Text fz={13} c="dimmed">
                        {v.label}
                      </Text>
                      {noDisp && (
                        <Badge size="xs" variant="filled" color="red">
                          No disponible
                        </Badge>
                      )}
                    </Group>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <Badge size="sm" variant="light" color="green">
                      ${Number(v.producto.precio).toLocaleString()}
                    </Badge>
                  </Table.Td>
                  <Table.Td style={{ width: 30, textAlign: "right", paddingRight: 0 }}>
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      onClick={() => onEdit(v.producto)}
                      aria-label={`Editar ${v.producto.nombre}`}
                    >
                      <IconEdit size={13} />
                    </Button>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Stack>
    </Card>
  );
}

function ProductoCard({
  producto: p,
  onEdit,
  onToggleDisponible,
}: {
  producto: Producto;
  onEdit: (p: Producto) => void;
  onToggleDisponible: (p: Producto) => void;
}) {
  const noDisponible = p.disponible === false;
  return (
    <Card radius="md" p="sm" withBorder style={noDisponible ? { opacity: 0.5 } : undefined}>
      <Stack gap="xs">
        <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
          {p.imagen_url && (
            <img
              src={p.imagen_url}
              alt={p.nombre}
              style={{
                width: 48,
                height: 48,
                borderRadius: 8,
                objectFit: "cover",
                flexShrink: 0,
              }}
            />
          )}
          <Stack gap={2} style={{ minWidth: 0, flex: 1 }}>
            <Text fw={600} fz={14} truncate="end">
              {p.nombre}
            </Text>
            {p.descripcion && (
              <Text fz={12} c="dimmed" lineClamp={1}>
                {p.descripcion}
              </Text>
            )}
          </Stack>
        </Group>
        <Group justify="space-between" wrap="nowrap">
          <Group gap={6} wrap="nowrap">
            <Switch
              size="xs"
              checked={p.disponible !== false}
              onChange={() => onToggleDisponible(p)}
              aria-label={`Disponibilidad ${p.nombre}`}
            />
            {noDisponible && (
              <Badge size="xs" variant="filled" color="red">
                No disponible
              </Badge>
            )}
          </Group>
          <Group gap={4} wrap="nowrap">
            <Badge size="lg" variant="light" color="green">
              ${Number(p.precio).toLocaleString()}
            </Badge>
            {p.costo != null && p.costo > 0 && (
              <Badge size="sm" variant="light" color="gray" title="Margen">
                {Math.round(((p.precio - p.costo) / p.precio) * 100)}%
              </Badge>
            )}
            <Button
              size="xs"
              variant="subtle"
              onClick={() => onEdit(p)}
              aria-label={`Editar ${p.nombre}`}
            >
              <IconEdit size={14} />
            </Button>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}

export default function CartaPage() {
  const rubro = useRubroLabels();
  const isDefault = rubro.key === RUBRO_DEFAULT;
  const catalogoTitle = isDefault ? "Carta & Menú" : rubro.labels.catalogo;
  const platosTab = isDefault ? "Platos" : plural(rubro.labels.item);

  return (
    <Stack gap="lg">
      <PageHeader title={catalogoTitle} />
      <Tabs defaultValue="platos" radius="md">
        <Tabs.List>
          <Tabs.Tab value="platos" leftSection={<IconPackage size={16} />}>
            {platosTab}
          </Tabs.Tab>
          <Tabs.Tab value="modificadores" leftSection={<IconToolsKitchen2 size={16} />}>
            Modificadores
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="platos" pt="md">
          <CartaTab />
        </Tabs.Panel>

        <Tabs.Panel value="modificadores" pt="md">
          <ModifierEditor />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
