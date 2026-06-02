#!/usr/bin/env python3
"""离线 A/B：对 task plan 试 5 种单变量，选最高分并可选写回 plan。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir", type=Path)
    ap.add_argument("--apply", action="store_true", help="将最优 variant 写回 slides_render_plan_douyin.json")
    ap.add_argument("--with-video", action="store_true", help="打分计入成片时长（需已有 douyin.mp4）")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from python_agent.douyin_offline_loop import write_offline_loop_report

    path = write_offline_loop_report(
        args.task_dir.resolve(),
        apply_best=args.apply,
        include_video=args.with_video,
    )
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    best = report.get("best_variant")
    print(f"\nBest variant: {best} (applied={report.get('recommended_applied')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
