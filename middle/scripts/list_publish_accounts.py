#!/usr/bin/env python3
"""列出发布账号固定 ID 与 Profile 路径。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--theme", default="", help="如 ai_news")
    parser.add_argument("--site", default="", help="如 ai-trends-news")
    args = parser.parse_args()

    from pipeline.config import load_config
    from pipeline.channel_registry import site_for_theme
    from publisher.profiles import account_profile_dir

    cfg = load_config(args.config)
    site_code = (args.site or "").strip()
    if args.theme and not site_code:
        s = site_for_theme(cfg.sites, args.theme.strip())
        site_code = s.code if s else ""

    print(f"data_dir={cfg.data_dir.resolve()}\n")
    rows = [a for a in cfg.channel_accounts if a.enabled]
    if site_code:
        rows = [a for a in rows if a.site_code == site_code]
    if not rows:
        print("无账号。先运行: py -3.12 scripts/init_ai_news_accounts.py")
        return 1

    for acc in rows:
        batch_id = acc.batch_id or (cfg.publisher.batch_for_site(acc.site_code).batch_id if cfg.publisher.batch_for_site(acc.site_code) else "?")
        prof = account_profile_dir(cfg.data_dir, batch_id, acc.id)
        login_cmd = ""
        if acc.channel_id in ("douyin", "xhs"):
            login_cmd = f"py -3.12 scripts/open_platform_login.py --account-id {acc.id}"
        print(f"{acc.id}")
        print(f"  渠道={acc.channel_id} 站点={acc.site_code} 批次={batch_id} 主账号={acc.is_primary}")
        print(f"  名称={acc.label or acc.handle or '-'}")
        print(f"  Profile={prof}")
        if login_cmd:
            print(f"  登录={login_cmd}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
