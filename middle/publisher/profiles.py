"""每个账号独立持久化 Profile 目录，切换账号时复用同一目录以保留登录态。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.channel_registry import ChannelAccount


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def browser_root(data_dir: Path) -> Path:
    return data_dir / "browser"


def account_profile_dir(data_dir: Path, batch_id: str, account_id: str) -> Path:
    """固定路径：data/browser/{batch_id}/{account_id}/ — 禁止随机临时目录。"""
    return browser_root(data_dir) / batch_id / account_id


def session_meta_path(data_dir: Path, batch_id: str, account_id: str) -> Path:
    return account_profile_dir(data_dir, batch_id, account_id) / "session_meta.json"


def read_session_meta(data_dir: Path, batch_id: str, account_id: str) -> dict[str, Any]:
    path = session_meta_path(data_dir, batch_id, account_id)
    if not path.is_file():
        return {
            "account_id": account_id,
            "batch_id": batch_id,
            "status": "unknown",
            "last_check_at": None,
            "last_login_at": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_session_meta(
    data_dir: Path,
    batch_id: str,
    account_id: str,
    *,
    status: str,
    message: str = "",
    mark_login: bool = False,
) -> dict[str, Any]:
    path = session_meta_path(data_dir, batch_id, account_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = read_session_meta(data_dir, batch_id, account_id)
    now = _utc_now()
    meta["status"] = status
    meta["last_check_at"] = now
    meta["message"] = message
    if mark_login:
        meta["last_login_at"] = now
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def ensure_profile_dir(data_dir: Path, batch_id: str, account: ChannelAccount) -> Path:
    p = account_profile_dir(data_dir, batch_id, account.id)
    p.mkdir(parents=True, exist_ok=True)
    return p
