"""Sync split-repos with latest monorepo state, preserving each repo's .git.

Unlike tools/bootstrap-microservice-repos.ps1 (which re-inits git from scratch),
this script keeps the existing .git directory of each split-repo so the
configured remote stays intact and the sync produces a normal commit on top
of existing history.

Usage:
    python tools/sync-split-repos.py [--services svc1 svc2 ...] [--no-commit] [--push]

Services: api_execute AI_dialer callback_manual tasks canales_service open_agent evolution_api
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
BACKEND = WORKSPACE / "backend"
SPLIT_ROOT = WORKSPACE / "split-repos"
TODAY = date.today().isoformat()

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


@dataclass
class Service:
    service_id: str
    repo_name: str
    image_name: str
    has_app: bool
    has_shared: bool
    include_db_assets: bool


MATRIX: list[Service] = [
    Service("api_execute", "sudamerica-api-execute", "api-execute", True, True, True),
    Service("AI_dialer", "sudamerica-ai-dialer", "ai-dialer", True, True, False),
    Service("callback_manual", "sudamerica-callback-manual", "callback-manual", True, True, False),
    Service("tasks", "sudamerica-tasks", "tasks", True, True, False),
    Service("canales_service", "sudamerica-canales-service", "canales-service", True, True, False),
    Service("open_agent", "sudamerica-open-agent", "open-agent", True, True, False),
    Service("evolution_api", "sudamerica-evolution-api", "evolution-api", False, False, False),
]

TEST_INTERNAL_SERVICE_KEYS = {
    "API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY": "test-api-execute-internal-service-key-0123456789ab",
    "AI_DIALER_INTERNAL_SERVICE_SECRET_KEY": "test-ai-dialer-internal-service-key-0123456789abcd",
    "CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY": "test-callback-manual-internal-service-key-0123456789",
    "TASKS_INTERNAL_SERVICE_SECRET_KEY": "test-tasks-internal-service-key-0123456789abcdef",
    "CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY": "test-canales-service-internal-service-key-012345678",
    "OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY": "test-open-agent-internal-service-key-012345678901",
}

GITIGNORE = """\
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
venv/
Lib/
Scripts/
Include/
.env
.env.local
*.py[cod]
*.egg
*.egg-info/
.coverage
coverage.xml
htmlcov/
dist/
build/
.idea/
.vscode/
"""

DOCKERIGNORE = """\
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
venv/
.git/
.env
*.egg
*.egg-info/
htmlcov/
.coverage
"""


def _ignore_junk(_src: str, names: list[str]) -> list[str]:
    out: list[str] = []
    for n in names:
        if n in EXCLUDE_DIRS:
            out.append(n)
            continue
        if n.endswith(".egg-info"):
            out.append(n)
            continue
        if any(n.endswith(s) for s in EXCLUDE_SUFFIXES):
            out.append(n)
    return out


def copytree_clean(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore_junk)


def copy_file(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def wipe_except_git(repo: Path) -> None:
    for entry in repo.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def pyproject(repo_name: str, has_shared: bool) -> str:
    source_line = '["app", "shared"]' if has_shared else '["app"]'
    return f"""\
[project]
name = "{repo_name}"
version = "0.1.0"
description = "Standalone microservice repo generated from MVP monorepo"
requires-python = ">=3.11"

[tool.ruff]
target-version = "py311"
line-length = 120
select = ["E", "F", "W", "I", "C901", "B", "UP"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short --import-mode=importlib"

[tool.coverage.run]
source = {source_line}
omit = ["*/tests/*"]

[tool.coverage.report]
fail_under = 70
show_missing = true
"""


def cloudbuild(image_name: str) -> str:
    return f"""\
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/sudamerica/{image_name}:$SHORT_SHA', '.']

images:
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/sudamerica/{image_name}:$SHORT_SHA'

options:
  logging: CLOUD_LOGGING_ONLY
"""


def dockerfile(service: Service, has_main_py: bool) -> str:
    if service.service_id == "evolution_api":
        return "FROM docker.io/evoapicloud/evolution-api:v2.3.7\n"
    lines = [
        "FROM python:3.12-slim",
        "",
        "WORKDIR /app",
        "",
        "RUN apt-get update && \\",
        "    apt-get install -y --no-install-recommends gcc libpq-dev && \\",
        "    rm -rf /var/lib/apt/lists/*",
        "",
    ]
    if service.has_shared:
        lines += ["COPY shared/ /opt/shared/", 'ENV PYTHONPATH="/opt"', ""]
    lines += [
        "COPY requirements.txt .",
        "RUN pip install --no-cache-dir -r requirements.txt",
        "",
    ]
    if has_main_py:
        lines += ["COPY main.py ./main.py"]
    lines += [
        "COPY app ./app",
        "",
        'CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]',
        "",
    ]
    return "\n".join(lines)


def conftest_bootstrap() -> str:
    lines = ['"""Standalone repo pytest bootstrap."""', "", "import os", "", "_TEST_INTERNAL_SERVICE_KEYS = {"]
    for k, v in TEST_INTERNAL_SERVICE_KEYS.items():
        lines.append(f'    "{k}": "{v}",')
    lines += [
        "}",
        "",
        "for env_name, env_value in _TEST_INTERNAL_SERVICE_KEYS.items():",
        "    os.environ.setdefault(env_name, env_value)",
        "",
    ]
    return "\n".join(lines)


def origin_note(service: Service) -> str:
    shared_line = (
        "- Vendored copy of backend/shared included."
        if service.has_shared
        else "- No vendored shared package required."
    )
    db_line = (
        "- DB migration assets copied: alembic/, infra/, alembic.ini, init_db.py, init_db.sql, run_alembic.py."
        if service.include_db_assets
        else "- No monorepo-level DB migration assets copied."
    )
    return f"""\
# Standalone Repo Origin

This repo was generated from the MVP monorepo working tree.

- Source workspace: {WORKSPACE}
- Source service path: backend/{service.service_id}
- Generated repo name: {service.repo_name}
- Last sync: {TODAY}
- Git history was not preserved for the initial bootstrap; subsequent commits
  are sync snapshots from the monorepo.
{shared_line}
{db_line}
"""


def evolution_readme() -> str:
    return """\
# sudamerica-evolution-api

Standalone repo wrapper for the Evolution API Cloud Run deployment.

- Source image: `docker.io/evoapicloud/evolution-api:v2.3.7`
- This repo contains only deployment assets.
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def sync_service(service: Service) -> Path:
    src_dir = BACKEND / service.service_id
    repo_dir = SPLIT_ROOT / service.repo_name

    if not repo_dir.exists():
        raise SystemExit(f"Missing split-repo dir: {repo_dir}")
    if not (repo_dir / ".git").exists():
        raise SystemExit(f"Split-repo missing .git: {repo_dir}")

    print(f"[sync] {service.repo_name}")
    wipe_except_git(repo_dir)

    if service.has_app:
        copytree_clean(src_dir / "app", repo_dir / "app")
        copytree_clean(src_dir / "tests", repo_dir / "tests")
        copy_file(src_dir / "main.py", repo_dir / "main.py")
        copy_file(src_dir / "requirements.txt", repo_dir / "requirements.txt")
        copy_file(src_dir / "README.md", repo_dir / "README.md")
        copy_file(src_dir / ".env.example", repo_dir / ".env.example")
    else:
        copy_file(src_dir / "Dockerfile", repo_dir / "Dockerfile")

    if service.has_shared:
        copytree_clean(BACKEND / "shared", repo_dir / "shared")

    if service.include_db_assets:
        copytree_clean(BACKEND / "alembic", repo_dir / "alembic")
        copytree_clean(BACKEND / "infra", repo_dir / "infra")
        copy_file(BACKEND / "alembic.ini", repo_dir / "alembic.ini")
        copy_file(BACKEND / "init_db.py", repo_dir / "init_db.py")
        copy_file(BACKEND / "init_db.sql", repo_dir / "init_db.sql")
        copy_file(BACKEND / "run_alembic.py", repo_dir / "run_alembic.py")

    has_main_py = (src_dir / "main.py").exists()
    write_text(repo_dir / "Dockerfile", dockerfile(service, has_main_py))
    write_text(repo_dir / ".dockerignore", DOCKERIGNORE)
    write_text(repo_dir / ".gitignore", GITIGNORE)
    write_text(repo_dir / "cloudbuild.yaml", cloudbuild(service.image_name))
    write_text(repo_dir / "MONOREPO_ORIGIN.md", origin_note(service))

    if service.has_app:
        write_text(repo_dir / "pyproject.toml", pyproject(service.repo_name, service.has_shared))
        write_text(repo_dir / "conftest.py", conftest_bootstrap())
    else:
        write_text(repo_dir / "README.md", evolution_readme())

    return repo_dir


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], check=check, text=True, capture_output=True)


def commit_and_push(repo: Path, commit_msg: str, push: bool) -> None:
    git(repo, "add", "-A")
    status = git(repo, "status", "--porcelain").stdout.strip()
    if not status:
        print(f"  (no changes to commit for {repo.name})")
        return
    git(repo, "commit", "-m", commit_msg)
    sha = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"  committed {sha}")
    if push:
        print(f"  pushing to origin main...")
        result = git(repo, "push", "origin", "main", check=False)
        if result.returncode != 0:
            print(f"  PUSH FAILED:\n{result.stderr}")
            raise SystemExit(1)
        print("  pushed OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--services", nargs="*", default=None)
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument(
        "--message",
        default=f"sync: refresh snapshot from MVP monorepo ({TODAY})",
    )
    args = parser.parse_args()

    selected = MATRIX
    if args.services:
        by_id = {s.service_id: s for s in MATRIX}
        by_repo = {s.repo_name: s for s in MATRIX}
        selected = []
        for name in args.services:
            if name in by_id:
                selected.append(by_id[name])
            elif name in by_repo:
                selected.append(by_repo[name])
            else:
                raise SystemExit(f"Unknown service: {name}")

    for svc in selected:
        repo = sync_service(svc)
        if not args.no_commit:
            commit_and_push(repo, args.message, push=args.push)

    print(f"\nDone. Synced {len(selected)} repo(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
