#!/usr/bin/env python3
"""删除本地测试/成片中间产物（reports、_slides_work、验收库等），不碰源码。"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 整目录删除（保留 .gitkeep）
DIR_TARGETS = (
    ROOT / "reports",
    ROOT / "research" / "motion" / "github_daily" / "verify_g20",
    ROOT / "verify_gv20",
    ROOT / "data" / "output",
)

# 通配清理
GLOB_PATTERNS = (
    "**/videos/_slides_work*",
    "**/videos/_audit_*",
    "**/flow1_v20_audio",
    "**/flow2_task",
    "_*.db",
    "*.db",
    "_test_result.txt",
    "reports_*.log",
    "_gv20_*.log",
    "_slides_*.log",
    "_platform_*.log",
)


def _rm_tree(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file():
        path.unlink(missing_ok=True)
        return True
    keep = {p.resolve() for p in path.rglob(".gitkeep")}
    for child in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if child.resolve() in keep:
            continue
        if child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            try:
                child.rmdir()
            except OSError:
                pass
    try:
        path.rmdir()
    except OSError:
        pass
    path.mkdir(parents=True, exist_ok=True)
    gitkeep = path / ".gitkeep"
    if not gitkeep.exists() and path.name in ("reports",):
        gitkeep.touch()
    return True


def main() -> int:
    removed_dirs = 0
    removed_files = 0

    for d in DIR_TARGETS:
        if d.exists() and _rm_tree(d):
            removed_dirs += 1
            print(f"[cleanup] dir reset: {d}")

    for pat in GLOB_PATTERNS:
        for p in ROOT.glob(pat):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed_dirs += 1
                print(f"[cleanup] rmtree: {p}")
            elif p.is_file():
                p.unlink(missing_ok=True)
                removed_files += 1
                print(f"[cleanup] file: {p}")

    print(f"[cleanup] done dirs~{removed_dirs} files~{removed_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
