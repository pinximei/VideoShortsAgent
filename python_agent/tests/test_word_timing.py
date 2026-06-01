from python_agent.caption_timeline import sentences_to_caption_pages
from python_agent.word_timing import estimate_word_timings, tokenize_spoken_text


def test_tokenize_mixed():
    parts = tokenize_spoken_text("GitHub Star 破万了")
    assert "GitHub" in parts
    assert any("破" in p or p == "破" for p in parts)


def test_estimate_word_timings_cover_range():
    words = estimate_word_timings("这是一句完整口播", 1.0, 3.0)
    assert len(words) >= 3
    assert words[0]["start"] >= 1.0
    assert abs(words[-1]["end"] - 3.0) < 0.05


def test_caption_pages_with_estimated_tokens():
    sents = [{"text": "开源神器真好用", "start": 0.0, "end": 2.0}]
    pages = sentences_to_caption_pages(sents)
    assert len(pages) == 1
    assert len(pages[0]["tokens"]) >= 2
