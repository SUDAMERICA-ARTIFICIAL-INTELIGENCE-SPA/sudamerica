"use client";

import {
  useAgenteConfigRaw,
  useUpdateAvailabilityInstructions,
} from "@/hooks/useAgenteConfig";
import { Button, Group, Skeleton, Stack, Textarea } from "@mantine/core";
import { useEffect, useState } from "react";

export function AvailabilityInstructions() {
  const { data: config, isLoading } = useAgenteConfigRaw();
  const { mutate: save, isPending } = useUpdateAvailabilityInstructions();
  const [value, setValue] = useState("");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (config) {
      const v = (config.instrucciones_disponibilidad as string) ?? "";
      setValue(v);
      setDirty(false);
    }
  }, [config]);

  function handleSave() {
    save(value, { onSuccess: () => setDirty(false) });
  }

  if (isLoading) return <Skeleton height={120} radius="md" />;

  return (
    <Stack gap="sm">
      <Textarea
        value={value}
        onChange={(e) => {
          setValue(e.currentTarget.value);
          setDirty(true);
        }}
        placeholder={"Ej: Si no hay pan de papa, ofrecer pan con sesamo.\nSi no hay Coca-Cola, ofrecer Pepsi.\nSi un plato esta agotado, sugerir el plato mas similar del menu."}
        rows={5}
        radius="md"
        aria-label="Instrucciones de disponibilidad"
      />
      <Group justify="flex-end">
        <Button
          onClick={handleSave}
          loading={isPending}
          disabled={!dirty}
          color="indigo"
          radius="md"
        >
          Guardar reglas
        </Button>
      </Group>
    </Stack>
  );
}
