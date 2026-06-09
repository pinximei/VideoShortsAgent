#!/usr/bin/env python3
"""按固定顺序发布到多个渠道（每渠道独立 dry-run / publish / mark）。

用法:
  py -3.12 scripts/publish_all_channels.py --article-id 885 --channels douyin,xhs
  py -3.12 scripts/publish_all_channels.py --article-id 885 --channels douyin,xhs,toutiao,douban --prepare --all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publish_lib import (  # noqa: E402
    DEFAULT_ACCOUNTS,
    step_dry_run,
    step_mark,
    step_preflight,
    step_prepare,
    step_publish,
    utc_now,
    write_report,
)
from publisher.scripts.registry import BROWSER_CHANNELS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--article-id", type=int, required=True)
    parser.add_argument(
        "--channels",
        default="douyin,xhs,toutiao,douban",
        help="逗号分隔渠道列表",
    )
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--mark", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        args.prepare = args.dry_run = args.publish = args.mark = True

    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    for ch in channels:
        if ch not in BROWSER_CHANNELS:
            print(f"未知渠道: {ch}", file=sys.stderr)
            return 2

    from pipeline.config import load_config

    cfg = load_config(args.config)
    summary_path = cfg.output_root / str(args.article_id) / "publish" / "all_channels_report.json"
    summary = {"article_id": args.article_id, "started_at": utc_now(), "channels": {}}
    exit_code = 0

    for ch in channels:
        acc = DEFAULT_ACCOUNTS.get(ch, "")
        ch_report: dict = {"channel": ch, "account_id": acc}
        try:
            if args.prepare:
                ch_report["prepare"] = step_prepare(cfg, args.article_id, ch)
            if args.dry_run or args.publish or args.mark:
                ch_report["preflight"] = step_preflight(cfg, args.article_id, ch, acc)
            if args.dry_run:
                ch_report["dry_run"] = step_dry_run(cfg, args.article_id, ch, acc)
            if args.publish:
                ch_report["publish"] = step_publish(cfg, args.article_id, ch, acc)
            if args.mark:
                ch_report["mark"] = step_mark(cfg, args.article_id, ch, "publish_all_channels.py")
            ch_report["ok"] = True
        except Exception as e:
            ch_report["ok"] = False
            ch_report["error"] = str(e)
            exit_code = 1
        summary["channels"][ch] = ch_report
        print(json.dumps(ch_report, ensure_ascii=False, indent=2))

    summary["finished_at"] = utc_now()
    summary["ok"] = exit_code == 0
    write_report(summary_path, summary)
    print(f"\n汇总: {summary_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
