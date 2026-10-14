from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .transcription.config import APP_NAME
from .ui.appearance import load_app_icon, stylesheet
from .ui.main_window import MainWindow


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Torchic.App")
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setStyleSheet(stylesheet())
    settings = QSettings("Torchic", "Torchic")
    app.setWindowIcon(load_app_icon(settings))
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())
