from pathlib import Path
import sys
import importlib

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_service_root_str = str(_SERVICE_ROOT)
if _service_root_str in sys.path:
    sys.path.remove(_service_root_str)
sys.path.insert(0, _service_root_str)

for _module_name in list(sys.modules):
    if _module_name == "app" or _module_name.startswith("app."):
        sys.modules.pop(_module_name, None)

importlib.invalidate_caches()
