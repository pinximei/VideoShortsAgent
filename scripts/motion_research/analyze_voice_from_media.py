#!/usr/bin/env python3
"""从下载的字幕/音频分析真实口播语速（可复现数字）。"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "research" / "voice_content" / "download_manifest.json"
MEDIA = ROOT / "research" / "voice_content" / "media"
OUT = ROOT / "research" / "voice_content" / "measured_analysis.json"


def _probe_duration(audio: Path) -> float | None:
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
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        return None
    try:
        return float(p.stdout.strip())
    except ValueError:
        return None


def _parse_vtt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    cues: list[dict] = []
    blocks = re.split(r"\n\n+", text.strip())
    ts_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
    )

    def _sec(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    for block in blocks:
        m = ts_re.search(block)
        if not m:
            continue
        g = m.groups()
        start = _sec(g[0], g[1], g[2], g[3])
        end = _sec(g[4], g[5], g[6], g[7])
        body = ts_re.sub("", block).strip()
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"\s+", "", body)
        if body:
            cues.append({"start": start, "end": end, "text": body, "chars": len(body)})
    return cues


def analyze_media(vid: str, entry: dict) -> dict:
    dest = MEDIA / vid
    result: dict = {
        "video_id": vid,
        "source": "media",
        "measurable": False,
    }
    vtt = entry.get("subtitle_vtt")
    if vtt:
        path = ROOT / vtt
        if path.is_file():
            cues = _parse_vtt(path)
            if cues:
                total_chars = sum(c["chars"] for c in cues)
                span = max(c["end"] for c in cues) - min(c["start"] for c in cues)
                gaps = []
                for i in range(1, len(cues)):
                    gaps.append(cues[i]["start"] - cues[i - 1]["end"])
                median_gap = sorted(gaps)[len(gaps) // 2] if gaps else None
                wpm = int((total_chars / span) * 60) if span > 1 else None
                result.update(
                    {
                        "measurable": True,
                        "subtitle_cues": len(cues),
                        "total_chars": total_chars,
                        "speech_span_sec": round(span, 2),
                        "chars_per_minute": wpm,
                        "cue_gap_median_sec": round(median_gap, 3) if median_gap is not None else None,
                        "sample_cues": cues[:5],
                        "method": "vtt_parse",
                    }
                )
    aud = entry.get("audio")
    if aud:
        ap = ROOT / aud
        if ap.is_file():
            dur = _probe_duration(ap)
            if dur:
                result["audio_duration_sec"] = round(dur, 2)
    return result


def main() -> int:
    if not MANIFEST.is_file():
        print(f"missing {MANIFEST}, run download_reference_media.py first")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    measured: list[dict] = []
    for d in manifest.get("downloads", []):
        if d.get("ok"):
            measured.append(analyze_media(str(d["video_id"]), d))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "analyze_voice_from_media.py",
        "measurable_count": sum(1 for m in measured if m.get("measurable")),
        "videos": measured,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} measurable={payload['measurable_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
