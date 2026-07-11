"use client";

import { RUBRO_OPTIONS, rubroSectorConfig } from "@/lib/rubros";
import { Badge, Card, Container, SimpleGrid, Stack, Text, TextInput, Title } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import Link from "next/link";
import { useMemo, useState } from "react";

// Panel-lanzador: una cuenta demo por rubro (auto-escala con el SSOT). Cada card entra
// al dashboard demo de ese rubro (mismos componentes → misma estética). Sin login ni backend.
export default function ShowroomPanel() {
  const [query, setQuery] = useState("");

  const cards = useMemo(() => {
    const all = RUBRO_OPTIONS.map((o) => ({
      key: o.value,
      nombre: o.label,
      emoji: o.emoji,
      sector: rubroSectorConfig(o.value).label,
    }));
    const needle = query.trim().toLowerCase();
    if (!needle) return all;
    return all.filter(
      (c) => c.nombre.toLowerCase().includes(needle) || c.sector.toLowerCase().includes(needle),
    );
  }, [query]);

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Text size="xs" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: "0.08em" }}>
            Sudamérica AI · Showroom
          </Text>
          <Title order={1} style={{ letterSpacing: "-0.6px" }}>
            {RUBRO_OPTIONS.length} cuentas demo
          </Title>
          <Text c="dimmed" size="sm">
            Explora el dashboard con datos realistas para cada uno de los {RUBRO_OPTIONS.length}{" "}
            rubros. Elige una cuenta para entrar — sin login ni backend.
          </Text>
        </Stack>

        <TextInput
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          placeholder="Buscar por rubro o sector…"
          leftSection={<IconSearch size={16} />}
          size="md"
          radius="md"
          aria-label="Buscar rubro"
          maw={420}
        />

        <Text size="sm" c="dimmed" aria-live="polite">
          {cards.length} {cards.length === 1 ? "cuenta" : "cuentas"}
        </Text>

        <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 4, lg: 5 }} spacing="md">
          {cards.map((c) => (
            <Card
              key={c.key}
              component={Link}
              href={`/showroom/${c.key}`}
              withBorder
              radius="md"
              padding="lg"
              aria-label={`Abrir dashboard demo de ${c.nombre}`}
              style={{ transition: "transform 150ms ease, box-shadow 150ms ease" }}
            >
              <Stack gap="xs" align="flex-start">
                <Text style={{ fontSize: 34, lineHeight: 1 }} aria-hidden>
                  {c.emoji}
                </Text>
                <Text fw={600} lineClamp={2}>
                  {c.nombre}
                </Text>
                <Badge variant="light" color="grape" radius="sm" size="sm">
                  {c.sector}
                </Badge>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  );
}
