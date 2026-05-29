"""内容赛道解析与存储。"""
from __future__ import annotations

from pathlib import Path

from pipeline.config import load_config
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.themes import resolve_theme, parse_themes


def test_resolve_theme_by_feed_kind() -> None:
    themes = parse_themes(None)
    assert resolve_theme({"feed_kind": "apps"}, themes) == "ai_monetize"
    assert resolve_theme({"feed_kind": "news"}, themes) == "ai_news"


def test_resolve_theme_by_category() -> None:
    themes = parse_themes(
        [
            {
                "id": "custom",
                "label": "定制",
                "categories": ["快讯"],
                "feed_kinds": [],
                "accounts": {},
            }
        ]
    )
    assert resolve_theme({"categories": ["快讯"]}, themes) == "custom"


def test_job_stores_theme_id(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.yaml")
    store = JobStore(tmp_path / "pipeline.db")
    ck = content_key_for_article(9)
    store.upsert_discovered(
        content_key=ck,
        article_id=9,
        snapshot={"id": 9, "feed_kind": "news"},
        theme_id="ai_news",
    )
    job = store.get_job(ck)
    assert job
    assert job["theme_id"] == "ai_news"


def test_pending_publish_filters_theme(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "pipeline.db")
    ck1 = content_key_for_article(1)
    ck2 = content_key_for_article(2)
    store.upsert_discovered(content_key=ck1, article_id=1, snapshot={"id": 1}, theme_id="ai_monetize")
    store.upsert_discovered(content_key=ck2, article_id=2, snapshot={"id": 2}, theme_id="ai_news")
    store.update_job(ck1, status="ready_to_publish")
    store.update_job(ck2, status="ready_to_publish")
    assert len(store.pending_publish("douyin", theme_id="ai_monetize")) == 1
    assert len(store.pending_publish("douyin", theme_id="ai_news")) == 1
