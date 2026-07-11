import { Badge, Card, Group, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconHourglassHigh } from "@tabler/icons-react";

interface ProximamenteProps {
  /** Nombre visible de la sección (label de la sub P2). */
  label: string;
  /** Categoría P2 a la que pertenece (contexto en el badge superior). */
  categoria?: string;
  /** Vistas nivel-3 del árbol — anticipo de lo que traerá la sección. */
  vistas?: readonly string[];
}

/**
 * Placeholder único para toda sub P2 sin ruta construida (NAV_TREE_ROUTES = null).
 * Mantine puro, sin lectura de color-scheme en render (evita hydration mismatch —
 * lección de dashboard-apple-v2); los colores salen de tokens/variables del tema.
 */
export function Proximamente({ label, categoria, vistas }: ProximamenteProps) {
  return (
    <Card withBorder radius="lg" padding="xl" style={{ maxWidth: 560, margin: "48px auto" }}>
      <Stack align="center" gap="sm" py="lg">
        <ThemeIcon size={56} radius="xl" variant="light" color="appleBlue" aria-hidden="true">
          <IconHourglassHigh size={28} />
        </ThemeIcon>
        {categoria && (
          <Badge variant="light" color="gray" size="sm">
            {categoria}
          </Badge>
        )}
        <Text fw={600} fz={20} ta="center">
          {label}
        </Text>
        <Badge variant="light" color="appleBlue" size="md" radius="sm">
          Próximamente
        </Badge>
        <Text c="dimmed" fz={14} ta="center">
          Esta sección está en construcción. Pronto vas a poder gestionarla desde aquí.
        </Text>
        {vistas && vistas.length > 0 && (
          <Group gap={6} justify="center" mt={4}>
            {vistas.map((vista) => (
              <Badge key={vista} variant="outline" color="gray" size="sm" radius="sm">
                {vista}
              </Badge>
            ))}
          </Group>
        )}
      </Stack>
    </Card>
  );
}
