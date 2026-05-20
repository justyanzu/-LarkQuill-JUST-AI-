from routed_image_gen.router import resolve_route, should_use_premium_route


def test_auto_standard_for_simple_prompt() -> None:
    assert resolve_route("auto", "a cute cat on grass") == "standard"
    assert not should_use_premium_route("a cute cat on grass")


def test_auto_premium_for_poster_keywords() -> None:
    prompt = "电商海报，主标题「夏日特惠」，专业排版，中文标题清晰可读"
    assert resolve_route("auto", prompt) == "premium"
    assert should_use_premium_route(prompt)


def test_explicit_flags() -> None:
    assert resolve_route("premium", "cat") == "premium"
    assert resolve_route("standard", "海报设计") == "standard"
    assert (
        resolve_route(
            "auto",
            "landscape",
            needs_chinese_text=True,
        )
        == "premium"
    )
