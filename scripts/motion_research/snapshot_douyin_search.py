#!/usr/bin/env python3
"""
用已登录的抖音创作者浏览器配置，打开搜索页并截屏 + 保存可见链接文本（预研采样）。

需先：cd middle && py -3 scripts/open_platform_login.py --account-id acc_ai_news_douyin

用法:
  py -3 scripts/motion_research/snapshot_douyin_search.py --query "AI资讯" --max 8
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIDDLE = ROOT / "middle"
OUT = ROOT / "research" / "motion" / "douyin_snapshots"


def _profile_dir(account_id: str) -> Path:
    return MIDDLE / "data" / "browser" / "batch_b" / account_id


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="AI资讯口播")
    ap.add_argument("--account-id", default="acc_ai_news_douyin")
    ap.add_argument("--max", type=int, default=8)
    args = ap.parse_args()

    profile = _profile_dir(args.account_id)
    if not profile.is_dir():
        print(f"profile missing: {profile}", file=sys.stderr)
        print("Run open_platform_login.py for douyin first.", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shot = OUT / f"search_{ts}.png"
    meta_path = OUT / f"search_{ts}.json"

    # 抖音 Web 搜索（非创作者后台）
    url = f"https://www.douyin.com/search/{args.query}?type=video"

    items: list[dict] = []
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(shot), full_page=False)

        # 尽力抓取卡片文案（选择器随抖音改版可能失效）
        cards = page.locator('a[href*="/video/"]').all()[: args.max]
        for i, card in enumerate(cards):
            try:
                href = card.get_attribute("href") or ""
                text = (card.inner_text(timeout=2000) or "").strip()[:200]
                items.append({"index": i, "href": href, "text": text})
            except Exception as exc:
                items.append({"index": i, "error": str(exc)})

        ctx.close()

    meta = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "query": args.query,
        "url": url,
        "screenshot": str(shot),
        "items": items,
        "note": "人工下一步：从 screenshot 挑 2-3 条对标视频，用 analyze_subtitle_motion.py 逐条拆帧",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"screenshot: {shot}")
    print(f"meta: {meta_path} ({len(items)} links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
