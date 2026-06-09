#!/usr/bin/env python3
"""发布后固定验收 — 打开各平台作品管理页，核对标题是否上线。

用法:
  py -3.12 scripts/verify_publish.py --channel xhs --article-id 885
  py -3.12 scripts/verify_publish.py --channel douyin --article-id 885 --wait 15

发布流程中已自动调用；也可在 publish 之后单独重跑验收。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publish_lib import (  # noqa: E402
    CHANNEL_LABELS,
    DEFAULT_ACCOUNTS,
    step_verify,
    utc_now,
    write_report,
)
from publisher.scripts.registry import BROWSER_CHANNELS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="发布后固定验收")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--channel", required=True, choices=sorted(BROWSER_CHANNELS))
    parser.add_argument("--article-id", type=int, required=True)
    parser.add_argument("--account-id", default="")
    parser.add_argument(
        "--wait",
        type=int,
        default=10,
        help="发布完成后等待秒数再验收（平台列表索引延迟）",
    )
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()

    from pipeline.config import load_config

    cfg = load_config(args.config)
    account_id = args.account_id or DEFAULT_ACCOUNTS.get(args.channel, "")
    label = CHANNEL_LABELS.get(args.channel, args.channel)
    report_path = (
        cfg.output_root
        / str(args.article_id)
        / "publish"
        / f"{args.channel}_publish_verify.json"
    )

    if args.wait > 0:
        print(f"等待 {args.wait}s 后验收…")
        time.sleep(args.wait)

    report: dict = {
        "channel": args.channel,
        "article_id": args.article_id,
        "account_id": account_id,
        "started_at": utc_now(),
    }
    try:
        r = step_verify(
            cfg,
            args.article_id,
            args.channel,
            account_id,
            retries=args.retries,
        )
        report["verify"] = r
        report["ok"] = True
        report["finished_at"] = utc_now()
        write_report(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\n[{label}] 验收报告: {report_path}")
        return 0
    except Exception as e:
        report["ok"] = False
        report["error"] = str(e)
        report["finished_at"] = utc_now()
        write_report(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
