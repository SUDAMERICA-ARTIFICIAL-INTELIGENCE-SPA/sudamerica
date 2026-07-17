"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useProductos } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
import { Avatar, Badge, Card, Group, Image, SimpleGrid, Skeleton, Stack, Text, TextInput } from "@mantine/core";
import { IconPhoto, IconSearch } from "@tabler/icons-react";
import { useMemo, useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

type ProductoSku = Producto & { sku?: string | null };

export default function Page() {
  const [search, setSearch] = useState("");
  const { data, isLoading } = useProductos({ page: 1, page_size: 60 });

  const productos = useMemo(() => {
    const q = search.trim().toLowerCase();
    return ((data?.data ?? []) as ProductoSku[])
      .filter((p) => !(p.sku ?? "").startsWith("SERV-"))
      .filter((p) => (q ? p.nombre.toLowerCase().includes(q) : true));
  }, [data, search]);

  return (
    <Stack gap="lg">
      <PageHeader title="Vitrina" subtitle="Catálogo público: cómo se ven los productos disponibles para tus clientes" />

      <SectionCard
        title="Productos"
        action={
          <TextInput
            leftSection={<IconSearch size={16} />}
            placeholder="Buscar…"
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            maw={260}
          />
        }
      >
        {isLoading ? (
          <SimpleGrid cols={{ base: 2, sm: 3, lg: 4 }}>
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <Skeleton key={i} height={220} radius="md" />)}
          </SimpleGrid>
        ) : productos.length === 0 ? (
          <EmptyState icon={<IconPhoto size={40} />} title="Sin productos" description="No hay productos que coincidan con la búsqueda." />
        ) : (
          <SimpleGrid cols={{ base: 2, sm: 3, lg: 4 }}>
            {productos.map((p) => (
              <Card key={p.id} radius="md" withBorder padding="sm">
                <Card.Section>
                  {p.imagen_url ? (
                    <Image src={p.imagen_url} h={150} alt={p.nombre} fit="cover" />
                  ) : (
                    <Group h={150} justify="center" align="center" bg="var(--mantine-color-default-hover)">
                      <Avatar size={56} radius="md" color="grape"><IconPhoto size={28} /></Avatar>
                    </Group>
                  )}
                </Card.Section>
                <Stack gap={6} mt="sm">
                  <Text fw={500} size="sm" lineClamp={2}>{p.nombre}</Text>
                  <Group justify="space-between" align="center">
                    <Text fw={700}>{clp(Number(p.precio))}</Text>
                    {Number(p.stock) > 0 ? (
                      <Badge variant="light" color="green" radius="sm">Disponible</Badge>
                    ) : (
                      <Badge variant="light" color="red" radius="sm">Agotado</Badge>
                    )}
                  </Group>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </SectionCard>
    </Stack>
  );
}
