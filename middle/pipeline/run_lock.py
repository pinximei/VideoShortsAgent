"""Pipeline 全局运行锁（API 手动触发与内置调度共用）。"""
from __future__ import annotations

import threading
from dataclasses import asdict
from typing import Any

from .models import RunStats

_lock = threading.Lock()
_running = False
_last_run: dict[str, Any] | None = None
_last_error: str | None = None


def run_status() -> dict[str, Any]:
    with _lock:
        return {
            "running": _running,
            "last_run": _last_run,
            "last_error": _last_error,
        }


def record_run(stats: RunStats, *, error: str | None = None) -> None:
    global _last_run, _last_error
    with _lock:
        _last_run = asdict(stats)
        _last_error = error


def try_acquire_run() -> bool:
    global _running
    with _lock:
        if _running:
            return False
        _running = True
        return True


def release_run() -> None:
    global _running
    with _lock:
        _running = False


def set_running(value: bool) -> None:
    """测试或维护用：强制设置运行标志。"""
    global _running
    with _lock:
        _running = value
