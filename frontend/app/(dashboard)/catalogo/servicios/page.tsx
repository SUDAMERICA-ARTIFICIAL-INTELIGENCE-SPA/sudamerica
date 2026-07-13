"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useProductos } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
import { Card, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";
import { useMemo } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

type ProductoSku = Producto & { sku?: string | null };

export default function Page() {
  const { data, isLoading } = useProductos({ page: 1, page_size: 100 });

  const servicios = useMemo(
    () => ((data?.data ?? []) as ProductoSku[]).filter((p) => (p.sku ?? "").startsWith("SERV-")),
    [data],
  );

  const precioPromedio = servicios.length > 0
    ? servicios.reduce((s, p) => s + Number(p.precio), 0) / servicios.length
    : 0;

  return (
    <Stack gap="lg">
      <PageHeader title="Servicios" subtitle="Servicios de belleza ofrecidos, con duración y precio" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Servicios" value={servicios.length} isLoading={isLoading} color="grape" icon={<IconSparkles size={18} />} />
        <KpiCard title="Precio promedio" value={precioPromedio} prefix="$" isLoading={isLoading} color="teal" />
      </SimpleGrid>

      <SectionCard title="Catálogo de servicios">
        {isLoading ? (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} height={120} radius="md" />)}
          </SimpleGrid>
        ) : servicios.length === 0 ? (
          <EmptyState icon={<IconSparkles size={40} />} title="Sin servicios" description="Aún no hay servicios registrados en el catálogo." />
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            {servicios.map((s) => (
              <Card key={s.id} radius="md" withBorder padding="lg">
                <Stack gap="xs">
                  <Text fw={600}>{s.nombre}</Text>
                  <Text size="sm" c="dimmed">{s.descripcion ?? "—"}</Text>
                  <Text fw={700} size="lg" c="grape.7">{clp(Number(s.precio))}</Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </SectionCard>
    </Stack>
  );
}
