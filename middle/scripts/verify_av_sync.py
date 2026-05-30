#!/usr/bin/env python3
"""对照落盘分镜与成片时长，检查音画同步（不重复调用 Edge TTS）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(ROOT))


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
        errors="replace",
    )
    return float((r.stdout or "0").strip() or 0)


def stream_durations(path: Path) -> dict[str, float]:
    r = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_entries", "stream=codec_type,duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
        errors="replace",
    )
    out: dict[str, float] = {}
    try:
        data = json.loads(r.stdout or "{}")
        for st in data.get("streams") or []:
            if not isinstance(st, dict) or st.get("duration") is None:
                continue
            ct = st.get("codec_type")
            if ct and ct not in out:
                out[ct] = float(st["duration"])
    except Exception:
        pass
    return out


def main() -> int:
    task_arg = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    task = Path(task_arg).resolve() if task_arg else ROOT / "data/output/838"
    if not task.is_dir():
        print(f"任务目录不存在: {task}", file=sys.stderr)
        return 1

    issues: list[str] = []

    for plat in ("xhs", "douyin"):
        plan_path = task / "llm" / f"video_clips_{plat}.json"
        mp4 = task / "videos" / f"{plat}.mp4"
        if not plan_path.is_file():
            issues.append(f"{plat}: 缺少分镜 {plan_path.name}")
            continue
        if not mp4.is_file():
            issues.append(f"{plat}: 缺少成片 {mp4.name}")
            continue

        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        clips = plan.get("clips") or []
        fx = plan.get("effects") or {}
        td = float(fx.get("transition_duration", 0.25))
        n = len(clips)
        tts_durs = plan.get("tts_durations") or []
        if tts_durs:
            tts_sum = sum(float(x) for x in tts_durs)
        else:
            # 无落盘时长时用字数粗估（与 pipeline_render 一致）
            tts_sum = sum(
                max(2.5, min(18.0, len(str(c.get("tts_text") or "")) / 3.8))
                for c in clips
            )
        bookends = 2.2 if fx.get("intro_card") and plat == "douyin" else 0.0
        if fx.get("outro_card"):
            bookends += 2.0
        expected = tts_sum + bookends
        if n > 1:
            expected -= (n - 1) * td

        actual = probe_duration(mp4)
        streams = stream_durations(mp4)
        vd = streams.get("video")
        ad = streams.get("audio")
        av_delta = actual - expected

        starts = [round(float(c.get("start") or 0), 2) for c in clips]
        broll_ok = len(set(starts)) > 1 or (len(starts) == 1 and starts[0] == 0)

        print(f"\n=== {plat}.mp4 ===")
        print(f"  成片时长: {actual:.2f}s (视频轨 {vd or 'n/a'}s / 音频轨 {ad or 'n/a'}s)")
        print(f"  计划段数: {n}  TTS合计(落盘/估算): {tts_sum:.2f}s  片头片尾约: {bookends:.1f}s")
        print(f"  预期约: {expected:.2f}s  Δ={av_delta:+.2f}s {'OK' if abs(av_delta) < 4.0 else 'WARN'}")
        print(f"  B-roll 起点: {starts} {'OK' if broll_ok else 'WARN'}")
        if vd and ad and abs(vd - ad) > 0.6:
            issues.append(f"{plat}: 视音轨时长差 {abs(vd - ad):.2f}s > 0.6s")
        if abs(av_delta) >= 4.0:
            issues.append(f"{plat}: 成片与预期时长偏差 {av_delta:+.1f}s")
        if not broll_ok and n > 1:
            issues.append(f"{plat}: B-roll 多段起点未拉开")

    print("\n=== 结论 ===")
    if issues:
        for x in issues:
            print(f"  ✗ {x}")
        return 1
    print("  通过（基于落盘分镜 + ffprobe，未调用 Edge TTS）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
