#!/usr/bin/env python3
"""按固定 account-id 打开有界面浏览器；Cookie 写入独立 Profile，后续同 ID 自动登录。

用法（在 middle 目录）:
  py -3.12 scripts/list_publish_accounts.py --theme ai_news
  py -3.12 scripts/open_platform_login.py --account-id acc_ai_news_douyin

登录完成后在终端按 Enter；Profile 目录 data/browser/{batch_id}/{account_id}/ 会保留会话。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO = ROOT.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CREATOR_URLS = {
    "douyin": "https://creator.douyin.com/creator-micro/content/upload",
    "xhs": "https://creator.xiaohongshu.com/publish/publish",
    "toutiao": "https://mp.toutiao.com/profile_v4/weitoutiao/publish",
    "douban": "https://www.douban.com/note/create",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="有界面浏览器登录（持久化 Profile）")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--account-id",
        required=True,
        help="config.yaml channel_accounts 里的固定 id，如 acc_ai_news_douyin",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=0,
        help="非交互环境用：保持浏览器 N 秒后自动保存并关闭（0=在终端按 Enter）",
    )
    args = parser.parse_args()

    from pipeline.config import load_config
    from publisher.profiles import ensure_profile_dir, write_session_meta
    from publisher.scripts.registry import get_login_script

    cfg = load_config(args.config)
    acc = next((a for a in cfg.channel_accounts if a.id == args.account_id), None)
    if not acc:
        print(
            f"ERROR: 未找到账号 id={args.account_id!r}。"
            " 先运行 py -3.12 scripts/init_ai_news_accounts.py",
            file=sys.stderr,
        )
        return 2

    batch_id = (acc.batch_id or "").strip()
    if not batch_id:
        batch = cfg.publisher.batch_for_site(acc.site_code)
        batch_id = batch.batch_id if batch else ""
    if not batch_id:
        print("ERROR: 账号未配置 batch_id，且站点未映射 publisher batch", file=sys.stderr)
        return 2

    if acc.channel_id not in CREATOR_URLS:
        print(f"ERROR: 渠道 {acc.channel_id} 无自动登录页", file=sys.stderr)
        return 2

    from publisher.profiles import profile_storage_id, resolve_profile_dir

    storage_id = profile_storage_id(batch_id, acc, cfg.publisher)
    profile_dir = resolve_profile_dir(cfg.data_dir, batch_id, acc, cfg.publisher)
    url = CREATOR_URLS[acc.channel_id]
    batch = cfg.publisher.batch_by_id(batch_id)
    shared = bool(batch and batch.shared_profile_id)
    print("=" * 60)
    print(f"account_id = {acc.id}")
    print(f"渠道       = {acc.channel_id}")
    print(f"批次       = {batch_id}")
    print(f"Profile    = {profile_dir}")
    if shared:
        print(f"共享浏览器 = {batch.shared_profile_id}（四渠道同一 Profile）")
    print(f"URL        = {url}")
    print("-" * 60)
    if shared:
        print(
            "说明：本 batch 已启用【共享浏览器】。在此窗口登录的四个平台 Cookie 都会写入同一目录。\n"
            "      推荐: py -3.12 scripts/open_shared_publish_login.py --wait-seconds 180"
        )
    else:
        print("说明：当前为每账号独立 Profile。")
    print("=" * 60)
    if args.wait_seconds > 0:
        print(f"在此窗口扫码/登录；浏览器将保持约 {args.wait_seconds} 秒后自动保存 Cookie。")
    else:
        print("在此窗口扫码/登录；完成后回到终端按 Enter 保存 Cookie 并关闭。")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            locale="zh-CN",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        if args.wait_seconds > 0:
            try:
                time.sleep(max(30, args.wait_seconds))
            except KeyboardInterrupt:
                pass
        else:
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                print("（非交互终端：若浏览器已关，请用 --wait-seconds 600 重新运行）")
                time.sleep(5)
        # 可选：登录脚本检测
        logged_in = False
        try:
            script = get_login_script(acc.channel_id)
            result = script.check(page)
            logged_in = bool(result.get("logged_in"))
            print("login_check:", result)
        except Exception as e:
            print("login_check skipped:", e)
        write_session_meta(
            cfg.data_dir,
            batch_id,
            acc.id,
            status="ok" if logged_in else "expired",
            message="open_platform_login closed",
            mark_login=logged_in,
        )
        ctx.close()

    print(f"已关闭。验证: py scripts/check_publisher_login.py --account-id {acc.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
