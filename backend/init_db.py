"""Apply Alembic migrations to the configured database.

This script intentionally avoids ``Base.metadata.create_all()`` so Alembic
remains the only schema authoring path for existing databases.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:12345@localhost:5432/america_db"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    subprocess.run(
        [sys.executable, str(BACKEND_DIR / "run_alembic.py"), "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )

    print(f"Alembic upgrade head applied to {database_url}.")
    print("For a fresh demo bootstrap, run init_db.sql against an empty database.")


if __name__ == "__main__":
    main()
