"use client";

import { Group, Paper, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface SectionCardProps {
  /** Título del header — si se omite, la card se renderiza sin zona de header (solo body). */
  title?: string;
  subtitle?: string;
  /** Slot de acciones a la derecha del header (botones, filtros, menú). */
  action?: ReactNode;
  /** Quita el padding del body — para tablas/listas a sangre. */
  noBodyPadding?: boolean;
  /** Estira la card al 100% de la altura del contenedor (columnas de Grid parejas). */
  fullHeight?: boolean;
  children: ReactNode;
}

const BODY_PADDING = 24;

/**
 * Card de sección — header con título + subtítulo opcional + slot de acción,
 * separado del body por una hairline. Pieza base para agrupar contenido
 * dentro de las vistas del dashboard (reemplaza `Paper` "a mano" con título).
 */
export function SectionCard({
  title,
  subtitle,
  action,
  noBodyPadding = false,
  fullHeight = false,
  children,
}: SectionCardProps) {
  return (
    <Paper
      radius="lg"
      shadow="sm"
      style={{ overflow: "hidden", height: fullHeight ? "100%" : undefined }}
    >
      {(title || action) && (
        <Group
          component="header"
          justify="space-between"
          align="flex-start"
          wrap="nowrap"
          gap="md"
          p="lg"
          style={{ borderBottom: "1px solid var(--mantine-color-default-border)" }}
        >
          <div style={{ minWidth: 0 }}>
            {title && (
              <Text
                component="h2"
                fw={600}
                style={{ fontSize: "15px", lineHeight: 1.3, margin: 0 }}
              >
                {title}
              </Text>
            )}
            {subtitle && (
              <Text size="xs" c="dimmed" mt={2}>
                {subtitle}
              </Text>
            )}
          </div>
          {action && (
            <Group gap="xs" wrap="nowrap" aria-label={title ? `Acciones de ${title}` : "Acciones"}>
              {action}
            </Group>
          )}
        </Group>
      )}
      <div style={{ padding: noBodyPadding ? 0 : BODY_PADDING }}>{children}</div>
    </Paper>
  );
}
