"""caption_timeline 单元测试。"""
from __future__ import annotations

from python_agent.caption_timeline import (
    prepare_slide_captions,
    sentences_to_caption_pages,
    validate_caption_pages,
)
from python_agent.word_timing import words_to_caption_tokens


def test_cjk_caption_tokens_no_extra_spaces():
    tokens = words_to_caption_tokens(
        {"text": "用自然语言说清你要做什么", "start": 0.0, "end": 2.0},
    )
    joined = "".join(t["text"] for t in tokens)
    assert joined.replace(" ", "") == "用自然语言说清你要做什么"
    assert " " not in joined


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


def test_caption_pages_end_before_tail_pad():
    """最后一页结束后不应再显示第一句（Remotion 侧用 active-page 选择）。"""
    sents = [
        {"text": "第一句口播", "start": 0.0, "end": 2.0},
        {"text": "第二句口播", "start": 2.2, "end": 4.0},
    ]
    pages = sentences_to_caption_pages(sents)
    last_end_ms = pages[-1]["startMs"] + pages[-1]["durationMs"]
    tail_ms = 6000
    active = None
    for p in pages:
        end = p["startMs"] + p["durationMs"]
        if tail_ms >= p["startMs"] and tail_ms < end:
            active = p["text"]
            break
    assert active is None


def test_validate_caption_pages_short():
    issues = validate_caption_pages([{"text": "好", "startMs": 0, "durationMs": 100, "tokens": []}])
    assert any("too_short" in x for x in issues)


def test_long_tts_splits_without_orphan():
    raw = [
        {
            "text": "处理文件和对话都在本机完成，适合合同、表格等不方便上传的资料",
            "start": 0.0,
            "end": 5.0,
        }
    ]
    slide = {"caption_mode": "tiktok", "caption_use_tts_timeline": True, "motion_params": {"maxCharsPerPage": 16}}
    _, pages = prepare_slide_captions(raw, slide, platform="douyin")
    texts = [str(p.get("text") or "") for p in pages]
    assert len(texts) >= 1
    joined = "".join(texts)
    assert "本机完成" in joined or "本机" in joined
    for t in texts:
        assert not (t.endswith("完") and len(t) < 8)
