from __future__ import annotations

import os
from pathlib import Path

from .common import _vocabulary_items
from .config import CancelCallback, ProgressCallback, TranscriptionConfig


def transcribe_openai(
    audio_path: Path,
    config: TranscriptionConfig,
    progress: ProgressCallback,
    cancelled: CancelCallback,
) -> str:
    if cancelled():
        raise InterruptedError("Transcription cancelled.")

    api_key = config.openai_api_key.strip() or os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key is available. Add one in Torchic Settings for this session, "
            "or set OPENAI_API_KEY in Windows."
        )

    progress(5, "Uploading audio to OpenAI…")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    keywords = _vocabulary_items(config.vocabulary)
    language = config.language.strip().lower()

    args = {
        "model": config.openai_model.strip() or "gpt-transcribe",
        "temperature": 0,
    }
    if language:
        args["language"] = language
    if keywords and args["model"] == "gpt-transcribe":
        args["keywords"] = keywords

    with audio_path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(file=audio_file, **args)

    if cancelled():
        raise InterruptedError("Transcription cancelled.")

    text = getattr(response, "text", None)
    if text is None and isinstance(response, str):
        text = response
    if text is None:
        raise RuntimeError("The OpenAI transcription response did not contain text.")

    progress(100, "Finished")
    return str(text).strip()
