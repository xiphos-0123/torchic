from __future__ import annotations

import re


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
