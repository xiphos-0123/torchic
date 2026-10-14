from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Signal

from ..runtime import APP_DIR
from ..transcription import TranscriptionConfig, transcribe


class Worker(QObject):
    progress = Signal(int, str)
    finished = Signal(str)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, audio_path: str, config: TranscriptionConfig):
        super().__init__()
        self.audio_path = audio_path
        self.config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            text = transcribe(
                self.audio_path,
                self.config,
                APP_DIR,
                lambda value, message: self.progress.emit(value, message),
                lambda: self._cancelled,
            )
        except InterruptedError:
            self.stopped.emit()
            return
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(text)
