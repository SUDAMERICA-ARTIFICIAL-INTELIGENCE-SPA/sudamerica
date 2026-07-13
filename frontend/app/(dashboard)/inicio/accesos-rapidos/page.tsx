"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { navItemsFlatCanonico } from "@/lib/nav-canonico";
import { Group, SimpleGrid, Stack, Text, ThemeIcon, UnstyledButton } from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

export default function Page() {
  const router = useRouter();
  const rubro = useRubroLabels();

  // Agrupa los accesos visibles del rubro por categoría (excluye este mismo acceso).
  const grupos = useMemo(() => {
    const items = navItemsFlatCanonico(rubro).filter(({ sub }) => sub.id !== "inicio-accesos");
    const byCat = new Map<string, typeof items>();
    for (const it of items) {
      const arr = byCat.get(it.catLabel) ?? [];
      arr.push(it);
      byCat.set(it.catLabel, arr);
    }
    return [...byCat.entries()];
  }, [rubro]);

  return (
    <Stack gap="lg">
      <PageHeader title="Accesos rápidos" subtitle="Todas las secciones de tu negocio, a un clic" />
      {grupos.map(([cat, items]) => (
        <SectionCard key={cat} title={cat}>
          <SimpleGrid cols={{ base: 1, xs: 2, md: 3, lg: 4 }} spacing="sm">
            {items.map(({ sub, label }) => (
              <UnstyledButton
                key={sub.id}
                onClick={() => router.push(sub.href)}
                style={{ borderRadius: 12, padding: 12, border: "1px solid var(--mantine-color-default-border)" }}
              >
                <Group gap="sm" wrap="nowrap">
                  <ThemeIcon size={38} radius="md" variant="light" color="indigo">
                    <sub.icon size={20} />
                  </ThemeIcon>
                  <Text fw={500} size="sm" style={{ flex: 1 }}>{label}</Text>
                  <IconChevronRight size={16} opacity={0.4} />
                </Group>
              </UnstyledButton>
            ))}
          </SimpleGrid>
        </SectionCard>
      ))}
    </Stack>
  );
}
