#!/usr/bin/env python3
"""对所有 media/*/audio*.m4a 做 faster-whisper tiny ASR → 字/分钟。"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "research" / "voice_content" / "media"
OUT = ROOT / "research" / "voice_content" / "asr_analysis.json"


def _probe_duration(audio: Path) -> float:
    p = subprocess.run(
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
        capture_output=True,
        text=True,
    )
    return float(p.stdout.strip())


def main() -> int:
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from faster_whisper import WhisperModel

    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    results: list[dict] = []

    for d in sorted(MEDIA.iterdir()):
        if not d.is_dir():
            continue
        audios = [f for f in d.iterdir() if f.suffix in (".m4a", ".mp3", ".webm", ".opus") and f.stat().st_size > 3000]
        if not audios:
            continue
        audio = audios[0]
        print(f"[asr] {d.name} ({audio.stat().st_size // 1024} KB) …")
        try:
            dur_total = _probe_duration(audio)
            segments, _ = model.transcribe(str(audio), language="zh", vad_filter=True)
            segs = []
            for seg in segments:
                t = (seg.text or "").replace(" ", "").strip()
                if t:
                    segs.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": t, "chars": len(t)})
            if not segs:
                results.append({"video_id": d.name, "measurable": False, "error": "no_segments"})
                continue
            chars = sum(s["chars"] for s in segs)
            span = max(s["end"] for s in segs) - min(s["start"] for s in segs)
            cpm = int(chars / span * 60) if span > 1 else None
            transcript_path = d / "asr_transcript.json"
            transcript_path.write_text(json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(
                {
                    "video_id": d.name,
                    "audio": str(audio.relative_to(ROOT)).replace("\\", "/"),
                    "audio_duration_sec": round(dur_total, 2),
                    "asr_segments": len(segs),
                    "asr_total_chars": chars,
                    "asr_speech_span_sec": round(span, 2),
                    "chars_per_minute": cpm,
                    "measurable": cpm is not None,
                    "method": "faster_whisper_tiny",
                    "transcript": str(transcript_path.relative_to(ROOT)).replace("\\", "/"),
                    "sample_segments": segs[:5],
                }
            )
        except Exception as exc:
            results.append({"video_id": d.name, "measurable": False, "error": str(exc)[:400]})

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "batch_asr_all_media.py",
        "measurable_count": sum(1 for r in results if r.get("measurable")),
        "videos": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} measurable={payload['measurable_count']}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
