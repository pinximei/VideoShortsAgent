"""站点（code）× 发布渠道 × 账号卡片 绑定注册表。"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from .themes import PUBLISH_CHANNEL_IDS, Theme, parse_themes

_ACCOUNT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

PLATFORM_CHANNELS: list[dict[str, str]] = [
    {"id": "douyin", "label": "抖音", "kind": "video"},
    {"id": "xhs", "label": "小红书", "kind": "video"},
    {"id": "toutiao", "label": "今日头条", "kind": "article"},
    {"id": "douban", "label": "豆瓣", "kind": "article"},
]

DEFAULT_SITES: list[dict[str, Any]] = [
    {
        "code": "ai-trends-apps",
        "label": "AI 变现站",
        "description": "Soul 应用/变现向内容站",
        "theme_id": "ai_monetize",
        "base_url": "https://ai-trends.news",
    },
    {
        "code": "ai-trends-news",
        "label": "AI 资讯站",
        "description": "Soul 资讯/快讯内容站",
        "theme_id": "ai_news",
        "base_url": "https://ai-trends.news",
    },
]


@dataclass
class Site:
    code: str
    label: str
    description: str = ""
    theme_id: str = ""
    base_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "description": self.description,
            "theme_id": self.theme_id,
            "base_url": self.base_url,
        }


@dataclass
class ChannelAccount:
    id: str
    site_code: str
    channel_id: str
    label: str = ""
    handle: str = ""
    profile_url: str = ""
    login_hint: str = ""
    note: str = ""
    enabled: bool = True
    is_primary: bool = False
    batch_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "site_code": self.site_code,
            "channel_id": self.channel_id,
            "batch_id": self.batch_id,
            "label": self.label,
            "handle": self.handle,
            "profile_url": self.profile_url,
            "login_hint": self.login_hint,
            "note": self.note,
            "enabled": self.enabled,
            "is_primary": self.is_primary,
        }


def new_account_id() -> str:
    return f"acc_{uuid.uuid4().hex[:12]}"


def parse_sites(raw: list[Any] | None, themes: list[Theme] | None = None) -> list[Site]:
    items = raw if raw else DEFAULT_SITES
    sites: list[Site] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        sites.append(
            Site(
                code=code,
                label=str(item.get("label") or code),
                description=str(item.get("description") or ""),
                theme_id=str(item.get("theme_id") or ""),
                base_url=str(item.get("base_url") or ""),
            )
        )
    if sites:
        return sites
    # 从 themes 推导默认站点
    theme_list = themes or parse_themes(None)
    out: list[Site] = []
    for t in theme_list:
        code = f"ai-trends-{t.feed_kinds[0]}" if t.feed_kinds else f"site-{t.id}"
        out.append(Site(code=code, label=t.label, theme_id=t.id))
    return out


def parse_channel_accounts(
    raw: list[Any] | None,
    *,
    sites: list[Site] | None = None,
    batches: list[Any] | None = None,
) -> list[ChannelAccount]:
    if not raw:
        return []
    accounts: list[ChannelAccount] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        aid = str(item.get("id") or "").strip() or new_account_id()
        site_code = str(item.get("site_code") or "").strip()
        channel_id = str(item.get("channel_id") or "").strip()
        if not site_code or channel_id not in PUBLISH_CHANNEL_IDS:
            continue
        batch_id = str(item.get("batch_id") or "").strip()
        if not batch_id and batches:
            site = site_by_code(sites or [], site_code)
            if site:
                for b in batches:
                    bid = getattr(b, "batch_id", None) or (b.get("batch_id") if isinstance(b, dict) else None)
                    sc = getattr(b, "site_code", None) or (b.get("site_code") if isinstance(b, dict) else None)
                    if bid and sc == site_code:
                        batch_id = str(bid)
                        break
        accounts.append(
            ChannelAccount(
                id=aid,
                site_code=site_code,
                channel_id=channel_id,
                batch_id=batch_id,
                label=str(item.get("label") or ""),
                handle=str(item.get("handle") or ""),
                profile_url=str(item.get("profile_url") or ""),
                login_hint=str(item.get("login_hint") or ""),
                note=str(item.get("note") or ""),
                enabled=bool(item.get("enabled", True)),
                is_primary=bool(item.get("is_primary", False)),
            )
        )
    return accounts


def migrate_accounts_from_themes(themes: list[Theme], sites: list[Site]) -> list[ChannelAccount]:
    """将旧 themes.accounts 迁移为 channel_accounts 卡片。"""
    site_by_theme = {s.theme_id: s for s in sites if s.theme_id}
    accounts: list[ChannelAccount] = []
    for theme in themes:
        site = site_by_theme.get(theme.id)
        if not site:
            continue
        for ch in PUBLISH_CHANNEL_IDS:
            acc = theme.accounts.get(ch)
            if not acc or not (acc.label or acc.handle or acc.note):
                continue
            accounts.append(
                ChannelAccount(
                    id=new_account_id(),
                    site_code=site.code,
                    channel_id=ch,
                    label=acc.label,
                    handle=acc.handle,
                    note=acc.note,
                    enabled=True,
                    is_primary=True,
                )
            )
    return accounts


def site_by_code(sites: list[Site], code: str) -> Site | None:
    for s in sites:
        if s.code == code:
            return s
    return None


def site_for_theme(sites: list[Site], theme_id: str) -> Site | None:
    for s in sites:
        if s.theme_id == theme_id:
            return s
    return None


def accounts_for(
    accounts: list[ChannelAccount],
    *,
    site_code: str,
    channel_id: str,
    enabled_only: bool = False,
) -> list[ChannelAccount]:
    rows = [
        a
        for a in accounts
        if a.site_code == site_code and a.channel_id == channel_id and (not enabled_only or a.enabled)
    ]
    rows.sort(key=lambda a: (not a.is_primary, a.label or a.id))
    return rows


def primary_account_label(
    accounts: list[ChannelAccount],
    sites: list[Site],
    *,
    theme_id: str,
    channel_id: str,
    fallback: str = "",
) -> str:
    site = site_for_theme(sites, theme_id)
    if not site:
        return fallback
    rows = accounts_for(accounts, site_code=site.code, channel_id=channel_id, enabled_only=True)
    if not rows:
        return fallback
    primary = next((a for a in rows if a.is_primary), rows[0])
    return primary.label or primary.handle or fallback


def normalize_primary_flags(accounts: list[ChannelAccount], *, site_code: str, channel_id: str) -> None:
    """同一 site+channel 至多一个主账号；若无主账号则第一个 enabled 为主。"""
    scoped = [a for a in accounts if a.site_code == site_code and a.channel_id == channel_id]
    primaries = [a for a in scoped if a.is_primary and a.enabled]
    if len(primaries) > 1:
        for a in primaries[1:]:
            a.is_primary = False
    if not any(a.is_primary and a.enabled for a in scoped):
        for a in scoped:
            if a.enabled:
                a.is_primary = True
                break


def validate_account_payload(data: dict[str, Any], sites: list[Site]) -> ChannelAccount:
    site_code = str(data.get("site_code") or "").strip()
    channel_id = str(data.get("channel_id") or "").strip()
    if not site_by_code(sites, site_code):
        raise ValueError(f"unknown site_code: {site_code}")
    if channel_id not in PUBLISH_CHANNEL_IDS:
        raise ValueError(f"invalid channel_id: {channel_id}")
    aid = str(data.get("id") or "").strip() or new_account_id()
    if not _ACCOUNT_ID_RE.match(aid):
        raise ValueError("invalid account id")
    return ChannelAccount(
        id=aid,
        site_code=site_code,
        channel_id=channel_id,
        label=str(data.get("label") or "").strip(),
        handle=str(data.get("handle") or "").strip(),
        profile_url=str(data.get("profile_url") or "").strip(),
        login_hint=str(data.get("login_hint") or "").strip(),
        note=str(data.get("note") or "").strip(),
        enabled=bool(data.get("enabled", True)),
        is_primary=bool(data.get("is_primary", False)),
        batch_id=str(data.get("batch_id") or "").strip(),
    )


def channel_config_overview(
    sites: list[Site],
    accounts: list[ChannelAccount],
) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for site in sites:
        grouped[site.code] = {}
        for ch in PLATFORM_CHANNELS:
            cid = ch["id"]
            grouped[site.code][cid] = [
                a.to_dict() for a in accounts_for(accounts, site_code=site.code, channel_id=cid)
            ]
    return {
        "sites": [s.to_dict() for s in sites],
        "channels": list(PLATFORM_CHANNELS),
        "accounts_by_site_channel": grouped,
    }
