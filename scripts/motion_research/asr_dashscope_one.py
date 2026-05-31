#!/usr/bin/env python3
"""DashScope Paraformer 转写单条音轨（需 DASHSCOPE_API_KEY）。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dashscope_asr_util import ROOT, extract_text, load_env


def main() -> int:
    load_env()
    if len(sys.argv) < 2:
        print("usage: asr_dashscope_one.py <audio.m4a>")
        return 1
    audio = Path(sys.argv[1]).resolve()
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not key:
        print("DASHSCOPE_API_KEY missing")
        return 1

    try:
        import dashscope
        from dashscope.audio.asr import Recognition
    except ImportError:
        print("pip install dashscope")
        return 1

    dashscope.api_key = key
    wav = audio.with_suffix(".wav")
    if not wav.is_file():
        subprocess.check_call(
            ["ffmpeg", "-y", "-i", str(audio), "-ar", "16000", "-ac", "1", str(wav)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    rec = Recognition(
        model="paraformer-realtime-v2",
        format="wav",
        sample_rate=16000,
        callback=None,
    )
    result = rec.call(str(wav))
    if result.status_code != 200:
        print(result.message)
        return 1
    text, sentences = extract_text(getattr(result, "output", None))
    out = audio.parent / "asr_dashscope.json"
    dur = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio),
            ],
            text=True,
        ).strip()
    )
    chars = len(text.replace(" ", ""))
    if sentences:
        span_ms = max((s.get("end_ms") or 0) for s in sentences) - min(
            (s.get("begin_ms") or 0) for s in sentences
        )
        span = span_ms / 1000.0 if span_ms > 500 else dur
    else:
        span = dur
    cpm = int(chars / span * 60) if span > 1 and chars else None
    payload = {
        "text": text,
        "chars": chars,
        "duration_sec": dur,
        "speech_span_sec": round(span, 2),
        "chars_per_minute": cpm,
        "sentences": sentences[:30],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
