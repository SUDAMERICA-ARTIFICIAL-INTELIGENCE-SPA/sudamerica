// CLI: regenera infra/029_rubros_seed.sql desde el fixture del manifiesto (Fase B, Paso 5).
//
//   node tools/gen_rubros_seed.mjs
//
// Lee la verdad-py commiteada (frontend/lib/__fixtures__/rubros.manifest.json), construye el SQL
// determinista con tools/rubros-seed.mjs, y lo escribe a backend/infra/029_rubros_seed.sql.
// El test frontend/lib/rubros.seed.test.ts falla si el archivo commiteado no coincide con lo
// que este generador produciria (drift seed<->fixture).

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildSeedSql } from "./rubros-seed.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..");
const FIXTURE = resolve(REPO, "frontend/lib/__fixtures__/rubros.manifest.json");
const OUT = resolve(REPO, "backend/infra/029_rubros_seed.sql");

const manifest = JSON.parse(readFileSync(FIXTURE, "utf8"));
const sql = buildSeedSql(manifest);
writeFileSync(OUT, sql, "utf8");

const n = Object.keys(manifest.rubros).length;
process.stdout.write(`029_rubros_seed.sql regenerado: ${n} rubros desde ${FIXTURE}\n`);
