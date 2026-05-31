#!/usr/bin/env python3
"""抖音对标视频抽帧 → captures/<id>/ + keyframes/（6 张关键帧供检查）。"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
MIDDLE = ROOT / "middle"
GITHUB_DAILY = ROOT / "research" / "motion" / "github_daily"
CORPUS_DEFAULT = GITHUB_DAILY / "video_corpus.json"

KEY_INDICES = [0, 0.15, 0.35, 0.55, 0.75, 1.0]


def _load_corpus(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    seen: set[str] = set()
    for v in data.get("videos", []):
        vid = str(v.get("id", ""))
        if not re.fullmatch(r"\d{15,22}", vid):
            continue
        if vid in seen:
            continue
        seen.add(vid)
        out.append(v)
    return out


def _extract_keyframes(src_dir: Path, dst_dir: Path) -> list[str]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(src_dir.glob("f_*.png"))
    if not frames:
        return []
    n = len(frames)
    rel_paths: list[str] = []
    for pct_i, pct in enumerate(KEY_INDICES):
        idx = min(int((n - 1) * pct), n - 1)
        src = frames[idx]
        dst = dst_dir / f"key_{pct_i:02d}_{int(pct*100):03d}pct.png"
        shutil.copy2(src, dst)
        rel_paths.append(str(dst.relative_to(ROOT)).replace("\\", "/"))
    return rel_paths


def harvest_more_ids(page, queries: list[str], limit: int = 20) -> list[str]:
    import re as _re

    seen: set[str] = set()
    for q in queries:
        url = f"https://www.douyin.com/search/{quote(q)}?type=video"
        print(f"[search] {q}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            continue
        page.wait_for_timeout(6000)
        for _ in range(5):
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(1200)
        hrefs = page.eval_on_selector_all(
            'a[href*="/video/"]',
            "els => els.map(e => e.href)",
        )
        for href in hrefs or []:
            m = _re.search(r"/video/(\d{15,22})", href)
            if m:
                seen.add(m.group(1))
        if len(seen) >= limit:
            break
    return list(seen)[:limit]


def _dismiss_login(page) -> None:
    """尽量关掉登录弹窗，避免整页截图污染抽帧。"""
    for sel in (
        'button:has-text("关闭")',
        '[aria-label="关闭"]',
        '.dy-account-close',
        'div[class*="close"]',
    ):
        try:
            page.locator(sel).first.click(timeout=800)
            page.wait_for_timeout(500)
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
    except Exception:
        pass


def capture_one(page, vid: str, out_dir: Path, frames: int, interval_ms: int, *, force: bool = False) -> int:
    key_dir = out_dir / "keyframes"
    if not force and key_dir.is_dir() and len(list(key_dir.glob("*.png"))) >= 6:
        print(f"  skip {vid} (keyframes exist)")
        return 6

    url = f"https://www.douyin.com/video/{vid}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[capture] {vid}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        _dismiss_login(page)
        video = page.locator("video").first
        try:
            video.click(timeout=3000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        count = 0
        for i in range(frames):
            fp = out_dir / f"f_{i:04d}.png"
            try:
                video.screenshot(path=str(fp), timeout=5000)
            except Exception:
                page.screenshot(path=str(fp), full_page=False)
            count += 1
            page.wait_for_timeout(interval_ms)
        _extract_keyframes(out_dir, key_dir)
        return count
    except Exception as exc:
        print(f"  error: {exc}")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=CORPUS_DEFAULT)
    ap.add_argument("--account-id", default="acc_ai_news_douyin")
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--interval-ms", type=int, default=600)
    ap.add_argument("--harvest-search", action="store_true", help="先搜索补全 corpus 至 20 条")
    ap.add_argument("--video-id", action="append", default=[])
    ap.add_argument("--force", action="store_true", help="覆盖已有 keyframes")
    ap.add_argument("--out-subdir", default="", help="如 captures_v2 写入子目录")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        return 1

    profile = MIDDLE / "data" / "browser" / "batch_b" / args.account_id
    items = _load_corpus(args.corpus)
    if args.video_id:
        items = [{"id": x, "url": f"https://www.douyin.com/video/{x}"} for x in args.video_id]

    report_entries: list[dict] = []

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            viewport={"width": 430, "height": 932},
            locale="zh-CN",
            is_mobile=True,
            has_touch=True,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if args.harvest_search:
            ids = harvest_more_ids(
                page,
                ["每天一个GitHub项目", "每天一个github", "github开源神器", "GitHub日更"],
                limit=20,
            )
            corpus_data = json.loads(args.corpus.read_text(encoding="utf-8"))
            existing = {str(v["id"]) for v in corpus_data.get("videos", []) if re.fullmatch(r"\d{15,22}", str(v.get("id","")))}
            for vid in ids:
                if vid not in existing:
                    corpus_data.setdefault("videos", []).append(
                        {"id": vid, "url": f"https://www.douyin.com/video/{vid}", "title": f"搜索采集-{vid}"}
                    )
            args.corpus.write_text(json.dumps(corpus_data, ensure_ascii=False, indent=2), encoding="utf-8")
            items = _load_corpus(args.corpus)
            print(f"corpus now {len(items)} videos")

        cap_root = GITHUB_DAILY / (args.out_subdir or "captures")
        for v in items[:20]:
            vid = str(v["id"])
            cap_dir = cap_root / vid
            n = capture_one(page, vid, cap_dir, args.frames, args.interval_ms, force=args.force)
            kf = sorted((cap_dir / "keyframes").glob("*.png")) if (cap_dir / "keyframes").is_dir() else []
            report_entries.append(
                {
                    "video_id": vid,
                    "title": v.get("title", ""),
                    "url": v.get("url", f"https://www.douyin.com/video/{vid}"),
                    "frames_captured": n,
                    "keyframes": [str(p.relative_to(ROOT)).replace("\\", "/") for p in kf],
                }
            )

        ctx.close()

    report = {
        "at": datetime.now(timezone.utc).isoformat(),
        "count": len(report_entries),
        "videos": report_entries,
    }
    path = GITHUB_DAILY / "capture_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report: {path}")
    ok = sum(1 for r in report_entries if r.get("keyframes"))
    print(f"done: {ok}/{len(report_entries)} with keyframes")
    return 0 if ok >= 20 else (0 if ok > 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
