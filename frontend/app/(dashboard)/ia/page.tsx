"use client";

import { AIMetrics } from "@/components/ia/AIMetrics";
import { AIPerformanceHeader } from "@/components/ia/AIPerformanceHeader";
import { InsightsFeed } from "@/components/ia/InsightsFeed";
import { RevisionHumanaQueue } from "@/components/ia/RevisionHumanaQueue";
import { Grid, SimpleGrid, Skeleton, Stack } from "@mantine/core";
import dynamic from "next/dynamic";

const HumanVsAIChart = dynamic(
  () =>
    import("@/components/ia/HumanVsAIChart").then((m) => ({
      default: m.HumanVsAIChart,
    })),
  {
    ssr: false,
    loading: () => (
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <Skeleton height={200} radius="md" />
        <Skeleton height={200} radius="md" />
      </SimpleGrid>
    ),
  },
);

export default function IAPage() {
  return (
    <Stack gap="lg">
      {/* F-Pattern Row 1: 4 KPI cards */}
      <AIPerformanceHeader />
      <AIMetrics />

      {/* F-Pattern Row 2: Charts */}
      <HumanVsAIChart />

      {/* F-Pattern Row 3: Insights + Review Queue */}
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <InsightsFeed />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <RevisionHumanaQueue />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
