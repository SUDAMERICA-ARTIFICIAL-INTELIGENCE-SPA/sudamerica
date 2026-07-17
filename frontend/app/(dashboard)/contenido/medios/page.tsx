"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useProductos } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
import { Group, Image, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";
import { IconPhoto, IconPhotoOff } from "@tabler/icons-react";
import { useMemo } from "react";

// Placeholder local (SVG data-URI) para imágenes rotas. Evita depender de un host
// externo (placehold.co) — imprescindible en el export estático servido por Pages.
const FALLBACK_IMG =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><rect width="300" height="300" fill="#e9ecef"/><text x="50%" y="50%" fill="#868e96" font-family="sans-serif" font-size="20" text-anchor="middle" dominant-baseline="middle">Sin imagen</text></svg>',
  );

export default function Page() {
  const { data, isLoading } = useProductos({ page: 1, page_size: 100 });

  const { conImagen, sinImagen } = useMemo(() => {
    const items = data?.data ?? [];
    return {
      conImagen: items.filter((p: Producto) => !!p.imagen_url),
      sinImagen: items.filter((p: Producto) => !p.imagen_url),
    };
  }, [data]);

  return (
    <Stack gap="lg">
      <PageHeader title="Biblioteca de medios" subtitle="Imágenes de los productos del catálogo" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Imágenes" value={conImagen.length} isLoading={isLoading} color="grape" icon={<IconPhoto size={18} />} />
        <KpiCard title="Sin imagen" value={sinImagen.length} isLoading={isLoading} color="orange" icon={<IconPhotoOff size={18} />} />
      </SimpleGrid>

      <SectionCard title="Galería" subtitle={`${conImagen.length} imágenes`}>
        {isLoading ? (
          <SimpleGrid cols={{ base: 2, sm: 3, lg: 5 }}>
            {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={140} radius="md" />)}
          </SimpleGrid>
        ) : conImagen.length === 0 ? (
          <EmptyState icon={<IconPhoto size={40} />} title="Sin imágenes" description="Ningún producto tiene imagen cargada todavía." />
        ) : (
          <SimpleGrid cols={{ base: 2, sm: 3, lg: 5 }}>
            {conImagen.map((p) => (
              <Stack key={p.id} gap={6}>
                <Image
                  src={p.imagen_url ?? ""}
                  h={130}
                  radius="md"
                  alt={p.nombre}
                  fit="cover"
                  fallbackSrc={FALLBACK_IMG}
                />
                <Text size="xs" c="dimmed" lineClamp={2} ta="center">{p.nombre}</Text>
              </Stack>
            ))}
          </SimpleGrid>
        )}
      </SectionCard>

      {!isLoading && sinImagen.length > 0 && (
        <SectionCard title="Sin imagen" subtitle={`${sinImagen.length} productos sin foto`}>
          <Stack gap="xs">
            {sinImagen.map((p) => (
              <Group key={p.id} gap="xs" wrap="nowrap">
                <IconPhotoOff size={16} color="var(--mantine-color-dimmed)" />
                <Text size="sm">{p.nombre}</Text>
              </Group>
            ))}
          </Stack>
        </SectionCard>
      )}
    </Stack>
  );
}
