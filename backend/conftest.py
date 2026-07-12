"""Root pytest hooks to isolate each microservice's `app` package during collection."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent
_SERVICE_ROOTS = {
    "api_execute": _REPO_ROOT / "api_execute",
    "callback_manual": _REPO_ROOT / "callback_manual",
    "tasks": _REPO_ROOT / "tasks",
    "canales_service": _REPO_ROOT / "canales_service",
    "open_agent": _REPO_ROOT / "open_agent",
}
_SERVICE_MODULE_CACHE: dict[str, dict[str, object]] = {}
_ACTIVE_SERVICE: str | None = None
_TEST_INTERNAL_SERVICE_KEYS = {
    "API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY": "test-api-execute-internal-service-key-0123456789ab",
    "CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY": "test-callback-manual-internal-service-key-0123456789",
    "TASKS_INTERNAL_SERVICE_SECRET_KEY": "test-tasks-internal-service-key-0123456789abcdef",
    "CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY": "test-canales-service-internal-service-key-012345678",
}

for env_name, env_value in _TEST_INTERNAL_SERVICE_KEYS.items():
    os.environ.setdefault(env_name, env_value)


def _service_for_path(path: Path) -> str | None:
    parts = set(path.parts)
    for service_name in _SERVICE_ROOTS:
        if service_name in parts:
            return service_name
    return None


def _detect_loaded_service() -> str | None:
    app_module = sys.modules.get("app")
    module_file = getattr(app_module, "__file__", None)
    if not module_file:
        return None
    module_path = Path(str(module_file)).resolve()
    for service_name, service_root in _SERVICE_ROOTS.items():
        if service_root in module_path.parents:
            return service_name
    return None


def _capture_active_service_modules() -> None:
    global _ACTIVE_SERVICE

    loaded_service = _detect_loaded_service()
    if loaded_service is None:
        return

    _SERVICE_MODULE_CACHE[loaded_service] = {
        module_name: module
        for module_name, module in sys.modules.items()
        if module_name == "app" or module_name.startswith("app.")
    }
    _ACTIVE_SERVICE = loaded_service


def _purge_app_modules() -> None:
    for module_name in tuple(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


def _prioritize_service_root(service_name: str) -> None:
    service_root_str = str(_SERVICE_ROOTS[service_name])
    if service_root_str in sys.path:
        sys.path.remove(service_root_str)
    sys.path.insert(0, service_root_str)
    importlib.invalidate_caches()


def _activate_service_imports(path: Path) -> None:
    global _ACTIVE_SERVICE

    target_service = _service_for_path(path)
    if target_service is None:
        return

    _capture_active_service_modules()
    if _ACTIVE_SERVICE == target_service:
        _prioritize_service_root(target_service)
        return

    cached_modules = _SERVICE_MODULE_CACHE.get(target_service)
    if cached_modules:
        _purge_app_modules()
        sys.modules.update(cached_modules)
        _ACTIVE_SERVICE = target_service
        _prioritize_service_root(target_service)
        return

    _purge_app_modules()
    _ACTIVE_SERVICE = target_service
    _prioritize_service_root(target_service)


def pytest_collect_file(file_path: Path, parent) -> None:
    _activate_service_imports(Path(str(file_path)))


def pytest_pycollect_makemodule(module_path: Path, parent) -> None:
    _activate_service_imports(Path(str(module_path)))


def pytest_runtest_setup(item) -> None:
    _activate_service_imports(Path(str(item.path)))
