"""Pipeline 发布运营统计。"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.publish_stats import publishing_overview


def test_publishing_overview_merges_local_publish(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path)
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(1)
    store.upsert_discovered(content_key=ck, article_id=1, snapshot={"id": 1})
    store.update_job(
        ck,
        status="packed",
        theme_id="ai_monetize",
        brief_json={"tags": ["AI工具", "副业"]},
    )
    store.mark_published(ck, "douyin", "test")

    out = publishing_overview(cfg, store, days=7)
    assert out["summary"]["today_videos"] >= 1
    assert out["channel_maintenance"]
    ch = next(
        c
        for c in out["channel_maintenance"]
        if c["channel"] == "douyin" and c.get("theme_id") == "ai_monetize"
    )
    assert ch["last_published_at"]
