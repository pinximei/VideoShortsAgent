"""屏显文案：单行字幕跟口播时间轴。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python_agent.display_text import (
    CAPTION_LINE_MAX_CHARS,
    fit_heading,
    fit_slide_for_display,
    split_caption_sentences,
    split_spoken_phrases,
)


def test_split_spoken_phrases_short_lines():
    long = "今天发现一个超好用的开源神器，能一键部署还能省不少时间"
    parts = split_spoken_phrases(long)
    assert len(parts) >= 2
    assert all(len(p) <= CAPTION_LINE_MAX_CHARS + 2 for p in parts)
    assert all("\n" not in p for p in parts)


def test_split_caption_no_multiline():
    seg = [{"text": "A" * 50, "start": 0.0, "end": 5.0}]
    parts = split_caption_sentences(seg)
    assert len(parts) >= 2
    assert all("\n" not in p["text"] for p in parts)
    assert all(p["end"] > p["start"] for p in parts)


def test_fit_heading_max_legacy():
    assert len(fit_heading("abcdefghijklmnop", max_chars=14)) <= 14


def test_fit_slide_github_daily_relaxed():
    slide = {
        "heading": "超长标题" * 5,
        "tts_text": "口播" * 30,
        "github_daily_style_id": "G01_cyber_hook_yellow",
        "bullets": [{"text": "要点" * 10, "trigger": "口播"}],
    }
    fitted = fit_slide_for_display(slide)
    assert len(fitted["heading"]) > 14
    assert fitted["tts_text"] == slide["tts_text"]


def test_split_tiktok_short_phrases():
    from python_agent.display_text import split_tiktok_caption_sentences, TIKTOK_PHRASE_MAX_CHARS

    seg = [{"text": "别划走这个GitHub开源神器太好用了赶紧收藏", "start": 0.0, "end": 5.0}]
    parts = split_tiktok_caption_sentences(seg)
    assert len(parts) >= 2
    assert all(len(p["text"]) <= TIKTOK_PHRASE_MAX_CHARS for p in parts)


def test_no_mid_word_split():
    from python_agent.display_text import split_spoken_clauses

    parts = split_spoken_clauses("这个平台真的好用")
    assert "这个平台" in parts[0] or parts[0] == "这个平台真的好用"
    assert not any(p == "这个" and i + 1 < len(parts) and parts[i + 1] == "平台" for i, p in enumerate(parts))
