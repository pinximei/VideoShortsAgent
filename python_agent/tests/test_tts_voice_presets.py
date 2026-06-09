from python_agent.tts_voice_presets import (
    compose_voice_style_from_preset,
    load_voice_preset,
)


def test_news_anchor_preset_is_xiaoxiao_calm():
    p = load_voice_preset("news_anchor_female")
    assert p["tts_voice"] == "zh-CN-XiaoxiaoNeural"
    assert p["edge_tts_rate"] == "+0%"
    assert float(p["sentence_pause_sec"]) >= 0.35


def test_compose_style_matches_preset_not_v20():
    style = compose_voice_style_from_preset({"tts_voice_preset": "news_anchor_female"})
    assert style["id"] == "news_anchor_female"
    assert style["words_per_minute"] <= 200
    assert "播报" in style.get("tone", "") or "主播" in style.get("tone", "")
