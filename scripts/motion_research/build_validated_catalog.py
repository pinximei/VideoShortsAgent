#!/usr/bin/env python3
"""用实测数据回填 voice_content_20：仅有 measured 的条目 validated=true。"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python_agent.tts_params import (  # noqa: E402
    GITHUB_DAILY_TTS_BASELINE,
    pitch_from_subtitle_ms,
    pause_from_subtitle_ms,
    rate_from_measured_wpm,
    rate_from_subtitle_ms,
)
CATALOG = ROOT / "templates" / "voice_content_20" / "catalog.json"
MEDIA = ROOT / "research" / "voice_content" / "measured_analysis.json"
VAD = ROOT / "research" / "voice_content" / "vad_analysis.json"
ASR = ROOT / "research" / "voice_content" / "asr_analysis.json"
PHASH = ROOT / "research" / "voice_content" / "phash_analysis.json"
FRAME = ROOT / "research" / "voice_content" / "analysis_report.json"
OUT_MAP = ROOT / "research" / "voice_content" / "validated_mapping.json"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def rate_from_wpm(wpm: int | None) -> str:
    return rate_from_measured_wpm(wpm)


def main() -> int:
    catalog = _load(CATALOG)
    media = _load(MEDIA)
    vad = {v["video_id"]: v for v in _load(VAD).get("videos", [])}
    asr = {v["video_id"]: v for v in _load(ASR).get("videos", []) if v.get("measurable")}
    phash = {
        v["video_id"]: v["analysis"]
        for v in _load(PHASH).get("videos", [])
        if (v.get("analysis") or {}).get("reliable")
    }

    measured_rows: list[dict] = []
    seen: set[str] = set()
    for v in media.get("videos", []):
        if v.get("measurable") and v.get("chars_per_minute"):
            measured_rows.append(v)
            seen.add(v.get("video_id", ""))
    for vid, v in asr.items():
        if vid not in seen:
            row = dict(v)
            pa = phash.get(vid)
            if pa:
                row["subtitle_switch_ms"] = pa.get("subtitle_switch_ms")
            measured_rows.append(row)
            seen.add(vid)
    for vid, pa in phash.items():
        if vid in seen:
            continue
        sub_ms = pa.get("subtitle_switch_ms")
        measured_rows.append(
            {
                "video_id": vid,
                "subtitle_switch_ms": sub_ms,
                "method": pa.get("method", "phash_bottom_band"),
                "phash_only": True,
                "edge_tts_rate": rate_from_subtitle_ms(int(sub_ms)) if sub_ms else None,
                "edge_tts_pitch": pitch_from_subtitle_ms(int(sub_ms) if sub_ms else None),
                "sentence_pause_sec": pause_from_subtitle_ms(int(sub_ms) if sub_ms else None),
            }
        )

    wpms = [r["chars_per_minute"] for r in measured_rows if r.get("chars_per_minute")]
    median_wpm = int(statistics.median(wpms)) if wpms else None

    for s in catalog.get("styles", []):
        s["validated"] = False
        s["measured_ref"] = None
        s["validation_note"] = "no_measurement_yet"

    # 有实测的样本：按 chars_per_minute 排序，映射到前 N 个 style 槽位
    measured_rows.sort(key=lambda x: x.get("chars_per_minute") or 0)
    styles = catalog.get("styles", [])
    mapping: list[dict] = []
    for i, row in enumerate(measured_rows):
        if i >= len(styles):
            break
        st = styles[i]
        wpm = row.get("chars_per_minute")
        st["validated"] = bool(wpm) or bool(row.get("subtitle_switch_ms"))
        st["measured_ref"] = row.get("video_id")
        if wpm:
            st["words_per_minute"] = wpm
            st["edge_tts_rate"] = rate_from_wpm(wpm)
            st["edge_tts_pitch"] = pitch_from_subtitle_ms(row.get("subtitle_switch_ms"))
            st["tts_voice"] = GITHUB_DAILY_TTS_BASELINE["tts_voice"]
        elif row.get("phash_only"):
            st["validation_note"] = "phash_subtitle_timing_only"
            st["phash_only"] = True
            sub_ms = row.get("subtitle_switch_ms")
            if sub_ms:
                st["subtitle_switch_ms"] = sub_ms
                st["edge_tts_rate"] = row.get("edge_tts_rate") or rate_from_subtitle_ms(int(sub_ms))
                st["edge_tts_pitch"] = row.get("edge_tts_pitch") or pitch_from_subtitle_ms(int(sub_ms))
                st["sentence_pause_sec"] = row.get("sentence_pause_sec") or pause_from_subtitle_ms(
                    int(sub_ms)
                )
            st["tts_voice"] = GITHUB_DAILY_TTS_BASELINE["tts_voice"]
        gap = row.get("cue_gap_median_sec")
        if gap:
            st["sentence_pause_sec"] = round(max(0.1, min(0.35, gap * 0.4)), 2)
        if row.get("subtitle_switch_ms"):
            st["subtitle_switch_ms"] = row["subtitle_switch_ms"]
        st["validation_note"] = row.get("method", "measured")
        vad_row = vad.get(row.get("video_id", ""), {})
        if vad_row.get("speech_ratio"):
            st["speech_ratio"] = vad_row["speech_ratio"]
        mapping.append({"style_id": st["id"], "video_id": row.get("video_id"), "wpm": wpm})

    catalog["tts_baseline"] = dict(GITHUB_DAILY_TTS_BASELINE)
    catalog["catalog_status"] = (
        f"PARTIAL_VALIDATED_{sum(1 for s in styles if s.get('validated'))}_of_{len(styles)}"
    )
    catalog["median_measured_wpm"] = median_wpm
    catalog["updated_at"] = datetime.now(timezone.utc).isoformat()

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MAP.write_text(
        json.dumps(
            {"mapping": mapping, "measured_count": len(measured_rows), "median_wpm": median_wpm},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"validated {len(mapping)}/{len(styles)} styles, median_wpm={median_wpm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
