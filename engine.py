"""Compatibility imports; engine implementations live in torchic.transcription."""

from torchic.runtime import add_local_gpu_runtime
from torchic.transcription import TranscriptionConfig, transcribe, transcribe_local, transcribe_openai

__all__ = [
    "TranscriptionConfig", "add_local_gpu_runtime",
    "transcribe", "transcribe_local", "transcribe_openai",
]
