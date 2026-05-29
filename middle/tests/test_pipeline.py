from __future__ import annotations

import json
from pathlib import Path

from pipeline.brief import build_brief, passes_filter
from pipeline.models import VideoBrief, brief_hash, content_key_for_article


def _fixture() -> dict:
    p = Path(__file__).parent / "fixtures" / "article_detail.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_content_key() -> None:
    assert content_key_for_article(870) == "aisoul:article:870"


def test_build_brief_from_fixture() -> None:
    article = _fixture()
    brief = build_brief(article, public_base_url="https://ai-trends.news")
    assert brief.article_id == 870
    assert brief.hook
    assert len(brief.talking_points) >= 2
    assert "ai-trends.news" in brief.cta
    assert brief.worth_score == 8


def test_brief_hash_stable() -> None:
    article = _fixture()
    b1 = build_brief(article, public_base_url="https://ai-trends.news")
    b2 = build_brief(article, public_base_url="https://ai-trends.news")
    assert b1.hash() == b2.hash()


def test_passes_filter() -> None:
    article = _fixture()
    ok, _ = passes_filter(article, min_worth=7, feed_kinds=["apps"])
    assert ok
    ok2, reason = passes_filter(article, min_worth=9, feed_kinds=["apps"])
    assert not ok2
    assert "worth" in reason


def test_dedup_same_hash(tmp_path: Path) -> None:
    from pipeline.db import JobStore

    store = JobStore(tmp_path / "t.db")
    ck = content_key_for_article(870)
    store.upsert_discovered(content_key=ck, article_id=870, snapshot={"id": 870})
    brief = build_brief(_fixture(), public_base_url="https://x")
    bh = brief.hash()
    store.update_job(ck, status="packed", brief_hash=bh, brief_json=brief.to_dict())
    assert store.should_skip_render(ck, bh)
    assert not store.should_skip_render(ck, "different_hash")


def test_publish_log_idempotent(tmp_path: Path) -> None:
    from pipeline.db import JobStore

    store = JobStore(tmp_path / "t.db")
    ck = content_key_for_article(1)
    assert store.mark_published(ck, "douyin")
    assert not store.mark_published(ck, "douyin")
    assert store.is_published(ck, "douyin")
