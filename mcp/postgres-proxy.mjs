#!/usr/bin/env node
/**
 * MCP Postgres Proxy for Cloud SQL
 *
 * Wraps @modelcontextprotocol/server-postgres with automatic
 * Cloud SQL IP allowlisting via gcloud CLI.
 *
 * Flow:
 *   1. Get public IP
 *   2. Allowlist it on Cloud SQL instance
 *   3. Spawn the official postgres MCP server (stdin/stdout passthrough)
 *   4. On exit, clear the allowlist
 *
 * Env vars (set via .mcp.json):
 *   CLOUD_SQL_URL       - Full postgres connection string
 *   GCP_PROJECT         - GCP project ID
 *   CLOUD_SQL_INSTANCE  - Cloud SQL instance name
 */

import { spawn, execSync } from "node:child_process";

const DB_URL = process.env.CLOUD_SQL_URL;
const PROJECT = process.env.GCP_PROJECT;
const INSTANCE = process.env.CLOUD_SQL_INSTANCE;

if (!DB_URL || !PROJECT || !INSTANCE) {
  process.stderr.write(
    "[mcp-postgres] Missing env vars: CLOUD_SQL_URL, GCP_PROJECT, CLOUD_SQL_INSTANCE\n",
  );
  process.exit(1);
}

let allowlisted = false;

async function getPublicIP() {
  const res = await fetch("https://ifconfig.me");
  return (await res.text()).trim();
}

function allowlistIP(ip) {
  process.stderr.write(`[mcp-postgres] Allowlisting IP ${ip}...\n`);
  execSync(
    `gcloud sql instances patch ${INSTANCE} --authorized-networks=${ip}/32 --project ${PROJECT} --quiet`,
    { stdio: "ignore", timeout: 60_000 },
  );
  allowlisted = true;
  process.stderr.write(`[mcp-postgres] IP ${ip} allowlisted.\n`);
}

function clearAllowlist() {
  if (!allowlisted) return;
  process.stderr.write("[mcp-postgres] Clearing authorized networks...\n");
  try {
    execSync(
      `gcloud sql instances patch ${INSTANCE} --clear-authorized-networks --project ${PROJECT} --quiet`,
      { stdio: "ignore", timeout: 60_000 },
    );
    process.stderr.write("[mcp-postgres] Authorized networks cleared.\n");
  } catch (err) {
    process.stderr.write(
      `[mcp-postgres] Warning: failed to clear allowlist: ${err.message}\n`,
    );
  }
  allowlisted = false;
}

async function main() {
  // Step 1: Allowlist current IP
  const ip = await getPublicIP();
  allowlistIP(ip);

  // Step 2: Spawn the official MCP postgres server
  const child = spawn(
    "npx",
    ["-y", "@modelcontextprotocol/server-postgres", DB_URL],
    {
      stdio: ["pipe", "pipe", "inherit"],
      shell: true,
    },
  );

  // Step 3: Pipe MCP protocol (stdin/stdout passthrough)
  process.stdin.pipe(child.stdin);
  child.stdout.pipe(process.stdout);

  // Step 4: Cleanup handlers
  let exiting = false;
  const cleanup = (code) => {
    if (exiting) return;
    exiting = true;
    clearAllowlist();
    process.exit(typeof code === "number" ? code : 0);
  };

  child.on("exit", cleanup);
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);
  process.on("exit", () => {
    // Last-resort cleanup (sync only)
    if (allowlisted) {
      try {
        execSync(
          `gcloud sql instances patch ${INSTANCE} --clear-authorized-networks --project ${PROJECT} --quiet`,
          { stdio: "ignore", timeout: 30_000 },
        );
      } catch {
        // best effort
      }
    }
  });

  // Handle stdin end (Claude Code disconnected)
  process.stdin.on("end", () => {
    child.kill();
    cleanup(0);
  });
}

main().catch((err) => {
  process.stderr.write(`[mcp-postgres] Fatal: ${err.message}\n`);
  clearAllowlist();
  process.exit(1);
});
