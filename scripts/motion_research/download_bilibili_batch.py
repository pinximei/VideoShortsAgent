#!/usr/bin/env python3
"""仅下载 corpus 中 B站条目（cookie 已验证可用）。"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
COOKIES = ROOT / "research" / "voice_content" / "cookies.txt"
MEDIA = ROOT / "research" / "voice_content" / "media"
MANIFEST = ROOT / "research" / "voice_content" / "download_manifest.json"


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    rows = []
    for v in corpus.get("videos", []):
        if v.get("platform") != "bilibili":
            continue
        vid = v["id"]
        url = v["url"]
        dest = MEDIA / vid
        dest.mkdir(parents=True, exist_ok=True)
        out_tpl = str(dest / "audio.%(ext)s")
        print(f"[bili] {vid}")
        cmd = [
            "yt-dlp",
            "--cookies",
            str(COOKIES),
            "-f",
            "ba[ext=m4a]/bestaudio/best",
            "--write-auto-sub",
            "--sub-lang",
            "zh-Hans,zh-CN,zh",
            "--convert-subs",
            "vtt",
            "-o",
            out_tpl,
            url,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        audio = next(
            (f for f in dest.iterdir() if f.suffix in (".m4a", ".mp3", ".webm", ".opus") and f.stat().st_size > 1000),
            None,
        )
        vtt = next((f for f in dest.glob("*.vtt")), None)
        rows.append(
            {
                "video_id": vid,
                "url": url,
                "ok": audio is not None,
                "audio": str(audio.relative_to(ROOT)).replace("\\", "/") if audio else None,
                "subtitle_vtt": str(vtt.relative_to(ROOT)).replace("\\", "/") if vtt else None,
                "yt_dlp_code": p.returncode,
                "log_tail": (p.stderr or "")[-300:],
            }
        )

    prev = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {"downloads": []}
    douyin = [d for d in prev.get("downloads", []) if d.get("video_id", "").isdigit() and len(d["video_id"]) > 12]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "download_bilibili_batch.py",
        "downloads": douyin + rows,
        "ok_count": sum(1 for r in douyin + rows if r.get("ok")),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    bili_ok = sum(1 for r in rows if r.get("ok"))
    print(f"Bilibili ok={bili_ok}/{len(rows)} total_ok={manifest['ok_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
