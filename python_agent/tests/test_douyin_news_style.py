from python_agent.douyin_news_style import apply_douyin_news_style, is_news_brief


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
