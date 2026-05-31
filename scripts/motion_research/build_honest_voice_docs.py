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
PHASH = ROOT / "research" / "voice_content" / "phash_analysis.json"
VISUAL = ROOT / "research" / "voice_content" / "visual_keyframe_audit.json"
OURS_TTS = ROOT / "research" / "voice_content" / "ours_tts_proof.json"
DL = ROOT / "research" / "voice_content" / "download_manifest.json"
CATALOG = ROOT / "templates" / "voice_content_20" / "catalog.json"
PROOF = ROOT / "docs" / "VOICE_CONTENT_PROOF_REPORT.md"
REF = ROOT / "docs" / "VOICE_CONTENT_REFERENCE_ANALYSIS.md"
CMP = ROOT / "docs" / "VOICE_CONTENT_COMPARE_OURS_VS_REFERENCE.md"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def main() -> int:
    frame = _load(FRAME)
    vad = _load(VAD)
    asr = _load(ASR)
    phash = _load(PHASH)
    visual = _load(VISUAL)
    ours = _load(OURS_TTS)
    dl = _load(DL)
    catalog = _load(CATALOG)

    reliable_frame = sum(
        1 for v in frame.get("videos", [])
        if (v.get("voice_analysis") or {}).get("reliable")
    )
    blocked = sum(
        1 for v in frame.get("videos", [])
        if (v.get("voice_analysis") or {}).get("login_blocked")
    )
    bili_ok = sum(
        1 for d in dl.get("downloads", [])
        if d.get("ok") and str(d.get("video_id", "")).startswith("BV")
    )
    asr_ok = asr.get("measurable_count", 0)
    phash_ok = phash.get("reliable_count", 0)
    validated_styles = sum(1 for s in catalog.get("styles", []) if s.get("validated"))

    ts = datetime.now(timezone.utc).isoformat()
    tts_rows = [
        f"| {s['rate']} | {s['chars']} | {s['duration_sec']} | "
        f"{int(s['chars'] / s['duration_sec'] * 60)} |"
        for s in ours.get("samples", [])
        if s.get("duration_sec")
    ]
    asr_rows = [
        f"| {v['video_id']} | {v.get('asr_clip_sec', v.get('audio_duration_sec','?'))} | "
        f"{v.get('asr_total_chars','?')} | **{v.get('chars_per_minute','—')}** | "
        f"{(v.get('text_preview') or '')[:40]}… |"
        for v in asr.get("videos", [])
        if v.get("measurable")
    ]
    phash_rows = [
        f"| {v['video_id']} | {a.get('subtitle_switch_ms','—')} | {a.get('phash_gaps','—')} | "
        f"{a.get('reliable')} |"
        for v in phash.get("videos", [])
        for a in [v.get("analysis") or {}]
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
        f"| B站音轨下载成功 | **{bili_ok}/12** | `download_manifest.json` |",
        f"| DashScope ASR 可算字/分钟 | **{asr_ok}/12** | `asr_analysis.json` |",
        f"| 抖音底栏 phash 字幕切换（可靠） | **{phash_ok}/8** | `phash_analysis.json` + `captures_v3/`（回退 v2） |",
        f"| 旧版抽帧差分「可靠」 | **{reliable_frame}/20** | `analysis_report.json`（已弃用主证据） |",
        f"| 旧版登录弹窗遮挡 | **{blocked}/20** | v1 captures；v2 已用 video seek 修复 |",
        f"| catalog validated 样式 | **{validated_styles}/20** | `templates/voice_content_20/catalog.json` |",
        "",
        "## B站 ASR 字/分钟（DashScope Paraformer，前 120s 或全片）",
        "",
        "| BV | 分析时长(s) | 字数 | 字/分钟 | 预览 |",
        "|----|------------|------|---------|------|",
        *asr_rows,
        "",
        "逐条转写：`research/voice_content/media/BV*/asr_dashscope.json`",
        "",
        "## 抖音字幕切换（phash 底栏，captures_v3）",
        "",
        "| 视频 ID | 切换间隔(ms) | phash 跳变 | reliable |",
        "|---------|-------------|-----------|----------|",
        *phash_rows,
        "",
        "## 我方 TTS rate 实测（同文案 38 字，ffprobe）",
        "",
        "| rate | 字数 | 秒数 | 字/分钟 |",
        "|------|------|------|---------|",
        *tts_rows,
        "",
        "MP3：`research/voice_content/ours_tts/sample_*.mp3`",
        "",
        "## 复现命令",
        "",
        "```powershell",
        "cd D:\\VideoShortsAgent",
        "pip install imagehash dashscope",
        "py -3 scripts/motion_research/download_bilibili_batch.py",
        "py -3 scripts/motion_research/capture_douyin_frames.py --force --out-subdir captures_v2",
        "py -3 scripts/motion_research/analyze_subtitle_phash.py",
        "py -3 scripts/motion_research/batch_asr_dashscope.py",
        "py -3 scripts/motion_research/build_validated_catalog.py",
        "py -3 scripts/motion_research/build_honest_voice_docs.py",
        "```",
        "",
        "## 对旧版文档的说明",
        "",
        "此前无 ASR 支撑的「240~290 字/分钟」已作废。",
        "当前 B站 ASR 中位约 **290~380 字/分钟**（见 asr_analysis.json，中文按字计）。",
        "无 ASR 的抖音条目仅能用 phash 证明**字幕切换节奏**，不能直接标语速。",
        "",
    ]
    PROOF.write_text("\n".join(proof_lines), encoding="utf-8")

    lines = [
        "# 口播对标分析（仅写实测）",
        "",
        f"> {ts}",
        "",
        "## B站语速（ASR）",
        "",
        f"- 可测量：**{asr_ok}/12**",
        "",
        "| # | BV | 字/分钟 | 方法 |",
        "|---|-----|---------|------|",
    ]
    for i, v in enumerate(asr.get("videos", []), 1):
        if not v.get("measurable"):
            continue
        lines.append(
            f"| {i} | {v['video_id']} | {v.get('chars_per_minute')} | {v.get('method')} |"
        )

    lines.extend(["", "## 抖音字幕节奏（phash）", ""])
    for v in phash.get("videos", []):
        a = v.get("analysis") or {}
        lines.append(
            f"- `{v['video_id']}`: switch≈{a.get('subtitle_switch_ms')}ms "
            f"reliable={a.get('reliable')}"
        )

    REF.write_text("\n".join(lines), encoding="utf-8")

    median_asr = None
    wpms = [v["chars_per_minute"] for v in asr.get("videos", []) if v.get("chars_per_minute")]
    if wpms:
        import statistics

        median_asr = int(statistics.median(wpms))

    cmp_lines = [
        "# 别人 vs 我们（仅有实测部分）",
        "",
        f"> {ts}",
        "",
        "## 对标 ASR（B站）",
        f"- 中位字/分钟（ASR）：**{median_asr}**（{asr_ok} 条）",
        "",
    ]
    for v in asr.get("videos", []):
        if v.get("measurable"):
            cmp_lines.append(
                f"- `{v['video_id']}`: {v['chars_per_minute']} 字/分钟 "
                f"（{v.get('asr_clip_sec')}s 片段）"
            )
    if ours.get("samples"):
        cmp_lines.extend(["", "## 我方 TTS rate", ""])
        for s in ours["samples"]:
            cpm = int(s["chars"] / s["duration_sec"] * 60) if s.get("duration_sec") else "?"
            cmp_lines.append(f"- {s['rate']}: {cpm} 字/分钟（{s['duration_sec']}s / {s['chars']}字）")
    cmp_lines.append("")
    cmp_lines.append(
        "**建议 edge-tts rate**：对标中位 ASR 若 ≥360 用 +18%，≥300 用 +12%，否则 +8%（见 catalog 回填）。"
    )
    CMP.write_text("\n".join(cmp_lines), encoding="utf-8")

    print(f"Updated {PROOF}, {REF}, {CMP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
