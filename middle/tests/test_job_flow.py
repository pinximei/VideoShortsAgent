"""任务状态与步骤流转。"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.config import PipelineConfig
from pipeline.db import JobStore
from pipeline.job_flow import (
    STATUS_COMPLETED,
    STATUS_DISCOVERED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
    STATUS_SKIPPED,
    STEP_DONE,
    STEP_FETCH,
    STEP_FILTER,
    STEP_LLM,
    STEP_PACK,
    STEP_READY,
    PUBLISH_CHANNELS,
)
from pipeline.models import content_key_for_article
from pipeline.orchestrator import run_pipeline


def _article(feed_kind: str = "apps", worth: int = 8) -> dict:
    p = Path(__file__).parent / "fixtures" / "article_detail.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["feed_kind"] = feed_kind
    data["replication_analysis"] = {"worth_score": worth}
    return data


@pytest.fixture()
def store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path / "pipeline.db")


def test_discovered_on_upsert(store: JobStore) -> None:
    ck = content_key_for_article(1)
    created = store.upsert_discovered(
        content_key=ck, article_id=1, snapshot={"id": 1, "feed_kind": "apps"}, theme_id="ai_monetize"
    )
    assert created
    job = store.get_job(ck)
    assert job["status"] == STATUS_DISCOVERED
    assert job["step"] == "discover"
    events = store.list_events(ck)
    assert events[0]["status"] == STATUS_DISCOVERED


def test_success_path_reaches_ready_to_publish(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path, feed_kinds=["apps"], llm_enabled=False, render_enabled=False)
    soul = MagicMock()
    soul.list_feed.return_value = [{"id": 10, "feed_kind": "apps", "replication_analysis": {"worth_score": 9}}]
    soul.get_article.return_value = _article()

    stats = run_pipeline(cfg, soul=soul)
    assert stats.discovered == 1
    assert stats.packed == 1

    store = JobStore(cfg.db_path)
    job = store.get_job(content_key_for_article(10))
    assert job["status"] == STATUS_READY
    assert job["step"] == STEP_READY
    assert job["theme_id"] == "ai_monetize"
    steps = [e["step"] for e in store.list_events(content_key_for_article(10))]
    assert STEP_FETCH in steps
    assert STEP_LLM in steps
    assert STEP_PACK in steps


def test_low_worth_skipped(store: JobStore, tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path, min_worth_score=9, feed_kinds=["apps"], llm_enabled=False)
    soul = MagicMock()
    soul.list_feed.return_value = []
    store.upsert_discovered(content_key=content_key_for_article(2), article_id=2, snapshot={"id": 2})
    soul.get_article.return_value = _article(worth=5)

    from pipeline.orchestrator import process_jobs

    stats = process_jobs(cfg, store, soul=soul)
    assert stats.skipped == 1
    job = store.get_job(content_key_for_article(2))
    assert job["status"] == STATUS_SKIPPED
    assert job["step"] == STEP_FILTER


def test_no_theme_skipped(store: JobStore, tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path, feed_kinds=["unknown_feed"], llm_enabled=False)
    soul = MagicMock()
    store.upsert_discovered(content_key=content_key_for_article(3), article_id=3, snapshot={"id": 3})
    soul.get_article.return_value = _article(feed_kind="unknown_feed")

    from pipeline.orchestrator import process_jobs

    stats = process_jobs(cfg, store, soul=soul)
    assert stats.skipped == 1
    job = store.get_job(content_key_for_article(3))
    assert job["status"] == STATUS_SKIPPED


def test_article_not_found_failed(store: JobStore, tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path, llm_enabled=False)
    soul = MagicMock()
    store.upsert_discovered(content_key=content_key_for_article(4), article_id=4, snapshot={"id": 4})
    soul.get_article.return_value = None

    from pipeline.orchestrator import process_jobs

    stats = process_jobs(cfg, store, soul=soul)
    assert stats.failed == 1
    job = store.get_job(content_key_for_article(4))
    assert job["status"] == STATUS_FAILED
    assert job["step"] == STEP_FETCH


def test_publish_marks_progress_to_completed(store: JobStore) -> None:
    ck = content_key_for_article(5)
    store.upsert_discovered(content_key=ck, article_id=5, snapshot={"id": 5})
    store.advance(ck, status=STATUS_READY, step=STEP_READY, message="ready")

    for i, ch in enumerate(PUBLISH_CHANNELS):
        created = store.mark_published(ck, ch)
        assert created is True
        job = store.get_job(ck)
        if i < len(PUBLISH_CHANNELS) - 1:
            assert job["status"] == STATUS_READY
        else:
            assert job["status"] == STATUS_COMPLETED
            assert job["step"] == STEP_DONE


def test_pending_only_ready_not_processing(store: JobStore) -> None:
    ck_ready = content_key_for_article(6)
    ck_proc = content_key_for_article(7)
    store.upsert_discovered(content_key=ck_ready, article_id=6, snapshot={"id": 6})
    store.upsert_discovered(content_key=ck_proc, article_id=7, snapshot={"id": 7})
    store.advance(ck_ready, status=STATUS_READY, step=STEP_READY)
    store.advance(ck_proc, status=STATUS_PROCESSING, step=STEP_LLM)

    pending = store.pending_publish("douyin")
    ids = {j["article_id"] for j in pending}
    assert 6 in ids
    assert 7 not in ids


def test_legacy_packed_status_in_pending_and_list(store: JobStore) -> None:
    ck = content_key_for_article(8)
    store.upsert_discovered(content_key=ck, article_id=8, snapshot={"id": 8})
    store.update_job(ck, status="packed")

    pending = store.pending_publish("xhs")
    assert any(j["article_id"] == 8 for j in pending)
    listed = store.list_jobs((STATUS_READY,))
    assert any(j["article_id"] == 8 for j in listed)


def test_ready_jobs_not_reprocessed(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path, llm_enabled=False)
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(9)
    store.upsert_discovered(content_key=ck, article_id=9, snapshot={"id": 9})
    store.advance(ck, status=STATUS_READY, step=STEP_READY, brief_hash="abc")

    soul = MagicMock()
    soul.get_article.return_value = _article()

    from pipeline.orchestrator import process_jobs

    stats = process_jobs(cfg, store, soul=soul)
    assert stats.packed == 0
    assert stats.failed == 0
    job = store.get_job(ck)
    assert job["status"] == STATUS_READY


def test_failed_job_retries(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path, feed_kinds=["apps"], llm_enabled=False, render_enabled=False)
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(11)
    store.upsert_discovered(content_key=ck, article_id=11, snapshot={"id": 11})
    store.advance(ck, status=STATUS_FAILED, step=STEP_FETCH, error="timeout")

    soul = MagicMock()
    soul.get_article.return_value = _article()

    from pipeline.orchestrator import process_jobs

    stats = process_jobs(cfg, store, soul=soul)
    assert stats.packed == 1
    job = store.get_job(ck)
    assert job["status"] == STATUS_READY
