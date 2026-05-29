"""内容赛道（主题）：同一平台不同账号维护不同垂直内容。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PUBLISH_CHANNEL_IDS = ("douyin", "xhs", "toutiao", "douban")

DEFAULT_THEMES: list[dict[str, Any]] = [
    {
        "id": "ai_monetize",
        "label": "AI 变现",
        "description": "工具、副业、高价值复刻等变现向内容",
        "feed_kinds": ["apps"],
        "categories": [],
        "accounts": {
            "douyin": {"label": "抖音 · AI变现号"},
            "xhs": {"label": "小红书 · AI变现号"},
            "toutiao": {"label": "头条 · AI变现号"},
            "douban": {"label": "豆瓣 · AI变现号"},
        },
    },
    {
        "id": "ai_news",
        "label": "AI 资讯",
        "description": "AI 行业新闻、快讯与趋势解读",
        "feed_kinds": ["news"],
        "categories": [],
        "accounts": {
            "douyin": {"label": "抖音 · AI资讯号"},
            "xhs": {"label": "小红书 · AI资讯号"},
            "toutiao": {"label": "头条 · AI资讯号"},
            "douban": {"label": "豆瓣 · AI资讯号"},
        },
    },
]


@dataclass
class ThemeAccount:
    label: str = ""
    handle: str = ""
    note: str = ""


@dataclass
class Theme:
    id: str
    label: str
    description: str = ""
    feed_kinds: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    accounts: dict[str, ThemeAccount] = field(default_factory=dict)

    def account_label(self, channel: str) -> str:
        acc = self.accounts.get(channel)
        if acc and acc.label:
            return acc.label
        return f"{self.label} · {channel}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "feed_kinds": list(self.feed_kinds),
            "categories": list(self.categories),
            "accounts": {
                ch: {"label": a.label, "handle": a.handle, "note": a.note}
                for ch, a in self.accounts.items()
            },
        }


def parse_themes(raw: list[Any] | None) -> list[Theme]:
    if not raw:
        raw = DEFAULT_THEMES
    themes: list[Theme] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id") or "").strip()
        if not tid:
            continue
        accounts: dict[str, ThemeAccount] = {}
        for ch in PUBLISH_CHANNEL_IDS:
            cell = (item.get("accounts") or {}).get(ch) or {}
            if isinstance(cell, dict):
                accounts[ch] = ThemeAccount(
                    label=str(cell.get("label") or ""),
                    handle=str(cell.get("handle") or ""),
                    note=str(cell.get("note") or ""),
                )
        themes.append(
            Theme(
                id=tid,
                label=str(item.get("label") or tid),
                description=str(item.get("description") or ""),
                feed_kinds=[str(x) for x in (item.get("feed_kinds") or []) if x],
                categories=[str(x) for x in (item.get("categories") or []) if x],
                accounts=accounts,
            )
        )
    return themes or [Theme(id="default", label="默认", feed_kinds=["apps", "news"])]


def theme_by_id(themes: list[Theme], theme_id: str) -> Theme | None:
    for t in themes:
        if t.id == theme_id:
            return t
    return None


def all_feed_kinds(themes: list[Theme]) -> list[str]:
    kinds: list[str] = []
    for t in themes:
        for k in t.feed_kinds:
            if k not in kinds:
                kinds.append(k)
    return kinds or ["apps"]


def resolve_theme(article: dict[str, Any], themes: list[Theme]) -> str | None:
    """按 feed_kind、categories 匹配赛道；先精确后默认。"""
    fk = str(article.get("feed_kind") or "").strip()
    cats = {str(c).strip() for c in (article.get("categories") or []) if c}

    matched: list[Theme] = []
    for t in themes:
        if t.feed_kinds and fk and fk in t.feed_kinds:
            matched.append(t)
            continue
        if t.categories and cats.intersection(t.categories):
            matched.append(t)

    if len(matched) == 1:
        return matched[0].id
    if len(matched) > 1:
        # feed_kind 优先于 categories
        for t in matched:
            if t.feed_kinds and fk in t.feed_kinds:
                return t.id
        return matched[0].id

    # 仅 feed_kind 单主题兜底
    if fk:
        for t in themes:
            if t.feed_kinds == [fk]:
                return t.id

    if len(themes) == 1:
        return themes[0].id
    return None


def resolve_theme_from_snapshot(snapshot: dict[str, Any], themes: list[Theme]) -> str:
    tid = resolve_theme(snapshot, themes)
    if tid:
        return tid
    if themes:
        return themes[0].id
    return "default"
