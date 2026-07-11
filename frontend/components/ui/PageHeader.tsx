"use client";

import { TYPOGRAPHY } from "@/lib/theme-tokens";
import { Group, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

/**
 * Encabezado de página — título (jerarquía `TYPOGRAPHY.pageTitle`), subtítulo opcional
 * y slot de acciones a la derecha. Pieza base de PageHeader para todas las vistas
 * del dashboard; ver `frontend/CLAUDE.md`.
 */
export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <Group component="header" justify="space-between" align="flex-start" wrap="wrap" gap="md">
      <div style={{ minWidth: 0 }}>
        <Text component="h1" style={{ ...TYPOGRAPHY.pageTitle, margin: 0 }}>
          {title}
        </Text>
        {subtitle && (
          <Text c="dimmed" style={{ ...TYPOGRAPHY.body, marginTop: 4 }}>
            {subtitle}
          </Text>
        )}
      </div>
      {actions && (
        <Group gap="sm" wrap="wrap" aria-label={`Acciones de ${title}`}>
          {actions}
        </Group>
      )}
    </Group>
  );
}
