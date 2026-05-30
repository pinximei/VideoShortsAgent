"""跨进程渲染槽位锁：限制同时进行的 VSA 出片任务数。"""
from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import IO, Iterator


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def _slot_stale(path: Path, *, max_age_sec: float = 7200.0) -> bool:
    if not path.is_file():
        return True
    if time.time() - path.stat().st_mtime > max_age_sec:
        return True
    try:
        pid = int(path.read_text(encoding="utf-8").splitlines()[0].strip())
    except (ValueError, OSError):
        return True
    return not _pid_alive(pid)


def _cleanup_stale(lock_dir: Path, *, max_slots: int, max_age_sec: float) -> None:
    for i in range(max_slots):
        p = lock_dir / f"slot_{i}.lock"
        if _slot_stale(p, max_age_sec=max_age_sec):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass


def _try_acquire(lock_dir: Path, slot_id: int) -> IO[str] | None:
    path = lock_dir / f"slot_{slot_id}.lock"
    if path.is_file() and _slot_stale(path):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        handle = open(path, "x", encoding="utf-8")
    except FileExistsError:
        return None
    handle.write(f"{os.getpid()}\n{time.time():.0f}\n")
    handle.flush()
    return handle


@contextlib.contextmanager
def global_render_slot(
    data_dir: Path,
    *,
    max_slots: int = 1,
    wait_sec: float = 7200.0,
    poll_sec: float = 2.0,
) -> Iterator[None]:
    """占用一个渲染槽；max_slots<=0 时不加锁。"""
    if max_slots <= 0:
        yield
        return

    lock_dir = Path(data_dir) / ".render_slots"
    lock_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + wait_sec
    handle: IO[str] | None = None
    slot_path: Path | None = None

    try:
        while time.time() < deadline:
            _cleanup_stale(lock_dir, max_slots=max_slots, max_age_sec=wait_sec)
            for i in range(max_slots):
                handle = _try_acquire(lock_dir, i)
                if handle is not None:
                    slot_path = lock_dir / f"slot_{i}.lock"
                    break
            if handle is not None:
                yield
                return
            time.sleep(poll_sec)
        raise TimeoutError(f"render slot unavailable after {wait_sec:.0f}s")
    finally:
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
        if slot_path is not None:
            try:
                slot_path.unlink(missing_ok=True)
            except OSError:
                pass
