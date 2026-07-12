"use client";

import { DailyReport } from "@/components/reportes/DailyReport";
import { FinancialDashboard } from "@/components/reportes/FinancialDashboard";
import { MenuEngineering } from "@/components/reportes/MenuEngineering";
import { MonthlyReport } from "@/components/reportes/MonthlyReport";
import { WeeklyReport } from "@/components/reportes/WeeklyReport";
import { PageHeader } from "@/components/ui/PageHeader";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { Stack, Tabs } from "@mantine/core";
import {
  IconCalendar,
  IconCalendarMonth,
  IconCalendarWeek,
  IconChartBar,
  IconCoin,
} from "@tabler/icons-react";

export default function ReportesPage() {
  const rubro = useRubroLabels();
  // "Menu Engineering" (matriz Estrella/Puzzle sobre platos) es gastronómico puro:
  // se oculta para rubros de otro sector en vez de mostrar un análisis sin sentido.
  const showMenuEngineering = !rubro.isLoading && rubro.sector === "gastronomia";

  return (
    <Stack gap="lg">
      <PageHeader title="Reportes" />

      <Tabs defaultValue="diario" keepMounted={false} variant="pills" radius="md">
        <Tabs.List mb="lg" aria-label="Seleccionar periodo de reporte">
          <Tabs.Tab
            value="financiero"
            leftSection={<IconCoin size={16} />}
            aria-label="Dashboard financiero"
          >
            Financiero
          </Tabs.Tab>
          <Tabs.Tab
            value="diario"
            leftSection={<IconCalendar size={16} />}
            aria-label="Reporte diario"
          >
            Diario
          </Tabs.Tab>
          <Tabs.Tab
            value="semanal"
            leftSection={<IconCalendarWeek size={16} />}
            aria-label="Reporte semanal"
          >
            Semanal
          </Tabs.Tab>
          <Tabs.Tab
            value="mensual"
            leftSection={<IconCalendarMonth size={16} />}
            aria-label="Reporte mensual"
          >
            Mensual
          </Tabs.Tab>
          {showMenuEngineering && (
            <Tabs.Tab
              value="menu"
              leftSection={<IconChartBar size={16} />}
              aria-label="Ingenieria de menu"
            >
              Menu Engineering
            </Tabs.Tab>
          )}
        </Tabs.List>

        <Tabs.Panel value="financiero">
          <FinancialDashboard />
        </Tabs.Panel>

        <Tabs.Panel value="diario">
          <DailyReport />
        </Tabs.Panel>

        <Tabs.Panel value="semanal">
          <WeeklyReport />
        </Tabs.Panel>

        <Tabs.Panel value="mensual">
          <MonthlyReport />
        </Tabs.Panel>

        {showMenuEngineering && (
          <Tabs.Panel value="menu">
            <MenuEngineering />
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  );
}
