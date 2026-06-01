"""屏显文案适配：长句换行/分句，口播不裁。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python_agent.display_text import (
    fit_heading,
    fit_slide_for_display,
    split_caption_sentences,
    wrap_lines,
)


def test_wrap_lines_truncates_extra_lines():
    long = "这是一段非常非常长的屏显标题用来测试换行与截断效果"
    out = wrap_lines(long, max_chars=8, max_lines=2)
    lines = out.split("\n")
    assert len(lines) <= 2
    assert "…" in out or len("".join(lines)) < len(long)


def test_fit_heading_max():
    assert len(fit_heading("abcdefghijklmnop")) <= 14


def test_split_caption_long_sentence():
    seg = [{"text": "A" * 50, "start": 0.0, "end": 5.0}]
    parts = split_caption_sentences(seg)
    assert len(parts) >= 2
    assert all(p["end"] > p["start"] for p in parts)


def test_fit_slide_keeps_tts():
    slide = {
        "heading": "超长标题" * 5,
        "tts_text": "口播" * 30,
        "bullets": [{"text": "要点" * 10, "trigger": "口播"}],
    }
    fitted = fit_slide_for_display(slide)
    assert len(fitted["heading"]) <= 14
    assert fitted["tts_text"] == slide["tts_text"]
