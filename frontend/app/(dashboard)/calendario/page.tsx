"use client";

import { CalendarView } from "@/components/calendario/CalendarView";
import { PageHeader } from "@/components/ui/PageHeader";
import { Paper, Stack } from "@mantine/core";

export default function CalendarioPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Calendario" />
      <Paper p="md" radius="md" shadow="sm">
        <CalendarView />
      </Paper>
    </Stack>
  );
}
