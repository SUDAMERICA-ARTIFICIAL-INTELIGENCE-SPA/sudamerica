"use client";

import { LeaderboardTable } from "@/components/equipo/LeaderboardTable";
import { TeamTargets } from "@/components/equipo/TeamTargets";
import { TeamUserManager } from "@/components/equipo/TeamUserManager";
import { PageHeader } from "@/components/ui/PageHeader";
import { Stack } from "@mantine/core";

export default function EquipoPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Equipo" />
      <TeamUserManager />
      <TeamTargets />
      <LeaderboardTable />
    </Stack>
  );
}
