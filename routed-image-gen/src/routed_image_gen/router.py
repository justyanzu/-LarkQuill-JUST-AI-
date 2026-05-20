from __future__ import annotations

import re
from enum import Enum
from typing import Literal

RouteChoice = Literal["premium", "standard"]


class RouteMode(str, Enum):
    AUTO = "auto"
    PREMIUM = "premium"
    STANDARD = "standard"


# Heuristics for poster / Chinese typography / professional design → GPT-Image-2
_PREMIUM_KEYWORDS = re.compile(
    r"(海报|排版|字体|标题字|主标题|副标题|banner|"
    r"poster|typography|layout|branding|logo|"
    r"专业设计|平面设计|宣传图|封面设计|"
    r"chinese\s*text|legible\s*text|text\s*rendering|"
    r"infographic|flyer|menu\s*design)",
    re.IGNORECASE,
)


def should_use_premium_route(
    prompt: str,
    *,
    requirements: str | None = None,
    needs_chinese_text: bool = False,
    needs_poster_layout: bool = False,
    needs_professional_design: bool = False,
) -> bool:
    if needs_chinese_text or needs_poster_layout or needs_professional_design:
        return True
    blob = f"{prompt}\n{requirements or ''}"
    return bool(_PREMIUM_KEYWORDS.search(blob))


def resolve_route(
    mode: RouteMode | str,
    prompt: str,
    *,
    requirements: str | None = None,
    needs_chinese_text: bool = False,
    needs_poster_layout: bool = False,
    needs_professional_design: bool = False,
) -> RouteChoice:
    normalized = RouteMode(str(mode).strip().lower()) if str(mode).strip() else RouteMode.AUTO
    if normalized == RouteMode.PREMIUM:
        return "premium"
    if normalized == RouteMode.STANDARD:
        return "standard"
    if should_use_premium_route(
        prompt,
        requirements=requirements,
        needs_chinese_text=needs_chinese_text,
        needs_poster_layout=needs_poster_layout,
        needs_professional_design=needs_professional_design,
    ):
        return "premium"
    return "standard"
