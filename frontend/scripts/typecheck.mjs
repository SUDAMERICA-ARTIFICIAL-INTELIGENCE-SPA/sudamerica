import { spawnSync } from "node:child_process";
import { rmSync } from "node:fs";
import path from "node:path";

const GENERATED_TYPES_DIR = path.join(process.cwd(), ".next", "types");
const BIN_DIR = path.join(process.cwd(), "node_modules", ".bin");
const NEXT_BIN = path.join(BIN_DIR, process.platform === "win32" ? "next.cmd" : "next");
const TSC_BIN = path.join(BIN_DIR, process.platform === "win32" ? "tsc.cmd" : "tsc");
const USE_SHELL = process.platform === "win32";

function resetGeneratedTypes() {
  rmSync(GENERATED_TYPES_DIR, { force: true, recursive: true });
}

function run(command, args) {
  const result = spawnSync(command, args, { shell: USE_SHELL, stdio: "inherit" });
  if (result.status === 0) {
    return;
  }

  if (result.error) {
    throw result.error;
  }

  process.exit(result.status ?? 1);
}

resetGeneratedTypes();
run(NEXT_BIN, ["typegen"]);
run(TSC_BIN, ["--noEmit"]);
