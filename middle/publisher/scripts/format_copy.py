"""各平台发文排版（段落、列表、链接单独成行）。"""
from __future__ import annotations

import re

from .article_layout import (
    blocks_to_html,
    format_douban_note as _format_douban_note,
    format_douban_note_html as _format_douban_note_html,
    format_toutiao_micro as _format_toutiao_micro,
    parse_structured_body,
)


def _split_sentences(text: str) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    parts = re.split(r"(?<=[。！？!?])\s*", t)
    return [p.strip() for p in parts if p.strip()]


def format_toutiao_micro(title: str, raw: str) -> str:
    return _format_toutiao_micro(title, raw)


def format_douban_note(title: str, raw: str) -> str:
    return _format_douban_note(title, raw)


def format_douban_note_html(title: str, raw: str) -> str:
    return _format_douban_note_html(title, raw)


def format_toutiao_micro_html(title: str, raw: str) -> str:
    """微头条 contenteditable 富文本粘贴用。"""
    body = raw or ""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if lines and lines[0] == (title or "").strip():
        body = "\n".join(lines[1:])
    blocks = parse_structured_body(body)
    lead = (title or "").strip()
    return blocks_to_html(blocks, lead=lead, style="toutiao")


def format_douyin_title_desc(full_title: str, body_hint: str = "") -> tuple[str, str]:
    """抖音：短标题 + 作品描述（分段）。"""
    raw = (full_title or "").strip()
    if "｜" in raw:
        short, rest = raw.split("｜", 1)
        short = short.strip()[:30]
        rest = rest.strip()
    else:
        short = raw[:30]
        rest = raw[30:].strip()

    desc_parts = []
    if rest:
        desc_parts.append(rest)
    if body_hint:
        desc_parts.append("")
        for sent in _split_sentences(body_hint)[:6]:
            if "http" not in sent:
                desc_parts.append(sent)
    # 抖音作品描述禁止外链，避免「引导去其它平台」审核

    desc = "\n".join(desc_parts).strip()[:1000]
    return short[:30] or "AI资讯", desc
