from __future__ import annotations

from pathlib import Path

from .config import CancelCallback, ProgressCallback, TranscriptionConfig
from .local import transcribe_local
from .openai import transcribe_openai

__all__ = ["TranscriptionConfig", "transcribe", "transcribe_local", "transcribe_openai"]


def transcribe(
    audio_path: str | Path,
    config: TranscriptionConfig,
    app_dir: str | Path,
    progress: ProgressCallback,
    cancelled: CancelCallback,
) -> str:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if config.backend == "openai":
        return transcribe_openai(path, config, progress, cancelled)
    return transcribe_local(path, config, Path(app_dir), progress, cancelled)
