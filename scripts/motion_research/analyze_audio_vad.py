#!/usr/bin/env python3
"""ffmpeg silencedetect → 有声时长占比（无需 ASR，可复现）。"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "research" / "voice_content" / "media"
OUT = ROOT / "research" / "voice_content" / "vad_analysis.json"


def analyze(audio: Path) -> dict:
    p = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(audio),
            "-af",
            "silencedetect=noise=-35dB:d=0.35",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log = (p.stderr or "") + (p.stdout or "")
    dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", log)
    if not dur_m:
        return {"measurable": False, "error": "no_duration"}
    h, m, s = dur_m.groups()
    total = int(h) * 3600 + int(m) * 60 + float(s)
    silences: list[tuple[float, float]] = []
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    for st, en in zip(starts, ends):
        silences.append((st, en))
    silence_sum = sum(en - st for st, en in silences)
    speech = max(0.0, total - silence_sum)
    return {
        "measurable": True,
        "audio_duration_sec": round(total, 2),
        "silence_total_sec": round(silence_sum, 2),
        "speech_active_sec": round(speech, 2),
        "speech_ratio": round(speech / total, 3) if total else None,
        "silence_gaps": len(silences),
        "method": "ffmpeg_silencedetect_-35dB",
    }


def main() -> int:
    rows = []
    for d in sorted(MEDIA.iterdir()):
        if not d.is_dir():
            continue
        aud = next(iter(d.glob("audio.*")), None)
        if not aud:
            continue
        print(f"[vad] {d.name}")
        rows.append({"video_id": d.name, "audio": str(aud.relative_to(ROOT)).replace("\\", "/"), **analyze(aud)})
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "videos": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
