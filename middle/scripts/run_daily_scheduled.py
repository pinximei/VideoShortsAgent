#!/usr/bin/env python3
"""每日定时（CLI）；生产环境请用中间层服务内置调度（start_server.py）。"""
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
    parser = argparse.ArgumentParser(description="每日定时（一次性 CLI）")
    parser.add_argument("-c", "--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--pipeline-only", action="store_true")
    parser.add_argument("--publish-only", action="store_true")
    parser.add_argument("--skip-login-check", action="store_true")
    parser.add_argument("--include-xhs", action="store_true")
    parser.add_argument("--random", action="store_true")
    parser.add_argument("--seed", type=int, default=-1)
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
    if not schedule.enabled:
        print("schedule.enabled=false，已跳过")
        return 0
    if args.include_xhs and "xhs" in schedule.skip_channels:
        schedule.skip_channels = [c for c in schedule.skip_channels if c != "xhs"]
    if args.random:
        schedule.pick_mode = "random"
    if args.seed >= 0:
        schedule.random_seed = args.seed

    cfg = load_config(args.config)
    rng = random.Random(schedule.random_seed)
    summary = run_publish_cycle(
        cfg,
        schedule,
        middle_root=ROOT,
        options=ScheduleRunOptions(
            pipeline_only=args.pipeline_only,
            publish_only=args.publish_only,
            skip_login_check=args.skip_login_check,
            count_override=args.count or None,
            note="run_daily_scheduled.py",
        ),
        rng=rng,
    )
    if summary.get("publish_skipped") == "auto_publish_disabled":
        print("提示: schedule.auto_publish=false，未自动发布；手动发请用 publish_channel.py 或 --publish-only")
    print(summary)
    return 0 if summary.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
