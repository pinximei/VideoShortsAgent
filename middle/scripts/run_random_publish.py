#!/usr/bin/env python3
"""随机发布（CLI）；生产环境请用中间层服务内置调度（start_server.py）。"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    import os

    env_path = ROOT.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="VSA 中间层 — 随机发布（一次性 CLI）")
    parser.add_argument("-c", "--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--count-min", type=int, default=0)
    parser.add_argument("--count-max", type=int, default=0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--pipeline-only", action="store_true")
    parser.add_argument("--publish-only", action="store_true")
    parser.add_argument("--skip-login-check", action="store_true")
    parser.add_argument("--skip-startup-delay", action="store_true")
    parser.add_argument("--skip-gap", action="store_true")
    parser.add_argument("--include-xhs", action="store_true")
    args = parser.parse_args()
    _load_dotenv()

    import yaml

    from pipeline.config import load_config
    from pipeline.schedule_config import parse_schedule_config
    from pipeline.schedule_runner import ScheduleRunOptions, run_publish_cycle

    raw = {}
    if args.config.is_file():
        raw = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    schedule = parse_schedule_config(raw.get("schedule"))
    schedule.pick_mode = "random"
    if args.count_min > 0 and args.count_max > 0:
        schedule.daily_publish_count_min = args.count_min
        schedule.daily_publish_count_max = args.count_max
    if args.seed >= 0:
        schedule.random_seed = args.seed
    if not schedule.enabled:
        print("schedule.enabled=false，已跳过")
        return 0
    if args.include_xhs and "xhs" in schedule.skip_channels:
        schedule.skip_channels = [c for c in schedule.skip_channels if c != "xhs"]

    cfg = load_config(args.config)
    rng = random.Random(schedule.random_seed)
    summary = run_publish_cycle(
        cfg,
        schedule,
        middle_root=ROOT,
        options=ScheduleRunOptions(
            pipeline_only=args.pipeline_only,
            publish_only=args.publish_only,
            skip_startup_delay=args.skip_startup_delay,
            skip_gap=args.skip_gap,
            skip_login_check=args.skip_login_check,
            count_override=args.count or None,
            note="run_random_publish.py",
        ),
        rng=rng,
    )
    print(summary)
    return 0 if summary.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
