"use client";

import {
  useUploadProductImage,
} from "@/hooks/useUploadProductImage";
import type { Producto } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Drawer,
  Group,
  Progress,
  ScrollArea,
  Stack,
  Text,
  rem,
} from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import {
  IconCheck,
  IconPhoto,
  IconUpload,
  IconX,
} from "@tabler/icons-react";
import { useState } from "react";

const IMAGE_ACCEPT = ["image/png", "image/jpeg", "image/webp"];
const IMAGE_MAX_SIZE = 5 * 1024 * 1024; // 5 MB

export function ImageUploadDrawer({
  opened,
  onClose,
  productos,
}: {
  opened: boolean;
  onClose: () => void;
  productos: Producto[];
}) {
  const { mutate: uploadImage, isPending } = useUploadProductImage();
  const [uploadedIds, setUploadedIds] = useState<Set<string>>(new Set());
  const [uploadingId, setUploadingId] = useState<string | null>(null);

  const withoutImage = productos.filter(
    (p) => !p.imagen_url && p.activo,
  );
  const total = withoutImage.length;
  const done = uploadedIds.size;

  function handleDrop(productoId: string, files: File[]) {
    const file = files[0];
    if (!file) return;
    setUploadingId(productoId);

    uploadImage(
      { productoId, file },
      {
        onSuccess: () => {
          setUploadedIds((prev) => new Set(prev).add(productoId));
          setUploadingId(null);
        },
        onError: () => {
          setUploadingId(null);
        },
      },
    );
  }

  function handleClose() {
    setUploadedIds(new Set());
    setUploadingId(null);
    onClose();
  }

  return (
    <Drawer
      opened={opened}
      onClose={handleClose}
      title="Agregar imagenes a platos"
      position="right"
      size="md"
    >
      <Stack gap="md">
        <Group justify="space-between">
          <Text fz="sm" c="dimmed">
            Sube imagenes para los platos que no tienen una.
          </Text>
          <Badge size="sm" variant="light">
            {done} de {total}
          </Badge>
        </Group>

        {total > 0 && (
          <Progress
            value={total > 0 ? (done / total) * 100 : 0}
            color="indigo"
            size="sm"
            radius="md"
          />
        )}

        <ScrollArea h="calc(100vh - 200px)" offsetScrollbars>
          <Stack gap="sm">
            {withoutImage.length === 0 ? (
              <Card radius="md" p="lg" withBorder>
                <Stack align="center" gap="xs">
                  <IconCheck size={32} color="var(--mantine-color-green-6)" />
                  <Text ta="center" fw={500}>
                    Todos los platos tienen imagen
                  </Text>
                </Stack>
              </Card>
            ) : (
              withoutImage.map((p) => {
                const isUploaded = uploadedIds.has(p.id);
                const isUploading = uploadingId === p.id;

                return (
                  <Card key={p.id} radius="md" p="sm" withBorder>
                    <Group justify="space-between" wrap="nowrap" gap="sm">
                      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
                        <Text fw={600} fz="sm" truncate="end">
                          {p.nombre}
                        </Text>
                        <Badge size="xs" variant="light" color="green">
                          ${Number(p.precio).toLocaleString()}
                        </Badge>
                      </Stack>

                      {isUploaded ? (
                        <Badge
                          size="lg"
                          variant="light"
                          color="green"
                          leftSection={<IconCheck size={14} />}
                        >
                          Listo
                        </Badge>
                      ) : (
                        <Dropzone
                          onDrop={(files) => handleDrop(p.id, files)}
                          accept={IMAGE_ACCEPT}
                          maxSize={IMAGE_MAX_SIZE}
                          multiple={false}
                          loading={isUploading}
                          radius="md"
                          style={{ width: 120 }}
                          p={6}
                        >
                          <Group
                            justify="center"
                            gap={4}
                            style={{ pointerEvents: "none" }}
                          >
                            <Dropzone.Accept>
                              <IconUpload size={16} color="var(--mantine-color-indigo-6)" />
                            </Dropzone.Accept>
                            <Dropzone.Reject>
                              <IconX size={16} color="var(--mantine-color-red-6)" />
                            </Dropzone.Reject>
                            <Dropzone.Idle>
                              <IconPhoto size={16} color="var(--mantine-color-dimmed)" />
                            </Dropzone.Idle>
                            <Text fz={11} c="dimmed">
                              Subir
                            </Text>
                          </Group>
                        </Dropzone>
                      )}
                    </Group>
                  </Card>
                );
              })
            )}
          </Stack>
        </ScrollArea>

        <Button variant="subtle" color="gray" onClick={handleClose} fullWidth>
          Finalizar
        </Button>
      </Stack>
    </Drawer>
  );
}
