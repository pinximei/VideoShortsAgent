"""双批次浏览器与固定脚本路由。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.config import load_config
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from publisher.batches import parse_publisher_config
from pipeline.channel_registry import ChannelAccount
from publisher.profiles import account_profile_dir, profile_storage_id, resolve_profile_dir
from publisher.runner import PublishRequest, publisher_overview
from publisher.scripts.registry import PUBLISH_SCRIPTS, get_publish_script


def test_two_fixed_slots_and_batches() -> None:
    pub = parse_publisher_config(None)
    assert len(pub.slots) == 2
    assert len(pub.batches) == 2
    assert pub.slot_for_batch("batch_a").slot_id == 1
    assert pub.slot_for_batch("batch_b").slot_id == 2
    assert pub.batch_for_theme("ai_monetize").batch_id == "batch_a"
    assert pub.batch_for_theme("ai_news").batch_id == "batch_b"


def test_profile_path_stable_per_account(tmp_path: Path) -> None:
    p = account_profile_dir(tmp_path, "batch_a", "acc_test")
    p2 = account_profile_dir(tmp_path, "batch_a", "acc_test")
    assert p == p2
    assert "batch_a" in str(p) and "acc_test" in str(p)


def test_shared_profile_id_for_batch_b() -> None:
    pub = parse_publisher_config(
        {
            "batches": [
                {
                    "batch_id": "batch_b",
                    "site_code": "ai-trends-news",
                    "theme_id": "ai_news",
                    "shared_profile_id": "acc_ai_news_shared",
                }
            ],
            "slots": [{"slot_id": 2, "batch_id": "batch_b"}],
        }
    )
    acc = ChannelAccount(
        id="acc_ai_news_xhs",
        site_code="ai-trends-news",
        channel_id="xhs",
        batch_id="batch_b",
    )
    assert profile_storage_id("batch_b", acc, pub) == "acc_ai_news_shared"
    p = resolve_profile_dir(Path("/tmp/x"), "batch_b", acc, pub)
    assert "acc_ai_news_shared" in str(p)


def test_publish_script_registry_no_llm() -> None:
    assert "douyin" in PUBLISH_SCRIPTS
    script = get_publish_script("douyin")
    assert script.fixed_steps
    assert "open_creator_upload" in script.fixed_steps
    assert "wait_publish_result" in script.fixed_steps
    assert "toutiao" in PUBLISH_SCRIPTS
    assert "douban" in PUBLISH_SCRIPTS


def test_publisher_overview_structure(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        (Path(__file__).resolve().parents[1] / "config.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    out = publisher_overview(cfg)
    assert len(out["slots"]) == 2
    assert out["browser_pool"]
    assert "大模型" in out["note"]


def test_dry_run_publish_routes_batch(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        (Path(__file__).resolve().parents[1] / "config.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    cfg.data_dir = tmp_path / "data"
    from pipeline.channel_registry import ChannelAccount

    cfg.channel_accounts.append(
        ChannelAccount(
            id="acc_test_douyin",
            site_code="ai-trends-apps",
            channel_id="douyin",
            batch_id="batch_a",
            label="测试抖音号",
            enabled=True,
            is_primary=True,
        )
    )
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(100)
    store.upsert_discovered(content_key=ck, article_id=100, snapshot={"id": 100}, theme_id="ai_monetize")
    bindings = __import__("pipeline.publish_guard", fromlist=["build_publish_bindings"]).build_publish_bindings(
        cfg, "ai_monetize"
    )
    store.update_job(
        ck,
        status="ready_to_publish",
        brief_json={"publish_bindings": bindings},
    )
    task = cfg.output_root / "100"
    (task / "videos").mkdir(parents=True)
    (task / "videos" / "douyin.mp4").write_bytes(b"x" * 60_000)
    (task / "publish").mkdir(parents=True)
    (task / "publish" / "douyin_title.txt").write_text("title", encoding="utf-8")

    from publisher.runner import publish_content

    result = publish_content(
        cfg,
        PublishRequest(article_id=100, channel_id="douyin", dry_run=True),
    )
    assert result.ok
    assert result.batch_id == "batch_a"
    assert result.slot_id == 1
