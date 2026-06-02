from python_agent.summary_timing import compute_summary_reveal_frames
from python_agent.tts_subtitle_bind import (
    apply_tts_subtitle_bind,
    build_summary_lines_from_sentences,
)
from python_agent.douyin_effect_policy import apply_douyin_effect_policy


def test_build_lines_from_sentences():
    sents = [
        {"text": "自然语言生成代码很方便", "start": 0.0, "end": 2.0},
        {"text": "本机部署更安全", "start": 2.2, "end": 4.0},
        {"text": "适合办公自动化", "start": 4.2, "end": 6.0},
    ]
    lines = build_summary_lines_from_sentences(sents, "自然语言生成", min_cards=3, max_cards=4)
    assert len(lines) >= 2


def test_apply_bind_sets_reveal_frames():
    slides = [
        {
            "type": "content_card",
            "scene_focus": True,
            "feature_label": "本机更安全",
            "summary_lines": ["a"],
            "tts_text": "本机部署更安全，数据不出本地。",
        }
    ]
    clips = [
        {
            "sentences": [
                {"text": "本机部署更安全", "start": 0.0, "end": 1.5},
                {"text": "数据不出本地", "start": 1.6, "end": 3.0},
                {"text": "适合企业使用", "start": 3.1, "end": 4.5},
            ]
        }
    ]
    out = apply_tts_subtitle_bind(slides, clips, platform="douyin")
    assert out[0].get("_tts_sentences_bound")
    assert len(out[0].get("summary_reveal_frames") or []) >= 3
    assert out[0]["summary_reveal_frames"] == sorted(out[0]["summary_reveal_frames"])


def test_reveal_matches_by_text_overlap():
    sents = [
        {"text": "第一句讲开源", "start": 0.0, "end": 2.0},
        {"text": "第二句讲部署", "start": 2.2, "end": 4.0},
    ]
    frames = compute_summary_reveal_frames(["开源部署", "第二句讲部署"], sents, fps=30)
    assert frames[1] >= int(2.2 * 30)


def test_effect_policy_limits_liquid():
    slides = [
        {
            "type": "content_card",
            "scene_focus": True,
            "tts_text": "自然语言生成很震撼",
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "tts_text": "自然语言也很炸裂",
        },
    ]
    out = apply_douyin_effect_policy(slides, platform="douyin")
    liquid = sum(1 for s in out if s.get("mid_effect") == "liquid_shake")
    assert liquid == 1
