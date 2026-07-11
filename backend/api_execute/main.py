"""Entrypoint for api_execute."""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            reload_dirs=[".", str(backend_dir / "shared")],
        )
    except OSError as exc:
        print(f"\n[ERROR] Cannot bind to port {port}: {exc}", file=sys.stderr)
        print(f"[HINT] Kill the process using port {port}, or set PORT=<other> env var.", file=sys.stderr)
        raise SystemExit(1)
