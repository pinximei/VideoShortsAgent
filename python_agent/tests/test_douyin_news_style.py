from python_agent.douyin_news_style import (
    apply_douyin_news_style,
    enforce_ai_news_cta_slide,
    enforce_ai_news_product_clarity,
    is_news_brief,
    news_cta_display_text,
    product_name_from_brief,
)


def test_is_news_brief():
    assert is_news_brief({"feed_kind": "news"})
    assert not is_news_brief({"feed_kind": "github_daily"})


def test_strip_github_decor():
    slides = [
        {
            "type": "title_card",
            "hook_beats": ["点个Star！", "Copilot 别烦你"],
            "css_decorations": ["github-badge", "sparkle-dots"],
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "css_decorations": ["github-badge", "glass-card"],
            "repo_name": "foo",
        },
    ]
    out = apply_douyin_news_style(slides, {"feed_kind": "news"})
    assert "github-badge" not in (out[0].get("css_decorations") or [])
    assert "Star" not in " ".join(out[0].get("hook_beats") or [])
    assert "repo_name" not in out[1]


def test_product_name_from_title():
    brief = {"title": "Bluedot 2.1：Apple Watch录音同步Claude"}
    assert product_name_from_brief(brief) == "Bluedot"


def test_enforce_product_in_title_slide():
    brief = {"feed_kind": "news", "title": "Bluedot 2.1：手表录音同步"}
    slides = [{"type": "title_card", "tts_text": "这个功能很猛", "heading": "别划走"}]
    out = enforce_ai_news_product_clarity(slides, brief)
    assert "Bluedot" in out[0]["tts_text"]
    assert out[0]["heading"] == "Bluedot"


def test_cta_not_url():
    brief = {"feed_kind": "news", "cta": "https://ai-trends.news/resource/foo"}
    assert "http" not in news_cta_display_text(brief)
    slides = [{"type": "cta_card", "cta_text": ""}]
    out = enforce_ai_news_cta_slide(slides, brief)
    assert out[0]["cta_text"] == "关注，每天一条 AI 资讯"
