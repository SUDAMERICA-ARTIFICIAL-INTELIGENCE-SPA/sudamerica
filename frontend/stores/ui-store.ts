import { create } from "zustand";
import { persist } from "zustand/middleware";

type ColorScheme = "light" | "dark";

interface UiStore {
  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // Theme
  colorScheme: ColorScheme;
  toggleColorScheme: () => void;

  // Global sucursal filter
  activeSucursalId: string | null;
  setActiveSucursalId: (id: string | null) => void;

  // Active filters (global — shared across pages)
  activeAsessorId: string | null;
  setActiveAsesorId: (id: string | null) => void;

  activePeriod: "day" | "week" | "month";
  setActivePeriod: (period: "day" | "week" | "month") => void;

  // Command palette
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // Favoritos de navegación (sub.id del nav canónico — ver lib/nav-canonico.ts; la
  // migración de ids legacy→canónico vive en Sidebar + remapFavoritosCanonico)
  favoriteNavIds: string[];
  toggleFavoriteNavId: (id: string) => void;
  setFavoriteNavIds: (ids: string[]) => void;

  // Colapso de grupos de navegación (key de NavGroupDef -> colapsado?)
  collapsedNavGroups: Record<string, boolean>;
  toggleNavGroupCollapsed: (key: string) => void;

  // Hidratación del persist middleware (SSR): true recién tras rehydrate() en cliente.
  // No se persiste — ver partialize. Ver stores/ui-store.ts skipHydration + Sidebar mount effect.
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      colorScheme: "light",
      toggleColorScheme: () =>
        set((s) => ({ colorScheme: s.colorScheme === "light" ? "dark" : "light" })),

      activeSucursalId: null,
      setActiveSucursalId: (id) => set({ activeSucursalId: id }),

      activeAsessorId: null,
      setActiveAsesorId: (id) => set({ activeAsessorId: id }),

      activePeriod: "month",
      setActivePeriod: (period) => set({ activePeriod: period }),

      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

      favoriteNavIds: [],
      toggleFavoriteNavId: (id) =>
        set((s) => ({
          favoriteNavIds: s.favoriteNavIds.includes(id)
            ? s.favoriteNavIds.filter((existingId) => existingId !== id)
            : [...s.favoriteNavIds, id],
        })),
      setFavoriteNavIds: (ids) => set({ favoriteNavIds: ids }),

      collapsedNavGroups: {},
      toggleNavGroupCollapsed: (key) =>
        set((s) => ({
          collapsedNavGroups: { ...s.collapsedNavGroups, [key]: !s.collapsedNavGroups[key] },
        })),

      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "sudamerica-ui",
      // SSR: no rehidratar automáticamente al crear el store (evita hydration mismatch
      // en favoriteNavIds/collapsedNavGroups). El cliente dispara rehydrate() manualmente
      // (ver Sidebar.tsx) y hasHydrated pasa a true recién cuando termina.
      skipHydration: true,
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        colorScheme: state.colorScheme,
        activeSucursalId: state.activeSucursalId,
        activePeriod: state.activePeriod,
        favoriteNavIds: state.favoriteNavIds,
        collapsedNavGroups: state.collapsedNavGroups,
      }),
      onRehydrateStorage: () => (_state, error) => {
        useUiStore.getState().setHasHydrated(true);
        if (error) {
          console.error("ui-store rehydrate", error);
        }
      },
    },
  ),
);
