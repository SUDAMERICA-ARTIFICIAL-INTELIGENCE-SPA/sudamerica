// Seed OLA B — complementa OLA A para la cuenta `aura-demo` (Aura Cosmética & Belleza).
//
//   node tools/seed_demo_aura_olab.mjs | ~/.local/micromamba/envs/sud/bin/psql "$DATABASE_URL"
//
// Puebla los dominios de OLA B. El NÚCLEO es Compras (hecho fuente nuevo) y CIERRA el grafo
// de coherencia de la demo:
//
//   orden_compra ─┬─► recepcion  (ENTRADA de stock → inventario/movimientos, kardex)
//                 └─► factura     (EGRESO de caja → dinero/flujo-caja · CxP)
//
// Invariante de inventario (por SKU):  entradas_compras = Σ ventas.cantidad + stock_actual
//   ⇒ el kardex (entradas − salidas) nunca es negativo y termina exactamente en el stock_actual
//     que ya muestra inventario/existencias (OLA A). Compra ≥ consumo.
//
// El resto (requisiciones, cotizaciones, devoluciones, plantillas, documentos, campañas, servicios)
// son datos demo realistas pero NO reconciliados — solo Compras es la fuente coherente nueva.
//
// Determinista (mulberry32, semilla fija), idempotente (borra datos OLA B del tenant y reinserta),
// RLS-aware (fija app.current_tenant_id), fechas relativas a hoy. Lee productos/ventas EN VIVO.

import { execFileSync } from "node:child_process";

// ── Config ──
const HOME = process.env.HOME;
const PSQL = process.env.PSQL || `${HOME}/.local/micromamba/envs/sud/bin/psql`;
const DB = process.env.DATABASE_URL || "postgresql://sudamerica@127.0.0.1:55432/sudamerica_ai";
const TENANT_SLUG = "aura-demo";
const SEED = 20260712;

// ── PRNG determinista (mulberry32) + helpers ──
let _s = (SEED ^ 0x9e3779b9) >>> 0;
function rnd() {
  _s |= 0; _s = (_s + 0x6d2b79f5) | 0;
  let t = Math.imul(_s ^ (_s >>> 15), 1 | _s);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const ri = (lo, hi) => lo + Math.floor(rnd() * (hi - lo + 1));
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const chance = (p) => rnd() < p;
function shuffle(a) { const r = a.slice(); for (let i = r.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [r[i], r[j]] = [r[j], r[i]]; } return r; }
function uuid() {
  const b = new Array(16).fill(0).map(() => Math.floor(rnd() * 256));
  b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
  const h = b.map((x) => x.toString(16).padStart(2, "0"));
  return `${h.slice(0, 4).join("")}-${h.slice(4, 6).join("")}-${h.slice(6, 8).join("")}-${h.slice(8, 10).join("")}-${h.slice(10, 16).join("")}`;
}

// ── Serialización SQL ──
const S = (v) => (v === null || v === undefined ? "NULL" : `'${String(v).replace(/'/g, "''")}'`);
const N = (v) => (v === null || v === undefined ? "NULL" : String(v));
const B = (v) => (v ? "TRUE" : "FALSE");
const J = (v) => (v === null || v === undefined ? "NULL" : `'${JSON.stringify(v).replace(/'/g, "''")}'::jsonb`);
const TS = (d) => `'${d.toISOString()}'`;
const DATE = (d) => `'${d.toISOString().slice(0, 10)}'`;

const NOW = new Date();
const DAY = 86400000;
const IVA = 0.19;

// ── Lecturas en vivo ──
function qjson(sql) {
  const out = execFileSync(PSQL, [DB, "-tAc", sql], { encoding: "utf8" }).trim();
  return out ? JSON.parse(out) : null;
}
const T = execFileSync(PSQL, [DB, "-tAc", `SELECT id FROM tenants WHERE slug='${TENANT_SLUG}'`], { encoding: "utf8" }).trim();
if (!T) throw new Error(`Tenant ${TENANT_SLUG} no encontrado`);
const productos = qjson(
  `SELECT json_agg(json_build_object('id',id,'nombre',nombre,'precio',precio,'costo',costo,'stock',stock,'categoria_id',categoria_id,'sku',sku)) FROM productos WHERE tenant_id='${T}' AND activo AND (sku IS NULL OR sku NOT LIKE 'SERV-%')`,
) || [];
const categorias = qjson(`SELECT json_agg(json_build_object('id',id,'nombre',nombre)) FROM categorias WHERE tenant_id='${T}'`) || [];
const ventasPorProd = qjson(
  `SELECT json_agg(json_build_object('producto_id',producto_id,'qty',qty)) FROM (SELECT producto_id, SUM(cantidad) qty FROM ventas WHERE tenant_id='${T}' AND activo GROUP BY producto_id) x`,
) || [];
const sucursales = qjson(`SELECT json_agg(json_build_object('id',id,'nombre',nombre,'es_principal',es_principal)) FROM sucursales WHERE tenant_id='${T}'`) || [];
const leadsClientes = qjson(
  `SELECT json_agg(json_build_object('id',id,'nombre',nombre)) FROM (SELECT id,nombre FROM leads WHERE tenant_id='${T}' AND total_pedidos>0 ORDER BY total_gastado DESC LIMIT 40) x`,
) || [];
const ventasMuestra = qjson(
  `SELECT json_agg(json_build_object('id',id,'lead_id',lead_id,'producto_id',producto_id,'total',total,'created_at',created_at)) FROM (SELECT id,lead_id,producto_id,total,created_at FROM ventas WHERE tenant_id='${T}' AND activo ORDER BY created_at DESC LIMIT 60) x`,
) || [];

if (!productos.length) throw new Error("No hay productos (¿corriste OLA A primero?)");
const qtyByProd = Object.fromEntries(ventasPorProd.map((v) => [v.producto_id, Number(v.qty)]));
const catById = Object.fromEntries(categorias.map((c) => [c.id, c.nombre]));
const sucPrincipal = (sucursales.find((s) => s.es_principal) || sucursales[0] || {}).id || null;
const sucIds = sucursales.map((s) => s.id);
const pickSuc = () => (sucIds.length ? pick(sucIds) : null);

// ── Proveedores (~20 de cosmética, mapeados a categorías reales) ──
const PROVEEDOR_POOL = [
  { nombre: "Distribuidora Belle Chile SpA", cat: "skincare", cond: "30 DIAS", lead: 7 },
  { nombre: "Cosmética Import Andes Ltda.", cat: "maquillaje", cond: "30 DIAS", lead: 10 },
  { nombre: "Perfumes del Pacífico S.A.", cat: "perfumes", cond: "60 DIAS", lead: 14 },
  { nombre: "Laboratorio Dermik", cat: "skincare", cond: "30 DIAS", lead: 9 },
  { nombre: "Beauty Supply Santiago", cat: "maquillaje", cond: "CONTADO", lead: 5 },
  { nombre: "Aromas & Esencias Ltda.", cat: "perfumes", cond: "30 DIAS", lead: 12 },
  { nombre: "Capilar Pro Chile", cat: "capilar", cond: "30 DIAS", lead: 8 },
  { nombre: "Nature Skin Distribución", cat: "skincare", cond: "CONTADO", lead: 6 },
  { nombre: "Glam Cosmetics Wholesale", cat: "maquillaje", cond: "30 DIAS", lead: 11 },
  { nombre: "Packaging Bello SpA", cat: "packaging", cond: "CONTADO", lead: 4 },
  { nombre: "EcoEnvases Chile", cat: "packaging", cond: "30 DIAS", lead: 6 },
  { nombre: "Insumos Estética Total", cat: "accesorios", cond: "CONTADO", lead: 5 },
  { nombre: "Korea Beauty Import", cat: "skincare", cond: "60 DIAS", lead: 21 },
  { nombre: "Fragancias Premium Ltda.", cat: "perfumes", cond: "60 DIAS", lead: 15 },
  { nombre: "MakeUp Store Mayorista", cat: "maquillaje", cond: "30 DIAS", lead: 9 },
  { nombre: "Hair Care Solutions", cat: "capilar", cond: "30 DIAS", lead: 10 },
  { nombre: "Dermocosmética Sur", cat: "skincare", cond: "30 DIAS", lead: 8 },
  { nombre: "Accesorios Beauty Chile", cat: "accesorios", cond: "CONTADO", lead: 4 },
  { nombre: "Gran Distribuidora Cosmética", cat: "maquillaje", cond: "30 DIAS", lead: 7 },
  { nombre: "Esencia Natural Wholesale", cat: "skincare", cond: "30 DIAS", lead: 9 },
];
const CONTACTOS = ["Paulina Herrera", "Rodrigo Castro", "Andrea Muñoz", "Felipe Rojas", "Carla Díaz", "Sebastián Vega", "María José Soto", "Diego Fuentes"];
const condDias = (c) => (c === "CONTADO" ? 0 : c === "60 DIAS" ? 60 : 30);

const proveedores = PROVEEDOR_POOL.map((p, i) => ({
  id: uuid(), nombre: p.nombre, categoria: p.cat, condicion_pago: p.cond, lead_time_dias: p.lead,
  rut: `${ri(70, 99)}.${ri(100, 999)}.${ri(100, 999)}-${ri(0, 9)}`,
  contacto_nombre: pick(CONTACTOS),
  email: `contacto@${p.nombre.toLowerCase().normalize("NFD").replace(/[^a-z]/g, "").slice(0, 14)}.cl`,
  telefono: `+562${ri(20000000, 29999999)}`,
  direccion: pick(["Av. Vicuña Mackenna", "Av. Américo Vespucio", "Camino a Melipilla", "Av. Eduardo Frei", "El Salto"]) + ` ${ri(1000, 9999)}, Santiago`,
  rating: (3.4 + rnd() * 1.6).toFixed(2),
}));
// índice proveedor por categoría de insumo
function categoriaInsumo(catNombre) {
  const c = (catNombre || "").toLowerCase();
  if (/facial|corporal|piel|skin|crema|serum/.test(c)) return "skincare";
  if (/maquillaje|labial|base|make/.test(c)) return "maquillaje";
  if (/perfum|fragancia|aroma/.test(c)) return "perfumes";
  if (/capilar|cabello|shampoo/.test(c)) return "capilar";
  if (/accesorio/.test(c)) return "accesorios";
  return pick(["skincare", "maquillaje"]);
}
const provByCat = {};
for (const p of proveedores) (provByCat[p.categoria] ||= []).push(p);
const provFor = (catInsumo) => pick(provByCat[catInsumo] || proveedores);

// ── Lotes de compra por SKU: entradas = ventas + stock_actual (invariante) ──
// Modelo realista: el stock de APERTURA (48M) ya existía antes de la ventana; dentro de los 12
// meses la tienda solo REPONE lo consumido por las ventas + un buffer de restock. Así las compras
// (egresos) ≈ COGS y el flujo de caja mensual es coherente (ingresos > egresos, margen ~50%).
// Invariante suave: entradas(SKU) ≥ salidas(SKU) ⇒ kardex por SKU nunca negativo.
const lots = []; // {producto, qty, catInsumo, monthOffset}
for (const p of productos) {
  const vendidas = qtyByProd[p.id] || 0;
  const buffer = Math.max(2, Math.round(vendidas * 0.15));
  // reposición = vendido + buffer; los SKUs sin ventas rara vez se compran (slow movers)
  const entradas = vendidas > 0 ? vendidas + buffer : (chance(0.4) ? ri(3, 10) : 0);
  if (entradas <= 0) continue;
  const catInsumo = categoriaInsumo(catById[p.categoria_id]);
  // nº de lotes proporcional al volumen (más rotación ⇒ más recepciones a lo largo del año)
  const K = Math.max(1, Math.min(10, Math.round(entradas / Math.max(6, ri(8, 16)))));
  let restante = entradas;
  const meses = shuffle([...Array(12).keys()]).slice(0, K).sort((a, b) => b - a); // 11..0 meses atrás
  for (let k = 0; k < K; k++) {
    const q = k === K - 1 ? restante : Math.max(1, Math.round(entradas / K + ri(-2, 2)));
    const qty = Math.min(restante, Math.max(1, q));
    restante -= qty;
    if (qty <= 0) continue;
    lots.push({ producto: p, qty, catInsumo, monthOffset: meses[k] });
    if (restante <= 0) break;
  }
}

// agrupa lotes por (proveedor, mes) en OCs
const ocMap = new Map();
for (const lot of lots) {
  const prov = provFor(lot.catInsumo);
  const key = `${prov.id}|${lot.monthOffset}`;
  if (!ocMap.has(key)) ocMap.set(key, { prov, monthOffset: lot.monthOffset, items: [] });
  ocMap.get(key).items.push(lot);
}

// ── Emitir OC + oc_items + recepciones + recepcion_items + facturas ──
const ordenes = [], ocItems = [], recepciones = [], recepcionItems = [], facturas = [];
let ocNum = 0, recNum = 0, facNum = 0;
const year = NOW.getFullYear();
const pad = (n, w = 5) => String(n).padStart(w, "0");

// OCs BASE: todas RECIBIDA con recepción COMPLETA ⇒ entradas recibidas = ventas + stock EXACTO
// (invariante de kardex intacta). La variedad de estados la aportan las OCs "en tránsito" (abajo).
for (const oc of [...ocMap.values()].sort((a, b) => b.monthOffset - a.monthOffset)) {
  let emision = new Date(year, NOW.getMonth() - oc.monthOffset, ri(1, 26), 10, 0, 0);
  // dejar margen para que la recepción (emision + lead_time) siga siendo pasada
  const maxEmision = NOW.getTime() - (oc.prov.lead_time_dias + 2) * DAY;
  if (emision.getTime() > maxEmision) emision = new Date(maxEmision - ri(0, 20) * DAY);
  const esperada = new Date(emision.getTime() + oc.prov.lead_time_dias * DAY);

  const ocId = uuid();
  let neto = 0;
  const lineItems = [];
  for (const lot of oc.items) {
    const p = lot.producto;
    const costo = Math.max(1, Math.round(Number(p.costo) || Number(p.precio) * 0.5));
    const subtotal = costo * lot.qty;
    neto += subtotal;
    const itemId = uuid();
    lineItems.push({ id: itemId, producto: p, qty: lot.qty, costo, subtotal });
    ocItems.push({ id: itemId, orden_compra_id: ocId, producto_id: p.id, descripcion: p.nombre, cantidad: lot.qty, cantidad_recibida: lot.qty, costo_unitario: costo, subtotal });
  }
  const iva = Math.round(neto * IVA);
  const total = neto + iva;
  ordenes.push({ id: ocId, proveedor_id: oc.prov.id, sucursal_id: pickSuc(), numero: `OC-${year}-${pad(++ocNum)}`, estado: "RECIBIDA", fecha_emision: emision, fecha_esperada: esperada, neto, iva, total, notas: null });

  // recepción completa
  const recId = uuid();
  const recFecha = new Date(Math.min(NOW.getTime(), esperada.getTime() + ri(-1, 2) * DAY));
  recepciones.push({ id: recId, orden_compra_id: ocId, sucursal_id: pickSuc(), numero: `REC-${year}-${pad(++recNum)}`, fecha: recFecha, estado: "COMPLETA", recibido_por: pick(CONTACTOS) });
  for (const li of lineItems) {
    recepcionItems.push({ id: uuid(), recepcion_id: recId, oc_item_id: li.id, producto_id: li.producto.id, descripcion: li.producto.nombre, cantidad: li.qty, costo_unitario: li.costo });
  }
  // factura del proveedor (egreso / CxP)
  const facFecha = new Date(recFecha.getTime() + ri(0, 3) * DAY);
  const venc = new Date(facFecha.getTime() + condDias(oc.prov.condicion_pago) * DAY);
  let facEstado, pagado;
  if (venc < NOW) {
    if (chance(0.12)) { facEstado = "VENCIDA"; pagado = chance(0.4) ? Math.round(total * 0.5) : 0; }
    else { facEstado = "PAGADA"; pagado = total; }
  } else {
    facEstado = "PENDIENTE"; pagado = chance(0.25) ? Math.round(total * 0.5) : 0;
  }
  facturas.push({ id: uuid(), proveedor_id: oc.prov.id, orden_compra_id: ocId, numero: `${ri(1000, 99999)}`, fecha_emision: facFecha, fecha_vencimiento: venc, estado: facEstado, neto, iva, total, monto_pagado: pagado, metodo_pago: facEstado === "PAGADA" ? pick(["TRANSFERENCIA", "TRANSFERENCIA", "CHEQUE"]) : null });
}

// OCs EN TRÁNSITO (~8): recientes, aún sin recibir ⇒ 0 en el kardex (no afectan la invariante).
// Aportan estados BORRADOR/ENVIADA/CONFIRMADA/CANCELADA a compras/ordenes.
for (let i = 0; i < 8; i++) {
  const prov = pick(proveedores);
  const emision = new Date(NOW.getTime() - ri(0, 18) * DAY);
  const esperada = new Date(emision.getTime() + prov.lead_time_dias * DAY);
  const estado = pick(["BORRADOR", "ENVIADA", "ENVIADA", "CONFIRMADA", "CONFIRMADA", "CANCELADA"]);
  const ocId = uuid();
  let neto = 0;
  const nItems = ri(1, 4);
  for (let k = 0; k < nItems; k++) {
    const pr = pick(productos);
    const costo = Math.max(1, Math.round(Number(pr.costo) || Number(pr.precio) * 0.5));
    const cant = ri(6, 40);
    const subtotal = costo * cant;
    neto += subtotal;
    ocItems.push({ id: uuid(), orden_compra_id: ocId, producto_id: pr.id, descripcion: pr.nombre, cantidad: cant, cantidad_recibida: 0, costo_unitario: costo, subtotal });
  }
  const iva = Math.round(neto * IVA);
  ordenes.push({ id: ocId, proveedor_id: prov.id, sucursal_id: pickSuc(), numero: `OC-${year}-${pad(++ocNum)}`, estado, fecha_emision: emision, fecha_esperada: esperada, neto, iva, total: neto + iva, notas: null });
}

// ── Requisiciones (~12, desde SKUs bajo mínimo) ──
const requisiciones = [];
let reqNum = 0;
const bajoStock = productos.slice().sort((a, b) => Number(a.stock) - Number(b.stock)).slice(0, 12);
for (const p of bajoStock) {
  const catInsumo = categoriaInsumo(catById[p.categoria_id]);
  const estado = pick(["PENDIENTE", "APROBADA", "APROBADA", "CONVERTIDA", "RECHAZADA"]);
  requisiciones.push({
    id: uuid(), sucursal_id: pickSuc(), numero: `REQ-${year}-${pad(++reqNum, 4)}`,
    solicitante: pick(["Camila Gaete", "Valentina Soto", "Josefa Muñoz", "Antonia Vera"]),
    estado, prioridad: pick(["ALTA", "MEDIA", "MEDIA", "BAJA"]), fecha: new Date(NOW.getTime() - ri(0, 40) * DAY),
    items: [{ descripcion: p.nombre, cantidad: ri(6, 40), producto_id: p.id }],
    notas: `Reposición por stock bajo (${p.stock} u.)`, catInsumo,
  });
}

// ── Cotizaciones (~15, ligadas a proveedores/requisiciones) ──
const cotizaciones = [];
let cotNum = 0;
for (let i = 0; i < 15; i++) {
  const prov = pick(proveedores);
  const req = chance(0.6) ? pick(requisiciones) : null;
  const nItems = ri(1, 3);
  const items = [];
  let total = 0;
  for (let k = 0; k < nItems; k++) {
    const p = pick(productos);
    const costo = Math.max(1, Math.round((Number(p.costo) || Number(p.precio) * 0.5) * (0.95 + rnd() * 0.2)));
    const cant = ri(5, 30);
    total += costo * cant;
    items.push({ descripcion: p.nombre, cantidad: cant, costo_unitario: costo });
  }
  cotizaciones.push({ id: uuid(), proveedor_id: prov.id, requisicion_id: req ? req.id : null, numero: `COT-${year}-${pad(++cotNum, 4)}`, estado: pick(["RECIBIDA", "RECIBIDA", "SELECCIONADA", "RECHAZADA"]), fecha: new Date(NOW.getTime() - ri(0, 60) * DAY), validez_dias: pick([10, 15, 30]), total, items });
}

// ── B3: devoluciones (~15) ──
const devoluciones = [];
let devNum = 0;
const MOTIVOS = ["DEFECTO", "INSATISFACCION", "ERROR_ENVIO", "TALLA", "OTRO"];
for (const v of shuffle(ventasMuestra).slice(0, 15)) {
  const estado = pick(["SOLICITADA", "APROBADA", "REEMBOLSADA", "REEMBOLSADA", "RECHAZADA"]);
  const monto = Math.round(Number(v.total) * (estado === "RECHAZADA" ? 0 : 0.5 + rnd() * 0.5));
  const prod = productos.find((p) => p.id === v.producto_id);
  devoluciones.push({
    id: uuid(), lead_id: v.lead_id, venta_id: v.id, sucursal_id: pickSuc(), numero: `DEV-${year}-${pad(++devNum, 4)}`,
    fecha: new Date(new Date(v.created_at).getTime() + ri(1, 20) * DAY), motivo: pick(MOTIVOS), estado,
    metodo_reembolso: estado === "REEMBOLSADA" ? pick(["GIFTCARD", "TARJETA", "EFECTIVO", "CAMBIO"]) : null,
    monto, items: [{ producto: prod ? prod.nombre : "Producto", cantidad: 1, monto }],
    notas: null,
  });
}

// ── B3: mensaje_plantillas (~10) ──
const plantillas = [
  { nombre: "Bienvenida nueva clienta", canal: "WHATSAPP", categoria: "BIENVENIDA", contenido: "¡Hola {{nombre}}! 💕 Bienvenida a Aura. Soy tu asesora de belleza, ¿en qué puedo ayudarte hoy?", variables: ["nombre"] },
  { nombre: "Confirmación de pedido", canal: "WHATSAPP", categoria: "POSTVENTA", contenido: "{{nombre}}, tu pedido por ${{total}} está confirmado ✅. Te avisamos cuando esté listo para retiro/despacho.", variables: ["nombre", "total"] },
  { nombre: "Despacho en camino", canal: "WHATSAPP", categoria: "POSTVENTA", contenido: "¡Tu pedido va en camino! 🚚 Llega hoy entre las {{hora}}. Cualquier cosa, escríbenos.", variables: ["hora"] },
  { nombre: "Recordatorio de recompra", canal: "WHATSAPP", categoria: "FIDELIZACION", contenido: "{{nombre}}, ¿se te está acabando tu {{producto}}? Te reservamos uno con 10% off esta semana 😍", variables: ["nombre", "producto"] },
  { nombre: "Promo VIP exclusiva", canal: "INSTAGRAM", categoria: "PROMO", contenido: "Solo para nuestras clientas VIP ✨ {{descuento}}% en toda la línea de skincare hasta el domingo.", variables: ["descuento"] },
  { nombre: "Reactivación clienta dormida", canal: "WHATSAPP", categoria: "FIDELIZACION", contenido: "¡Te extrañamos {{nombre}}! 💫 Vuelve con un 15% de regalo en tu próxima compra.", variables: ["nombre"] },
  { nombre: "Cobranza factura pendiente", canal: "EMAIL", categoria: "COBRANZA", contenido: "Estimada {{nombre}}, recordamos el saldo pendiente de ${{monto}} con vencimiento {{fecha}}.", variables: ["nombre", "monto", "fecha"] },
  { nombre: "Cumpleaños", canal: "WHATSAPP", categoria: "FIDELIZACION", contenido: "🎂 ¡Feliz cumpleaños {{nombre}}! Te regalamos un labial en tu próxima visita. ¡Te esperamos!", variables: ["nombre"] },
  { nombre: "Encuesta de satisfacción", canal: "WHATSAPP", categoria: "POSTVENTA", contenido: "{{nombre}}, ¿cómo estuvo tu experiencia? Cuéntanos del 1 al 5 ⭐ para seguir mejorando.", variables: ["nombre"] },
  { nombre: "Lanzamiento nueva colección", canal: "INSTAGRAM", categoria: "PROMO", contenido: "¡Ya llegó lo nuevo! 🌸 Descubre la colección {{coleccion}} antes que nadie.", variables: ["coleccion"] },
].map((t) => ({ id: uuid(), ...t, usos: ri(3, 180) }));

// ── B3: documentos_archivos (~24) ──
const documentos = [];
const facMuestra = facturas.slice(0, 10);
for (const f of facMuestra) {
  const prov = proveedores.find((p) => p.id === f.proveedor_id);
  documentos.push({ id: uuid(), nombre: `Factura ${prov ? prov.nombre : ""} N°${f.numero}.pdf`, tipo: "FACTURA", categoria: "Compras", url: `https://demo.aura.cl/docs/fac-${f.numero}.pdf`, mime: "application/pdf", tamano_kb: ri(80, 420), subido_por: "Camila Gaete", entidad_tipo: "proveedor", entidad_id: f.proveedor_id, created_at: f.fecha_emision });
}
const OTROS_DOCS = [
  { nombre: "Contrato arriendo local Providencia.pdf", tipo: "CONTRATO", categoria: "Legal", mime: "application/pdf" },
  { nombre: "Reglamento interno Aura.pdf", tipo: "CONTRATO", categoria: "RRHH", mime: "application/pdf" },
  { nombre: "Catálogo primavera-verano.pdf", tipo: "OTRO", categoria: "Marketing", mime: "application/pdf" },
  { nombre: "Planilla inventario físico Q2.xlsx", tipo: "PLANILLA", categoria: "Inventario", mime: "application/vnd.ms-excel" },
  { nombre: "Boleta servicios básicos junio.pdf", tipo: "BOLETA", categoria: "Gastos", mime: "application/pdf" },
  { nombre: "Manual de marca Aura.pdf", tipo: "OTRO", categoria: "Marketing", mime: "application/pdf" },
  { nombre: "Póliza seguro local.pdf", tipo: "CONTRATO", categoria: "Legal", mime: "application/pdf" },
  { nombre: "Foto vitrina campaña madre.jpg", tipo: "IMAGEN", categoria: "Marketing", mime: "image/jpeg" },
  { nombre: "Cotización proveedor packaging.pdf", tipo: "OTRO", categoria: "Compras", mime: "application/pdf" },
  { nombre: "Certificado sanitario cosméticos.pdf", tipo: "CONTRATO", categoria: "Legal", mime: "application/pdf" },
  { nombre: "Planilla remuneraciones junio.xlsx", tipo: "PLANILLA", categoria: "RRHH", mime: "application/vnd.ms-excel" },
  { nombre: "Boleta arriendo Viña.pdf", tipo: "BOLETA", categoria: "Gastos", mime: "application/pdf" },
  { nombre: "Guía despacho proveedor skincare.pdf", tipo: "OTRO", categoria: "Compras", mime: "application/pdf" },
  { nombre: "Foto producto lanzamiento.png", tipo: "IMAGEN", categoria: "Marketing", mime: "image/png" },
];
for (const d of OTROS_DOCS) documentos.push({ id: uuid(), ...d, url: `https://demo.aura.cl/docs/${d.nombre.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`, tamano_kb: ri(40, 2200), subido_por: pick(["Camila Gaete", "Valentina Soto"]), entidad_tipo: null, entidad_id: null, created_at: new Date(NOW.getTime() - ri(5, 200) * DAY) });

// ── B3: campanas (~8) ──
const CAMPANAS = [
  { nombre: "Día de la Madre — Skincare", canal: "INSTAGRAM", tipo: "PROMO", segmento: "TODOS", mesOffset: 2 },
  { nombre: "Reactivación clientas dormidas", canal: "WHATSAPP", tipo: "REACTIVACION", segmento: "INACTIVO", mesOffset: 1 },
  { nombre: "Club VIP — beneficios exclusivos", canal: "WHATSAPP", tipo: "FIDELIZACION", segmento: "VIP", mesOffset: 0 },
  { nombre: "Lanzamiento colección primavera", canal: "INSTAGRAM", tipo: "LANZAMIENTO", segmento: "TODOS", mesOffset: 0 },
  { nombre: "Black Friday Belleza", canal: "EMAIL", tipo: "PROMO", segmento: "TODOS", mesOffset: 8 },
  { nombre: "Cyber Cosmética", canal: "INSTAGRAM", tipo: "PROMO", segmento: "FRECUENTE", mesOffset: 5 },
  { nombre: "Bienvenida nuevas clientas", canal: "WHATSAPP", tipo: "FIDELIZACION", segmento: "NUEVO", mesOffset: 0 },
  { nombre: "San Valentín — Perfumes", canal: "INSTAGRAM", tipo: "PROMO", segmento: "TODOS", mesOffset: 5 },
];
const campanas = CAMPANAS.map((c) => {
  const inicio = new Date(year, NOW.getMonth() - c.mesOffset, ri(1, 15));
  const fin = new Date(inicio.getTime() + ri(7, 30) * DAY);
  const finalizada = fin < NOW;
  const estado = finalizada ? "FINALIZADA" : inicio <= NOW ? "ACTIVA" : c.mesOffset === 0 ? pick(["PROGRAMADA", "ACTIVA"]) : "BORRADOR";
  const enviados = estado === "BORRADOR" ? 0 : ri(120, 1400);
  const abiertos = Math.round(enviados * (0.35 + rnd() * 0.4));
  const conversiones = Math.round(abiertos * (0.04 + rnd() * 0.12));
  const presupuesto = pick([50000, 80000, 120000, 150000, 200000]);
  return { id: uuid(), nombre: c.nombre, canal: c.canal, tipo: c.tipo, estado, segmento: c.segmento, fecha_inicio: inicio, fecha_fin: fin, presupuesto, enviados, abiertos, conversiones, ingresos_generados: conversiones * ri(18000, 45000) };
});

// ── B1: servicios de belleza (como productos, categoría "Servicios de Belleza", sku SERV-*) ──
const servicios = [
  { nombre: "Limpieza facial profunda", precio: 28000, dur: 60 },
  { nombre: "Manicure semipermanente", precio: 15000, dur: 45 },
  { nombre: "Pedicure spa", precio: 18000, dur: 60 },
  { nombre: "Maquillaje social", precio: 25000, dur: 50 },
  { nombre: "Depilación facial con cera", precio: 8000, dur: 20 },
  { nombre: "Tratamiento hidratante capilar", precio: 22000, dur: 40 },
  { nombre: "Asesoría de skincare personalizada", precio: 12000, dur: 30 },
  { nombre: "Diseño de cejas + laminado", precio: 16000, dur: 40 },
];

// ─────────────────────────────────────────────────────────────────────────────
// Emisión SQL
// ─────────────────────────────────────────────────────────────────────────────
const out = [];
const p = (s) => out.push(s);
function insertRows(table, cols, rows, rowFn) {
  if (!rows.length) return;
  p(`INSERT INTO ${table} (${cols.join(", ")}) VALUES`);
  p(rows.map(rowFn).join(",\n") + ";");
  p("");
}

p("-- Seed OLA B — Aura Cosmética & Belleza (aura-demo). Generado por tools/seed_demo_aura_olab.mjs.");
p(`-- Determinista (semilla ${SEED}), idempotente, RLS-aware. Anclado a ${NOW.toISOString()}.`);
p("BEGIN;");
p(`SET LOCAL app.current_tenant_id = '${T}';`);
p("");
p("-- 1) Limpieza idempotente (scoped al tenant demo)");
p(`DELETE FROM recepcion_items WHERE recepcion_id IN (SELECT id FROM recepciones WHERE tenant_id='${T}');`);
p(`DELETE FROM recepciones WHERE tenant_id='${T}';`);
p(`DELETE FROM facturas_proveedor WHERE tenant_id='${T}';`);
p(`DELETE FROM oc_items WHERE orden_compra_id IN (SELECT id FROM ordenes_compra WHERE tenant_id='${T}');`);
p(`DELETE FROM cotizaciones WHERE tenant_id='${T}';`);
p(`DELETE FROM ordenes_compra WHERE tenant_id='${T}';`);
p(`DELETE FROM requisiciones WHERE tenant_id='${T}';`);
p(`DELETE FROM proveedores WHERE tenant_id='${T}';`);
p(`DELETE FROM devoluciones WHERE tenant_id='${T}';`);
p(`DELETE FROM mensaje_plantillas WHERE tenant_id='${T}';`);
p(`DELETE FROM documentos_archivos WHERE tenant_id='${T}';`);
p(`DELETE FROM campanas WHERE tenant_id='${T}';`);
p(`DELETE FROM productos WHERE tenant_id='${T}' AND sku LIKE 'SERV-%';`);
p("");

p("-- 2) Proveedores");
insertRows("proveedores",
  ["id", "tenant_id", "nombre", "rut", "contacto_nombre", "email", "telefono", "direccion", "categoria", "condicion_pago", "lead_time_dias", "rating", "activo"],
  proveedores,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.nombre)}, ${S(x.rut)}, ${S(x.contacto_nombre)}, ${S(x.email)}, ${S(x.telefono)}, ${S(x.direccion)}, ${S(x.categoria)}, ${S(x.condicion_pago)}, ${N(x.lead_time_dias)}, ${N(x.rating)}, TRUE)`);

p("-- 3) Órdenes de compra");
insertRows("ordenes_compra",
  ["id", "tenant_id", "proveedor_id", "sucursal_id", "numero", "estado", "fecha_emision", "fecha_esperada", "moneda", "neto", "iva", "total", "activo", "created_at", "updated_at"],
  ordenes,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.proveedor_id)}, ${x.sucursal_id ? S(x.sucursal_id) : "NULL"}, ${S(x.numero)}, ${S(x.estado)}, ${DATE(x.fecha_emision)}, ${DATE(x.fecha_esperada)}, 'CLP', ${N(x.neto)}, ${N(x.iva)}, ${N(x.total)}, TRUE, ${TS(x.fecha_emision)}, ${TS(x.fecha_emision)})`);

p("-- 4) OC items");
insertRows("oc_items",
  ["id", "orden_compra_id", "producto_id", "descripcion", "cantidad", "cantidad_recibida", "costo_unitario", "subtotal"],
  ocItems,
  (x) => `(${S(x.id)}, ${S(x.orden_compra_id)}, ${x.producto_id ? S(x.producto_id) : "NULL"}, ${S(x.descripcion)}, ${N(x.cantidad)}, ${N(x.cantidad_recibida)}, ${N(x.costo_unitario)}, ${N(x.subtotal)})`);

p("-- 5) Recepciones (entradas de stock)");
insertRows("recepciones",
  ["id", "tenant_id", "orden_compra_id", "sucursal_id", "numero", "fecha", "estado", "recibido_por", "activo", "created_at", "updated_at"],
  recepciones,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.orden_compra_id)}, ${x.sucursal_id ? S(x.sucursal_id) : "NULL"}, ${S(x.numero)}, ${DATE(x.fecha)}, ${S(x.estado)}, ${S(x.recibido_por)}, TRUE, ${TS(x.fecha)}, ${TS(x.fecha)})`);

p("-- 6) Recepción items");
insertRows("recepcion_items",
  ["id", "recepcion_id", "oc_item_id", "producto_id", "descripcion", "cantidad", "costo_unitario"],
  recepcionItems,
  (x) => `(${S(x.id)}, ${S(x.recepcion_id)}, ${x.oc_item_id ? S(x.oc_item_id) : "NULL"}, ${x.producto_id ? S(x.producto_id) : "NULL"}, ${S(x.descripcion)}, ${N(x.cantidad)}, ${N(x.costo_unitario)})`);

p("-- 7) Facturas de proveedor (egresos / CxP)");
insertRows("facturas_proveedor",
  ["id", "tenant_id", "proveedor_id", "orden_compra_id", "numero", "fecha_emision", "fecha_vencimiento", "estado", "neto", "iva", "total", "monto_pagado", "metodo_pago", "activo", "created_at", "updated_at"],
  facturas,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.proveedor_id)}, ${x.orden_compra_id ? S(x.orden_compra_id) : "NULL"}, ${S(x.numero)}, ${DATE(x.fecha_emision)}, ${DATE(x.fecha_vencimiento)}, ${S(x.estado)}, ${N(x.neto)}, ${N(x.iva)}, ${N(x.total)}, ${N(x.monto_pagado)}, ${x.metodo_pago ? S(x.metodo_pago) : "NULL"}, TRUE, ${TS(x.fecha_emision)}, ${TS(x.fecha_emision)})`);

p("-- 8) Requisiciones");
insertRows("requisiciones",
  ["id", "tenant_id", "sucursal_id", "numero", "solicitante", "estado", "prioridad", "fecha", "items", "notas", "activo", "created_at", "updated_at"],
  requisiciones,
  (x) => `(${S(x.id)}, ${S(T)}, ${x.sucursal_id ? S(x.sucursal_id) : "NULL"}, ${S(x.numero)}, ${S(x.solicitante)}, ${S(x.estado)}, ${S(x.prioridad)}, ${DATE(x.fecha)}, ${J(x.items)}, ${S(x.notas)}, TRUE, ${TS(x.fecha)}, ${TS(x.fecha)})`);

p("-- 9) Cotizaciones");
insertRows("cotizaciones",
  ["id", "tenant_id", "proveedor_id", "requisicion_id", "numero", "estado", "fecha", "validez_dias", "total", "items", "activo", "created_at", "updated_at"],
  cotizaciones,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.proveedor_id)}, ${x.requisicion_id ? S(x.requisicion_id) : "NULL"}, ${S(x.numero)}, ${S(x.estado)}, ${DATE(x.fecha)}, ${N(x.validez_dias)}, ${N(x.total)}, ${J(x.items)}, TRUE, ${TS(x.fecha)}, ${TS(x.fecha)})`);

p("-- 10) Devoluciones");
insertRows("devoluciones",
  ["id", "tenant_id", "lead_id", "venta_id", "sucursal_id", "numero", "fecha", "motivo", "estado", "metodo_reembolso", "monto", "items", "notas", "activo", "created_at", "updated_at"],
  devoluciones,
  (x) => `(${S(x.id)}, ${S(T)}, ${x.lead_id ? S(x.lead_id) : "NULL"}, ${x.venta_id ? S(x.venta_id) : "NULL"}, ${x.sucursal_id ? S(x.sucursal_id) : "NULL"}, ${S(x.numero)}, ${DATE(x.fecha)}, ${S(x.motivo)}, ${S(x.estado)}, ${x.metodo_reembolso ? S(x.metodo_reembolso) : "NULL"}, ${N(x.monto)}, ${J(x.items)}, ${x.notas ? S(x.notas) : "NULL"}, TRUE, ${TS(x.fecha)}, ${TS(x.fecha)})`);

p("-- 11) Plantillas de mensaje");
insertRows("mensaje_plantillas",
  ["id", "tenant_id", "nombre", "canal", "categoria", "contenido", "variables", "usos", "activo"],
  plantillas,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.nombre)}, ${S(x.canal)}, ${S(x.categoria)}, ${S(x.contenido)}, ${J(x.variables)}, ${N(x.usos)}, TRUE)`);

p("-- 12) Documentos");
insertRows("documentos_archivos",
  ["id", "tenant_id", "nombre", "tipo", "categoria", "url", "mime", "tamano_kb", "subido_por", "entidad_tipo", "entidad_id", "activo", "created_at", "updated_at"],
  documentos,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.nombre)}, ${S(x.tipo)}, ${S(x.categoria)}, ${S(x.url)}, ${S(x.mime)}, ${N(x.tamano_kb)}, ${S(x.subido_por)}, ${x.entidad_tipo ? S(x.entidad_tipo) : "NULL"}, ${x.entidad_id ? S(x.entidad_id) : "NULL"}, TRUE, ${TS(x.created_at)}, ${TS(x.created_at)})`);

p("-- 13) Campañas");
insertRows("campanas",
  ["id", "tenant_id", "nombre", "canal", "tipo", "estado", "segmento", "fecha_inicio", "fecha_fin", "presupuesto", "enviados", "abiertos", "conversiones", "ingresos_generados", "activo", "created_at", "updated_at"],
  campanas,
  (x) => `(${S(x.id)}, ${S(T)}, ${S(x.nombre)}, ${S(x.canal)}, ${S(x.tipo)}, ${S(x.estado)}, ${S(x.segmento)}, ${DATE(x.fecha_inicio)}, ${DATE(x.fecha_fin)}, ${N(x.presupuesto)}, ${N(x.enviados)}, ${N(x.abiertos)}, ${N(x.conversiones)}, ${N(x.ingresos_generados)}, TRUE, ${TS(x.fecha_inicio)}, ${TS(x.fecha_inicio)})`);

p("-- 14) Servicios de belleza (como productos, categoría propia)");
p(`INSERT INTO categorias (id, tenant_id, nombre, activo) SELECT uuid_generate_v4(), '${T}', 'Servicios de Belleza', TRUE WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE tenant_id='${T}' AND nombre='Servicios de Belleza');`);
servicios.forEach((sv, i) => {
  p(`INSERT INTO productos (id, tenant_id, categoria_id, nombre, descripcion, precio, costo, sku, stock, stock_minimo, disponible, activo) VALUES (${S(uuid())}, ${S(T)}, (SELECT id FROM categorias WHERE tenant_id='${T}' AND nombre='Servicios de Belleza' LIMIT 1), ${S(sv.nombre)}, ${S(`Servicio · ${sv.dur} min`)}, ${N(sv.precio)}, ${N(Math.round(sv.precio * 0.3))}, ${S(`SERV-${pad(i + 1, 3)}`)}, 0, 0, TRUE, TRUE);`);
});
p("");

// ── Verificación + invariante de kardex ──
p("-- Verificación");
p(`SELECT 'proveedores' t, count(*) n FROM proveedores WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'ordenes_compra', count(*) FROM ordenes_compra WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'oc_items', count(*) FROM oc_items oi JOIN ordenes_compra o ON o.id=oi.orden_compra_id WHERE o.tenant_id='${T}'`);
p(`UNION ALL SELECT 'recepciones', count(*) FROM recepciones WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'recepcion_items', count(*) FROM recepcion_items ri JOIN recepciones r ON r.id=ri.recepcion_id WHERE r.tenant_id='${T}'`);
p(`UNION ALL SELECT 'facturas_proveedor', count(*) FROM facturas_proveedor WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'requisiciones', count(*) FROM requisiciones WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'cotizaciones', count(*) FROM cotizaciones WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'devoluciones', count(*) FROM devoluciones WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'mensaje_plantillas', count(*) FROM mensaje_plantillas WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'documentos', count(*) FROM documentos_archivos WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'campanas', count(*) FROM campanas WHERE tenant_id='${T}'`);
p(`UNION ALL SELECT 'servicios', count(*) FROM productos WHERE tenant_id='${T}' AND sku LIKE 'SERV-%';`);
p("COMMIT;");
p("");
// Invariante fuera de la transacción (solo lectura): entradas >= salidas por SKU
p(`-- Invariante kardex: SKUs con entradas < salidas (debe ser 0 filas)`);
p(`SELECT p.nombre, COALESCE(e.entradas,0) entradas, COALESCE(s.salidas,0) salidas FROM productos p
   LEFT JOIN (SELECT producto_id, SUM(cantidad) entradas FROM recepcion_items GROUP BY producto_id) e ON e.producto_id=p.id
   LEFT JOIN (SELECT producto_id, SUM(cantidad) salidas FROM ventas WHERE tenant_id='${T}' AND activo GROUP BY producto_id) s ON s.producto_id=p.id
   WHERE p.tenant_id='${T}' AND COALESCE(e.entradas,0) < COALESCE(s.salidas,0);`);

process.stdout.write(out.join("\n") + "\n");
process.stderr.write(
  `[seed_olab] tenant=${T} proveedores=${proveedores.length} oc=${ordenes.length} oc_items=${ocItems.length} recepciones=${recepciones.length} rec_items=${recepcionItems.length} facturas=${facturas.length} requisiciones=${requisiciones.length} cotizaciones=${cotizaciones.length} devoluciones=${devoluciones.length} plantillas=${plantillas.length} documentos=${documentos.length} campanas=${campanas.length} servicios=${servicios.length}\n`,
);
