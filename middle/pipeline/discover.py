from __future__ import annotations

from typing import Any

from .themes import resolve_theme_from_snapshot
from .config import PipelineConfig
from .db import JobStore
from .models import RunStats, content_key_for_article
from .soul_client import SoulClient


def discover_from_soul(
    cfg: PipelineConfig,
    store: JobStore,
    soul: SoulClient | None = None,
) -> RunStats:
    """从 Soul 拉 feed，写入 jobs（discovered）。"""
    stats = RunStats()
    client = soul or SoulClient(cfg)
    items = client.list_feed()
    for card in items:
        article_id = card.get("id")
        if article_id is None:
            continue
        ck = content_key_for_article(int(article_id))
        snapshot: dict[str, Any] = {
            "id": article_id,
            "title": card.get("title"),
            "worth_score": (card.get("replication_analysis") or {}).get("worth_score"),
            "feed_kind": card.get("feed_kind"),
            "admin_source_key": card.get("admin_source_key"),
        }
        if store.upsert_discovered(
            content_key=ck,
            article_id=int(article_id),
            snapshot=snapshot,
            theme_id=resolve_theme_from_snapshot(snapshot, cfg.themes),
        ):
            stats.discovered += 1
        else:
            existing = store.get_job(ck)
            if existing and existing.get("status") in ("ready_to_publish", "completed", "packed", "rendered"):
                stats.deduped += 1
    return stats
