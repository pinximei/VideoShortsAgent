from python_agent.hero_copy import is_generic_hero, sanitize_hero_title
from python_agent.subtitle_copy import dedupe_subtitles_across_slides


def test_generic_hero_detected():
    assert is_generic_hero("核心亮点")
    assert not is_generic_hero("自然语言生成")


def test_sanitize_from_tts():
    hero = sanitize_hero_title(
        "核心亮点",
        tts="自然语言生成代码，本机运行更安全，适合办公自动化。",
    )
    assert "自然语言" in hero
    assert not is_generic_hero(hero)


def test_cross_slide_dedupe():
    slides = [
        {
            "type": "content_card",
            "scene_focus": True,
            "feature_label": "本机更安全",
            "summary_lines": ["本地部署", "一步上手", "值得收藏"],
            "tts_text": "本地部署很方便。",
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "feature_label": "办公自动化",
            "summary_lines": ["本地部署", "省时省力", "立刻见效"],
            "tts_text": "办公自动化提效明显。",
        },
    ]
    out = dedupe_subtitles_across_slides(slides)
    all_subs = [x for s in out for x in (s.get("summary_lines") or [])]
    assert all_subs.count("本地部署") == 1
