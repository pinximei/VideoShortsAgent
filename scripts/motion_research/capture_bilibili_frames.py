#!/usr/bin/env python3
"""B站「每日 github」类视频抽帧，补足抖音不足 20 条。"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "motion" / "github_daily" / "captures"
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
KEY_INDICES = [0, 0.15, 0.35, 0.55, 0.75, 1.0]


def _extract_keyframes(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(src_dir.glob("f_*.png"))
    if not frames:
        return
    n = len(frames)
    for pct_i, pct in enumerate(KEY_INDICES):
        idx = min(int((n - 1) * pct), n - 1)
        shutil.copy2(frames[idx], dst_dir / f"key_{pct_i:02d}_{int(pct*100):03d}pct.png")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return 1

    queries = ["每日github项目分享", "github开源项目推荐", "每天认识一款开源项目"]
    bvids: list[str] = []
    report: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for q in queries:
            url = f"https://search.bilibili.com/video?keyword={quote(q)}"
            print(f"[bili-search] {q}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            for _ in range(4):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(800)
            html = page.content()
            found = re.findall(r"BV[A-Za-z0-9]{10}", html)
            for b in found:
                if b not in bvids:
                    bvids.append(b)
            if len(bvids) >= 15:
                break

        need = max(0, 20 - 8)  # 已有 8 条抖音
        for bvid in bvids[: need + 3]:
            if len(report) >= need:
                break
            cap_dir = OUT / bvid
            if (cap_dir / "keyframes").is_dir() and len(list((cap_dir / "keyframes").glob("*.png"))) >= 4:
                continue
            vurl = f"https://www.bilibili.com/video/{bvid}"
            print(f"[bili-capture] {bvid}")
            cap_dir.mkdir(parents=True, exist_ok=True)
            try:
                page.goto(vurl, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                try:
                    page.locator(".bpx-player-ctrl-play").click(timeout=3000)
                except Exception:
                    page.keyboard.press("Space")
                page.wait_for_timeout(2000)
                for i in range(18):
                    page.screenshot(path=str(cap_dir / f"f_{i:04d}.png"))
                    page.wait_for_timeout(700)
                _extract_keyframes(cap_dir, cap_dir / "keyframes")
                report.append({"id": bvid, "platform": "bilibili", "url": vurl})
            except Exception as exc:
                print(f"  err {exc}")
        browser.close()

    corpus = json.loads(CORPUS.read_text(encoding="utf-8")) if CORPUS.is_file() else {"videos": []}
    for r in report:
        if not any(str(v.get("id")) == r["id"] for v in corpus.get("videos", [])):
            corpus.setdefault("videos", []).append(
                {"id": r["id"], "url": r["url"], "title": f"B站-{r['id']}", "platform": "bilibili"}
            )
    CORPUS.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"added {len(report)} bilibili, corpus total {len(corpus['videos'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
