"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useUsuarios } from "@/hooks/useUsuarios";
import { useVentas } from "@/hooks/useVentas";
import type { Usuario, Venta } from "@/lib/types";
import { Avatar, Badge, Group, Paper, Skeleton, Stack, Table, Text } from "@mantine/core";

interface AdvisorStats {
  usuario: Usuario;
  ventasCount: number;
  revenueTotal: number;
  leadsConvertidos: number;
  rank: number;
}

function getInitials(nombre: string) {
  return nombre
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function RankBadge({ rank }: { rank: number }) {
  const medals = ["🥇", "🥈", "🥉"];
  if (rank <= 3) {
    return (
      <Text fz={18} role="img" aria-label={`Puesto ${rank}`}>
        {medals[rank - 1]}
      </Text>
    );
  }
  return (
    <Text fw={600} c="dimmed" fz={14} aria-label={`Puesto ${rank}`}>
      #{rank}
    </Text>
  );
}

function buildLeaderboard(usuarios: Usuario[], ventas: Venta[]): AdvisorStats[] {
  const stats = usuarios.map((u) => {
    const uvs = ventas.filter((v) => v.asesor_id === u.id);
    return {
      usuario: u,
      ventasCount: uvs.length,
      revenueTotal: uvs.reduce((s, v) => s + v.total, 0),
      leadsConvertidos: uvs.length,
      rank: 0,
    };
  });

  stats.sort((a, b) => b.revenueTotal - a.revenueTotal);
  return stats.map((s, i) => ({ ...s, rank: i + 1 }));
}

export function LeaderboardTable() {
  const { data: usuarios, isLoading: usersLoading } = useUsuarios();
  const { data: ventas, isLoading: ventasLoading } = useVentas({
    page_size: 100,
  });

  const isLoading = usersLoading || ventasLoading;

  if (isLoading) {
    return (
      <Paper p="md" radius="md" shadow="sm">
        <Skeleton height={20} width="40%" mb="md" />
        <Stack gap="xs">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height={52} radius="sm" />
          ))}
        </Stack>
      </Paper>
    );
  }

  const leaderboard = buildLeaderboard(usuarios ?? [], ventas?.data ?? []);

  return (
    <SectionCard title="Ranking del Equipo" noBodyPadding>
      {leaderboard.length === 0 ? (
        <EmptyState
          icon="👥"
          title="Sin datos de equipo"
          description="No hay asesores registrados."
        />
      ) : (
        <Table highlightOnHover aria-label="Tabla de ranking del equipo">
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 48 }}>#</Table.Th>
              <Table.Th>Asesor</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Ventas</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Ingresos</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {leaderboard.map((row) => (
              <Table.Tr key={row.usuario.id}>
                <Table.Td>
                  <RankBadge rank={row.rank} />
                </Table.Td>
                <Table.Td>
                  <Group gap="sm" wrap="nowrap">
                    <Avatar size={32} radius="xl" color="indigo" aria-hidden="true">
                      {getInitials(row.usuario.nombre)}
                    </Avatar>
                    <Stack gap={0}>
                      <Text size="sm" fw={500} lineClamp={1}>
                        {row.usuario.nombre}
                      </Text>
                      <Badge size="xs" variant="light" color="gray">
                        {row.usuario.role}
                      </Badge>
                    </Stack>
                  </Group>
                </Table.Td>
                <Table.Td className="num-tabular">
                  <Text size="sm" fw={600}>
                    {row.ventasCount}
                  </Text>
                </Table.Td>
                <Table.Td className="num-tabular">
                  <Text size="sm" fw={600} c="indigo">
                    $
                    {Intl.NumberFormat("es-AR", {
                      maximumFractionDigits: 0,
                    }).format(row.revenueTotal)}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </SectionCard>
  );
}
