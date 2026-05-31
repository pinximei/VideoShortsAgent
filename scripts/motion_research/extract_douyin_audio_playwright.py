#!/usr/bin/env python3
"""Playwright 登录态读取 video.src → ffmpeg 下载音轨（抖音 yt-dlp 失败时的备选）。"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIDDLE = ROOT / "middle"
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
MEDIA = ROOT / "research" / "voice_content" / "media"
PROFILE = MIDDLE / "data" / "browser" / "batch_b" / "acc_ai_news_douyin"
MANIFEST_EXTRA = ROOT / "research" / "voice_content" / "douyin_audio_manifest.json"


def _load_douyin_ids() -> list[dict]:
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return [v for v in data.get("videos", []) if not v.get("platform")]


def _dismiss(page) -> None:
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
    except Exception:
        pass


def main() -> int:
    from playwright.sync_api import sync_playwright

    items = _load_douyin_ids()
    results: list[dict] = []

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE),
            headless=False,
            viewport={"width": 430, "height": 932},
            locale="zh-CN",
            is_mobile=True,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for v in items:
            vid = str(v["id"])
            dest = MEDIA / vid
            dest.mkdir(parents=True, exist_ok=True)
            out_audio = dest / "audio_douyin.m4a"
            if out_audio.is_file() and out_audio.stat().st_size > 5000:
                print(f"  skip {vid}")
                results.append({"video_id": vid, "ok": True, "audio": str(out_audio.relative_to(ROOT)).replace("\\", "/")})
                continue

            url = f"https://www.douyin.com/video/{vid}"
            print(f"[douyin-audio] {vid}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(5000)
                _dismiss(page)
                page.locator("video").first.click(timeout=3000)
                page.wait_for_timeout(2000)
                src = page.locator("video").first.get_attribute("src") or ""
                if not src or src.startswith("blob:"):
                    # 尝试从 performance 或 source 子元素
                    src = page.eval_on_selector(
                        "video source",
                        "el => el ? el.src : ''",
                    ) or src
                if not src or src.startswith("blob:"):
                    results.append({"video_id": vid, "ok": False, "error": "no_direct_src"})
                    continue
                tmp = dest / "_video.mp4"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", src, "-vn", "-acodec", "aac", str(out_audio)],
                    capture_output=True,
                    timeout=120,
                )
                ok = out_audio.is_file() and out_audio.stat().st_size > 3000
                results.append(
                    {
                        "video_id": vid,
                        "ok": ok,
                        "audio": str(out_audio.relative_to(ROOT)).replace("\\", "/") if ok else None,
                        "src_preview": src[:120],
                    }
                )
            except Exception as exc:
                results.append({"video_id": vid, "ok": False, "error": str(exc)[:200]})

        ctx.close()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": sum(1 for r in results if r.get("ok")),
        "results": results,
    }
    MANIFEST_EXTRA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST_EXTRA} ok={payload['ok']}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
