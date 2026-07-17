"use client";

import { MenuImportModal } from "@/components/carta/MenuImportModal";
import { useProductos } from "@/hooks/useProductos";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { plural } from "@/lib/rubros";
import { Alert, Button, Group, Stack, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconArrowLeft, IconArrowRight, IconInfoCircle, IconUpload } from "@tabler/icons-react";
import { type OnboardingStepProps, nowIso, useSaveOnboarding } from "./shared";

export function StepDatos({ goNext, goBack }: OnboardingStepProps) {
  const rubro = useRubroLabels();
  const save = useSaveOnboarding();
  const [opened, handlers] = useDisclosure(false);
  const { data, refetch } = useProductos({ page: 1, page_size: 1 });

  const count = data?.meta.total ?? 0;
  const catalogoLower = rubro.labels.catalogo.toLowerCase();
  const itemsLower = plural(rubro.labels.item).toLowerCase();

  async function finish(skipped: boolean) {
    await save.mutateAsync({
      onboarding: skipped ? { datos_skipped_at: nowIso() } : { datos_completed_at: nowIso() },
    });
    goNext();
  }

  return (
    <>
      <MenuImportModal
        opened={opened}
        onClose={handlers.close}
        onImportComplete={() => void refetch()}
      />

      <Stack gap="md">
        <Text c="dimmed" size="sm">
          Sube tu {catalogoLower} desde el archivo que ya tengas — CSV, PDF o una foto. Extraemos{" "}
          {itemsLower} y categorías, y los revisas antes de guardar.
        </Text>

        <Alert color={count > 0 ? "green" : "blue"} radius="md" icon={<IconInfoCircle size={16} />}>
          {count > 0
            ? `Tu ${catalogoLower} tiene ${count} ${itemsLower}. Volver a subir agrega ítems (no reemplaza).`
            : `Aún no cargaste ${itemsLower}. Es opcional: puedes hacerlo ahora o más tarde.`}
        </Alert>

        <Group>
          <Button leftSection={<IconUpload size={16} />} onClick={handlers.open}>
            {rubro.labels.ingesta}
          </Button>
        </Group>

        <Group justify="space-between" mt="xs">
          <Button
            variant="subtle"
            color="gray"
            leftSection={<IconArrowLeft size={16} />}
            onClick={goBack}
          >
            Atrás
          </Button>
          <Group gap="xs">
            <Button
              variant="subtle"
              color="gray"
              onClick={() => void finish(true)}
              loading={save.isPending}
            >
              Lo haré luego
            </Button>
            <Button
              onClick={() => void finish(false)}
              loading={save.isPending}
              disabled={count === 0}
              rightSection={<IconArrowRight size={16} />}
            >
              Continuar
            </Button>
          </Group>
        </Group>
      </Stack>
    </>
  );
}
