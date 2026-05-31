#!/usr/bin/env python3
"""从 Playwright 登录态导出 cookies.txt 供 yt-dlp 使用。"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIDDLE = ROOT / "middle"
DEFAULT_PROFILE = MIDDLE / "data" / "browser" / "batch_b" / "acc_ai_news_douyin"
OUT = ROOT / "research" / "voice_content" / "cookies.txt"


def to_netscape(cookies: list[dict]) -> str:
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in cookies:
        domain = c.get("domain", "")
        if domain.startswith("."):
            flag = "TRUE"
        else:
            flag = "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        exp = str(int(c.get("expires", 0) or 0))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{exp}\t{name}\t{value}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("-o", type=Path, default=OUT)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    args.o.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(args.profile),
            headless=True,
            locale="zh-CN",
        )
        cookies = ctx.cookies()
        ctx.close()
    args.o.write_text(to_netscape(cookies), encoding="utf-8")
    print(f"Wrote {args.o} ({len(cookies)} cookies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
