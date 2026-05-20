from __future__ import annotations

import base64
from pathlib import Path
from uuid import uuid4

import httpx

from routed_image_gen.config import Settings
from routed_image_gen.providers.base import GeneratedImage


class VolcengineSeedreamProvider:
    """Volcengine Ark — OpenAI-compatible images/generations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(self, prompt: str, *, size: str = "2K") -> GeneratedImage:
        if not self._settings.volcengine_api_key:
            raise RuntimeError(
                "VOLCENGINE_API_KEY is required for standard (Seedream lite) route."
            )

        url = f"{self._settings.volcengine_base_url}/images/generations"
        payload = {
            "model": self._settings.volcengine_image_model,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
            "watermark": False,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._settings.http_timeout_sec) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()

        data = body.get("data") or []
        if not data:
            raise RuntimeError(f"Volcengine image API returned no data: {body!r}")

        item = data[0]
        b64 = item.get("b64_json")
        image_url = item.get("url")
        mime = "image/png"
        local_path = self._save_image(b64=b64, image_url=image_url, suffix=".png")

        return GeneratedImage(
            provider="volcengine",
            model=self._settings.volcengine_image_model,
            prompt_used=prompt,
            local_path=local_path,
            public_url=image_url,
            mime_type=mime,
        )

    def _save_image(self, *, b64: str | None, image_url: str | None, suffix: str) -> Path:
        out_dir = self._settings.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"seedream-{uuid4().hex}{suffix}"

        if b64:
            path.write_bytes(base64.b64decode(b64))
            return path

        if image_url:
            with httpx.Client(timeout=self._settings.http_timeout_sec) as client:
                resp = client.get(image_url)
                resp.raise_for_status()
                path.write_bytes(resp.content)
            return path

        raise RuntimeError("Volcengine image response had neither b64_json nor url.")
