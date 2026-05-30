#!/usr/bin/env python3
"""验收已有任务目录（不重渲、不拉 Soul）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir", type=str, help="如 data/output/889")
    ap.add_argument("--full", action="store_true", help="跑完整抽帧/音画验收")
    args = ap.parse_args()

    from pipeline.config import load_config
    from pipeline.render_verify import run_post_render_verify

    cfg_path = ROOT / "config.yaml"
    cfg = load_config(cfg_path if cfg_path.is_file() else ROOT / "config.example.yaml")
    task_dir = Path(args.task_dir)
    if not task_dir.is_dir():
        print(f"目录不存在: {task_dir}", file=sys.stderr)
        return 1

    report = run_post_render_verify(
        task_dir,
        platforms=cfg.render_platforms,
        full_verify=args.full or cfg.render_full_verify,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
