"use client";

import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useWithBase } from "@/lib/demo/showroom-nav";
import { useSsrColorScheme } from "@/hooks/useSsrColorScheme";
import { navItemsFlatCanonico } from "@/lib/nav-canonico";
import { GLASS } from "@/lib/theme-tokens";
import { useUiStore } from "@/stores/ui-store";
import {
  Group,
  Kbd,
  Modal,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  UnstyledButton,
  useMantineColorScheme,
} from "@mantine/core";
import {
  IconBrain,
  IconCalculator,
  IconHome,
  IconLayoutGrid,
  IconLayoutKanban,
  IconMoon,
  IconSearch,
  IconSparkles,
  IconStar,
  IconSun,
} from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";

interface CommandItem {
  id: string;
  label: string;
  description: string;
  icon: ReactNode;
  color: string;
  execute: () => void;
}

interface LegacyCommandDef {
  id: string;
  label: string;
  description: string;
  icon: ReactNode;
  href: string;
  color: string;
}

/**
 * Huérfanos vivos: rutas reales fuera del sidebar canónico (decisión Paso 7 §D). Se
 * mantienen accesibles por Cmd+K. Se dedupean contra los ítems de nav por `href` (p.ej.
 * "Panel" /dashboard coincide con la sub "Resumen" → aparece una sola vez).
 */
const LEGACY_COMMANDS: LegacyCommandDef[] = [
  {
    // El Copiloto es una acción global del shell (no una sub del nav) — esta entrada lo
    // mantiene en Cmd+K.
    id: "sudamerica-ia",
    label: "Copiloto Admin",
    description: "Copiloto administrativo con IA",
    icon: <IconSparkles size={15} />,
    href: "/sudamerica-ia",
    color: "grape",
  },
  {
    id: "dashboard",
    label: "Panel",
    description: "Resumen ejecutivo del negocio",
    icon: <IconHome size={15} />,
    href: "/dashboard",
    color: "indigo",
  },
  {
    id: "pipeline",
    label: "Embudo",
    description: "Embudo de prospectos activos",
    icon: <IconLayoutKanban size={15} />,
    href: "/pipeline",
    color: "blue",
  },
  {
    id: "ia",
    label: "Rendimiento IA",
    description: "Métricas de inteligencia artificial",
    icon: <IconBrain size={15} />,
    href: "/ia",
    color: "violet",
  },
  {
    id: "roi",
    label: "Calculadora ROI",
    description: "Calculadora de retorno de inversión",
    icon: <IconCalculator size={15} />,
    href: "/roi",
    color: "yellow",
  },
];

export function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen } = useUiStore();
  const hasHydrated = useUiStore((s) => s.hasHydrated);
  const persistedFavoriteNavIds = useUiStore((s) => s.favoriteNavIds);
  // Antes de hidratar (SSR skipHydration), tratar favoritos como vacío — mismo guard que Sidebar.
  const favoriteNavIds = hasHydrated ? persistedFavoriteNavIds : [];
  const { toggleColorScheme } = useMantineColorScheme();
  // SSR-safe (ver hooks/useSsrColorScheme): evita el hydration mismatch del
  // comando de tema y el glass cuando hay un scheme persistido distinto al default.
  const colorScheme = useSsrColorScheme();
  const rubro = useRubroLabels();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const router = useRouter();
  const withBase = useWithBase();
  const inputRef = useRef<HTMLInputElement>(null);

  function navigate(href: string) {
    // Base "" en la app real; "/showroom/<rubro>" dentro de la vitrina.
    router.push(withBase(href));
    setCommandPaletteOpen(false);
  }

  // Ítems de nav visibles para el rubro activo (respeta gating por capacidad y label por rubro).
  // Fuente única: nav canónico. Cada href es único ⇒ sin dedup por href; se excluye
  // "inicio-accesos" (ese ítem ES abrir esta paleta).
  const navItems = navItemsFlatCanonico(rubro).filter(({ sub }) => sub.id !== "inicio-accesos");
  const navHrefs = new Set(navItems.map(({ sub }) => sub.href));

  const navCommands: CommandItem[] = navItems.map(({ sub, label, catLabel }) => ({
    id: `nav-${sub.id}`,
    label,
    description: catLabel,
    icon: <sub.icon size={15} />,
    color: "gray",
    execute: () => navigate(sub.href),
  }));

  const legacyCommands: CommandItem[] = LEGACY_COMMANDS.filter(
    (legacy) => !navHrefs.has(legacy.href),
  ).map((legacy) => ({
    id: legacy.id,
    label: legacy.label,
    description: legacy.description,
    icon: legacy.icon,
    color: legacy.color,
    execute: () => navigate(legacy.href),
  }));

  const themeActionCommand: CommandItem = {
    id: "action-toggle-theme",
    label: colorScheme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro",
    description: "Alternar el tema visual de la aplicación",
    icon: colorScheme === "dark" ? <IconSun size={15} /> : <IconMoon size={15} />,
    color: "gray",
    execute: () => {
      toggleColorScheme();
      setCommandPaletteOpen(false);
    },
  };

  const favoritesActionCommand: CommandItem = showFavoritesOnly
    ? {
        id: "action-show-all",
        label: "Ver todos los comandos",
        description: "Salir del filtro de favoritos",
        icon: <IconLayoutGrid size={15} />,
        color: "gray",
        execute: () => setShowFavoritesOnly(false),
      }
    : {
        id: "action-show-favorites",
        label: "Ir a Favoritos",
        description: "Mostrar solo tus vistas fijadas",
        icon: <IconStar size={15} />,
        color: "yellow",
        execute: () => setShowFavoritesOnly(true),
      };

  const navAndLegacyCommands = showFavoritesOnly
    ? navCommands.filter(({ id }) => favoriteNavIds.includes(id.replace(/^nav-/, "")))
    : [...navCommands, ...legacyCommands];

  const allCommands: CommandItem[] = [
    themeActionCommand,
    favoritesActionCommand,
    ...navAndLegacyCommands,
  ];

  const filtered = query.trim()
    ? allCommands.filter((c) => {
        const q = query.toLowerCase();
        return c.label.toLowerCase().includes(q) || c.description.toLowerCase().includes(q);
      })
    : allCommands;

  // Reset state on open + focus input
  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery("");
      setSelectedIndex(0);
      setShowFavoritesOnly(false);
      // Defer focus to after modal animation
      const timer = setTimeout(() => inputRef.current?.focus(), 60);
      return () => clearTimeout(timer);
    }
  }, [commandPaletteOpen]);

  // Global Cmd/Ctrl+K shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setCommandPaletteOpen]);

  function handleKeyDown(e: React.KeyboardEvent) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
        break;
      case "Enter": {
        const cmd = filtered[selectedIndex];
        if (cmd) cmd.execute();
        break;
      }
      case "Escape":
        setCommandPaletteOpen(false);
        break;
    }
  }

  const glass = colorScheme === "dark" ? GLASS.dark : GLASS.light;

  return (
    <Modal
      opened={commandPaletteOpen}
      onClose={() => setCommandPaletteOpen(false)}
      withCloseButton={false}
      padding={0}
      radius="lg"
      size="lg"
      styles={{
        content: {
          overflow: "hidden",
          background: glass.background,
          backdropFilter: glass.backdropFilter,
          WebkitBackdropFilter: glass.backdropFilter,
        },
        body: { padding: 0 },
      }}
      aria-label="Paleta de comandos"
    >
      <div onKeyDown={handleKeyDown}>
        <TextInput
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.currentTarget.value);
            setSelectedIndex(0);
          }}
          placeholder="Buscar páginas y acciones..."
          leftSection={<IconSearch size={16} />}
          rightSection={
            <Kbd size="xs" style={{ fontSize: 11 }}>
              Esc
            </Kbd>
          }
          size="lg"
          radius={0}
          styles={{
            input: {
              border: "none",
              borderBottom: "1px solid var(--mantine-color-default-border)",
              borderRadius: 0,
              fontSize: 15,
              background: "transparent",
            },
            section: { pointerEvents: "none" },
          }}
          aria-label="Buscar comandos"
          aria-autocomplete="list"
          aria-controls="command-list"
        />

        <Stack
          id="command-list"
          gap={2}
          p="sm"
          aria-label="Resultados de búsqueda"
          style={{ maxHeight: 360, overflowY: "auto" }}
        >
          {filtered.length === 0 ? (
            <Text c="dimmed" fz={13} ta="center" py="md">
              Sin resultados para &ldquo;{query}&rdquo;
            </Text>
          ) : (
            filtered.map((cmd, idx) => (
              <UnstyledButton
                key={cmd.id}
                onClick={() => cmd.execute()}
                onMouseEnter={() => setSelectedIndex(idx)}
                aria-label={`${cmd.label} — ${cmd.description}`}
                aria-current={idx === selectedIndex ? "true" : undefined}
                style={{
                  borderRadius: 8,
                  padding: "8px 12px",
                  backgroundColor:
                    idx === selectedIndex ? "var(--mantine-color-appleBlue-light)" : "transparent",
                  transition: "background-color 100ms ease",
                }}
              >
                <Group gap="sm">
                  <ThemeIcon
                    color={cmd.color}
                    variant="light"
                    size="sm"
                    radius="sm"
                    aria-hidden="true"
                  >
                    {cmd.icon}
                  </ThemeIcon>
                  <Stack gap={0}>
                    <Text size="sm" fw={500}>
                      {cmd.label}
                    </Text>
                    <Text fz={11} c="dimmed">
                      {cmd.description}
                    </Text>
                  </Stack>
                </Group>
              </UnstyledButton>
            ))
          )}
        </Stack>

        <Group
          justify="flex-end"
          px="sm"
          py="xs"
          style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}
        >
          <Group gap="xs">
            <Kbd size="xs">↑</Kbd>
            <Kbd size="xs">↓</Kbd>
            <Text fz={11} c="dimmed">
              navegar
            </Text>
          </Group>
          <Group gap="xs">
            <Kbd size="xs">↵</Kbd>
            <Text fz={11} c="dimmed">
              ir
            </Text>
          </Group>
        </Group>
      </div>
    </Modal>
  );
}
