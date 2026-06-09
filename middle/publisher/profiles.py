"""每个账号独立持久化 Profile；batch 可配置 shared_profile_id 四渠道共用一个浏览器。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.channel_registry import ChannelAccount

if TYPE_CHECKING:
    from .batches import PublisherConfig


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def browser_root(data_dir: Path) -> Path:
    return data_dir / "browser"


def account_profile_dir(data_dir: Path, batch_id: str, account_id: str) -> Path:
    """固定路径：data/browser/{batch_id}/{account_id}/ — 禁止随机临时目录。"""
    return browser_root(data_dir) / batch_id / account_id


def profile_storage_id(
    batch_id: str,
    account: ChannelAccount,
    publisher: PublisherConfig | None = None,
) -> str:
    """逻辑账号 id → 磁盘 Profile 目录名（共享时四渠道相同）。"""
    if publisher:
        batch = publisher.batch_by_id(batch_id)
        if batch and batch.shared_profile_id:
            return batch.shared_profile_id
    return account.id


def resolve_profile_dir(
    data_dir: Path,
    batch_id: str,
    account: ChannelAccount,
    publisher: PublisherConfig | None = None,
) -> Path:
    return account_profile_dir(
        data_dir, batch_id, profile_storage_id(batch_id, account, publisher)
    )


def session_meta_path(data_dir: Path, batch_id: str, account_id: str) -> Path:
    return account_profile_dir(data_dir, batch_id, account_id) / "session_meta.json"


def read_session_meta(data_dir: Path, batch_id: str, account_id: str) -> dict:
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
) -> dict:
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


def ensure_profile_dir(
    data_dir: Path,
    batch_id: str,
    account: ChannelAccount,
    publisher: PublisherConfig | None = None,
) -> Path:
    p = resolve_profile_dir(data_dir, batch_id, account, publisher)
    p.mkdir(parents=True, exist_ok=True)
    return p
