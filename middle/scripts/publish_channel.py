#!/usr/bin/env python3
"""多平台固定发布 CLI（抖音 / 小红书 / 头条 / 豆瓣），无需 Agent。

用法（在 middle 目录）:
  py -3.12 scripts/publish_channel.py --channel douyin --article-id 885 --prepare --dry-run
  py -3.12 scripts/publish_channel.py --channel xhs --article-id 885 --publish --mark
  py -3.12 scripts/publish_channel.py --channel toutiao --article-id 885 --all
  py -3.12 scripts/publish_channel.py --channel douban --article-id 885 --all
  py -3.12 scripts/verify_publish.py --channel xhs --article-id 885

首次登录（每账号一次）:
  py -3.12 scripts/open_platform_login.py --account-id acc_ai_news_douyin --wait-seconds 120
  py -3.12 scripts/check_publisher_login.py --account-id acc_ai_news_douyin

文档: docs/PUBLISH_RUNBOOK.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publish_lib import (  # noqa: E402
    CHANNEL_LABELS,
    DEFAULT_ACCOUNTS,
    step_dry_run,
    step_mark,
    step_preflight,
    step_prepare,
    step_publish,
    step_verify,
    utc_now,
    write_report,
)
from publisher.scripts.registry import BROWSER_CHANNELS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="多平台固定发布（Playwright 脚本）")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--channel", required=True, choices=sorted(BROWSER_CHANNELS))
    parser.add_argument("--article-id", type=int, required=True)
    parser.add_argument(
        "--account-id",
        default="",
        help="默认按渠道使用爱资讯账号 acc_ai_news_*",
    )
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--mark", action="store_true")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="发布后验收（作品管理页核对标题）",
    )
    parser.add_argument(
        "--verify-wait",
        type=int,
        default=12,
        help="发布完成后等待秒数再验收（默认 12）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="prepare + preflight + dry-run + publish + verify + mark",
    )
    args = parser.parse_args()

    if args.all:
        args.prepare = args.preflight = args.dry_run = True
        args.publish = args.verify = args.mark = True

    if not any(
        (args.prepare, args.preflight, args.dry_run, args.publish, args.verify, args.mark)
    ):
        parser.error("请指定步骤或使用 --all")

    account_id = args.account_id or DEFAULT_ACCOUNTS.get(args.channel, "")
    from pipeline.config import load_config

    cfg = load_config(args.config)
    label = CHANNEL_LABELS.get(args.channel, args.channel)
    report_path = (
        cfg.output_root
        / str(args.article_id)
        / "publish"
        / f"{args.channel}_publish_report.json"
    )
    report: dict[str, Any] = {
        "channel": args.channel,
        "channel_label": label,
        "article_id": args.article_id,
        "account_id": account_id,
        "started_at": utc_now(),
        "steps_run": [],
    }

    try:
        if args.prepare:
            r = step_prepare(cfg, args.article_id, args.channel)
            report["prepare"] = r
            report["steps_run"].append("prepare")

        if args.preflight or args.dry_run or args.publish or args.mark:
            r = step_preflight(cfg, args.article_id, args.channel, account_id)
            report["preflight"] = r
            report["steps_run"].append("preflight")

        if args.dry_run:
            r = step_dry_run(cfg, args.article_id, args.channel, account_id)
            report["dry_run"] = r
            report["steps_run"].append("dry_run")

        if args.publish:
            r = step_publish(cfg, args.article_id, args.channel, account_id)
            report["publish"] = r
            report["steps_run"].append("publish")

        if args.verify:
            if args.verify_wait > 0:
                import time

                time.sleep(args.verify_wait)
            r = step_verify(cfg, args.article_id, args.channel, account_id)
            report["verify"] = r
            report["steps_run"].append("verify")

        if args.mark:
            r = step_mark(cfg, args.article_id, args.channel, "publish_channel.py")
            report["mark"] = r
            report["steps_run"].append("mark")

        report["ok"] = True
        report["finished_at"] = utc_now()
        write_report(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\n[{label}] 报告: {report_path}")
        return 0
    except Exception as e:
        report["ok"] = False
        report["error"] = str(e)
        report["finished_at"] = utc_now()
        write_report(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"报告: {report_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
