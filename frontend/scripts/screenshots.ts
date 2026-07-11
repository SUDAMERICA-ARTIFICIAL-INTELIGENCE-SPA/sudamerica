import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const BASE_URL = "http://localhost:3002";
const OUT_DIR = join(process.cwd(), "screenshots");

const PAGES = [
  { name: "01-panel", path: "/dashboard" },
  { name: "02-embudo", path: "/pipeline" },
  { name: "03-prospectos", path: "/leads" },
  { name: "04-productos", path: "/productos" },
  { name: "05-ventas", path: "/ventas" },
  { name: "06-calendario", path: "/calendario" },
  { name: "07-rendimiento-ia", path: "/ia" },
  { name: "08-reportes-diario", path: "/reportes" },
  { name: "09-equipo", path: "/equipo" },
  { name: "10-calculadora-roi", path: "/roi" },
  { name: "11-configuracion", path: "/configuracion" },
];

const REPORT_TABS = [
  ["semanal", "semanal"],
  ["mensual", "mensual"],
] as const;

async function main() {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2, // Retina quality
  });

  const page = await context.newPage();

  // Mock auth — set localStorage before navigating
  await page.goto(BASE_URL);
  await page.evaluate(() => {
    localStorage.setItem("__mock_auth__", "true");
  });

  for (const route of PAGES) {
    console.log(`📸 Capturando ${route.name}...`);
    await page.goto(`${BASE_URL}${route.path}`, { waitUntil: "networkidle" });

    // Wait for skeletons to resolve
    await page.waitForTimeout(1500);

    const filePath = join(OUT_DIR, `${route.name}.png`);
    await page.screenshot({ path: filePath, fullPage: true });
    console.log(`   ✅ ${filePath}`);
  }

  // Extra: prospectos con drawer abierto
  console.log("📸 Capturando prospecto-detalle...");
  await page.goto(`${BASE_URL}/leads`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  // Click primer prospecto si existe
  const firstRow = page.locator("tbody tr").first();
  if (await firstRow.isVisible()) {
    await firstRow.click();
    await page.waitForTimeout(800);
    await page.screenshot({
      path: join(OUT_DIR, "03b-prospecto-detalle.png"),
      fullPage: true,
    });
    console.log("   ✅ 03b-prospecto-detalle.png");
  }

  // Extra: reportes tabs
  for (const [tab, label] of REPORT_TABS) {
    console.log(`📸 Capturando reportes-${label}...`);
    await page.goto(`${BASE_URL}/reportes`, { waitUntil: "networkidle" });
    await page.waitForTimeout(800);
    const tabBtn = page.getByRole("tab", { name: new RegExp(tab, "i") });
    if (await tabBtn.isVisible()) {
      await tabBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: join(OUT_DIR, `08b-reportes-${tab}.png`),
        fullPage: true,
      });
      console.log(`   ✅ 08b-reportes-${tab}.png`);
    }
  }

  await browser.close();
  console.log(`\n✅ Todas las capturas guardadas en: ${OUT_DIR}`);
}

main().catch(console.error);
