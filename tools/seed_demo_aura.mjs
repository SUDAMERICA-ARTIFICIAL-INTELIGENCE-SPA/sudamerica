// Seed demo UNIFICADO para la cuenta `aura-demo` (Aura Cosmética & Belleza, rubro cosmetica_belleza).
//
//   node tools/seed_demo_aura.mjs | ~/.local/micromamba/envs/sud/bin/psql "$DATABASE_URL"
//
// Emite UNA transacción SQL determinista e idempotente que puebla las tablas de la OLA A
// ("solo falta seed") para las 13 páginas reales visibles del rubro. NO es "datos falsos por
// página": simula UN negocio y proyecta el MISMO hecho fuente (un pedido) a varias lentes:
//
//   pedido  ─┬─►  comanda + comanda_items   (dinero/reportes: financiero + operativo)
//            ├─►  ventas (1 fila por línea)  (pedidos/ordenes, dashboard/revenue, top productos)
//            └─►  agregados del lead         (contactos/directorio · vista Clientes)
//
// Determinista: PRNG con semilla fija (mulberry32) — nada de Math.random. Reproducible.
// Relativo a hoy: las fechas se anclan a `new Date()` al generar, así cada corrida re-ancla la
// ventana de 12 meses al presente (los KPIs "de este mes" y "hoy" siempre traen datos).
// Idempotente: empieza borrando los datos demo del tenant (scoped por tenant_id) y reinserta.
// RLS-aware: fija el GUC `app.current_tenant_id` como el backend (el rol local es SUPERUSER y
// bypassa RLS, pero se replica el patrón real).
//
// Lee productos/usuarios/categorías EN VIVO (vía psql) para que las ventas referencien SKUs y
// precios reales de la cuenta. Requiere: PSQL (bin) y DATABASE_URL en el entorno (o defaults).

import { execFileSync } from "node:child_process";

// ─────────────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────────────
const HOME = process.env.HOME;
const PSQL = process.env.PSQL || `${HOME}/.local/micromamba/envs/sud/bin/psql`;
const DB =
  process.env.DATABASE_URL ||
  "postgresql://sudamerica@127.0.0.1:55432/sudamerica_ai";
const TENANT_SLUG = "aura-demo";
const DEMO_EMAIL = "demo@aura.cl";

const N_LEADS = 150; // total contactos CRM
const N_CUSTOMERS = 120; // de esos, cuántos son clientes con historial de compra
const SEED = 20260712; // semilla fija

// ─────────────────────────────────────────────────────────────────────────────
// PRNG determinista (mulberry32) + helpers
// ─────────────────────────────────────────────────────────────────────────────
let _s = SEED >>> 0;
function rnd() {
  _s |= 0;
  _s = (_s + 0x6d2b79f5) | 0;
  let t = Math.imul(_s ^ (_s >>> 15), 1 | _s);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const ri = (lo, hi) => lo + Math.floor(rnd() * (hi - lo + 1)); // entero en [lo,hi]
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const chance = (p) => rnd() < p;
function weightedIndex(weights) {
  const sum = weights.reduce((a, b) => a + b, 0);
  let r = rnd() * sum;
  for (let i = 0; i < weights.length; i++) {
    r -= weights[i];
    if (r <= 0) return i;
  }
  return weights.length - 1;
}
// UUID v4 determinista desde el PRNG (estable entre corridas con la misma semilla).
function uuid() {
  const b = new Array(16).fill(0).map(() => Math.floor(rnd() * 256));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = b.map((x) => x.toString(16).padStart(2, "0"));
  return `${h.slice(0, 4).join("")}-${h.slice(4, 6).join("")}-${h
    .slice(6, 8)
    .join("")}-${h.slice(8, 10).join("")}-${h.slice(10, 16).join("")}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Serialización SQL
// ─────────────────────────────────────────────────────────────────────────────
const S = (v) => (v === null || v === undefined ? "NULL" : `'${String(v).replace(/'/g, "''")}'`);
const N = (v) => (v === null || v === undefined ? "NULL" : String(v));
const B = (v) => (v ? "TRUE" : "FALSE");
const J = (v) => (v === null || v === undefined ? "NULL" : `'${JSON.stringify(v).replace(/'/g, "''")}'::jsonb`);
const TS = (d) => `'${d.toISOString()}'`; // timestamptz ISO
const DATE = (d) => `'${d.toISOString().slice(0, 10)}'`; // date

// ─────────────────────────────────────────────────────────────────────────────
// Fechas relativas a hoy + estacionalidad
// ─────────────────────────────────────────────────────────────────────────────
const NOW = new Date();
const DAY = 86400000;
const periodoOf = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
// Peso comercial por mes calendario (0=Ene..11=Dic): día de la madre (may), fiestas patrias
// (sep), black friday/navidad (nov-dic), san valentín/verano (feb).
const MONTH_W = [0.8, 1.1, 0.9, 0.9, 1.3, 0.9, 1.0, 0.85, 1.15, 0.95, 1.25, 1.4];
// Fecha de pedido: uniforme en los últimos 365 días con muestreo por rechazo según estación
// y una leve tendencia de crecimiento hacia el presente.
function orderDate() {
  for (let tries = 0; tries < 40; tries++) {
    const off = ri(0, 364); // días atrás
    const d = new Date(NOW.getTime() - off * DAY);
    const growth = 0.7 + 0.3 * ((365 - off) / 365); // más reciente ⇒ más probable
    const w = (MONTH_W[d.getMonth()] / 1.4) * growth;
    if (chance(w)) {
      d.setHours(ri(9, 20), ri(0, 59), ri(0, 59), 0);
      return d;
    }
  }
  const d = new Date(NOW.getTime() - ri(0, 60) * DAY);
  d.setHours(ri(9, 20), ri(0, 59), 0, 0);
  return d;
}

// ─────────────────────────────────────────────────────────────────────────────
// Lecturas en vivo (psql → JSON)
// ─────────────────────────────────────────────────────────────────────────────
function qjson(sql) {
  const out = execFileSync(PSQL, [DB, "-tAc", sql], { encoding: "utf8" }).trim();
  return out ? JSON.parse(out) : null;
}
const tenantId = execFileSync(PSQL, [DB, "-tAc", `SELECT id FROM tenants WHERE slug='${TENANT_SLUG}'`], {
  encoding: "utf8",
}).trim();
if (!tenantId) throw new Error(`Tenant ${TENANT_SLUG} no encontrado`);
const productos = qjson(
  `SELECT json_agg(json_build_object('id',id,'nombre',nombre,'precio',precio,'categoria_id',categoria_id,'stock',stock) ORDER BY precio) FROM productos WHERE tenant_id='${tenantId}' AND activo`,
);
const categorias = qjson(
  `SELECT json_agg(json_build_object('id',id,'nombre',nombre)) FROM categorias WHERE tenant_id='${tenantId}'`,
);
const demoUserId = execFileSync(
  PSQL,
  [DB, "-tAc", `SELECT id FROM usuarios WHERE tenant_id='${tenantId}' AND email='${DEMO_EMAIL}'`],
  { encoding: "utf8" },
).trim();
if (!productos?.length) throw new Error("No hay productos para la cuenta demo");
if (!demoUserId) throw new Error(`Usuario demo ${DEMO_EMAIL} no encontrado`);

const catById = Object.fromEntries((categorias || []).map((c) => [c.id, c.nombre]));
// Peso de venta por producto: los más baratos rotan más (weight ∝ precio^-0.6).
const prodW = productos.map((p) => 1 / Math.pow(Number(p.precio), 0.6));

// ─────────────────────────────────────────────────────────────────────────────
// Pools de datos (Chile)
// ─────────────────────────────────────────────────────────────────────────────
const NOMBRES = ["Sofía","Isidora","Emilia","Antonia","Florencia","Josefa","Martina","Catalina","Valentina","Amanda","Fernanda","Constanza","Javiera","Trinidad","Maite","Agustina","Camila","Paula","Daniela","Carolina","Francisca","Rocío","Bárbara","Macarena","Pía","Ignacia","Renata","Colomba","Magdalena","Anaís"];
const APELLIDOS = ["González","Muñoz","Rojas","Díaz","Pérez","Soto","Contreras","Silva","Martínez","Sepúlveda","Morales","Rodríguez","López","Fuentes","Hernández","Torres","Araya","Flores","Espinoza","Valenzuela","Castillo","Tapia","Reyes","Gutiérrez","Castro","Vergara","Álvarez","Vega","Riquelme","Cortés"];
const ASESORAS = [
  { nombre: "Valentina", apellido: "Soto" },
  { nombre: "Josefa", apellido: "Muñoz" },
  { nombre: "Antonia", apellido: "Vera" },
];
const CANALES = ["WHATSAPP", "INSTAGRAM", "WEB", "REFERIDO", "TELEFONO"];
const CANAL_W = [0.42, 0.24, 0.16, 0.12, 0.06];
const METODOS = ["EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA"];
const CANAL_ORIGEN = ["WHATSAPP", "WEB", "PRESENCIAL"];

// ─────────────────────────────────────────────────────────────────────────────
// Sucursales (2) y equipo (Camila ADMIN + 3 asesoras)
// ─────────────────────────────────────────────────────────────────────────────
const suc = [
  { id: uuid(), nombre: "Aura Providencia", slug: "aura-providencia", ciudad: "Santiago", region: "Metropolitana", direccion: "Av. Providencia 2134, Providencia", principal: true },
  { id: uuid(), nombre: "Aura Viña del Mar", slug: "aura-vina", ciudad: "Viña del Mar", region: "Valparaíso", direccion: "Av. San Martín 421, Viña del Mar", principal: false },
];
const asesoras = ASESORAS.map((a, i) => ({
  id: uuid(),
  nombre: a.nombre,
  apellido: a.apellido,
  email: `${a.nombre.toLowerCase()}.${a.apellido.toLowerCase().normalize("NFD").replace(/[^a-z]/g, "")}@aura.cl`,
  sucursal_id: suc[i % suc.length].id,
}));
// Vendedores para asignar ventas/metas: demo (ADMIN) + 3 asesoras.
const vendedores = [{ id: demoUserId, nombre: "Camila", sucursal_id: suc[0].id }, ...asesoras.map((a) => ({ id: a.id, nombre: a.nombre, sucursal_id: a.sucursal_id }))];

// ─────────────────────────────────────────────────────────────────────────────
// Leads (150): 120 clientes con historial + 30 en pipeline
// ─────────────────────────────────────────────────────────────────────────────
const usedNames = new Set();
function fullName() {
  for (let i = 0; i < 50; i++) {
    const n = `${pick(NOMBRES)} ${pick(APELLIDOS)}`;
    if (!usedNames.has(n)) {
      usedNames.add(n);
      return n;
    }
  }
  return `${pick(NOMBRES)} ${pick(APELLIDOS)} ${ri(2, 99)}`;
}
const leads = [];
for (let i = 0; i < N_LEADS; i++) {
  const nombre = fullName();
  const v = pick(vendedores);
  const canal = CANALES[weightedIndex(CANAL_W)];
  leads.push({
    id: uuid(),
    nombre,
    email: `${nombre.toLowerCase().normalize("NFD").replace(/[^a-z ]/g, "").replace(/ /g, ".")}@gmail.com`,
    telefono: `+569${ri(30000000, 89999999)}`,
    canal,
    asignado_a: v.id,
    sucursal_id: v.sucursal_id,
    isCustomer: i < N_CUSTOMERS,
    // agregados (se completan al generar pedidos)
    orders: [],
  });
}
const customers = leads.filter((l) => l.isCustomer);

// ─────────────────────────────────────────────────────────────────────────────
// Pedidos → comandas + comanda_items + ventas.  El hecho fuente.
// ─────────────────────────────────────────────────────────────────────────────
// Cada cliente recibe un nº de pedidos con cola larga (pocas clientas VIP concentran compra).
function orderCountFor() {
  const r = rnd();
  if (r < 0.55) return ri(1, 2);
  if (r < 0.82) return ri(3, 5);
  if (r < 0.95) return ri(6, 10);
  return ri(12, 20);
}
const comandas = [];
const comandaItems = [];
const ventas = [];
for (const c of customers) {
  const nOrders = orderCountFor();
  for (let o = 0; o < nOrders; o++) {
    const created = orderDate();
    const ageDays = (NOW - created) / DAY;
    // estado del pedido: recientes pueden estar en curso; ~7% cancelado; resto entregado.
    let estado;
    if (ageDays < 2 && chance(0.5)) estado = pick(["PENDIENTE", "EN_PROCESO", "LISTO"]);
    else if (chance(0.07)) estado = "CANCELADO";
    else estado = "ENTREGADO";
    const cancelado = estado === "CANCELADO";
    const entregado = estado === "ENTREGADO";
    const tipoEntrega = chance(0.55) ? "RETIRO" : "DELIVERY";
    const vendedor = chance(0.8) ? { id: c.asignado_a, sucursal_id: c.sucursal_id } : pick(vendedores);
    const sucursalId = c.sucursal_id;
    // 1–3 líneas de producto
    const nItems = weightedIndex([0.5, 0.35, 0.15]) + 1;
    const comandaId = uuid();
    const chosen = new Set();
    let total = 0;
    const items = [];
    for (let li = 0; li < nItems; li++) {
      let pi = weightedIndex(prodW);
      let guard = 0;
      while (chosen.has(pi) && guard++ < 8) pi = weightedIndex(prodW);
      chosen.add(pi);
      const p = productos[pi];
      const precio = Number(p.precio);
      const cant = weightedIndex([0.72, 0.22, 0.06]) + 1; // 1..3
      const costo = Math.round(precio * (0.4 + 0.18 * ((pi % 10) / 10))); // determinista por producto
      const subtotal = precio * cant;
      total += subtotal;
      items.push({ p, precio, cant, costo, subtotal });
      comandaItems.push({
        id: uuid(),
        comanda_id: comandaId,
        producto_id: p.id,
        cantidad: cant,
        precio_unitario: precio,
        costo_unitario: costo,
        subtotal,
      });
      // Proyección a ventas (una fila por línea) — salvo pedidos cancelados.
      if (!cancelado) {
        ventas.push({
          id: uuid(),
          lead_id: c.id,
          producto_id: p.id,
          usuario_id: vendedor.id,
          sucursal_id: sucursalId,
          cantidad: cant,
          precio_unitario: precio,
          total: subtotal,
          tipo_entrega: tipoEntrega,
          created_at: created,
        });
      }
    }
    const costoDelivery = tipoEntrega === "DELIVERY" ? pick([2500, 3000, 3500, 0]) : 0;
    const entregadoAt = entregado ? new Date(created.getTime() + ri(20, 240) * 60000) : null;
    comandas.push({
      id: comandaId,
      cliente_id: c.id,
      sucursal_id: sucursalId,
      tipo_entrega: tipoEntrega,
      estado,
      canal_origen: pick(CANAL_ORIGEN),
      metodo_pago: pick(METODOS),
      costo_delivery: costoDelivery,
      pago_confirmado: entregado,
      entregado_at: entregadoAt,
      created_at: created,
    });
    if (!cancelado) c.orders.push({ created, total, items });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Agregados por cliente (coherentes con sus pedidos) + tiering
// ─────────────────────────────────────────────────────────────────────────────
const gastos = customers.map((c) => c.orders.reduce((s, o) => s + o.total, 0)).filter((x) => x > 0).sort((a, b) => b - a);
const vipCut = gastos[Math.floor(gastos.length * 0.15)] || 0; // top 15% ⇒ VIP
for (const c of leads) {
  if (!c.isCustomer || c.orders.length === 0) {
    // Lead de pipeline (sin compras).
    c.estado = pick(["NUEVO", "CONTACTADO", "EN_PROCESO", "EN_PROCESO", "DESCARTADO"]);
    c.estado_cliente = "NUEVO";
    c.total_pedidos = 0;
    c.total_gastado = 0;
    c.ultima_visita = null;
    c.frecuencia_dias = null;
    c.plato_favorito = null;
    c.score = ri(20, 65);
    c.valor_estimado = pick([30000, 45000, 60000, 90000, 120000]);
    c.tags = pick([["nuevo"], ["instagram"], ["prospecto"], ["referido"]]);
    // Prospecto captado en las últimas ~8 semanas (algunos hoy, para el KPI de nuevos leads).
    c.created_at = new Date(NOW.getTime() - ri(0, 55) * DAY);
    continue;
  }
  const orders = c.orders.slice().sort((a, b) => a.created - b.created);
  const totalGastado = orders.reduce((s, o) => s + o.total, 0);
  const ultima = orders[orders.length - 1].created;
  const primera = orders[0].created;
  const diasSinComprar = (NOW - ultima) / DAY;
  // producto favorito = el de mayor gasto acumulado
  const gastoPorProd = {};
  for (const o of orders) for (const it of o.items) gastoPorProd[it.p.nombre] = (gastoPorProd[it.p.nombre] || 0) + it.subtotal;
  const favorito = Object.entries(gastoPorProd).sort((a, b) => b[1] - a[1])[0][0];
  let estadoCliente;
  if (diasSinComprar > 120) estadoCliente = "INACTIVO";
  else if (totalGastado >= vipCut) estadoCliente = "VIP";
  else if (orders.length >= 4) estadoCliente = "FRECUENTE";
  else estadoCliente = "OCASIONAL";
  const catFav = catById[productos.find((p) => p.nombre === favorito)?.categoria_id] || "";
  const tags = [];
  if (estadoCliente === "VIP") tags.push("vip");
  if (/facial|corporal|capilar/i.test(catFav)) tags.push("skincare");
  if (/maquillaje/i.test(catFav)) tags.push("maquillaje");
  if (/perfum/i.test(catFav)) tags.push("perfumes");
  if (/accesorio/i.test(catFav)) tags.push("accesorios");
  c.estado = "CONVERTIDO";
  c.estado_cliente = estadoCliente;
  c.total_pedidos = orders.length;
  c.total_gastado = totalGastado;
  c.ultima_visita = ultima;
  c.frecuencia_dias = orders.length > 1 ? Math.max(1, Math.round((ultima - primera) / DAY / (orders.length - 1))) : null;
  c.plato_favorito = favorito;
  c.score = Math.min(100, 40 + orders.length * 4 + (estadoCliente === "VIP" ? 25 : 0));
  c.valor_estimado = Math.round(totalGastado / orders.length);
  c.tags = tags.length ? tags : ["cliente"];
  // Captado poco antes de su primera compra (adquisición realista, no todo "hoy").
  c.created_at = new Date(primera.getTime() - ri(1, 20) * DAY);
}

// ─────────────────────────────────────────────────────────────────────────────
// sales_targets: meta empresa (asesor_id NULL) últimos 7 meses + meta por asesor mes actual
// ─────────────────────────────────────────────────────────────────────────────
// Ventas reales por periodo (para fijar metas ~95% de attainment).
const ventasPorPeriodo = {};
for (const v of ventas) {
  const per = periodoOf(v.created_at);
  ventasPorPeriodo[per] = (ventasPorPeriodo[per] || 0) + v.total;
}
const salesTargets = [];
for (let m = 6; m >= 0; m--) {
  const d = new Date(NOW.getFullYear(), NOW.getMonth() - m, 1);
  const per = periodoOf(d);
  const real = ventasPorPeriodo[per] || 0;
  const base = m === 0 ? real / Math.max(0.35, NOW.getDate() / 30) : real; // proyecta el mes en curso
  salesTargets.push({
    id: uuid(),
    asesor_id: null, // meta global de la empresa (la que lee el dashboard)
    periodo: per,
    meta_ventas: Math.max(500000, Math.round((base * 1.05) / 10000) * 10000),
    meta_leads: ri(35, 60),
    meta_conversion: 0.28 + rnd() * 0.1,
  });
}
const perActual = periodoOf(NOW);
for (const v of vendedores) {
  salesTargets.push({
    id: uuid(),
    asesor_id: v.id,
    periodo: perActual,
    meta_ventas: pick([1500000, 2000000, 2500000, 3000000]),
    meta_leads: ri(10, 20),
    meta_conversion: 0.25 + rnd() * 0.12,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// smart_alerts (~12): stock bajo real, clientas VIP dormidas, meta del mes
// ─────────────────────────────────────────────────────────────────────────────
const alerts = [];
const lowStock = productos.filter((p) => Number(p.stock) <= 15).slice(0, 4);
for (const p of lowStock) alerts.push({ id: uuid(), tipo: "STOCK_BAJO", lead_id: null, mensaje: `Stock bajo: ${p.nombre} (${p.stock} u.). Considera reponer.`, leido: chance(0.3) });
const dormidas = leads.filter((l) => l.estado_cliente === "VIP" || l.estado_cliente === "INACTIVO").filter((l) => l.ultima_visita && (NOW - l.ultima_visita) / DAY > 45).slice(0, 4);
for (const l of dormidas) alerts.push({ id: uuid(), tipo: "CLIENTE_INACTIVO", lead_id: l.id, mensaje: `${l.nombre} (${l.estado_cliente}) no compra hace ${Math.round((NOW - l.ultima_visita) / DAY)} días. Reactívala con una oferta.`, leido: false });
const metaMes = salesTargets.find((t) => t.asesor_id === null && t.periodo === perActual);
if (metaMes) {
  const realMes = ventasPorPeriodo[perActual] || 0;
  const pct = Math.round((realMes / Number(metaMes.meta_ventas)) * 100);
  alerts.push({ id: uuid(), tipo: "META", lead_id: null, mensaje: `Meta mensual al ${pct}% ($${realMes.toLocaleString("es-CL")} de $${Number(metaMes.meta_ventas).toLocaleString("es-CL")}).`, leido: false });
}
const topLead = leads.filter((l) => l.total_pedidos > 0).sort((a, b) => b.total_gastado - a.total_gastado)[0];
if (topLead) alerts.push({ id: uuid(), tipo: "OPORTUNIDAD", lead_id: topLead.id, mensaje: `${topLead.nombre} es tu mejor clienta ($${topLead.total_gastado.toLocaleString("es-CL")}). Ofrécele el programa VIP.`, leido: false });

// ─────────────────────────────────────────────────────────────────────────────
// ai_conversations (~18 hilos WhatsApp con clientas)
// ─────────────────────────────────────────────────────────────────────────────
const QA = [
  ["Hola! tienen el perfume Dior J'adore disponible?", "¡Hola! 😊 Sí, tenemos Dior J'adore en stock. Vale $85.500 y puedes retirarlo en Providencia o pedir despacho. ¿Te reservo uno?"],
  ["Cuánto se demora el despacho a Ñuñoa?", "El despacho a Ñuñoa demora 24–48 h y tiene un costo de $3.000 (gratis sobre $50.000). ¿Quieres que lo coordine?"],
  ["Qué base me recomiendan para piel mixta?", "Para piel mixta te recomiendo una base de acabado natural mate. Tenemos opciones de larga duración; ¿prefieres cobertura media o alta?"],
  ["Hacen envoltorio para regalo?", "¡Sí! El envoltorio de regalo es gratis 🎁. Solo avísame al momento de la compra y lo dejamos listo."],
  ["Tienen el set de skincare en oferta?", "Esta semana el set de cuidado facial está con 15% de descuento. ¿Te comparto el detalle de lo que incluye?"],
  ["Puedo pagar con transferencia?", "Claro, aceptamos transferencia, débito y crédito. Al confirmar el pedido te envío los datos. 🙌"],
  ["El labial mate reseca los labios?", "Nuestra línea mate lleva ingredientes hidratantes, así que no reseca como los mate tradicionales. ¿Buscas algún tono en particular?"],
  ["A qué hora cierran hoy?", "Hoy atendemos hasta las 20:00 en Providencia y 19:00 en Viña. ¿Te esperamos? 😊"],
];
const aiConvos = [];
const convLeads = customers.slice(0, 18);
for (const l of convLeads) {
  const session = uuid();
  const nTurns = ri(2, 4);
  let t = new Date(NOW.getTime() - ri(0, 26) * DAY);
  t.setHours(ri(9, 20), ri(0, 59), 0, 0);
  for (let k = 0; k < nTurns; k++) {
    const [u, a] = pick(QA);
    t = new Date(t.getTime() + ri(1, 6) * 60000);
    aiConvos.push({ id: uuid(), lead_id: l.id, session_id: session, role: "user", content: u, canal: "WHATSAPP", tokens_used: 0, created_at: new Date(t) });
    t = new Date(t.getTime() + ri(1, 4) * 60000);
    aiConvos.push({ id: uuid(), lead_id: l.id, session_id: session, role: "assistant", content: a, canal: "WHATSAPP", tokens_used: ri(45, 210), modelo: "claude-haiku-4-5", created_at: new Date(t) });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// tenant_knowledge (base de conocimiento del agente IA)
// ─────────────────────────────────────────────────────────────────────────────
const knowledge = [
  { type: "politica", title: "Despachos y retiros", content: "Despacho en RM 24–48 h ($3.000, gratis sobre $50.000). Retiro gratis en Providencia y Viña del Mar el mismo día.", priority: 10 },
  { type: "politica", title: "Cambios y devoluciones", content: "Aceptamos cambios dentro de 30 días con boleta, en productos sin abrir por temas sanitarios. Devolución del valor en giftcard.", priority: 9 },
  { type: "faq", title: "Medios de pago", content: "Aceptamos efectivo, débito, crédito (hasta 3 cuotas sin interés) y transferencia.", priority: 8 },
  { type: "faq", title: "Horario de atención", content: "Providencia: Lun–Sáb 10:00–20:00. Viña del Mar: Lun–Sáb 10:00–19:00.", priority: 7 },
  { type: "producto", title: "Asesoría de skincare", content: "Ofrecemos asesoría gratuita de rutina facial según tipo de piel (seca, mixta, grasa, sensible). Agenda por WhatsApp.", priority: 6 },
  { type: "general", title: "Tono de marca", content: "Aura es cercana, femenina y experta. Trata a la clienta de forma amable y con emojis suaves. Nunca prometas resultados médicos.", priority: 5 },
];

// ─────────────────────────────────────────────────────────────────────────────
// Emisión SQL
// ─────────────────────────────────────────────────────────────────────────────
const T = tenantId;
const out = [];
const p = (s) => out.push(s);
function insertRows(table, cols, rows, rowFn) {
  if (!rows.length) return;
  p(`INSERT INTO ${table} (${cols.join(", ")}) VALUES`);
  const vals = rows.map(rowFn);
  p(vals.join(",\n") + ";");
}

p("-- Seed demo UNIFICADO — Aura Cosmética & Belleza (aura-demo). Generado por tools/seed_demo_aura.mjs.");
p(`-- Determinista (semilla ${SEED}), idempotente, RLS-aware. Anclado a ${NOW.toISOString()}.`);
p("BEGIN;");
p(`SET LOCAL app.current_tenant_id = '${T}';`);
p("");
p("-- 1) Limpieza idempotente (scoped al tenant demo)");
p(`DELETE FROM comanda_items WHERE comanda_id IN (SELECT id FROM comandas WHERE tenant_id='${T}');`);
p(`DELETE FROM comandas WHERE tenant_id='${T}';`);
p(`DELETE FROM ventas WHERE tenant_id='${T}';`);
p(`DELETE FROM smart_alerts WHERE tenant_id='${T}';`);
p(`DELETE FROM ai_conversations WHERE tenant_id='${T}';`);
p(`DELETE FROM sales_targets WHERE tenant_id='${T}';`);
p(`DELETE FROM tenant_knowledge WHERE tenant_id='${T}';`);
p(`UPDATE usuarios SET sucursal_id=NULL WHERE tenant_id='${T}';`);
p(`DELETE FROM leads WHERE tenant_id='${T}';`);
p(`DELETE FROM usuarios WHERE tenant_id='${T}' AND email <> '${DEMO_EMAIL}';`);
p(`DELETE FROM sucursales WHERE tenant_id='${T}';`);
p("");

p("-- 2) Sucursales");
insertRows(
  "sucursales",
  ["id", "tenant_id", "nombre", "slug", "direccion", "ciudad", "region", "pais", "es_principal", "activo"],
  suc,
  (s) => `(${S(s.id)}, ${S(T)}, ${S(s.nombre)}, ${S(s.slug)}, ${S(s.direccion)}, ${S(s.ciudad)}, ${S(s.region)}, 'CL', ${B(s.principal)}, TRUE)`,
);
p("");

p("-- 3) Equipo (asesoras; clona el hash de contraseña del usuario demo)");
insertRows(
  "usuarios",
  ["id", "tenant_id", "email", "hashed_password", "nombre", "apellido", "role", "email_verified", "activo", "sucursal_id"],
  asesoras,
  (a) => `(${S(a.id)}, ${S(T)}, ${S(a.email)}, (SELECT hashed_password FROM usuarios WHERE tenant_id=${S(T)} AND email=${S(DEMO_EMAIL)}), ${S(a.nombre)}, ${S(a.apellido)}, 'ASESOR', TRUE, TRUE, ${S(a.sucursal_id)})`,
);
p("");

p("-- 4) Leads (clientes CRM: 120 con historial + 30 en pipeline)");
insertRows(
  "leads",
  ["id", "tenant_id", "nombre", "email", "telefono", "canal", "estado", "estado_cliente", "valor_estimado", "score", "total_pedidos", "total_gastado", "plato_favorito", "ultima_visita", "frecuencia_dias", "tags", "asignado_a", "sucursal_id", "activo", "created_at", "updated_at"],
  leads,
  (l) => `(${S(l.id)}, ${S(T)}, ${S(l.nombre)}, ${S(l.email)}, ${S(l.telefono)}, ${S(l.canal)}, ${S(l.estado)}, ${S(l.estado_cliente)}, ${N(l.valor_estimado)}, ${N(l.score)}, ${N(l.total_pedidos)}, ${N(l.total_gastado)}, ${S(l.plato_favorito)}, ${l.ultima_visita ? DATE(l.ultima_visita) : "NULL"}, ${N(l.frecuencia_dias)}, ${J(l.tags)}, ${S(l.asignado_a)}, ${S(l.sucursal_id)}, TRUE, ${TS(l.created_at)}, ${TS(l.created_at)})`,
);
p("");

p("-- 5) Ventas (proyección de líneas de pedido — pedidos/ordenes, dashboard, revenue)");
insertRows(
  "ventas",
  ["id", "tenant_id", "lead_id", "producto_id", "usuario_id", "sucursal_id", "cantidad", "precio_unitario", "total", "tipo_entrega", "activo", "created_at", "updated_at"],
  ventas,
  (v) => `(${S(v.id)}, ${S(T)}, ${S(v.lead_id)}, ${S(v.producto_id)}, ${S(v.usuario_id)}, ${S(v.sucursal_id)}, ${N(v.cantidad)}, ${N(v.precio_unitario)}, ${N(v.total)}, ${S(v.tipo_entrega)}, TRUE, ${TS(v.created_at)}, ${TS(v.created_at)})`,
);
p("");

p("-- 6) Comandas (fulfillment — dinero/reportes financiero + operativo)");
insertRows(
  "comandas",
  ["id", "tenant_id", "cliente_id", "sucursal_id", "tipo_entrega", "estado", "canal_origen", "metodo_pago", "costo_delivery", "pago_confirmado", "entregado_at", "activo", "created_at", "updated_at"],
  comandas,
  (c) => `(${S(c.id)}, ${S(T)}, ${S(c.cliente_id)}, ${S(c.sucursal_id)}, ${S(c.tipo_entrega)}, ${S(c.estado)}, ${S(c.canal_origen)}, ${S(c.metodo_pago)}, ${N(c.costo_delivery)}, ${B(c.pago_confirmado)}, ${c.entregado_at ? TS(c.entregado_at) : "NULL"}, TRUE, ${TS(c.created_at)}, ${TS(c.created_at)})`,
);
p("");

p("-- 7) Comanda items (líneas con costo — food/margen)");
insertRows(
  "comanda_items",
  ["id", "comanda_id", "producto_id", "cantidad", "precio_unitario", "costo_unitario", "subtotal"],
  comandaItems,
  (it) => `(${S(it.id)}, ${S(it.comanda_id)}, ${S(it.producto_id)}, ${N(it.cantidad)}, ${N(it.precio_unitario)}, ${N(it.costo_unitario)}, ${N(it.subtotal)})`,
);
p("");

p("-- 8) Metas de venta (empresa mensual + por asesor)");
insertRows(
  "sales_targets",
  ["id", "tenant_id", "asesor_id", "periodo", "meta_ventas", "meta_leads", "meta_conversion", "activo"],
  salesTargets,
  (t) => `(${S(t.id)}, ${S(T)}, ${t.asesor_id ? S(t.asesor_id) : "NULL"}, ${S(t.periodo)}, ${N(t.meta_ventas)}, ${N(t.meta_leads)}, ${t.meta_conversion.toFixed(4)}, TRUE)`,
);
p("");

p("-- 9) Alertas inteligentes");
insertRows(
  "smart_alerts",
  ["id", "tenant_id", "tipo", "lead_id", "mensaje", "leido", "activo"],
  alerts,
  (a) => `(${S(a.id)}, ${S(T)}, ${S(a.tipo)}, ${a.lead_id ? S(a.lead_id) : "NULL"}, ${S(a.mensaje)}, ${B(a.leido)}, TRUE)`,
);
p("");

p("-- 10) Conversaciones IA (bandeja WhatsApp)");
insertRows(
  "ai_conversations",
  // session_id → NULL: la bandeja agrupa por lead_id, y session_id tiene FK a `sessions` (auth).
  ["id", "tenant_id", "lead_id", "session_id", "role", "content", "canal", "tokens_used", "modelo", "status", "created_at"],
  aiConvos,
  (m) => `(${S(m.id)}, ${S(T)}, ${S(m.lead_id)}, NULL, ${S(m.role)}, ${S(m.content)}, ${S(m.canal)}, ${N(m.tokens_used)}, ${m.modelo ? S(m.modelo) : "NULL"}, 'SENT', ${TS(m.created_at)})`,
);
p("");

p("-- 11) Base de conocimiento del agente");
insertRows(
  "tenant_knowledge",
  ["id", "tenant_id", "type", "title", "content", "priority", "activo"],
  knowledge,
  (k) => `(${S(uuid())}, ${S(T)}, ${S(k.type)}, ${S(k.title)}, ${S(k.content)}, ${N(k.priority)}, TRUE)`,
);
p("");

p("-- 12) Costos y mínimos de stock en productos (márgenes + alertas de reposición)");
p(
  `UPDATE productos SET costo = ROUND(precio * (0.40 + 0.18 * (('x' || substr(md5(id::text),1,2))::bit(8)::int / 255.0))), stock_minimo = CASE WHEN precio < 30000 THEN 20 WHEN precio < 80000 THEN 12 ELSE 6 END WHERE tenant_id='${T}' AND costo IS NULL;`,
);
p("");

// Contadores de verificación
p("-- Verificación");
p(`SELECT 'leads' t, count(*) n FROM leads WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'ventas', count(*) FROM ventas WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'comandas', count(*) FROM comandas WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'comanda_items', count(*) FROM comanda_items ci JOIN comandas c ON c.id=ci.comanda_id WHERE c.tenant_id='${T}'`);
p(`UNION ALL SELECT 'sales_targets', count(*) FROM sales_targets WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'smart_alerts', count(*) FROM smart_alerts WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'ai_conversations', count(*) FROM ai_conversations WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'usuarios', count(*) FROM usuarios WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'sucursales', count(*) FROM sucursales WHERE tenant_id='${T}';`);
p("COMMIT;");

process.stdout.write(out.join("\n") + "\n");
process.stderr.write(
  `[seed_demo_aura] tenant=${T} leads=${leads.length} ventas=${ventas.length} comandas=${comandas.length} items=${comandaItems.length} targets=${salesTargets.length} alerts=${alerts.length} convos=${aiConvos.length}\n`,
);
