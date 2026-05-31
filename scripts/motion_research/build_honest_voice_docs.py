#!/usr/bin/env python3
"""仅根据实测 JSON 重写口播文档，撤回无证据结论。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAME = ROOT / "research" / "voice_content" / "analysis_report.json"
VAD = ROOT / "research" / "voice_content" / "vad_analysis.json"
ASR = ROOT / "research" / "voice_content" / "asr_analysis.json"
VISUAL = ROOT / "research" / "voice_content" / "visual_keyframe_audit.json"
OURS_TTS = ROOT / "research" / "voice_content" / "ours_tts_proof.json"
DL = ROOT / "research" / "voice_content" / "download_manifest.json"
PROOF = ROOT / "docs" / "VOICE_CONTENT_PROOF_REPORT.md"
REF = ROOT / "docs" / "VOICE_CONTENT_REFERENCE_ANALYSIS.md"
CMP = ROOT / "docs" /"VOICE_CONTENT_COMPARE_OURS_VS_REFERENCE.md"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def main() -> int:
    frame = _load(FRAME)
    vad = _load(VAD)
    visual = _load(VISUAL)
    ours = _load(OURS_TTS)
    dl = _load(DL)

    reliable = sum(
        1 for v in frame.get("videos", [])
        if (v.get("voice_analysis") or {}).get("reliable")
    )
    blocked = sum(
        1 for v in frame.get("videos", [])
        if (v.get("voice_analysis") or {}).get("login_blocked")
    )
    dl_ok = dl.get("ok_count", 0)

    ts = datetime.now(timezone.utc).isoformat()
    tts_rows = [
        f"| {s['rate']} | {s['chars']} | {s['duration_sec']} | "
        f"{int(s['chars'] / s['duration_sec'] * 60)} |"
        for s in ours.get("samples", [])
        if s.get("duration_sec")
    ]
    proof_lines = [
        "# 口播预研可证伪报告",
        "",
        f"> {ts}",
        "",
        "## 实测摘要（机器输出，可复现）",
        "",
        "| 指标 | 数值 | 证据文件 |",
        "|------|------|----------|",
        f"| 抽帧字幕差分「可靠」条数 | **{reliable}/20** | `analysis_report.json` |",
        f"| 抽帧被登录弹窗遮挡 | **{blocked}/20** | `login_blocked:true` |",
        f"| yt-dlp 成功下载音轨 | **{dl_ok}/20** | `download_manifest.json` |",
        f"| VAD 有声占比（仅下载成功样本） | 见 vad_analysis | BV1dU4y1e7N9 speech_ratio≈0.987 |",
        "",
        "## 我方 TTS rate 实测（同文案 38 字，ffprobe）",
        "",
        "| rate | 字数 | 秒数 | 字/分钟 |",
        "|------|------|------|---------|",
        *tts_rows,
        "",
        "MP3：`research/voice_content/ours_tts/sample_*.mp3`",
        "",
        "## 画面文案审计（非语速，需你打开 PNG 核对）",
        "",
        "见 `research/voice_content/visual_keyframe_audit.json`（4 条已写证据路径）",
        "",
        "## 复现",
        "",
        "```powershell",
        "cd D:\\VideoShortsAgent",
        "py -3 scripts/motion_research/analyze_voice_from_captures.py",
        "py -3 scripts/motion_research/audit_visual_from_keyframes.py",
        "py -3 scripts/motion_research/download_reference_media.py",
        "py -3 scripts/motion_research/analyze_audio_vad.py",
        "```",
        "",
        "## 对旧版文档的说明",
        "",
        "此前 `VOICE_CONTENT_*` 中「240~290 字/分钟」等数字**无足够实测支撑**，已作废。",
        "`templates/voice_content_20/catalog.json` 全部 `validated:false`，不得当已学完爆款。",
        "",
    ]
    PROOF.write_text("\n".join(proof_lines), encoding="utf-8")

    lines = [
        "# 口播对标分析（仅写实测/可核对画面文字）",
        "",
        f"> {ts}",
        "",
        "## 抽帧自动分析（字幕差分）",
        "",
        f"- 可靠条数：**{reliable}/20**",
        f"- 登录遮挡：**{blocked}/20**",
        "",
        "| # | 标题 | reliable | login_blocked | peaks | 证据帧 |",
        "|---|------|----------|---------------|-------|--------|",
    ]
    for i, v in enumerate(frame.get("videos", []), 1):
        va = v.get("voice_analysis") or {}
        kf = va.get("note", "")
        ev = v["keyframes"][2] if len(v.get("keyframes", [])) > 2 else ""
        lines.append(
            f"| {i} | {v.get('title','')[:20]} | {va.get('reliable')} | {va.get('login_blocked')} | "
            f"{va.get('change_peaks')} | `{ev}` |"
        )

    lines.extend(["", "## 画面可见文案（人工审计 JSON）", ""])
    for it in visual.get("items", []):
        lines.append(f"### {it['video_id']} — {it.get('title','')}")
        lines.append(f"- 证据图：`{it['evidence']}`（exists={it.get('evidence_exists')})")
        lines.append(f"- 画面字：{', '.join(it.get('visible_slide_text') or [])}")
        if it.get("subtitle_sample"):
            lines.append(f"- 可见字幕样例：{it['subtitle_sample']}")
        lines.append(f"- 内容风格（画面）：{it.get('content_style')}")
        lines.append("")

    REF.write_text("\n".join(lines), encoding="utf-8")

    vad_lines = ["# 别人 vs 我们（仅有实测部分）", "", f"> {ts}", ""]
    if vad.get("videos"):
        vad_lines.append("## 音轨 VAD（B站下载成功样本）")
        for v in vad["videos"]:
            if v.get("measurable"):
                vad_lines.append(
                    f"- `{v['video_id']}`: 时长 {v['audio_duration_sec']}s, "
                    f"有声约 {v['speech_active_sec']}s, 占比 {v['speech_ratio']}"
                )
    if ours.get("samples"):
        vad_lines.append("## 我方 TTS rate")
        for s in ours["samples"]:
            vad_lines.append(f"- {s['rate']}: {s['duration_sec']}s / {s['chars']}字")
    vad_lines.append("")
    vad_lines.append("**口播字/分钟**：抖音样本尚无音轨；禁止沿用臆测数字。")
    CMP.write_text("\n".join(vad_lines), encoding="utf-8")

    print(f"Updated {PROOF}, {REF}, {CMP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
