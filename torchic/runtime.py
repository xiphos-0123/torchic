from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
_DLL_HANDLES: list[object] = []


def add_local_gpu_runtime(app_dir: Path) -> None:
    """Use optional portable CUDA DLLs without touching System32."""
    runtime = app_dir / "gpu_runtime"
    if not runtime.exists():
        return

    candidates = [runtime]
    candidates.extend(p for p in runtime.rglob("bin") if p.is_dir())
    candidates.extend(p for p in runtime.rglob("lib") if p.is_dir())

    seen: set[str] = set()
    ordered: list[str] = []
    for path in candidates:
        value = str(path.resolve())
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)
            if hasattr(os, "add_dll_directory"):
                try:
                    _DLL_HANDLES.append(os.add_dll_directory(value))
                except OSError:
                    pass

    current = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(ordered + [current])


def app_data_dir() -> Path:
    path = APP_DIR / ".torchic"
    path.mkdir(exist_ok=True)
    return path
