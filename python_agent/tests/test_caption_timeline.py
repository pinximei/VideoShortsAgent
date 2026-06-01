"""caption_timeline 单元测试。"""
from __future__ import annotations

from python_agent.caption_timeline import (
    prepare_slide_captions,
    sentences_to_caption_pages,
    validate_caption_pages,
)


def test_tts_one_sentence_one_page():
    sents = [{"text": "这个平台真的好用", "start": 0.0, "end": 2.5}]
    pages = sentences_to_caption_pages(sents)
    assert len(pages) == 1
    assert pages[0]["text"] == "这个平台真的好用"
    assert pages[0]["durationMs"] >= 280


def test_prepare_slide_captions_tiktok_no_resplit():
    raw = [{"text": "第一句完整口播", "start": 0, "end": 2}, {"text": "第二句也完整", "start": 2.2, "end": 4}]
    slide = {"caption_mode": "tiktok", "caption_use_tts_timeline": True}
    sentences, pages = prepare_slide_captions(raw, slide, platform="douyin")
    assert len(sentences) == 2
    assert len(pages) == 2
    assert pages[0]["startMs"] <= int(0 * 1000)


def test_validate_caption_pages_short():
    issues = validate_caption_pages([{"text": "好", "startMs": 0, "durationMs": 100, "tokens": []}])
    assert any("too_short" in x for x in issues)
