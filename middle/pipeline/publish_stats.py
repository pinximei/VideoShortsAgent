"""Pipeline：各渠道发布运营统计（视频/短文 + Soul 站内文章）。"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import PipelineConfig
from .db import JobStore
from .soul_client import SoulClient

CHANNEL_LABELS: dict[str, str] = {
    "ai-trends-news": "站内 · 资讯",
    "ai-trends-apps": "站内 · 应用",
    "douyin": "抖音",
    "xhs": "小红书",
    "toutiao": "今日头条",
    "douban": "豆瓣",
}

# 渠道内容形态：统计时区分文章 vs 视频
CHANNEL_KIND: dict[str, str] = {
    "douyin": "video",
    "xhs": "video",
    "toutiao": "article",
    "douban": "article",
    "ai-trends-news": "article",
    "ai-trends-apps": "article",
}


def _day_from_iso(iso: str) -> str:
    return (iso or "")[:10]


def _fetch_soul_daily(cfg: PipelineConfig, days: int) -> dict[str, Any]:
    client = SoulClient(cfg)
    try:
        return client._get_data("/api/public/v1/publishing/daily", {"days": days})
    except Exception:
        return {"daily": [], "categories": []}


def publishing_overview(cfg: PipelineConfig, store: JobStore, *, days: int = 30) -> dict[str, Any]:
    days = max(1, min(int(days), 90))
    soul = _fetch_soul_daily(cfg, days)

    # 本地已标记发布
    with store._conn() as conn:
        rows = conn.execute("SELECT content_key, channel, published_at, note FROM publish_log").fetchall()
    pub_rows = [dict(r) for r in rows]

    daily: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"articles": 0, "videos": 0})
    )
    category_counts: dict[str, int] = defaultdict(int)
    channel_last: dict[str, str | None] = {k: None for k in CHANNEL_LABELS}

    for r in pub_rows:
        ch = r["channel"]
        day = _day_from_iso(r["published_at"])
        if not day:
            continue
        kind = CHANNEL_KIND.get(ch, "article")
        if kind == "video":
            daily[day][ch]["videos"] += 1
        else:
            daily[day][ch]["articles"] += 1
        ts = r["published_at"]
        if ts and (not channel_last.get(ch) or ts > (channel_last.get(ch) or "")):
            channel_last[ch] = ts

    # 合并 Soul 站内
    for row in soul.get("daily") or []:
        d = row.get("date")
        if not d:
            continue
        for sk, cell in (row.get("sites") or {}).items():
            if sk not in daily[d]:
                daily[d][sk] = {"articles": 0, "videos": 0}
            daily[d][sk]["articles"] += int(cell.get("articles") or 0)

    for item in soul.get("categories") or []:
        cat = item.get("category")
        if cat:
            category_counts[str(cat)] += int(item.get("count") or 0)

    # 已打包未发布、待发
    jobs = store.list_jobs()
    packed = [j for j in jobs if j.get("status") in ("packed", "rendered")]
    pending_by_channel: dict[str, int] = {}
    for ch in ("douyin", "xhs", "toutiao", "douban"):
        pending_by_channel[ch] = len(store.pending_publish(ch))

    # 发布任务的分类（brief tags）
    pipeline_categories: dict[str, int] = defaultdict(int)
    published_keys = {(r["content_key"], r["channel"]) for r in pub_rows}
    for j in jobs:
        raw = j.get("brief_json")
        if not raw:
            continue
        try:
            brief = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            continue
        ck = j.get("content_key")
        for ch in ("douyin", "xhs", "toutiao", "douban"):
            if (ck, ch) in published_keys:
                for tag in brief.get("tags") or []:
                    pipeline_categories[str(tag)] += 1

    site_keys = list(CHANNEL_LABELS.keys())
    daily_series: list[dict[str, Any]] = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date().isoformat()
        sites_out: dict[str, Any] = {}
        for sk in site_keys:
            cell = daily.get(d, {}).get(sk, {"articles": 0, "videos": 0})
            sites_out[sk] = {
                "label": CHANNEL_LABELS[sk],
                "articles": int(cell["articles"]),
                "videos": int(cell["videos"]),
            }
        daily_series.append({"date": d, "sites": sites_out})

    today = datetime.now(timezone.utc).date().isoformat()
    today_sum = {"articles": 0, "videos": 0}
    for sk in site_keys:
        c = daily.get(today, {}).get(sk, {})
        today_sum["articles"] += int(c.get("articles") or 0)
        today_sum["videos"] += int(c.get("videos") or 0)

    return {
        "days": days,
        "summary": {
            "today_articles": today_sum["articles"],
            "today_videos": today_sum["videos"],
            "packed_ready": len(packed),
            "pending_publish": pending_by_channel,
        },
        "daily": daily_series,
        "categories": [
            {"category": k, "count": v} for k, v in sorted(category_counts.items(), key=lambda kv: -kv[1])
        ],
        "pipeline_categories": [
            {"category": k, "count": v} for k, v in sorted(pipeline_categories.items(), key=lambda kv: -kv[1])
        ],
        "channel_maintenance": [
            {
                "channel": ch,
                "label": CHANNEL_LABELS[ch],
                "last_published_at": channel_last.get(ch),
                "pending": pending_by_channel.get(ch, 0),
            }
            for ch in ("douyin", "xhs", "toutiao", "douban")
        ],
        "site_maintenance": soul.get("site_last_published")
        or [
            {"site_key": sk, "site_label": CHANNEL_LABELS[sk], "last_published_at": None}
            for sk in ("ai-trends-news", "ai-trends-apps")
        ],
    }
