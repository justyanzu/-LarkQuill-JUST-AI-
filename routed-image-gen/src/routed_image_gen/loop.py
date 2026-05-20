from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from routed_image_gen.config import MAX_ITERATIONS_HARD_CAP, Settings, load_settings
from routed_image_gen.critic import DeepSeekVisionCritic
from routed_image_gen.providers import OpenAIImageProvider, VolcengineSeedreamProvider
from routed_image_gen.providers.base import GeneratedImage
from routed_image_gen.router import resolve_route


@dataclass
class IterationRecord:
    iteration: int
    prompt: str
    route: str
    provider: str
    model: str
    image_path: str
    image_url: str | None
    critique_acceptable: bool | None
    critique_feedback: str | None
    critique_prompt_patch: str | None


@dataclass
class GenerateLoopResult:
    ok: bool
    accepted: bool
    iterations_used: int
    max_iterations: int
    route: str
    final_prompt: str
    final_image_path: str
    final_image_url: str | None
    provider: str
    model: str
    history: list[IterationRecord]
    circuit_breaker_hit: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "accepted": self.accepted,
            "iterations_used": self.iterations_used,
            "max_iterations": self.max_iterations,
            "route": self.route,
            "final_prompt": self.final_prompt,
            "final_image_path": self.final_image_path,
            "final_image_url": self.final_image_url,
            "provider": self.provider,
            "model": self.model,
            "circuit_breaker_hit": self.circuit_breaker_hit,
            "message": self.message,
            "history": [asdict(record) for record in self.history],
        }


def _apply_prompt_patch(base: str, patch: str) -> str:
    patch = patch.strip()
    if not patch:
        return base
    return f"{base.strip()}\n\nRevision notes:\n{patch}"


def run_iterative_generation(
    prompt: str,
    *,
    requirements: str | None = None,
    route_mode: str = "auto",
    size: str | None = None,
    needs_chinese_text: bool = False,
    needs_poster_layout: bool = False,
    needs_professional_design: bool = False,
    max_iterations: int | None = None,
    settings: Settings | None = None,
) -> GenerateLoopResult:
    settings = settings or load_settings()
    cap = min(max_iterations or settings.max_iterations, MAX_ITERATIONS_HARD_CAP)
    requirements_text = (requirements or prompt).strip()

    route = resolve_route(
        route_mode,
        prompt,
        requirements=requirements_text,
        needs_chinese_text=needs_chinese_text,
        needs_poster_layout=needs_poster_layout,
        needs_professional_design=needs_professional_design,
    )

    openai = OpenAIImageProvider(settings)
    seedream = VolcengineSeedreamProvider(settings)
    critic = DeepSeekVisionCritic(settings)

    current_prompt = prompt.strip()
    history: list[IterationRecord] = []
    last_image: GeneratedImage | None = None
    last_acceptable = False

    for iteration in range(1, cap + 1):
        if route == "premium":
            gen_size = size or "1024x1024"
            image = openai.generate(current_prompt, size=gen_size)
        else:
            gen_size = size or "2K"
            image = seedream.generate(current_prompt, size=gen_size)

        last_image = image

        try:
            critique = critic.review(
                image_path=image.local_path,
                mime_type=image.mime_type,
                original_prompt=prompt,
                requirements=requirements_text,
                iteration=iteration,
            )
            acceptable = critique.acceptable
            feedback = critique.feedback
            patch = critique.prompt_patch
        except Exception as exc:  # noqa: BLE001 — return partial success with error note
            history.append(
                IterationRecord(
                    iteration=iteration,
                    prompt=current_prompt,
                    route=route,
                    provider=image.provider,
                    model=image.model,
                    image_path=str(image.local_path),
                    image_url=image.public_url,
                    critique_acceptable=None,
                    critique_feedback=f"Critic failed: {exc}",
                    critique_prompt_patch=None,
                )
            )
            return GenerateLoopResult(
                ok=True,
                accepted=False,
                iterations_used=iteration,
                max_iterations=cap,
                route=route,
                final_prompt=current_prompt,
                final_image_path=str(image.local_path),
                final_image_url=image.public_url,
                provider=image.provider,
                model=image.model,
                history=history,
                circuit_breaker_hit=iteration >= cap,
                message="Image generated but vision critique failed; returning last image.",
            )

        history.append(
            IterationRecord(
                iteration=iteration,
                prompt=current_prompt,
                route=route,
                provider=image.provider,
                model=image.model,
                image_path=str(image.local_path),
                image_url=image.public_url,
                critique_acceptable=acceptable,
                critique_feedback=feedback,
                critique_prompt_patch=patch,
            )
        )

        last_acceptable = acceptable
        if acceptable:
            return GenerateLoopResult(
                ok=True,
                accepted=True,
                iterations_used=iteration,
                max_iterations=cap,
                route=route,
                final_prompt=current_prompt,
                final_image_path=str(image.local_path),
                final_image_url=image.public_url,
                provider=image.provider,
                model=image.model,
                history=history,
                circuit_breaker_hit=False,
                message="Image accepted by vision critic.",
            )

        if iteration >= cap:
            break

        current_prompt = _apply_prompt_patch(current_prompt, patch)

    assert last_image is not None
    return GenerateLoopResult(
        ok=True,
        accepted=last_acceptable,
        iterations_used=len(history),
        max_iterations=cap,
        route=route,
        final_prompt=current_prompt,
        final_image_path=str(last_image.local_path),
        final_image_url=last_image.public_url,
        provider=last_image.provider,
        model=last_image.model,
        history=history,
        circuit_breaker_hit=True,
        message=(
            "Circuit breaker: max iterations reached; returning last generated image."
            if not last_acceptable
            else "Accepted on final iteration."
        ),
    )
