"use client";

import { usePlatformKeys, useRotateKey, useTenantKeys } from "@/hooks/useAdminApiKeys";
import {
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Modal,
  Pagination,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
  ThemeIcon,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconKey, IconRefresh } from "@tabler/icons-react";
import dayjs from "dayjs";
import { useState } from "react";

function KeyCard({
  provider,
  maskedKey,
  status,
  onRotate,
}: {
  provider: string;
  maskedKey: string;
  status: string;
  onRotate: () => void;
}) {
  return (
    <Card p="md" withBorder>
      <Group justify="space-between">
        <Group>
          <ThemeIcon size="lg" variant="light" color={provider === "openai" ? "green" : "blue"}>
            <IconKey size={20} />
          </ThemeIcon>
          <div>
            <Text fw={600} tt="uppercase" size="sm">
              {provider}
            </Text>
            <Text size="sm" c="dimmed" ff="monospace">
              {maskedKey}
            </Text>
          </div>
        </Group>
        <Group>
          <Badge color={status === "active" ? "green" : "red"} variant="light">
            {status}
          </Badge>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconRefresh size={14} />}
            onClick={onRotate}
          >
            Rotar
          </Button>
        </Group>
      </Group>
    </Card>
  );
}

export default function ApiKeysPage() {
  const { data: platformKeys, isLoading } = usePlatformKeys();
  const [keysPage, setKeysPage] = useState(1);
  const { data: tenantKeysData } = useTenantKeys({ page: keysPage });
  const rotateMutation = useRotateKey();
  const [modalOpened, modal] = useDisclosure(false);
  const [rotateProvider, setRotateProvider] = useState("");

  const form = useForm({
    initialValues: { new_key: "", reason: "" },
    validate: {
      new_key: (v) => (v.length < 10 ? "Key inválida" : null),
    },
  });

  const openRotateModal = (provider: string) => {
    setRotateProvider(provider);
    form.reset();
    modal.open();
  };

  const handleRotate = form.onSubmit((values) => {
    rotateMutation.mutate(
      { provider: rotateProvider, new_key: values.new_key, reason: values.reason || undefined },
      { onSuccess: () => modal.close() },
    );
  });

  return (
    <Stack gap="lg">
      <Title order={2}>API Keys</Title>

      <Text fw={600}>Keys de plataforma</Text>

      {isLoading ? (
        <Stack gap="sm">
          <Skeleton h={80} />
          <Skeleton h={80} />
        </Stack>
      ) : (
        <Stack gap="sm">
          {platformKeys?.openai && (
            <KeyCard
              provider="OpenAI"
              maskedKey={platformKeys.openai.masked_key}
              status={platformKeys.openai.status}
              onRotate={() => openRotateModal("openai")}
            />
          )}
          {platformKeys?.gemini && (
            <KeyCard
              provider="Gemini"
              maskedKey={platformKeys.gemini.masked_key}
              status={platformKeys.gemini.status}
              onRotate={() => openRotateModal("gemini")}
            />
          )}
          {!platformKeys?.openai && !platformKeys?.gemini && (
            <Text c="dimmed">No hay keys configuradas en este entorno.</Text>
          )}
        </Stack>
      )}

      <Divider my="md" />

      <Text fw={600}>Keys por tenant</Text>
      {tenantKeysData && tenantKeysData.data.length > 0 ? (
        <>
          <Card p={0}>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Tenant</Table.Th>
                  <Table.Th>Provider</Table.Th>
                  <Table.Th>Key</Table.Th>
                  <Table.Th>Creado</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {tenantKeysData.data.map((key) => (
                  <Table.Tr key={key.id}>
                    <Table.Td>{key.tenant_nombre || key.tenant_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="light">{key.provider}</Badge>
                    </Table.Td>
                    <Table.Td ff="monospace">{key.masked_key}</Table.Td>
                    <Table.Td>{dayjs(key.created_at).format("DD/MM/YYYY")}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
          {tenantKeysData.meta.total_pages > 1 && (
            <Group justify="center">
              <Pagination
                total={tenantKeysData.meta.total_pages}
                value={keysPage}
                onChange={setKeysPage}
              />
            </Group>
          )}
        </>
      ) : (
        <Text c="dimmed" size="sm">
          No hay keys de tenant configuradas.
        </Text>
      )}

      <Modal opened={modalOpened} onClose={modal.close} title={`Rotar key — ${rotateProvider.toUpperCase()}`}>
        <form onSubmit={handleRotate}>
          <Stack gap="sm">
            <TextInput
              label="Nueva API Key"
              placeholder="sk-..."
              required
              {...form.getInputProps("new_key")}
            />
            <Textarea
              label="Razón (opcional)"
              placeholder="Créditos agotados, rotación mensual..."
              {...form.getInputProps("reason")}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={modal.close}>
                Cancelar
              </Button>
              <Button type="submit" loading={rotateMutation.isPending}>
                Rotar key
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
}
