from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pipeline.db import JobStore
from pipeline.models import content_key_for_article


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "t.db"
    out = tmp_path / "output"
    out.mkdir()
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        f"""
soul:
  base_url: "https://example.com"
paths:
  data_dir: "{tmp_path.as_posix()}"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PIPELINE_CONFIG", str(cfg_path))
    import server.app as app_mod

    app_mod._cfg = None
    return TestClient(app_mod.app)


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["code"] == 0


def test_jobs_and_publish(client: TestClient, tmp_path: Path) -> None:
    from pipeline.channel_registry import ChannelAccount
    from pipeline.config import load_config
    from pipeline.publish_guard import build_publish_bindings

    cfg_path = tmp_path / "config.yaml"
    example = (Path(__file__).resolve().parents[1] / "config.example.yaml").read_text(encoding="utf-8")
    cfg_path.write_text(
        example.replace('data_dir: "./data"', f'data_dir: "{tmp_path.as_posix()}"'),
        encoding="utf-8",
    )
    import server.app as app_mod

    app_mod._cfg = None
    cfg = load_config(cfg_path)
    cfg.data_dir = tmp_path
    cfg.channel_accounts.append(
        ChannelAccount(
            id="acc_test_douyin",
            site_code="ai-trends-apps",
            channel_id="douyin",
            batch_id="batch_a",
            label="测试抖音",
            enabled=True,
            is_primary=True,
        )
    )
    bindings = build_publish_bindings(cfg, "ai_monetize")
    app_mod._cfg = cfg
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(42)
    store.upsert_discovered(content_key=ck, article_id=42, snapshot={"id": 42, "title": "T"}, theme_id="ai_monetize")
    store.update_job(
        ck,
        status="ready_to_publish",
        theme_id="ai_monetize",
        brief_json={"hook": "h", "talking_points": ["a"], "publish_bindings": bindings},
    )

    r = client.get("/api/v1/jobs")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1

    aid = bindings["channels"]["douyin"]["account_id"]
    r2 = client.post(
        "/api/v1/publish",
        json={"article_id": 42, "channel": "douyin", "account_id": aid},
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["created"] is True

    r_bad = client.post(
        "/api/v1/publish",
        json={"article_id": 42, "channel": "xhs", "account_id": aid},
    )
    assert r_bad.status_code == 409

    r3 = client.get("/api/v1/pending/douyin")
    assert r3.json()["data"] == []


def test_trigger_run_conflict(client: TestClient) -> None:
    import server.state as st

    st.set_running(True)
    try:
        r = client.post("/api/v1/run")
        assert r.status_code == 409
    finally:
        st.set_running(False)
