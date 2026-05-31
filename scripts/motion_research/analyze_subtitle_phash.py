#!/usr/bin/env python3
"""底栏 perceptual hash 变化 → 字幕切换间隔（captures_v2）。"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GITHUB_DAILY = ROOT / "research" / "motion" / "github_daily"
CORPUS = GITHUB_DAILY / "video_corpus.json"
OUT = ROOT / "research" / "voice_content" / "phash_analysis.json"

try:
    import imagehash
except ImportError:
    imagehash = None


def crop_sub(img: Image.Image) -> Image.Image:
    w, h = img.size
    return img.crop((0, int(h * 0.72), w, h)).convert("L").resize((320, 90))


def analyze_dir(cap: Path, *, interval_ms: int = 500) -> dict | None:
    frames = sorted(cap.glob("f_*.png"))
    if len(frames) < 4:
        return None
    hashes = []
    for p in frames:
        if imagehash:
            hashes.append(imagehash.phash(crop_sub(Image.open(p))))
        else:
            hashes.append(None)
    gaps_idx: list[int] = []
    if imagehash:
        for i in range(1, len(hashes)):
            dist = hashes[i] - hashes[i - 1]
            if dist >= 8:
                gaps_idx.append(i)
    else:
        return None
    if len(gaps_idx) < 2:
        return {
            "frames": len(frames),
            "phash_gaps": len(gaps_idx),
            "reliable": False,
            "note": "few_phash_changes",
        }
    sample_fps = 1000.0 / interval_ms
    gaps_sec = [(gaps_idx[i] - gaps_idx[0]) / sample_fps for i in range(len(gaps_idx))]
    step = [gaps_idx[i] - gaps_idx[i - 1] for i in range(1, len(gaps_idx))]
    median_step = statistics.median(step) / sample_fps
    switches_per_min = len(gaps_idx) / (len(frames) / sample_fps) * 60
    cpm_est = int((8 / median_step) * 60) if median_step > 0 else None
    return {
        "frames": len(frames),
        "phash_gaps": len(gaps_idx),
        "subtitle_switch_sec": round(median_step, 2),
        "subtitle_switch_ms": int(median_step * 1000),
        "switches_per_min": round(switches_per_min, 1),
        "chars_per_minute_est": cpm_est,
        "reliable": len(gaps_idx) >= 3,
        "method": "phash_bottom_band",
    }


def main() -> int:
    if not imagehash:
        print("pip install imagehash")
        return 1
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    rows = []
    for v in corpus.get("videos", []):
        if v.get("platform") == "bilibili":
            continue
        vid = str(v["id"])
        cap = GITHUB_DAILY / "captures_v3" / vid
        if not cap.is_dir():
            cap = GITHUB_DAILY / "captures_v2" / vid
        if not cap.is_dir():
            cap = GITHUB_DAILY / "captures" / vid
        a = analyze_dir(cap)
        rows.append({"video_id": vid, "title": v.get("title"), "analysis": a})

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reliable_count": sum(1 for r in rows if (r.get("analysis") or {}).get("reliable")),
        "videos": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} reliable={payload['reliable_count']}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
