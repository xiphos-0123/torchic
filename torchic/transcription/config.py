from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

APP_NAME = "Torchic"
DEFAULT_LOCAL_MODEL = "large-v3"
DEFAULT_OPENAI_MODEL = "gpt-transcribe"

LOCAL_MODEL_HINTS = {
    "large-v3": "Accuracy first; full multilingual Whisper model. Slowest and most demanding of these choices.",
    "large-v3-turbo": "Faster multilingual transcription with fewer decoder layers; accuracy can vary by recording.",
    "distil-large-v3": "Faster distilled model for English recordings.",
    "medium": "Lower memory use than large-v3; useful on smaller GPUs or CPU.",
    "small": "Lightweight option for a quick check or a slower PC.",
}

ProgressCallback = Callable[[int, str], None]
CancelCallback = Callable[[], bool]


@dataclass(slots=True)
class TranscriptionConfig:
    backend: str = "local"
    language: str = "en"
    vocabulary: str = ""
    local_model: str = DEFAULT_LOCAL_MODEL
    device: str = "auto"
    compute_type: str = "auto"
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_api_key: str = ""
    timestamps: bool = False
