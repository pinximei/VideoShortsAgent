"""渲染槽位锁。"""
from __future__ import annotations

from pathlib import Path

from pipeline.render_lock import global_render_slot


def test_render_slot_acquire_release(tmp_path: Path) -> None:
    with global_render_slot(tmp_path, max_slots=1, wait_sec=5.0, poll_sec=0.2):
        lock = tmp_path / ".render_slots" / "slot_0.lock"
        assert lock.is_file()
    assert not lock.is_file()
