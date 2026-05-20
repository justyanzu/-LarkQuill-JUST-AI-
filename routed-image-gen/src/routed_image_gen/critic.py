from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from routed_image_gen.config import Settings


@dataclass(frozen=True)
class CritiqueResult:
    acceptable: bool
    feedback: str
    prompt_patch: str
    raw_model_text: str


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _image_to_data_url(path: Path, mime: str) -> str:
    encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _parse_critique_json(text: str) -> CritiqueResult:
    match = _JSON_BLOCK.search(text)
    if not match:
        return CritiqueResult(
            acceptable=False,
            feedback=text.strip() or "Critic returned non-JSON.",
            prompt_patch="",
            raw_model_text=text,
        )
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return CritiqueResult(
            acceptable=False,
            feedback="Critic JSON parse failed.",
            prompt_patch="",
            raw_model_text=text,
        )

    acceptable = bool(payload.get("acceptable", False))
    feedback = str(payload.get("feedback", "")).strip()
    prompt_patch = str(payload.get("prompt_patch", "")).strip()
    return CritiqueResult(
        acceptable=acceptable,
        feedback=feedback,
        prompt_patch=prompt_patch,
        raw_model_text=text,
    )


class DeepSeekVisionCritic:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def review(
        self,
        *,
        image_path: Path,
        mime_type: str,
        original_prompt: str,
        requirements: str,
        iteration: int,
    ) -> CritiqueResult:
        if not self._settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for vision critique.")

        data_url = _image_to_data_url(image_path, mime_type)
        system = (
            "You are a strict image QA reviewer for an automated image generation pipeline. "
            "Compare the generated image against the user's prompt and requirements. "
            "Reply with a single JSON object only (no markdown), keys: "
            '"acceptable" (boolean), "feedback" (string), "prompt_patch" (string). '
            "Set acceptable=true only if the image roughly matches intent (composition, subject, style). "
            "If acceptable=false, prompt_patch must be concise additive instructions to fix the image "
            "(do not repeat the entire prompt)."
        )
        user_text = (
            f"Iteration: {iteration}\n"
            f"Original prompt:\n{original_prompt}\n\n"
            f"Requirements:\n{requirements}\n\n"
            "Judge whether this image is acceptable. Focus on missing subjects, wrong style, "
            "unreadable or missing Chinese text when required, and poster/layout issues."
        )

        url = f"{self._settings.deepseek_base_url}/v1/chat/completions"
        payload = {
            "model": self._settings.deepseek_vision_model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self._settings.http_timeout_sec) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError(f"DeepSeek critic returned no choices: {body!r}")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            content = "\n".join(text_parts)

        return _parse_critique_json(str(content))
