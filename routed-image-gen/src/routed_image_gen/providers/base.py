from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GeneratedImage:
    provider: str
    model: str
    prompt_used: str
    local_path: Path
    public_url: str | None
    mime_type: str
