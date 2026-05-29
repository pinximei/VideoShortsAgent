"""双槽位无头浏览器池：slot_id ↔ batch_id 固定绑定，同槽位切换账号时换 Profile 目录。"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from pipeline.channel_registry import ChannelAccount

from .batches import PublisherConfig
from .profiles import ensure_profile_dir

_playwright = None
_lock = threading.Lock()


def _get_playwright():
    global _playwright
    from playwright.sync_api import sync_playwright

    if _playwright is None:
        _playwright = sync_playwright().start()
    return _playwright


class BrowserSlotRunner:
    """一个槽位 = 一个 batch_id = 当前最多一个 persistent context。"""

    def __init__(self, slot_id: int, batch_id: str, *, headless: bool = True) -> None:
        self.slot_id = slot_id
        self.batch_id = batch_id
        self.headless = headless
        self._context = None
        self._active_account_id: str | None = None
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            if self._context is not None:
                self._context.close()
                self._context = None
                self._active_account_id = None

    def run_with_account(
        self,
        data_dir: Path,
        account: ChannelAccount,
        fn: Callable[[Any], dict[str, Any]],
    ) -> dict[str, Any]:
        """切换账号时关闭旧 context，用同一账号固定 userDataDir 重新打开。"""
        profile_dir = ensure_profile_dir(data_dir, self.batch_id, account)
        with self._lock:
            if self._context is not None and self._active_account_id != account.id:
                self._context.close()
                self._context = None
                self._active_account_id = None

            if self._context is None:
                pw = _get_playwright()
                self._context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=self.headless,
                    locale="zh-CN",
                    viewport={"width": 1280, "height": 900},
                    args=["--disable-blink-features=AutomationControlled"],
                )
                self._active_account_id = account.id

            page = self._context.pages[0] if self._context.pages else self._context.new_page()
            return fn(page)

    def status(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "batch_id": self.batch_id,
            "active_account_id": self._active_account_id,
            "context_open": self._context is not None,
        }


class BrowserPool:
    """固定两个槽位，与 config.publisher.slots 一一对应。"""

    def __init__(self, publisher: PublisherConfig) -> None:
        self._runners: dict[int, BrowserSlotRunner] = {}
        for slot in publisher.slots:
            self._runners[slot.slot_id] = BrowserSlotRunner(
                slot.slot_id,
                slot.batch_id,
                headless=publisher.headless,
            )
        self._batch_to_slot = {s.batch_id: s.slot_id for s in publisher.slots}

    def runner_for_batch(self, batch_id: str) -> BrowserSlotRunner:
        slot_id = self._batch_to_slot.get(batch_id)
        if slot_id is None:
            raise ValueError(f"no browser slot for batch_id={batch_id}")
        return self._runners[slot_id]

    def status(self) -> list[dict[str, Any]]:
        return [r.status() for r in self._runners.values()]

    def close_all(self) -> None:
        for r in self._runners.values():
            r.close()


_pool: BrowserPool | None = None
_pool_cfg_id: int | None = None


def get_pool(publisher: PublisherConfig) -> BrowserPool:
    global _pool, _pool_cfg_id
    cfg_id = id(publisher)
    with _lock:
        if _pool is None or _pool_cfg_id != cfg_id:
            if _pool is not None:
                _pool.close_all()
            _pool = BrowserPool(publisher)
            _pool_cfg_id = cfg_id
        return _pool
