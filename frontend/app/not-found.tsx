import { Anchor, Center, Stack, Text, Title } from "@mantine/core";
import Link from "next/link";

export default function NotFound() {
  return (
    <Center mih="100dvh" p="xl">
      <Stack align="center" gap="xs">
        <Title order={1}>404</Title>
        <Text c="dimmed">Esta página no existe.</Text>
        <Anchor component={Link} href="/dashboard">
          Ir al inicio
        </Anchor>
      </Stack>
    </Center>
  );
}
