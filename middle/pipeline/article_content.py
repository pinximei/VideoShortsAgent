"""从 Soul 文章抽取实质正文，识别「仅链接无内容」的占位稿。"""
from __future__ import annotations

import re
from typing import Any

_URL_RE = re.compile(r"https?://[^\s\]\)\"'<>]+|www\.[^\s\]\)\"'<>]+", re.I)
# 常见占位摘要
_PLACEHOLDER_PATTERNS = (
    re.compile(r"^HTTP\s*\d{3}\s*$", re.I),
    re.compile(r"^返回列表"),
    re.compile(r"^详见原文"),
    re.compile(r"^原文链接"),
    re.compile(r"^点击.*查看", re.I),
)

MIN_SUBSTANTIVE_CHARS = 60
MIN_TALKING_POINT_CHARS = 12


def _strip_md_noise(text: str) -> str:
    s = (text or "").strip()
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[#*_`>\[\]]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def plain_without_urls(text: str) -> str:
    s = _strip_md_noise(text)
    s = _URL_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def substantive_char_count(text: str) -> int:
    return len(plain_without_urls(text))


def is_placeholder_summary(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True
    if substantive_char_count(s) < 20:
        return True
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.search(s):
            return True
    # 整段几乎全是 URL
    if len(s) > 30 and substantive_char_count(s) < 15:
        return True
    return False


def collect_article_text(article: dict[str, Any], *, max_chars: int = 12000) -> str:
    """合并 article_body、body、tabs、复刻分析等可读字段。"""
    parts: list[str] = []

    article_body = (article.get("article_body") or "").strip()
    if article_body:
        parts.append(article_body)

    body = (article.get("body") or "").strip()
    if body and body not in article_body:
        parts.append(body)

    for tab in article.get("tabs") or []:
        if not isinstance(tab, dict):
            continue
        label = (tab.get("label") or "").strip()
        summ = (tab.get("summary") or "").strip()
        bmd = (tab.get("body_md") or "").strip()
        if summ:
            parts.append(f"【{label}】{summ}" if label else summ)
        if bmd and bmd != summ:
            parts.append(bmd)

    summ = (article.get("summary") or article.get("card_description") or "").strip()
    if summ and summ not in "\n".join(parts):
        parts.append(summ)

    repl = article.get("replication_analysis") or {}
    if isinstance(repl, dict):
        for key in ("value_summary", "verdict", "replication_tier"):
            v = str(repl.get(key) or "").strip()
            if v:
                parts.append(v)
        mp = repl.get("market_position") or {}
        if isinstance(mp, dict):
            for key in ("monetization_hypothesis", "positioning", "target_user"):
                v = str(mp.get(key) or "").strip()
                if v:
                    parts.append(v)
        for tab in repl.get("tabs") or repl.get("tab_summaries") or []:
            if isinstance(tab, dict):
                parts.append(str(tab.get("summary") or ""))
                parts.append(str(tab.get("body_md") or ""))

    blob = "\n\n".join(p for p in parts if p and p.strip())
    if len(blob) > max_chars:
        blob = blob[:max_chars]
    return blob


def content_quality_report(article: dict[str, Any]) -> dict[str, Any]:
    blob = collect_article_text(article)
    plain = plain_without_urls(blob)
    title = (article.get("title") or "").strip()
    src = (article.get("source_original_url") or "").strip()
    tab_count = len(article.get("tabs") or [])
    return {
        "substantive_chars": len(plain),
        "total_chars": len(blob),
        "tab_count": tab_count,
        "has_body": bool((article.get("body") or "").strip()),
        "title": title[:120],
        "source_url": src[:200],
        "preview": plain[:240],
    }


def article_has_substantive_content(article: dict[str, Any]) -> tuple[bool, str]:
    """
    判断是否具备可加工的实质内容（非仅标题+外链）。
    返回 (ok, reason)。
    """
    report = content_quality_report(article)
    n = report["substantive_chars"]
    if n >= MIN_SUBSTANTIVE_CHARS:
        return True, ""

    title_plain = plain_without_urls(report["title"])
    if n < MIN_SUBSTANTIVE_CHARS and len(title_plain) >= 10 and report["tab_count"] == 0 and not report["has_body"]:
        return False, (
            f"仅链接/标题无正文（实质字数 {n}<{MIN_SUBSTANTIVE_CHARS}），"
            f"请在 Soul 补全 tabs 或正文后再同步；原文 {report['source_url'] or '—'}"
        )
    if is_placeholder_summary(article.get("summary") or "") and n < MIN_SUBSTANTIVE_CHARS:
        return False, (
            f"摘要为占位/链接（实质字数 {n}），跳过；"
            f"source={article.get('admin_source_key') or '?'}"
        )
    return False, (
        f"正文过短（实质字数 {n}<{MIN_SUBSTANTIVE_CHARS}），"
        "可能仅为链接卡片，已跳过避免生成空文案"
    )


def extract_talking_point_candidates(article: dict[str, Any], *, max_points: int = 5) -> list[str]:
    """从全文抽取要点候选（优先标准 tab 标签，否则按段落）。"""
    preferred_labels = (
        "描述",
        "变现评估",
        "数据支撑",
        "全文",
        "详情",
        "产品",
        "亮点",
        "为什么火",
    )
    points: list[str] = []

    for label in preferred_labels:
        for tab in article.get("tabs") or []:
            if not isinstance(tab, dict):
                continue
            if (tab.get("label") or "").strip() != label:
                continue
            for field in ("summary", "body_md"):
                raw = str(tab.get(field) or "").strip()
                if not raw:
                    continue
                plain = plain_without_urls(raw)
                if len(plain) >= MIN_TALKING_POINT_CHARS and plain not in points:
                    points.append(plain[:280])
            if len(points) >= max_points:
                return points[:max_points]

    blob = collect_article_text(article)
    for chunk in re.split(r"\n{2,}|(?=【)", blob):
        plain = plain_without_urls(chunk)
        if len(plain) >= MIN_TALKING_POINT_CHARS and plain not in points:
            points.append(plain[:280])
        if len(points) >= max_points:
            break

    return points[:max_points]
