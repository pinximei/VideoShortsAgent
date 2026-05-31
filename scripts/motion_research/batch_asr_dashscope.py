#!/usr/bin/env python3
"""批量 DashScope Paraformer 转写 B站音轨 → asr_analysis.json。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dashscope_asr_util import ROOT, extract_text, load_env

MEDIA = ROOT / "research" / "voice_content" / "media"
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
OUT = ROOT / "research" / "voice_content" / "asr_analysis.json"
MAX_ASR_SEC = 120


def _probe_duration(audio: Path) -> float:
    return float(
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


def _to_wav(audio: Path, *, max_sec: float | None) -> Path:
    wav = audio.parent / "_asr_clip.wav"
    cmd = ["ffmpeg", "-y", "-i", str(audio)]
    if max_sec and max_sec > 0:
        cmd.extend(["-t", str(max_sec)])
    cmd.extend(["-ar", "16000", "-ac", "1", str(wav)])
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav


def _transcribe(wav: Path, key: str) -> tuple[str, list[dict]]:
    import dashscope
    from dashscope.audio.asr import Recognition

    dashscope.api_key = key
    rec = Recognition(
        model="paraformer-realtime-v2",
        format="wav",
        sample_rate=16000,
        callback=None,
    )
    result = rec.call(str(wav))
    if result.status_code != 200:
        raise RuntimeError(getattr(result, "message", str(result)))
    return extract_text(getattr(result, "output", None))


def _bilibili_ids() -> list[str]:
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return [str(v["id"]) for v in data.get("videos", []) if v.get("platform") == "bilibili"]


def main() -> int:
    load_env()
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not key:
        print("DASHSCOPE_API_KEY missing (.env)")
        return 1
    try:
        import dashscope  # noqa: F401
    except ImportError:
        print("pip install dashscope")
        return 1

    results: list[dict] = []
    for vid in _bilibili_ids():
        dest = MEDIA / vid
        audios = [
            f
            for f in dest.iterdir()
            if f.is_file() and f.suffix in (".m4a", ".mp3", ".webm", ".opus") and f.stat().st_size > 3000
        ] if dest.is_dir() else []
        if not audios:
            results.append({"video_id": vid, "measurable": False, "error": "no_audio"})
            continue
        audio = audios[0]
        per_file = audio.parent / "asr_dashscope.json"
        print(f"[asr] {vid} …")
        try:
            dur_total = _probe_duration(audio)
            clip_sec = min(dur_total, MAX_ASR_SEC) if dur_total > MAX_ASR_SEC else dur_total
            wav = _to_wav(audio, max_sec=clip_sec)
            text, sentences = _transcribe(wav, key)
            chars = len(text.replace(" ", ""))
            if sentences:
                span_ms = max((s.get("end_ms") or 0) for s in sentences) - min(
                    (s.get("begin_ms") or 0) for s in sentences
                )
                span_sec = span_ms / 1000.0 if span_ms > 500 else clip_sec
            else:
                span_sec = clip_sec
            cpm = int(chars / span_sec * 60) if span_sec > 1 and chars else None
            payload = {
                "text": text[:2000],
                "chars": chars,
                "duration_sec": round(clip_sec, 2),
                "speech_span_sec": round(span_sec, 2),
                "audio_duration_sec": round(dur_total, 2),
                "chars_per_minute": cpm,
                "clipped": dur_total > MAX_ASR_SEC,
                "sentences": sentences[:30],
            }
            per_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(
                {
                    "video_id": vid,
                    "audio": str(audio.relative_to(ROOT)).replace("\\", "/"),
                    "audio_duration_sec": round(dur_total, 2),
                    "asr_clip_sec": round(clip_sec, 2),
                    "asr_total_chars": chars,
                    "chars_per_minute": cpm,
                    "measurable": cpm is not None and chars >= 20,
                    "method": "dashscope_paraformer_v2",
                    "clipped": dur_total > MAX_ASR_SEC,
                    "transcript": str(per_file.relative_to(ROOT)).replace("\\", "/"),
                    "text_preview": text[:120],
                }
            )
            print(f"  ok chars={chars} cpm={cpm}")
        except Exception as exc:
            results.append({"video_id": vid, "measurable": False, "error": str(exc)[:400]})
            print(f"  fail {exc}")

    out_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "batch_asr_dashscope.py",
        "max_asr_sec": MAX_ASR_SEC,
        "measurable_count": sum(1 for r in results if r.get("measurable")),
        "videos": results,
    }
    OUT.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} measurable={out_payload['measurable_count']}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
