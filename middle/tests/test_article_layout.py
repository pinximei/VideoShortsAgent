"""头条/豆瓣排版。"""
from __future__ import annotations

from publisher.scripts.article_layout import format_douban_note, format_toutiao_micro


def test_toutiao_preserves_paragraphs_not_one_blob():
    raw = """## 发生了什么

OpenAI 发布新模型，**性能翻倍**。

- 推理更快
- 价格更低

https://ai-trends.news/resource/demo
"""
    out = format_toutiao_micro("重磅更新", raw)
    assert "📌" in out
    assert "▎" in out or "发生了什么" in out
    assert "· 推理更快" in out
    assert "【性能翻倍】" in out or "性能翻倍" in out
    assert "https://" in out
    assert "\n\n" in out or out.count("\n") >= 5
    assert " " not in out.replace("\n", "")[:80] or len(out.split("\n")) >= 4


def test_douban_no_title_line_in_body():
    raw = """## 阅读笔记

第一段说明。

- 要点一
- 要点二

https://example.com/a
"""
    out = format_douban_note("我的标题", raw)
    assert not out.startswith("我的标题")
    assert "◆" in out or "阅读笔记" in out
    assert "· 要点一" in out
    assert "原文：" in out or "https://" in out
