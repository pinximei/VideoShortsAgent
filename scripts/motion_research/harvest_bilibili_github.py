#!/usr/bin/env python3
"""B站搜索「每天一个github」采集真实 BV 号写入 corpus 补足样本。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"


def main() -> int:
    from playwright.sync_api import sync_playwright

    queries = ["每天一个github", "github开源 推荐", "GitHub项目 抖音风格"]
    found: list[dict] = []
    seen: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        for q in queries:
            url = f"https://search.bilibili.com/video?keyword={quote(q)}"
            print(f"[bili-search] {q}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            hrefs = page.eval_on_selector_all(
                'a[href*="/video/BV"]',
                "els => els.map(e => e.href)",
            )
            for href in hrefs or []:
                m = re.search(r"(BV[0-9A-Za-z]+)", href)
                if not m:
                    continue
                bv = m.group(1)
                if bv in seen or len(bv) < 10:
                    continue
                seen.add(bv)
                found.append(
                    {
                        "id": bv,
                        "url": f"https://www.bilibili.com/video/{bv}",
                        "title": f"B站-{bv}",
                        "platform": "bilibili",
                    }
                )
            if len(found) >= 12:
                break
        browser.close()

    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    douyin = [v for v in data.get("videos", []) if not v.get("platform")]
    data["videos"] = douyin + found[:12]
    data["bilibili_harvested_at"] = datetime.now(timezone.utc).isoformat()
    CORPUS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"corpus: {len(douyin)} douyin + {min(12, len(found))} bilibili = {len(data['videos'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
