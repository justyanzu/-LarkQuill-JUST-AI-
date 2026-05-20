from __future__ import annotations

import base64
import os
from pathlib import Path
from uuid import uuid4

import httpx

from routed_image_gen.config import Settings
from routed_image_gen.providers.base import GeneratedImage


class OpenAIImageProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(self, prompt: str, *, size: str = "1024x1024") -> GeneratedImage:
        if not self._settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for premium (GPT-Image-2) route.")

        # Support relay/transit: if OPENAI_IMAGE_ENDPOINT is set, use it as the full URL.
        # Otherwise use standard OpenAI path: {base_url}/images/generations
        custom_endpoint = os.getenv("OPENAI_IMAGE_ENDPOINT", "").strip()
        if custom_endpoint:
            url = custom_endpoint
        else:
            url = f"{self._settings.openai_base_url}/images/generations"

        payload = {
            "model": self._settings.openai_image_model,
            "prompt": prompt,
            "size": size,
            "n": 1,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._settings.http_timeout_sec) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()

        # Standard OpenAI: {"data": [...]}, relay/transit: {"results": [...]}
        data = body.get("data") or body.get("results") or []
        if not data:
            raise RuntimeError(f"OpenAI image API returned no data: {body!r}")

        item = data[0]
        b64 = item.get("b64_json")
        image_url = item.get("url")
        mime = "image/png"
        local_path = self._save_image(b64=b64, image_url=image_url, suffix=".png")

        return GeneratedImage(
            provider="openai",
            model=self._settings.openai_image_model,
            prompt_used=prompt,
            local_path=local_path,
            public_url=image_url,
            mime_type=mime,
        )

    def _save_image(self, *, b64: str | None, image_url: str | None, suffix: str) -> Path:
        out_dir = self._settings.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"openai-{uuid4().hex}{suffix}"

        if b64:
            path.write_bytes(base64.b64decode(b64))
            return path

        if image_url:
            with httpx.Client(timeout=self._settings.http_timeout_sec) as client:
                resp = client.get(image_url)
                resp.raise_for_status()
                path.write_bytes(resp.content)
            return path

        raise RuntimeError("OpenAI image response had neither b64_json nor url.")
