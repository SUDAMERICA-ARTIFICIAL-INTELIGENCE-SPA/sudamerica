"use client";

import type { TopProduct } from "@/lib/types";
import { Badge, Divider, Group, Paper, Skeleton, Stack, Text } from "@mantine/core";

interface TopProductsListProps {
  products: TopProduct[];
  isLoading?: boolean;
  title: string;
  emptyMessage?: string;
  /** Omite el Paper + título propios — para cuando ya viene envuelto en SectionCard. */
  bare?: boolean;
}

function formatMoney(value: number) {
  return `$${Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(value)}`;
}

export function TopProductsList({
  products,
  isLoading,
  title,
  emptyMessage = "Aun no hay ventas registradas en este periodo.",
  bare = false,
}: TopProductsListProps) {
  if (isLoading) {
    return <Skeleton height={280} radius="md" />;
  }

  const list = (
    <Stack gap="sm">
      {!bare && (
        <Text
          fw={600}
          size="sm"
          c="dimmed"
          tt="uppercase"
          style={{ letterSpacing: "0.04em", fontSize: "11px" }}
        >
          {title}
        </Text>
      )}

      {products.length === 0 ? (
        <Text size="sm" c="dimmed">
          {emptyMessage}
        </Text>
      ) : (
        products.map((product, index) => (
          <Stack key={product.producto_id} gap={8}>
            <Group justify="space-between" align="flex-start" gap="sm">
              <Stack gap={2}>
                <Text fw={600} size="sm">
                  {product.nombre}
                </Text>
                <Text size="xs" c="dimmed">
                  {formatMoney(Number(product.revenue))} facturados
                </Text>
              </Stack>
              <Badge color="green" variant="light" radius="sm">
                {product.total_vendido} uds
              </Badge>
            </Group>
            {index < products.length - 1 && <Divider />}
          </Stack>
        ))
      )}
    </Stack>
  );

  if (bare) {
    return list;
  }

  return (
    <Paper p="md" radius="md" shadow="sm">
      {list}
    </Paper>
  );
}
