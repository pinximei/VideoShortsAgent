#!/usr/bin/env python3
"""调用与控制台相同的 login-check API 逻辑（无需起 HTTP 服务）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check_headed(cfg, batch_id: str, acc) -> dict:
    from publisher.profiles import resolve_profile_dir
    from publisher.scripts.registry import get_login_script

    profile_dir = resolve_profile_dir(cfg.data_dir, batch_id, acc, cfg.publisher)
    script = get_login_script(acc.channel_id)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            locale="zh-CN",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        result = script.check(page)
        ctx.close()
    return {
        "batch_id": batch_id,
        "account_id": acc.id,
        "channel_id": acc.channel_id,
        "headed": True,
        **result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--account-id", required=True)
    parser.add_argument(
        "--headed",
        action="store_true",
        help="有界面浏览器检测（与登录窗口一致，推荐人工刚登完后使用）",
    )
    args = parser.parse_args()

    from pipeline.config import load_config
    from publisher.runner import check_login

    cfg = load_config(args.config)
    acc = next((a for a in cfg.channel_accounts if a.id == args.account_id), None)
    if not acc:
        print(json.dumps({"error": "account not found"}, ensure_ascii=False))
        return 2
    batch_id = (acc.batch_id or "").strip()
    if not batch_id:
        batch = cfg.publisher.batch_for_site(acc.site_code)
        batch_id = batch.batch_id if batch else ""
    if not batch_id:
        print(json.dumps({"error": "no batch_id"}, ensure_ascii=False))
        return 2

    out = _check_headed(cfg, batch_id, acc) if args.headed else check_login(cfg, batch_id, acc)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("logged_in") else 1


if __name__ == "__main__":
    raise SystemExit(main())
