// Golden tests del árbol P2 gateado por capacidad (oracle concreto, no "coherente").
// El golden de restaurante es BYTE-IDÉNTICO congelado: cambiarlo requiere decisión explícita.
import { describe, expect, it } from "vitest";
import { CAPACIDADES } from "./capacidades";
import { NAV_TREE_P2, construirSidebar, construirSidebarParaRubro } from "./nav-tree";
import { RUBROS } from "./rubros";

/** Proyección estable para goldens: { categoriaId: [subIds...] } en orden del árbol. */
function proyectar(tree: ReturnType<typeof construirSidebar>): Record<string, string[]> {
  return Object.fromEntries(tree.map((c) => [c.id, c.subs.map((s) => s.id)]));
}

describe("NAV_TREE_P2 — estructura", () => {
  it("tiene las 11 categorías P2 en orden", () => {
    expect(NAV_TREE_P2.map((c) => c.id)).toEqual([
      "inicio",
      "contactos",
      "conversaciones",
      "catalogo",
      "agenda",
      "pedidos",
      "dinero",
      "inventario",
      "documentos",
      "contenido",
      "cuenta",
    ]);
    expect(NAV_TREE_P2.map((c) => c.num)).toEqual([
      "01",
      "02",
      "03",
      "04",
      "05",
      "06",
      "07",
      "08",
      "09",
      "10",
      "11",
    ]);
  });

  it("ids de sub únicos y caps válidas", () => {
    const ids = NAV_TREE_P2.flatMap((c) => c.subs.map((s) => s.id));
    expect(new Set(ids).size).toBe(ids.length);
    for (const c of NAV_TREE_P2) {
      for (const s of c.subs) {
        if (s.cap) expect(CAPACIDADES).toContain(s.cap);
      }
    }
  });

  it("toda categoría fija tiene ≥1 sub sin cap (siempre visible)", () => {
    for (const c of NAV_TREE_P2.filter((c) => c.fija)) {
      expect(c.subs.some((s) => !s.cap)).toBe(true);
    }
  });

  it("con todas las capacidades activas no se pierde ningún nodo", () => {
    const full = construirSidebar(CAPACIDADES);
    expect(proyectar(full)).toEqual(proyectar([...NAV_TREE_P2]));
  });

  it("sin capacidades solo quedan las categorías fijas con sus subs base", () => {
    const vacio = construirSidebar([]);
    expect(vacio.map((c) => c.id)).toEqual([
      "inicio",
      "contactos",
      "conversaciones",
      "dinero",
      "documentos",
      "contenido",
      "cuenta",
    ]);
  });
});

describe("goldens congelados por rubro", () => {
  it("restaurante — byte-idéntico (ancla)", () => {
    expect(proyectar(construirSidebarParaRubro(RUBROS.restaurante))).toEqual({
      inicio: ["resumen", "tareas-del-dia", "notificaciones", "accesos-rapidos"],
      contactos: ["directorio", "segmentos", "ficha-de-contacto"],
      conversaciones: ["bandeja-de-entrada", "canales", "respuestas-ia", "plantillas"],
      catalogo: ["productos", "servicios", "variantes-precios"],
      agenda: ["calendario", "reservas-citas", "disponibilidad", "recursos-profesionales"],
      pedidos: ["ordenes", "comandas", "mesas-salon", "entregas", "devoluciones"],
      dinero: ["ingresos", "cobros-pagos", "reportes-financieros"],
      documentos: ["archivos"],
      contenido: ["biblioteca-medios", "catalogo-publico"],
      cuenta: [
        "perfil-negocio",
        "equipo-permisos",
        "capacidades-modulos",
        "integraciones",
        "facturacion-servicio",
      ],
    });
  });

  it("ferreteria — ERP retail (cotizador, inventario, compras, facturación; sin agenda)", () => {
    expect(proyectar(construirSidebarParaRubro(RUBROS.ferreteria))).toEqual({
      inicio: ["resumen", "tareas-del-dia", "notificaciones", "accesos-rapidos"],
      contactos: ["directorio", "segmentos", "ficha-de-contacto"],
      conversaciones: ["bandeja-de-entrada", "canales", "respuestas-ia", "plantillas"],
      catalogo: ["productos", "servicios", "variantes-precios", "cotizaciones"],
      pedidos: ["ordenes", "entregas", "devoluciones"],
      dinero: ["ingresos", "cobros-pagos", "facturacion", "reportes-financieros"],
      inventario: ["existencias", "movimientos", "bodegas", "ordenes-compra"],
      documentos: ["archivos", "documentos-tributarios"],
      contenido: ["biblioteca-medios", "catalogo-publico"],
      cuenta: [
        "perfil-negocio",
        "equipo-permisos",
        "capacidades-modulos",
        "integraciones",
        "facturacion-servicio",
      ],
    });
  });

  it("clinica_dental — salud electiva (expedientes, consentimientos, campañas; sin pedidos)", () => {
    expect(proyectar(construirSidebarParaRubro(RUBROS.clinica_dental))).toEqual({
      inicio: ["resumen", "tareas-del-dia", "notificaciones", "accesos-rapidos"],
      contactos: ["directorio", "segmentos", "ficha-de-contacto", "expedientes", "consentimientos"],
      conversaciones: ["bandeja-de-entrada", "canales", "respuestas-ia", "plantillas"],
      catalogo: ["productos", "servicios", "variantes-precios", "cotizaciones"],
      agenda: ["calendario", "reservas-citas", "disponibilidad", "recursos-profesionales"],
      dinero: ["ingresos", "cobros-pagos", "facturacion", "reportes-financieros"],
      documentos: [
        "archivos",
        "consentimientos-firmados",
        "documentos-tributarios",
        "expedientes-casos",
      ],
      contenido: ["campanas", "biblioteca-medios", "catalogo-publico"],
      cuenta: [
        "perfil-negocio",
        "equipo-permisos",
        "capacidades-modulos",
        "integraciones",
        "facturacion-servicio",
      ],
    });
  });

  it("taller_mecanico — ERP servicio (soporte, terreno, inventario+compras, expedientes)", () => {
    expect(proyectar(construirSidebarParaRubro(RUBROS.taller_mecanico))).toEqual({
      inicio: ["resumen", "tareas-del-dia", "notificaciones", "accesos-rapidos"],
      contactos: ["directorio", "segmentos", "ficha-de-contacto", "expedientes"],
      conversaciones: ["bandeja-de-entrada", "canales", "respuestas-ia", "plantillas", "tickets"],
      catalogo: ["productos", "servicios", "variantes-precios", "cotizaciones"],
      agenda: [
        "calendario",
        "reservas-citas",
        "disponibilidad",
        "recursos-profesionales",
        "visitas-terreno",
      ],
      pedidos: ["ordenes", "devoluciones"],
      dinero: ["ingresos", "cobros-pagos", "facturacion", "reportes-financieros"],
      inventario: ["existencias", "movimientos", "bodegas", "ordenes-compra"],
      documentos: ["archivos", "documentos-tributarios", "expedientes-casos"],
      contenido: ["biblioteca-medios", "catalogo-publico"],
      cuenta: [
        "perfil-negocio",
        "equipo-permisos",
        "capacidades-modulos",
        "integraciones",
        "facturacion-servicio",
      ],
    });
  });

  it("gimnasio — recurrencia (suscripciones, cursos, campañas; sin pedidos ni inventario)", () => {
    expect(proyectar(construirSidebarParaRubro(RUBROS.gimnasio))).toEqual({
      inicio: ["resumen", "tareas-del-dia", "notificaciones", "accesos-rapidos"],
      contactos: ["directorio", "segmentos", "ficha-de-contacto"],
      conversaciones: ["bandeja-de-entrada", "canales", "respuestas-ia", "plantillas"],
      catalogo: [
        "productos",
        "servicios",
        "variantes-precios",
        "planes-membresias",
        "cursos-programas",
      ],
      agenda: ["calendario", "reservas-citas", "disponibilidad", "recursos-profesionales"],
      dinero: ["ingresos", "cobros-pagos", "suscripciones-recurrencia", "reportes-financieros"],
      documentos: ["archivos"],
      contenido: ["campanas", "biblioteca-medios", "catalogo-publico"],
      cuenta: [
        "perfil-negocio",
        "equipo-permisos",
        "capacidades-modulos",
        "integraciones",
        "facturacion-servicio",
      ],
    });
  });
});
