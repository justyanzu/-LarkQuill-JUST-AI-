from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS_HARD_CAP = 3


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    openai_image_model: str

    volcengine_api_key: str
    volcengine_base_url: str
    volcengine_image_model: str

    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_vision_model: str

    output_dir: Path
    max_iterations: int
    http_timeout_sec: float


def _int_env(name: str, default: int, *, cap: int | None = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    if cap is not None:
        value = min(value, cap)
    return max(1, value)


def load_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip(),
        volcengine_api_key=os.getenv("VOLCENGINE_API_KEY", "").strip(),
        volcengine_base_url=os.getenv(
            "VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        ).rstrip("/"),
        volcengine_image_model=os.getenv("VOLCENGINE_IMAGE_MODEL", "doubao-seedream-5-0-lite").strip(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_vision_model=os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-v4-pro").strip(),
        output_dir=Path(os.getenv("IMAGE_GEN_OUTPUT_DIR", "./generated-images")).expanduser(),
        max_iterations=_int_env(
            "IMAGE_GEN_MAX_ITERATIONS",
            MAX_ITERATIONS_HARD_CAP,
            cap=MAX_ITERATIONS_HARD_CAP,
        ),
        http_timeout_sec=float(os.getenv("IMAGE_GEN_HTTP_TIMEOUT_SEC", "180")),
    )
