"""兼容层：运行状态由 pipeline.run_lock 提供。"""
from __future__ import annotations

from pipeline.models import RunStats
from pipeline.run_lock import (
    record_run as _record_run,
    release_run,
    run_status,
    set_running,
    try_acquire_run,
)

__all__ = [
    "run_status",
    "record_run",
    "try_acquire_run",
    "release_run",
    "set_running",
]


def record_run(stats: RunStats, *, error: str | None = None) -> None:
    _record_run(stats, error=error)
