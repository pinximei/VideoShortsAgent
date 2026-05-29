#!/usr/bin/env python3
"""查看任务与待发布清单。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import load_config
from pipeline.db import JobStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--pending", metavar="CHANNEL", help="douyin|xhs|...")
    args = parser.parse_args()
    cfg = load_config(args.config)
    store = JobStore(cfg.db_path)

    if args.pending:
        rows = store.pending_publish(args.pending)
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        return 0

    rows = store.list_jobs()
    print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
