"""渠道账号配置 API 与持久化。"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pipeline.channel_config import get_overview, replace_accounts_for_slot
from pipeline.channel_registry import accounts_for
from pipeline.config import load_config


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        (Path(__file__).resolve().parents[1] / "config.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setenv("PIPELINE_CONFIG", str(cfg_path))
    import server.app as app_mod

    app_mod._cfg = None
    return TestClient(app_mod.app), cfg_path


def test_channel_config_overview(client) -> None:
    c, _ = client
    r = c.get("/api/v1/channel-config")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["sites"]
    assert data["channels"]
    assert "ai-trends-apps" in data["accounts_by_site_channel"]


def test_save_and_reload_accounts(client) -> None:
    c, cfg_path = client
    payload = {
        "site_code": "ai-trends-apps",
        "channel_id": "douyin",
        "accounts": [
            {
                "label": "抖音变现主号",
                "handle": "@monetize_main",
                "profile_url": "https://douyin.com/user/1",
                "enabled": True,
                "is_primary": True,
            }
        ],
    }
    r = c.put("/api/v1/channel-config/accounts", json=payload)
    assert r.status_code == 200
    assert r.json()["data"]["saved"] == 1

    cfg = load_config(cfg_path)
    rows = accounts_for(cfg.channel_accounts, site_code="ai-trends-apps", channel_id="douyin")
    assert len(rows) == 1
    assert rows[0].handle == "@monetize_main"
    theme = next(t for t in cfg.themes if t.id == "ai_monetize")
    assert theme.accounts["douyin"].handle == "@monetize_main"


def test_replace_accounts_for_slot(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        (Path(__file__).resolve().parents[1] / "config.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    cfg = replace_accounts_for_slot(
        cfg,
        site_code="ai-trends-news",
        channel_id="xhs",
        cards=[{"label": "资讯小红书", "handle": "@news_xhs", "is_primary": True}],
    )
    overview = get_overview(cfg)
    cards = overview["accounts_by_site_channel"]["ai-trends-news"]["xhs"]
    assert len(cards) == 1
    assert cards[0]["label"] == "资讯小红书"
