#!/usr/bin/env python3
"""下载对标视频音轨+字幕（yt-dlp），供真实语速/文案分析。"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
OUT = ROOT / "research" / "voice_content" / "media"
COOKIES = ROOT / "research" / "voice_content" / "cookies.txt"


def _run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return p.returncode, (p.stderr or "") + (p.stdout or "")


def download_one(url: str, vid: str, dest: Path, *, cookies: Path | None = None) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    audio_tpl = str(dest / "audio.%(ext)s")
    meta: dict = {"video_id": vid, "url": url, "ok": False}
    cmd = [
        "yt-dlp",
        "-f",
        "ba[ext=m4a]/bestaudio/best",
        "--write-auto-sub",
        "--write-sub",
        "--sub-lang",
        "zh-Hans,zh-CN,zh,en",
        "--convert-subs",
        "vtt",
        "-o",
        audio_tpl,
        "--print",
        "%(title)s|||%(duration)s",
        "--no-overwrites",
        "--ignore-errors",
    ]
    if cookies and cookies.is_file():
        cmd.extend(["--cookies", str(cookies)])
    cmd.append(url)

    code, log = _run(cmd, timeout=420)
    meta["log_tail"] = log[-800:] if log else ""

    for sub in sorted(dest.glob("*.vtt")) + sorted(dest.glob("*.zh*.vtt")):
        meta["subtitle_vtt"] = str(sub.relative_to(ROOT)).replace("\\", "/")
        break
    for aud in sorted(dest.glob("audio.*")):
        if aud.suffix in (".m4a", ".mp3", ".opus", ".webm", ".aac") and aud.stat().st_size > 1000:
            meta["audio"] = str(aud.relative_to(ROOT)).replace("\\", "/")
            break
    # yt-dlp 有时输出为 title.ext
    if not meta.get("audio"):
        for aud in sorted(dest.iterdir()):
            if aud.suffix in (".m4a", ".mp3", ".opus", ".webm") and aud.stat().st_size > 1000:
                meta["audio"] = str(aud.relative_to(ROOT)).replace("\\", "/")
                break

    if "|||" in log:
        parts = [ln for ln in log.splitlines() if "|||" in ln]
        if parts:
            title, dur = parts[-1].split("|||", 1)
            meta["title_downloaded"] = title.strip()
            try:
                meta["duration_sec"] = float(dur.strip())
            except ValueError:
                pass

    meta["ok"] = bool(meta.get("audio") or meta.get("subtitle_vtt"))
    meta["yt_dlp_code"] = code
    return meta


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for v in corpus.get("videos", []):
        vid = str(v["id"])
        url = str(v.get("url", ""))
        platform = v.get("platform", "douyin")
        dest = OUT / vid
        print(f"[download] {vid} ({platform})")
        ck = COOKIES if COOKIES.is_file() else None
        if url.startswith("http"):
            rows.append(download_one(url, vid, dest, cookies=ck))
        else:
            rows.append({"video_id": vid, "url": url, "ok": False, "note": "no_url"})

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "download_reference_media.py",
        "downloads": rows,
        "ok_count": sum(1 for r in rows if r.get("ok")),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT.parent / "download_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {path} ok={manifest['ok_count']}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
