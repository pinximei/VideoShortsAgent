#!/usr/bin/env python3
"""从对标抽帧序列分析字幕区切换间隔 → 推断口播语速/分页节奏。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITHUB_DAILY = ROOT / "research" / "motion" / "github_daily"
CAPTURES = GITHUB_DAILY / "captures"
CORPUS = GITHUB_DAILY / "video_corpus.json"
CAPTURE_SUBDIR = "captures_v2"  # 优先 v2，否则 captures
OUT = ROOT / "research" / "voice_content" / "analysis_report.json"

# 复用字幕动效分析
sys.path.insert(0, str(ROOT / "scripts" / "motion_research"))
from analyze_subtitle_motion import crop_subtitle_band, detect_peaks, frame_diff  # noqa: E402

from PIL import Image


def _login_overlay_score(img: Image.Image) -> float:
    """中心区域过亮通常=登录弹窗。返回 0~1，越高越像被挡。"""
    w, h = img.size
    cx0, cx1 = int(w * 0.2), int(w * 0.8)
    cy0, cy1 = int(h * 0.15), int(h * 0.85)
    band = img.crop((cx0, cy0, cx1, cy1)).convert("L")
    px = list(band.getdata())
    bright = sum(1 for p in px if p > 220) / max(1, len(px))
    return round(bright, 3)


def analyze_capture_dir(cap_dir: Path, *, sample_interval_ms: int = 600) -> dict | None:
    frames = sorted(cap_dir.glob("f_*.png"))
    if len(frames) < 4:
        return None
    login_scores = [_login_overlay_score(Image.open(p)) for p in frames[:5]]
    login_blocked = sum(1 for s in login_scores if s > 0.35) >= 3

    bands = [crop_subtitle_band(Image.open(p)) for p in frames]
    diffs = [frame_diff(bands[i - 1], bands[i]) for i in range(1, len(bands))]
    motion_mean = sum(diffs) / len(diffs) if diffs else 0.0
    peaks = detect_peaks(diffs, threshold=0.025)
    sample_fps = 1000.0 / sample_interval_ms
    if len(peaks) >= 2:
        gaps = [(peaks[i] - peaks[i - 1]) / sample_fps for i in range(1, len(peaks))]
        median_gap = sorted(gaps)[len(gaps) // 2]
    else:
        median_gap = None
    duration_est = len(frames) * sample_interval_ms / 1000.0
    switches_per_min = (
        round((len(peaks) / duration_est) * 60, 1) if duration_est > 0 and peaks else None
    )
    wpm_est = None
    if median_gap and median_gap > 0:
        chars_per_switch = 8
        wpm_est = int((chars_per_switch / median_gap) * 60)

    reliable = (not login_blocked) and len(peaks) >= 2 and median_gap is not None

    return {
        "frames": len(frames),
        "duration_est_sec": round(duration_est, 1),
        "login_overlay_scores": login_scores,
        "login_blocked": login_blocked,
        "motion_mean_diff": round(motion_mean, 4),
        "subtitle_switch_ms": int(median_gap * 1000) if median_gap else None,
        "switches_per_min": switches_per_min,
        "words_per_minute_est": wpm_est if reliable else None,
        "change_peaks": len(peaks),
        "pace_label": _pace_label(median_gap, wpm_est) if reliable else "未证实",
        "reliable": reliable,
        "note": "login_modal" if login_blocked else ("static_slide" if len(peaks) < 2 else "ok"),
    }


def _pace_label(gap: float | None, wpm: int | None) -> str:
    if wpm and wpm >= 270:
        return "极快"
    if wpm and wpm >= 240:
        return "快"
    if wpm and wpm >= 210:
        return "中快"
    if gap and gap >= 0.9:
        return "慢"
    return "中"


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for v in corpus.get("videos", []):
        vid = str(v["id"])
        cap = GITHUB_DAILY / CAPTURE_SUBDIR / vid
        if not cap.is_dir():
            cap = CAPTURES / vid
        kf_dir = cap / "keyframes"
        kfs = [str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted(kf_dir.glob("*.png"))] if kf_dir.is_dir() else []
        analysis = analyze_capture_dir(cap) if cap.is_dir() else None
        rows.append(
            {
                "video_id": vid,
                "title": v.get("title", ""),
                "platform": v.get("platform", "douyin"),
                "url": v.get("url", ""),
                "keyframes": kfs,
                "voice_analysis": analysis,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "analyze_voice_from_captures.py",
        "count": len(rows),
        "videos": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} videos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
