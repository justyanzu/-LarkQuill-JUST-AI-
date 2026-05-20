from __future__ import annotations

import json
import traceback
from typing import Literal

from mcp.server.fastmcp import FastMCP

from routed_image_gen.loop import run_iterative_generation
from routed_image_gen.router import resolve_route, should_use_premium_route

mcp = FastMCP("routed-image-gen")


@mcp.tool()
def preview_image_route(
    prompt: str,
    requirements: str = "",
    route_mode: Literal["auto", "premium", "standard"] = "auto",
    needs_chinese_text: bool = False,
    needs_poster_layout: bool = False,
    needs_professional_design: bool = False,
) -> str:
    """
    Preview which image backend would be selected (gpt-image-2 vs doubao-seedream-5.0-lite).
    Does not call paid APIs.
    """
    route = resolve_route(
        route_mode,
        prompt,
        requirements=requirements or None,
        needs_chinese_text=needs_chinese_text,
        needs_poster_layout=needs_poster_layout,
        needs_professional_design=needs_professional_design,
    )
    model = "gpt-image-2 (OpenAI)" if route == "premium" else "doubao-seedream-5.0-lite (Volcengine)"
    return json.dumps(
        {
            "route": route,
            "model": model,
            "auto_would_pick_premium": should_use_premium_route(
                prompt,
                requirements=requirements or None,
                needs_chinese_text=needs_chinese_text,
                needs_poster_layout=needs_poster_layout,
                needs_professional_design=needs_professional_design,
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def generate_image_iterative(
    prompt: str,
    requirements: str = "",
    route_mode: Literal["auto", "premium", "standard"] = "auto",
    size: str = "",
    needs_chinese_text: bool = False,
    needs_poster_layout: bool = False,
    needs_professional_design: bool = False,
    max_iterations: int = 3,
) -> str:
    """
    Generate an image with model routing and up to 3 review/regenerate loops.

    Routing:
    - premium → OpenAI GPT-Image-2 (poster / Chinese text / professional design)
    - standard → Volcengine doubao-seedream-5.0-lite (default)

    After each generation, DeepSeek vision (deepseek-v4-pro) judges the image.
    If not acceptable, the prompt is patched and regeneration continues until
    accepted or the circuit breaker (max 3 iterations).

    Returns JSON with final_image_path, final_image_url, history, and status fields.
    """
    try:
        capped = min(max(1, max_iterations), 3)
        result = run_iterative_generation(
            prompt,
            requirements=requirements or None,
            route_mode=route_mode,
            size=size or None,
            needs_chinese_text=needs_chinese_text,
            needs_poster_layout=needs_poster_layout,
            needs_professional_design=needs_professional_design,
            max_iterations=capped,
        )
        payload = result.to_dict()
        summary = (
            f"Route={payload['route']} provider={payload['provider']} "
            f"iterations={payload['iterations_used']}/{payload['max_iterations']} "
            f"accepted={payload['accepted']} path={payload['final_image_path']}"
        )
        return json.dumps(
            {"summary": summary, **payload},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
