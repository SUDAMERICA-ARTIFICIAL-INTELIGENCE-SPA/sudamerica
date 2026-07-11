"use client";

import { AlertCenter } from "@/components/layout/AlertCenter";
import { SucursalSelector } from "@/components/layout/SucursalSelector";
import { DEV_RUBRO_OVERRIDE_KEY, useRubroLabels } from "@/hooks/useRubroLabels";
import { useSmartAlerts } from "@/hooks/useSmartAlerts";
import { useSsrColorScheme } from "@/hooks/useSsrColorScheme";
import { useAuth } from "@/lib/auth";
import { USER_ROLE_COLORS, USER_ROLE_LABELS, type UserRole } from "@/lib/enums";
import { type VisibleNavItem, getVisibleNavGroups, getVisibleNavItemsFlat } from "@/lib/nav-config";
import {
  NAV_P2_ENABLED,
  esSubActivaP2,
  getVisibleNavGroupsP2,
  getVisibleNavItemsFlatP2,
  remapLegacyFavoriteIds,
} from "@/lib/nav-p2";
import { RUBRO_DEFAULT, RUBRO_OPTIONS } from "@/lib/rubros";
import { HEADER_HEIGHT, MOTION, RADIUS } from "@/lib/theme-tokens";
import { useUiStore } from "@/stores/ui-store";
import {
  ActionIcon,
  AppShell,
  Avatar,
  Badge,
  Box,
  Collapse,
  Group,
  Indicator,
  Menu,
  NavLink,
  Select,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
  useMantineColorScheme,
} from "@mantine/core";
import {
  IconBell,
  IconChevronDown,
  IconChevronRight,
  IconLogout,
  IconMoon,
  IconSearch,
  IconSparkles,
  IconStar,
  IconStarFilled,
  IconSun,
  IconUser,
} from "@tabler/icons-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const HAIRLINE = "1px solid var(--mantine-color-default-border)";

/**
 * Paleta de marca del logo (coral · amber · ocean · teal), espejo de las vars
 * `--sudamerica-*` de `globals.css`. El sidebar de prod pintaba un punto con glow por
 * sección; allí eran 5 secciones fijas, aquí el nav P2 tiene N grupos → se cicla
 * la paleta por índice de grupo. Ningún hex inventado.
 */
const SECTION_COLORS = ["#FF4757", "#FFB800", "#0099FF", "#00B894"] as const;

/**
 * Tipografía de encabezado de categoría. El sidebar de prod usaba 10px; se sube a
 * 14px porque el nav P2 tiene 11 categorías y a 12px las subcategorías (15px)
 * pesaban más que su propia categoría — jerarquía invertida.
 */
const SECTION_LABEL = {
  fontSize: "14px",
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
} as const;

/** Label de subcategoría — un punto sobre el `sm` (14px) por defecto de Mantine. */
const NAV_LINK_STYLES = { label: { fontSize: "15px" } } as const;

function getRoleColor(role: UserRole): string {
  return USER_ROLE_COLORS[role] ?? "gray";
}

function getRoleLabel(role: UserRole): string {
  return USER_ROLE_LABELS[role] ?? role;
}

function getInitials(nombre: string): string {
  return nombre
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

interface NavItemRowProps {
  visible: VisibleNavItem;
  isActive: boolean;
  isFavorite: boolean;
  onToggleFavorite: (id: string) => void;
}

/** Fila de ítem: NavLink + botón de fijar, como hermanos (nunca anidar botón dentro de <a>). */
function NavItemRow({ visible, isActive, isFavorite, onToggleFavorite }: NavItemRowProps) {
  const { item, label } = visible;
  return (
    <Group gap={2} wrap="nowrap" align="center" className="sidebar-nav-row">
      <NavLink
        component={Link}
        href={item.href}
        label={label}
        leftSection={<item.icon size={18} />}
        active={isActive}
        color="appleBlue"
        variant={isActive ? "filled" : "subtle"}
        styles={NAV_LINK_STYLES}
        style={{ borderRadius: RADIUS.sm, flex: 1, minWidth: 0 }}
        aria-label={`Navegar a ${label}`}
        aria-current={isActive ? "page" : undefined}
      />
      <ActionIcon
        variant="subtle"
        color={isFavorite ? "yellow" : "gray"}
        size="sm"
        className={`sidebar-fav-star${isFavorite ? " sidebar-fav-star--active" : ""}`}
        aria-label={isFavorite ? `Quitar ${label} de favoritos` : `Añadir ${label} a favoritos`}
        onClick={() => onToggleFavorite(item.id)}
      >
        {isFavorite ? <IconStarFilled size={14} /> : <IconStar size={14} />}
      </ActionIcon>
    </Group>
  );
}

interface NavGroupHeaderProps {
  groupKey: string;
  label: string;
  color: string;
  collapsed: boolean;
  onToggle: () => void;
}

/** Encabezado de grupo colapsable — punto con glow por sección (sidebar de prod). */
function NavGroupHeader({ groupKey, label, color, collapsed, onToggle }: NavGroupHeaderProps) {
  return (
    <UnstyledButton
      onClick={onToggle}
      aria-expanded={!collapsed}
      aria-controls={`nav-group-${groupKey}`}
      aria-label={`${collapsed ? "Expandir" : "Colapsar"} sección ${label}`}
      style={{ width: "100%", borderRadius: 6 }}
    >
      <Group gap={6} align="center" px="sm" pt="md" pb={8} wrap="nowrap">
        <IconChevronRight
          size={12}
          style={{
            color: "var(--mantine-color-dimmed)",
            transform: collapsed ? "rotate(0deg)" : "rotate(90deg)",
            transition: `transform ${MOTION.durationFast} ${MOTION.easing}`,
            flexShrink: 0,
          }}
        />
        <Box
          className="sudamerica-section-dot"
          aria-hidden="true"
          style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            backgroundColor: color,
            boxShadow: `0 0 8px ${color}`,
            flexShrink: 0,
          }}
        />
        <Text c="dimmed" style={SECTION_LABEL}>
          {label}
        </Text>
      </Group>
    </UnstyledButton>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const favoriteNavIds = useUiStore((s) => s.favoriteNavIds);
  const toggleFavoriteNavId = useUiStore((s) => s.toggleFavoriteNavId);
  const setFavoriteNavIds = useUiStore((s) => s.setFavoriteNavIds);
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const collapsedNavGroups = useUiStore((s) => s.collapsedNavGroups);
  const toggleNavGroupCollapsed = useUiStore((s) => s.toggleNavGroupCollapsed);
  const hasHydrated = useUiStore((s) => s.hasHydrated);
  const rubro = useRubroLabels();
  const { toggleColorScheme } = useMantineColorScheme();
  // SSR-safe (ver hooks/useSsrColorScheme): evita el hydration mismatch del
  // icono/label del toggle cuando hay un scheme persistido distinto al default.
  const colorScheme = useSsrColorScheme();
  const [alertCenterOpen, setAlertCenterOpen] = useState(false);
  const { data: alertData } = useSmartAlerts({ leido: false, page_size: 1 });
  const unreadCount = alertData?.meta.total ?? 0;

  // Persist middleware usa skipHydration: true (evita hydration mismatch SSR en
  // favoriteNavIds/collapsedNavGroups) — rehidratar acá, una vez, tras el mount en cliente.
  useEffect(() => {
    useUiStore.persist.rehydrate();
  }, []);

  // Migración one-shot de favoritos legacy → subIds P2 (decisión Fase 0: LEGACY_FAV_ID_MAP).
  // Solo en modo P2 y tras hidratar; idempotente (si nada cambia, no escribe).
  useEffect(() => {
    if (!NAV_P2_ENABLED || !hasHydrated) return;
    const remapped = remapLegacyFavoriteIds(favoriteNavIds);
    if (JSON.stringify(remapped) !== JSON.stringify(favoriteNavIds)) {
      setFavoriteNavIds(remapped);
    }
  }, [hasHydrated, favoriteNavIds, setFavoriteNavIds]);

  if (!sidebarOpen) return null;

  const initials = user ? getInitials(user.nombre) : "?";
  const brandTagline = rubro.key === RUBRO_DEFAULT ? "Gastronomia IA" : "Asistente IA";
  // Fuente del nav: árbol P2 por rubro→capacidades tras NEXT_PUBLIC_NAV_P2; nav-config si OFF.
  // Ambas fuentes producen la misma forma estructural — el render de abajo no cambia.
  const visibleGroups: { key: string; label: string; items: VisibleNavItem[] }[] = NAV_P2_ENABLED
    ? getVisibleNavGroupsP2(rubro)
    : getVisibleNavGroups(rubro);
  const flatItems: (VisibleNavItem & { groupLabel: string })[] = NAV_P2_ENABLED
    ? getVisibleNavItemsFlatP2(rubro)
    : getVisibleNavItemsFlat(rubro);
  // Antes de hidratar, favoriteNavIds es el default ([]) — no mostrar el bloque
  // "Favoritos" hasta confirmar que se leyó el valor persistido real (evita parpadeo/mismatch).
  const favoriteItems = hasHydrated
    ? flatItems.filter(({ item }) => favoriteNavIds.includes(item.id))
    : [];

  function isActiveHref(href: string): boolean {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  // En modo P2 el active-state aplica la regla de sub canónica (rutas compartidas).
  function isRowActive(item: { id: string; href: string }): boolean {
    return NAV_P2_ENABLED ? esSubActivaP2(pathname, item) : isActiveHref(item.href);
  }

  return (
    <>
      <AlertCenter opened={alertCenterOpen} onClose={() => setAlertCenterOpen(false)} />
      <AppShell.Navbar
        p={0}
        style={{
          borderRight: HAIRLINE,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header zone — alineado en altura con el TopBar (HEADER_HEIGHT), hairline inferior continuo */}
        <Box style={{ borderBottom: HAIRLINE }}>
          <Group h={HEADER_HEIGHT} gap={10} wrap="nowrap" align="center" px="sm">
            <Image
              src="/logo.png"
              alt="Sudamérica AI"
              title="Sudamérica AI"
              width={36}
              height={36}
              priority
              className="sudamerica-logo-glow"
              style={{ borderRadius: 8 }}
            />
            <Stack gap={0} style={{ minWidth: 0 }}>
              <Text
                fw={800}
                fz={18}
                truncate="end"
                className="sudamerica-gradient-text"
                style={{ letterSpacing: "-0.5px", lineHeight: 1 }}
              >
                Sudamérica AI
              </Text>
              <Text
                fz={9}
                fw={500}
                c="dimmed"
                tt="uppercase"
                style={{ letterSpacing: "0.8px", marginTop: 2 }}
              >
                {brandTagline}
              </Text>
            </Stack>
          </Group>

          {/* Acciones globales del shell. Vivían en el TopBar de Apple v2; al no
              haber barra superior vuelven aquí, como en el sidebar de prod. */}
          <Group gap={4} px="sm" pb="xs" justify="center">
            {/* La IA es transversal en P2 (sin pilar "Inteligencia"): el Copiloto es
                una acción global del shell, no un ítem del nav (decisión Fase 0). */}
            {NAV_P2_ENABLED && (
              <Tooltip label="Copiloto Admin" position="bottom" withArrow>
                <ActionIcon
                  component={Link}
                  href="/sudamerica-ia"
                  variant="subtle"
                  color="gray"
                  size="md"
                  radius="md"
                  aria-label="Abrir Copiloto Admin"
                >
                  <IconSparkles size={16} />
                </ActionIcon>
              </Tooltip>
            )}

            <Tooltip label="Buscar (Ctrl+K)" position="bottom" withArrow>
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                aria-label="Buscar — Ctrl+K"
                onClick={() => setCommandPaletteOpen(true)}
              >
                <IconSearch size={16} />
              </ActionIcon>
            </Tooltip>

            <Tooltip
              label={colorScheme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
              position="bottom"
              withArrow
            >
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                aria-label={
                  colorScheme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"
                }
                onClick={() => toggleColorScheme()}
              >
                {colorScheme === "dark" ? <IconSun size={16} /> : <IconMoon size={16} />}
              </ActionIcon>
            </Tooltip>

            <Tooltip label="Notificaciones" position="bottom" withArrow>
              <Indicator
                label={unreadCount > 0 ? String(unreadCount) : undefined}
                size={14}
                color="red"
                disabled={unreadCount === 0}
                offset={4}
              >
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  size="md"
                  radius="md"
                  aria-label={
                    unreadCount > 0
                      ? `${unreadCount} notificaciones sin leer`
                      : "Sin notificaciones nuevas"
                  }
                  onClick={() => setAlertCenterOpen(true)}
                >
                  <IconBell size={16} />
                </ActionIcon>
              </Indicator>
            </Tooltip>
          </Group>

          {/* Divider de gradiente bajo la marca (sidebar de prod) */}
          <Box
            mx="sm"
            mb="xs"
            aria-hidden="true"
            style={{
              height: 1,
              background: "linear-gradient(90deg, #FF4757, #FFB800, #0099FF, #00B894)",
              opacity: 0.2,
              borderRadius: 1,
            }}
          />

          {/* Rubro switcher — Select real SOLO en dev (NEXT_PUBLIC_MOCK_AUTH, env de build:
              en prod la condición es `false` literal y la rama muere en el bundle);
              en prod queda el control de solo lectura de siempre. */}
          <Stack gap={8} px="sm" pb={8}>
            {process.env.NEXT_PUBLIC_MOCK_AUTH === "true" ? (
              <Select
                size="xs"
                radius={RADIUS.md}
                value={rubro.key}
                data={RUBRO_OPTIONS.map((opcion) => ({
                  value: opcion.value,
                  label: `${opcion.emoji} ${opcion.label}`,
                }))}
                onChange={(value) => {
                  if (!value) return;
                  window.localStorage.setItem(DEV_RUBRO_OVERRIDE_KEY, value);
                  window.location.reload();
                }}
                searchable
                aria-label="Cambiar rubro (solo desarrollo)"
              />
            ) : (
              <Group
                gap={8}
                wrap="nowrap"
                px={8}
                py={6}
                aria-label={`Rubro activo: ${rubro.nombre}`}
                style={{
                  border: HAIRLINE,
                  borderRadius: RADIUS.md,
                  cursor: "default",
                }}
              >
                <Text component="span" fz={14} aria-hidden="true" style={{ lineHeight: 1 }}>
                  {rubro.emoji}
                </Text>
                <Text fz={13} fw={600} truncate="end" style={{ flex: 1, minWidth: 0 }}>
                  {rubro.nombre}
                </Text>
                <IconChevronDown
                  size={14}
                  aria-hidden="true"
                  style={{ opacity: 0.45, flexShrink: 0 }}
                />
              </Group>
            )}
          </Stack>

          {/* Global sucursal filter (only shows when >1 sucursal) — mismo componente/funcionalidad */}
          <SucursalSelector />
        </Box>

        {/* Main nav — taxonomía neutra por grupos, agnóstica de rubro (100+ rubros) */}
        {/* `minHeight: 0` es obligatorio: el min-height por defecto de un flex item es
            `auto`, así que sin esto el Stack crece con su contenido, `overflowY` nunca
            se dispara y el bloque de usuario queda empujado fuera del viewport. */}
        <Stack gap={2} py={4} style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
          {favoriteItems.length > 0 && (
            <Box>
              <Group gap={6} align="center" px="sm" pt="md" pb={8}>
                <IconStarFilled size={12} color="var(--mantine-color-yellow-6)" />
                <Text c="dimmed" style={SECTION_LABEL}>
                  Favoritos
                </Text>
              </Group>
              {favoriteItems.map((visible) => (
                <NavItemRow
                  key={`fav-${visible.item.id}`}
                  visible={visible}
                  isActive={isRowActive(visible.item)}
                  isFavorite
                  onToggleFavorite={toggleFavoriteNavId}
                />
              ))}
            </Box>
          )}

          {visibleGroups.map((group, groupIndex) => {
            // Default false hasta hidratar — todos los grupos abiertos en el primer render
            // de cliente, igual que en SSR (evita hydration mismatch).
            const collapsed = hasHydrated ? (collapsedNavGroups[group.key] ?? false) : false;
            return (
              <Box key={group.key}>
                <NavGroupHeader
                  groupKey={group.key}
                  label={group.label}
                  color={SECTION_COLORS[groupIndex % SECTION_COLORS.length] as string}
                  collapsed={collapsed}
                  onToggle={() => toggleNavGroupCollapsed(group.key)}
                />
                <Collapse in={!collapsed} id={`nav-group-${group.key}`}>
                  {group.items.map((visible) =>
                    // "Accesos rápidos" (P2) abre Cmd+K, no navega (crosswalk §0.1).
                    NAV_P2_ENABLED && visible.item.id === "accesos-rapidos" ? (
                      <NavLink
                        key={visible.item.id}
                        component="button"
                        label={visible.label}
                        leftSection={<visible.item.icon size={18} />}
                        onClick={() => setCommandPaletteOpen(true)}
                        styles={NAV_LINK_STYLES}
                        style={{ borderRadius: RADIUS.sm, width: "100%" }}
                        aria-label={`Abrir ${visible.label} (Ctrl+K)`}
                      />
                    ) : (
                      <NavItemRow
                        key={visible.item.id}
                        visible={visible}
                        isActive={isRowActive(visible.item)}
                        isFavorite={favoriteNavIds.includes(visible.item.id)}
                        onToggleFavorite={toggleFavoriteNavId}
                      />
                    ),
                  )}
                </Collapse>
              </Box>
            );
          })}
        </Stack>

        {/* User section — hairline superior + Menu con las acciones existentes (perfil/logout) */}
        {user && (
          <Box px="xs" py={8} style={{ borderTop: HAIRLINE }}>
            <Menu width={200} shadow="md" position="right-end" offset={8}>
              <Menu.Target>
                <UnstyledButton
                  aria-label={`Menu de cuenta de ${user.nombre}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    width: "100%",
                    padding: 6,
                    borderRadius: RADIUS.md,
                    minWidth: 0,
                  }}
                >
                  <Avatar
                    size={32}
                    radius="xl"
                    color="indigo"
                    aria-hidden="true"
                    style={{
                      boxShadow:
                        "0 0 0 2px var(--mantine-color-body), 0 0 0 3.5px var(--mantine-color-indigo-5)",
                    }}
                  >
                    {initials}
                  </Avatar>
                  <Stack gap={0} style={{ minWidth: 0, flex: 1 }}>
                    <Text fz={13} fw={600} truncate="end">
                      {user.nombre}
                    </Text>
                    <Badge
                      size="xs"
                      variant="light"
                      color={getRoleColor(user.role)}
                      radius="sm"
                      style={{ alignSelf: "flex-start" }}
                    >
                      {getRoleLabel(user.role)}
                    </Badge>
                  </Stack>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item
                  component={Link}
                  href="/perfil"
                  leftSection={<IconUser size={14} />}
                  aria-label="Ver mi perfil"
                >
                  Mi perfil
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item
                  color="red"
                  leftSection={<IconLogout size={14} />}
                  onClick={logout}
                  aria-label="Cerrar sesion"
                >
                  Cerrar sesión
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Box>
        )}
      </AppShell.Navbar>
    </>
  );
}
