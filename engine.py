from __future__ import annotations

import inspect
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


ProgressCallback = Callable[[int, str], None]
CancelCallback = Callable[[], bool]
_DLL_HANDLES: list[object] = []


@dataclass(slots=True)
class TranscriptionConfig:
    backend: str = "local"
    language: str = "en"
    vocabulary: str = ""
    local_model: str = "large-v3"
    device: str = "auto"
    compute_type: str = "auto"
    openai_model: str = "gpt-transcribe"
    openai_api_key: str = ""
    timestamps: bool = False


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


def _vocabulary_items(raw: str) -> list[str]:
    """Turn user vocabulary into short factual hotwords, never prompt prose."""
    raw = raw.strip()
    if not raw:
        return []

    items: list[str] = []
    for part in re.split(r"[,;\n]+", raw):
        item = " ".join(part.strip().split())
        if not item:
            continue
        # Keep hotwords compact; long prose encourages prompt leakage in Whisper.
        if len(item) > 80:
            item = item[:80].rstrip()
        if item.casefold() not in {x.casefold() for x in items}:
            items.append(item)
        if len(items) >= 120:
            break
    return items


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


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

    # Newer faster-whisper exposes hotwords directly. Older versions get a compact
    # vocabulary-only initial prompt instead of instruction prose.
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
