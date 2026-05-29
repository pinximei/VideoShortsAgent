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
    from pipeline.config import load_config

    cfg_path = tmp_path / "config.yaml"
    store = JobStore(load_config(cfg_path).db_path)
    ck = content_key_for_article(42)
    store.upsert_discovered(content_key=ck, article_id=42, snapshot={"id": 42, "title": "T"})
    store.update_job(ck, status="packed", brief_json={"hook": "h", "talking_points": ["a"]})

    r = client.get("/api/v1/jobs")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 1

    r2 = client.post("/api/v1/publish", json={"article_id": 42, "channel": "douyin"})
    assert r2.status_code == 200
    assert r2.json()["data"]["created"] is True

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
