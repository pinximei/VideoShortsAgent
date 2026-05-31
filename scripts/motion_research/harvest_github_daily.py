#!/usr/bin/env python3
"""
采集「每天一个 GitHub / GitHub 日更」类短视频链接，并批量抽帧分析。

目标：尽量凑满 N 条样本（默认 100），输出聚类报告供 20 套模板归纳。

用法:
  py -3 scripts/motion_research/harvest_github_daily.py --target 100
  py -3 scripts/motion_research/harvest_github_daily.py --analyze-only
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
MIDDLE = ROOT / "middle"
OUT = ROOT / "research" / "motion" / "github_daily"
FRAMES = OUT / "frames"
REPORTS = ROOT / "research" / "motion" / "reports"
ANALYZE = ROOT / "scripts" / "motion_research" / "analyze_subtitle_motion.py"

QUERIES = [
    "每天一个GitHub项目",
    "每天一个github",
    "每天分享一个GitHub",
    "github开源神器",
    "GitHub日更",
]


def _profile_dir(account_id: str) -> Path:
    return MIDDLE / "data" / "browser" / "batch_b" / account_id


def harvest_links(account_id: str, per_query: int = 25) -> list[dict]:
    from playwright.sync_api import sync_playwright

    profile = _profile_dir(account_id)
    if not profile.is_dir():
        raise FileNotFoundError(f"Douyin profile missing: {profile}")

    seen: set[str] = set()
    items: list[dict] = []

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1400, "height": 900},
            locale="zh-CN",
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for q in QUERIES:
            url = f"https://www.douyin.com/search/{quote(q)}?type=video"
            print(f"[harvest] search: {q}")
            try:
                page.goto(url, wait_until="networkidle", timeout=90000)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(8000)
            for _ in range(4):
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(1500)

            hrefs = page.eval_on_selector_all(
                'a[href*="/video/"]',
                "els => els.map(e => e.href).filter(Boolean)",
            )
            for href in hrefs:
                m = re.search(r"/video/(\d+)", href)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                items.append({"video_id": vid, "url": href.split("?")[0], "query": q})
                if len([x for x in items if x["query"] == q]) >= per_query:
                    break

            shot = OUT / f"search_{quote(q, safe='')}_{datetime.now(timezone.utc).strftime('%H%M%S')}.png"
            page.screenshot(path=str(shot), full_page=False)

        ctx.close()

    return items


def save_index(items: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "harvest_index.json"
    path.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def download_samples(items: list[dict], max_dl: int) -> list[Path]:
    """yt-dlp 下载（需网络；抖音可能需 cookies）。"""
    paths: list[Path] = []
    for i, it in enumerate(items[:max_dl]):
        url = it.get("url") or ""
        if not url:
            continue
        dest = OUT / f"dy_{it['video_id']}.mp4"
        if dest.is_file() and dest.stat().st_size > 50_000:
            paths.append(dest)
            continue
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f",
            "bv*[height<=720]+ba/b",
            "-o",
            str(dest),
            url,
        ]
        print(f"[download] {i+1}/{max_dl} {url}")
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0 and dest.is_file():
            paths.append(dest)
    return paths


def run_analyze(videos: list[Path]) -> Path | None:
    if not videos:
        return None
    REPORTS.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ANALYZE), *[str(v) for v in videos]]
    subprocess.check_call(cmd)
    reports = sorted(REPORTS.glob("subtitle_motion_*.json"))
    return reports[-1] if reports else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100, help="目标采集链接数")
    ap.add_argument("--account-id", default="acc_ai_news_douyin")
    ap.add_argument("--per-query", type=int, default=25)
    ap.add_argument("--download", type=int, default=0, help="下载前 N 条 mp4")
    ap.add_argument("--harvest-only", action="store_true")
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()

    if args.analyze_only:
        videos = sorted(OUT.glob("dy_*.mp4")) + sorted(OUT.glob("bili_*.mp4"))
        run_analyze(videos)
        return 0

    items = harvest_links(args.account_id, per_query=args.per_query)
    # 去重后截断到 target
    items = items[: args.target]
    idx = save_index(items)
    print(f"harvested {len(items)} links -> {idx}")

    if args.harvest_only:
        return 0

    if args.download > 0 and items:
        vids = download_samples(items, args.download)
        print(f"downloaded {len(vids)} mp4")
        if vids:
            run_analyze(vids)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
