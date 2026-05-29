#!/usr/bin/env python3
"""执行一轮 pipeline：发现 Soul 内容 → 去重 → 生成 brief/文案包（可选 VSA 出片）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import load_config
from pipeline.orchestrator import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="AiSoul video pipeline — run once")
    parser.add_argument(
        "-c",
        "--config",
        default=str(ROOT / "config.yaml"),
        help="config.yaml path",
    )
    args = parser.parse_args()
    cfg = load_config(args.config)
    stats = run_pipeline(cfg)
    print(
        f"discovered={stats.discovered} skipped={stats.skipped} queued={stats.queued} "
        f"packed={stats.packed} rendered={stats.rendered} deduped={stats.deduped} failed={stats.failed}"
    )
    for err in stats.errors:
        print(f"  error: {err}", file=sys.stderr)
    return 1 if stats.failed and not stats.packed else 0


if __name__ == "__main__":
    raise SystemExit(main())
