#!/usr/bin/env python3
"""检查四渠道登录；未登录则【按渠道依次】打开独立 Profile 浏览器等待扫码。

batch_b 默认共用 acc_ai_news_shared 一个浏览器；四站 Cookie 同目录。
推荐: py -3.12 scripts/open_shared_publish_login.py --wait-seconds 180

用法:
  py -3.12 scripts/ensure_publish_logins.py --check-only
  py -3.12 scripts/ensure_publish_logins.py --wait-seconds 180
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publish_lib import DEFAULT_ACCOUNTS  # noqa: E402
from publisher.scripts.registry import BROWSER_CHANNELS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--channels",
        default=",".join(sorted(BROWSER_CHANNELS)),
    )
    parser.add_argument("--wait-seconds", type=int, default=120)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    from pipeline.config import load_config
    from publisher.runner import check_login

    cfg = load_config(args.config)
    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    batch = cfg.publisher.batch_by_id("batch_b")
    if batch and batch.shared_profile_id:
        print(
            f"提示：batch_b 使用共享浏览器 {batch.shared_profile_id}；"
            "未登录时建议先运行 open_shared_publish_login.py\n"
        )
    report: dict = {"channels": {}, "ok": True}

    for ch in channels:
        aid = DEFAULT_ACCOUNTS.get(ch, "")
        acc = next((a for a in cfg.channel_accounts if a.id == aid), None)
        if not acc:
            report["channels"][ch] = {"ok": False, "error": f"no account {aid}"}
            report["ok"] = False
            continue
        batch_id = acc.batch_id or (cfg.publisher.batch_for_site(acc.site_code).batch_id if cfg.publisher.batch_for_site(acc.site_code) else "")
        out = check_login(cfg, batch_id, acc)
        report["channels"][ch] = out
        if not out.get("logged_in"):
            report["ok"] = False

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.check_only or report["ok"]:
        return 0 if report["ok"] else 1

    import subprocess

    if batch and batch.shared_profile_id:
        print(
            f"\n>>> 打开共享浏览器登录四站 ({batch.shared_profile_id})，约 {args.wait_seconds}s …"
        )
        r = subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts" / "open_shared_publish_login.py"),
                "--wait-seconds",
                str(args.wait_seconds),
            ],
            cwd=str(ROOT),
        )
        return r

    code = 0
    for ch in channels:
        if report["channels"].get(ch, {}).get("logged_in"):
            continue
        aid = DEFAULT_ACCOUNTS[ch]
        print(f"\n>>> 请扫码登录 {ch} ({aid})，浏览器约保持 {args.wait_seconds}s …")
        r = subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts" / "open_platform_login.py"),
                "--account-id",
                aid,
                "--wait-seconds",
                str(args.wait_seconds),
            ],
            cwd=str(ROOT),
        )
        if r != 0:
            code = r
    return code


if __name__ == "__main__":
    raise SystemExit(main())
