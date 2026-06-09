"""Soul/LLM 文案 → 头条微头条、豆瓣笔记的结构化排版（段落/小标题/要点/强调）。"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field


@dataclass
class LayoutBlock:
    kind: str  # heading, paragraph, bullets, quote, link, spacer
    text: str = ""
    items: list[str] = field(default_factory=list)
    url: str = ""


_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_HEADING = re.compile(r"^#{1,3}\s+(.+)$")
_RE_BULLET = re.compile(r"^[\-\*•·]\s+(.+)$")
_RE_NUM = re.compile(r"^\d+[\.\)、]\s+(.+)$")
_RE_LINK_ONLY = re.compile(r"^(https?://\S+)$")
_RE_SECTION = re.compile(r"^【(.+)】$")


def _emphasize_plain(text: str) -> str:
    """**粗体** → 【粗体】（纯文本编辑器可读的重点标记）。"""
    t = _RE_BOLD.sub(r"【\1】", text or "")
    return re.sub(r"\s+", " ", t).strip()


def _extract_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s\]\)]+", text or "")
    return m.group(0).rstrip(".,;，。") if m else None


def parse_structured_body(raw: str) -> list[LayoutBlock]:
    """解析 LLM 输出的 Markdown 风格正文（保留空行分段）。"""
    blocks: list[LayoutBlock] = []
    lines = (raw or "").replace("\r\n", "\n").split("\n")
    bullet_buf: list[str] = []

    def flush_bullets() -> None:
        nonlocal bullet_buf
        if bullet_buf:
            blocks.append(LayoutBlock(kind="bullets", items=bullet_buf[:8]))
            bullet_buf = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_bullets()
            if blocks and blocks[-1].kind != "spacer":
                blocks.append(LayoutBlock(kind="spacer"))
            continue

        if _RE_LINK_ONLY.match(stripped):
            flush_bullets()
            blocks.append(LayoutBlock(kind="link", url=stripped))
            continue

        hm = _RE_HEADING.match(stripped)
        if hm:
            flush_bullets()
            blocks.append(LayoutBlock(kind="heading", text=_emphasize_plain(hm.group(1))))
            continue

        sm = _RE_SECTION.match(stripped)
        if sm:
            flush_bullets()
            blocks.append(LayoutBlock(kind="heading", text=sm.group(1)))
            continue

        bm = _RE_BULLET.match(stripped) or _RE_NUM.match(stripped)
        if bm:
            bullet_buf.append(_emphasize_plain(bm.group(1)))
            continue

        flush_bullets()
        url = _extract_url(stripped)
        plain = _emphasize_plain(stripped)
        if url and url != stripped and len(plain) < 12:
            blocks.append(LayoutBlock(kind="link", url=url))
        else:
            blocks.append(LayoutBlock(kind="paragraph", text=plain))

    flush_bullets()
    return blocks


def _split_long_paragraph(text: str, *, max_len: int = 120) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = re.split(r"(?<=[。！？!?；;])\s*", text)
    out: list[str] = []
    buf = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) <= max_len:
            buf = (buf + p).strip()
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out or [text[:max_len]]


def blocks_to_plain(
    blocks: list[LayoutBlock],
    *,
    style: str,
    lead: str = "",
    footer_link: str = "",
) -> str:
    """style: toutiao | douban"""
    lines: list[str] = []
    if lead:
        if style == "toutiao":
            lines.append(f"📌 {lead}")
        else:
            lines.append(f"💡 {lead}")
        lines.append("")

    for block in blocks:
        if block.kind == "spacer":
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if block.kind == "heading":
            prefix = "▎" if style == "toutiao" else "◆"
            lines.append(f"{prefix} {block.text}")
            lines.append("")
            continue
        if block.kind == "paragraph":
            for para in _split_long_paragraph(block.text):
                lines.append(para)
            lines.append("")
            continue
        if block.kind == "bullets":
            if style == "toutiao":
                lines.append("🔹 划重点")
            else:
                lines.append("📎 要点")
            for item in block.items:
                lines.append(f"  · {item}")
            lines.append("")
            continue
        if block.kind == "quote":
            lines.append(f"「{block.text}」")
            lines.append("")
            continue
        if block.kind == "link":
            url = block.url or block.text
            if style == "toutiao":
                lines.append("🔗 详情")
                lines.append(url)
            else:
                lines.append("——")
                lines.append(f"原文：{url}")
            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    if footer_link and not any(b.kind == "link" for b in blocks):
        lines.append("")
        if style == "toutiao":
            lines.append("🔗 详情")
            lines.append(footer_link)
        else:
            lines.append("——")
            lines.append(f"原文：{footer_link}")

    if style == "toutiao" and lines:
        lines.append("")
        lines.append("💬 欢迎评论区聊聊你的看法。")

    text = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def blocks_to_html(blocks: list[LayoutBlock], *, lead: str = "", style: str = "toutiao") -> str:
    """供 contenteditable 粘贴：段落 <p>、要点 <ul>、强调 <strong>。"""
    parts: list[str] = []
    if lead:
        parts.append(f"<p><strong>{html.escape(lead)}</strong></p>")

    for block in blocks:
        if block.kind == "spacer":
            continue
        if block.kind == "heading":
            parts.append(f"<p><strong>{html.escape(block.text)}</strong></p>")
            continue
        if block.kind == "paragraph":
            for para in _split_long_paragraph(block.text):
                esc = html.escape(para)
                esc = re.sub(r"【([^】]+)】", r"<strong>\1</strong>", esc)
                parts.append(f"<p>{esc}</p>")
            continue
        if block.kind == "bullets":
            items = "".join(f"<li>{html.escape(i)}</li>" for i in block.items)
            parts.append(f"<ul>{items}</ul>")
            continue
        if block.kind == "link":
            url = html.escape(block.url or block.text)
            parts.append(f'<p><a href="{url}">{url}</a></p>')

    return "".join(parts)


def format_toutiao_micro(title: str, raw: str) -> str:
    """微头条：分段+小标题+要点+链接（粘贴/键入均友好）。"""
    body = raw or ""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if lines and lines[0] == (title or "").strip():
        body = "\n".join(lines[1:])
    blocks = parse_structured_body(body)
    if not blocks and body.strip():
        blocks = [LayoutBlock(kind="paragraph", text=_emphasize_plain(body))]
    lead = (title or "").strip() or _emphasize_plain(body[:40])
    footer = _extract_url(body)
    return blocks_to_plain(blocks, style="toutiao", lead=lead, footer_link=footer or "")[:2000]


def format_douban_note(title: str, raw: str) -> str:
    """豆瓣笔记正文（标题由发布页单独填写，此处不含标题行）。"""
    body = raw or ""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if lines and lines[0] == (title or "").strip():
        body = "\n".join(lines[1:])
    blocks = parse_structured_body(body)
    if not blocks and body.strip():
        blocks = [LayoutBlock(kind="paragraph", text=_emphasize_plain(body))]
    lead = ""
    footer = _extract_url(body)
    return blocks_to_plain(blocks, style="douban", lead=lead, footer_link=footer or "")[:2000]


def format_douban_note_html(title: str, raw: str) -> str:
    body = raw or ""
    if body.splitlines() and body.splitlines()[0].strip() == (title or "").strip():
        body = "\n".join(body.splitlines()[1:])
    blocks = parse_structured_body(body)
    return blocks_to_html(blocks, lead="", style="douban")
