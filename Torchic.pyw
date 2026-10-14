from __future__ import annotations

# Keep double-click startup through the Windows project environment.
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
if VENV_PYTHONW.exists() and Path(sys.executable).resolve() != VENV_PYTHONW.resolve():
    os.execv(str(VENV_PYTHONW), [str(VENV_PYTHONW), str(Path(__file__).resolve()), *sys.argv[1:]])

from torchic.app import main

if __name__ == "__main__":
    main()
