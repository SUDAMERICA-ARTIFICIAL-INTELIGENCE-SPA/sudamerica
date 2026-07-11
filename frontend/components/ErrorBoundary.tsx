"use client";

import { Button, Center, Paper, Stack, Text, Title } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <Center py="xl" px="md">
          <Paper p="xl" radius="md" shadow="sm" maw={480} w="100%">
            <Stack align="center" gap="md">
              <IconAlertTriangle size={48} color="var(--mantine-color-orange-5)" stroke={1.5} />
              <Title order={3} ta="center">
                Algo salió mal
              </Title>
              <Text size="sm" c="dimmed" ta="center">
                Ocurrió un error inesperado. Intenta recargar la página.
              </Text>
              {this.state.error && (
                <Text
                  size="xs"
                  c="dimmed"
                  ta="center"
                  style={{
                    fontFamily: "monospace",
                    padding: "8px 12px",
                    borderRadius: 8,
                    backgroundColor: "var(--mantine-color-default)",
                    maxWidth: "100%",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {this.state.error.message}
                </Text>
              )}
              <Button
                variant="light"
                color="indigo"
                radius="md"
                onClick={() => {
                  this.setState({ hasError: false, error: null });
                  window.location.reload();
                }}
                aria-label="Recargar página"
              >
                Recargar página
              </Button>
            </Stack>
          </Paper>
        </Center>
      );
    }

    return this.props.children;
  }
}
