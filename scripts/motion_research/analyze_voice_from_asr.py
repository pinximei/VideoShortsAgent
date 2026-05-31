#!/usr/bin/env python3
"""对已下载音轨做 ASR，实测字/分钟（可复现）。"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "research" / "voice_content" / "media"
OUT = ROOT / "research" / "voice_content" / "asr_analysis.json"


def _audio_duration(path: Path) -> float:
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return float(p.stdout.strip())


def _transcribe(audio: Path) -> list[dict]:
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio), language="zh", vad_filter=True)
    rows = []
    for seg in segments:
        t = re.sub(r"\s+", "", seg.text or "")
        if t:
            rows.append(
                {
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": t,
                    "chars": len(t),
                }
            )
    return rows


def main() -> int:
    results: list[dict] = []
    for vid_dir in sorted(MEDIA.iterdir()):
        if not vid_dir.is_dir():
            continue
        audios = list(vid_dir.glob("audio.*"))
        if not audios:
            continue
        audio = audios[0]
        print(f"[asr] {vid_dir.name} …")
        try:
            dur = _audio_duration(audio)
            segs = _transcribe(audio)
            chars = sum(s["chars"] for s in segs)
            span = max(s["end"] for s in segs) - min(s["start"] for s in segs) if segs else 0
            cpm = int((chars / span) * 60) if span > 3 else None
            results.append(
                {
                    "video_id": vid_dir.name,
                    "audio": str(audio.relative_to(ROOT)).replace("\\", "/"),
                    "audio_duration_sec": round(dur, 2),
                    "asr_segments": len(segs),
                    "asr_total_chars": chars,
                    "asr_speech_span_sec": round(span, 2),
                    "chars_per_minute": cpm,
                    "measurable": bool(segs) and cpm is not None,
                    "method": "faster_whisper_base",
                    "sample_segments": segs[:8],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "video_id": vid_dir.name,
                    "measurable": False,
                    "error": str(exc)[:300],
                }
            )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "analyze_voice_from_asr.py",
        "measurable_count": sum(1 for r in results if r.get("measurable")),
        "videos": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} measurable={payload['measurable_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
