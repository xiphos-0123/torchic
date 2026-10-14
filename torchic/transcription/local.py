from __future__ import annotations

import inspect
from pathlib import Path

from ..runtime import add_local_gpu_runtime
from .common import _format_timestamp, _vocabulary_items
from .config import CancelCallback, ProgressCallback, TranscriptionConfig


def _choose_local_runtime(device_setting: str, compute_setting: str) -> tuple[str, str]:
    import ctranslate2

    requested = device_setting.lower()
    if requested == "auto":
        try:
            requested = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            requested = "cpu"

    compute = compute_setting.lower()
    if compute == "auto":
        # Accuracy comes mainly from large-v3; this default keeps VRAM usage practical.
        compute = "int8_float16" if requested == "cuda" else "int8"
    return requested, compute


def transcribe_local(
    audio_path: Path,
    config: TranscriptionConfig,
    app_dir: Path,
    progress: ProgressCallback,
    cancelled: CancelCallback,
) -> str:
    add_local_gpu_runtime(app_dir)
    progress(1, "Loading local model…")

    from faster_whisper import WhisperModel

    device, compute = _choose_local_runtime(config.device, config.compute_type)
    progress(2, f"Loading {config.local_model} on {device} ({compute})…")

    try:
        model = WhisperModel(config.local_model, device=device, compute_type=compute)
    except Exception as exc:
        if config.device.lower() == "auto" and device == "cuda":
            progress(2, "CUDA unavailable; retrying on CPU…")
            device, compute = "cpu", "int8"
            model = WhisperModel(config.local_model, device=device, compute_type=compute)
        else:
            raise RuntimeError(
                f"Could not load the local model on {device}.\n\n{exc}"
            ) from exc

    language = config.language.strip().lower() or None
    hotwords = _vocabulary_items(config.vocabulary)

    kwargs = dict(
        language=language,
        beam_size=8,
        patience=1.2,
        temperature=0.0,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
        condition_on_previous_text=False,
        word_timestamps=False,
    )

    # Use the supported hotword parameter without adding prompt prose.
    parameters = inspect.signature(model.transcribe).parameters
    if hotwords:
        joined = ", ".join(hotwords)
        if "hotwords" in parameters:
            kwargs["hotwords"] = joined
    if "hallucination_silence_threshold" in parameters:
        kwargs["hallucination_silence_threshold"] = 2.0

    progress(3, "Transcribing…")
    segments, info = model.transcribe(str(audio_path), **kwargs)
    duration = float(getattr(info, "duration", 0.0) or 0.0)

    lines: list[str] = []
    for segment in segments:
        if cancelled():
            raise InterruptedError("Transcription cancelled.")

        text = " ".join(segment.text.strip().split())
        if text:
            if config.timestamps:
                lines.append(f"[{_format_timestamp(segment.start)}] {text}")
            else:
                lines.append(text)

        if duration > 0:
            pct = min(99, max(3, int((float(segment.end) / duration) * 100)))
            progress(pct, f"Transcribing… {pct}%")

    progress(100, "Finished")
    return "\n".join(lines).strip()
