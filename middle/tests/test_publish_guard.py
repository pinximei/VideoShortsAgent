"""防发串号：冻结绑定与发布校验。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.channel_registry import ChannelAccount
from pipeline.config import PipelineConfig, load_config
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.publish_guard import (
    PublishGuardError,
    build_publish_bindings,
    refresh_job_bindings,
    validate_publish_target,
)


def _cfg_with_accounts(tmp_path: Path) -> PipelineConfig:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        (Path(__file__).resolve().parents[1] / "config.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    cfg.data_dir = tmp_path / "data"
    cfg.channel_accounts.extend(
        [
            ChannelAccount(
                id="acc_apps_douyin",
                site_code="ai-trends-apps",
                channel_id="douyin",
                batch_id="batch_a",
                label="变现抖音号",
                enabled=True,
                is_primary=True,
            ),
            ChannelAccount(
                id="acc_news_douyin",
                site_code="ai-trends-news",
                channel_id="douyin",
                batch_id="batch_b",
                label="资讯抖音号",
                enabled=True,
                is_primary=True,
            ),
        ]
    )
    return cfg


def test_build_bindings_per_channel(tmp_path: Path) -> None:
    cfg = _cfg_with_accounts(tmp_path)
    b = build_publish_bindings(cfg, "ai_monetize")
    assert b["batch_id"] == "batch_a"
    assert b["channels"]["douyin"]["account_id"] == "acc_apps_douyin"


def test_reject_wrong_account(tmp_path: Path) -> None:
    cfg = _cfg_with_accounts(tmp_path)
    job = {
        "theme_id": "ai_monetize",
        "brief_json": json.dumps(
            {"publish_bindings": build_publish_bindings(cfg, "ai_monetize")},
            ensure_ascii=False,
        ),
    }
    with pytest.raises(PublishGuardError) as exc:
        validate_publish_target(cfg, job, "douyin", "acc_news_douyin")
    assert exc.value.code == "account_mismatch"


def test_reject_wrong_theme_in_bindings(tmp_path: Path) -> None:
    cfg = _cfg_with_accounts(tmp_path)
    bindings = build_publish_bindings(cfg, "ai_news")
    job = {"theme_id": "ai_monetize", "brief_json": json.dumps({"publish_bindings": bindings})}
    with pytest.raises(PublishGuardError) as exc:
        validate_publish_target(cfg, job, "douyin", "acc_news_douyin")
    assert exc.value.code == "theme_binding_mismatch"


def test_accept_correct_account(tmp_path: Path) -> None:
    cfg = _cfg_with_accounts(tmp_path)
    job = {
        "theme_id": "ai_monetize",
        "brief_json": json.dumps(
            {"publish_bindings": build_publish_bindings(cfg, "ai_monetize")},
            ensure_ascii=False,
        ),
    }
    ch, acc, _ = validate_publish_target(cfg, job, "douyin", None)
    assert acc.id == "acc_apps_douyin"
    assert ch["batch_id"] == "batch_a"


def test_orchestrator_writes_bindings(tmp_path: Path) -> None:
    from unittest.mock import MagicMock

    from pipeline.orchestrator import run_pipeline

    cfg = _cfg_with_accounts(tmp_path)
    cfg.llm_enabled = False
    cfg.render_enabled = False
    soul = MagicMock()
    soul.list_feed.return_value = [
        {"id": 50, "feed_kind": "apps", "replication_analysis": {"worth_score": 9}}
    ]
    article = json.loads(
        (Path(__file__).parent / "fixtures" / "article_detail.json").read_text(encoding="utf-8")
    )
    article["id"] = 50
    soul.get_article.return_value = article

    run_pipeline(cfg, soul=soul)
    store = JobStore(cfg.db_path)
    job = store.get_job(content_key_for_article(50))
    brief = json.loads(job["brief_json"])
    bindings = brief.get("publish_bindings") or {}
    if bindings.get("channels", {}).get("douyin"):
        assert bindings["channels"]["douyin"]["account_id"] == "acc_apps_douyin"
    else:
        assert bindings.get("warning") or bindings.get("channels") == {}


def test_refresh_bindings_on_theme_change(tmp_path: Path) -> None:
    cfg = _cfg_with_accounts(tmp_path)
    old = build_publish_bindings(cfg, "ai_monetize")
    new_brief = refresh_job_bindings(cfg, "ai_news", {"hook": "x", "publish_bindings": old})
    assert new_brief["publish_bindings"]["batch_id"] == "batch_b"
