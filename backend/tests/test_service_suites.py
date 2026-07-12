import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SUITES = (
    "api_execute/tests",
    "callback_manual/tests",
    "canales_service/tests",
    "tasks/tests",
    "open_agent/tests",
)


def run_suite(path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", path, "-q"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
        timeout=300,
    )


@pytest.mark.parametrize("suite_path", SUITES)
def test_service_suite(suite_path: str) -> None:
    result = run_suite(suite_path)
    if result.returncode == 0:
        return

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    pytest.fail(f"{suite_path} failed:\n{output}")
