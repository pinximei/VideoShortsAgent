#!/usr/bin/env python3
"""生成口播/语速对标分析 + 我方样例对比文档。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "research" / "voice_content" / "analysis_report.json"
CATALOG = ROOT / "templates" / "voice_content_20" / "catalog.json"
OURS = ROOT / "research" / "voice_content" / "ours_samples.json"
REF_DOC = ROOT / "docs" / "VOICE_CONTENT_REFERENCE_ANALYSIS.md"
TMPL_DOC = ROOT / "docs" / "VOICE_CONTENT_20_TEMPLATES.md"
CMP_DOC = ROOT / "docs" / "VOICE_CONTENT_COMPARE_OURS_VS_REFERENCE.md"

STYLE_MAP = {
    "极快": "V01_burst_hook_fast",
    "快": "V02_tiktok_follow_punch",
    "中快": "V13_marquee_news",
    "中": "V04_minimal_calm",
    "慢": "V20_clean_badge_friend",
}


def main() -> int:
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8")) if ANALYSIS.is_file() else {"videos": []}
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    ours = json.loads(OURS.read_text(encoding="utf-8")) if OURS.is_file() else {"samples": []}
    ts = datetime.now(timezone.utc).isoformat()

    lines = [
        "# 抖音爆款口播/语速对标分析（20 条抽帧）",
        "",
        f"> 生成：{ts}",
        "> 方法：底部字幕带帧差 → 字幕切换间隔 → 估算字/分钟",
        "",
        "## 1. 别人怎么讲",
        "",
        "| 维度 | 爆款共性 |",
        "|------|----------|",
        "| 语速 | 240~290 字/分钟（科技/GitHub 类偏快） |",
        "| 字幕切换 | 450~900ms/页（跟读型更短） |",
        "| 开场 | 3 秒内「别划走/今天这个/Top10」 |",
        "| 句长 | 单句 ≤18 字，少从句 |",
        "| 结构 | 钩子→项目名→2~3 要点→引导 |",
        "",
        "## 2. 逐条视频",
        "",
    ]
    for i, v in enumerate(analysis.get("videos", []), 1):
        va = v.get("voice_analysis") or {}
        lines.append(f"### {i}. {v.get('title', v.get('video_id'))}")
        lines.append("")
        lines.append(f"- **平台**：{v.get('platform')}")
        lines.append(f"- **ID**：`{v['video_id']}`")
        lines.append(f"- **URL**：{v.get('url', '')}")
        if va:
            lines.append(f"- **语速标签**：{va.get('pace_label', '—')}")
            lines.append(f"- **字幕切换间隔**：{va.get('subtitle_switch_ms', '—')} ms")
            lines.append(f"- **估算字/分钟**：{va.get('words_per_minute_est', '—')}")
            lines.append(f"- **建议模板**：`{STYLE_MAP.get(va.get('pace_label', ''), 'V01')}`")
        else:
            lines.append("- ❌ 无抽帧数据")
        if v.get("keyframes"):
            lines.append("")
            lines.append("**关键帧（看字幕节奏/口播态）：**")
            for k in v["keyframes"]:
                lines.append(f"- `{k}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    REF_DOC.write_text("\n".join(lines), encoding="utf-8")

    tmpl_lines = [
        "# 口播/文案 20 套模板（V01–V20）",
        "",
        f"> 生成：{ts}",
        "> 机器目录：`templates/voice_content_20/catalog.json`",
        "",
        "## 与画面模板关系",
        "",
        "每套 Vxx 可通过 `reference_motion` 与 Gxx 配对；也可独立哈希选型。",
        "",
        "| ID | 名称 | TTS rate | 句停顿 | 目标 WPM | 钩子 |",
        "|----|------|----------|--------|----------|------|",
    ]
    for s in catalog.get("styles", []):
        tmpl_lines.append(
            f"| {s['id']} | {s['name']} | {s.get('edge_tts_rate', '')} | "
            f"{s.get('sentence_pause_sec', '')}s | {s.get('words_per_minute', '')} | {s.get('hook_pattern', '')} |"
        )
    tmpl_lines.extend(
        [
            "",
            "## VSA 接线",
            "",
            "- `platform_llm` / `ComposeSkill` 注入 `voice_style_prompt_block`",
            "- `slides_render` 写入 `llm/voice_content_style.json`",
            "- `DubbingSkill(tts_rate=..., sentence_pause=...)`",
            "",
            "复现分析：`py -3 scripts/motion_research/analyze_voice_from_captures.py`",
            "",
        ]
    )
    TMPL_DOC.write_text("\n".join(tmpl_lines), encoding="utf-8")

    cmp_lines = [
        "# 口播风格：别人 vs 我们",
        "",
        f"> 生成：{ts}",
        "",
        "## 差距摘要",
        "",
        "| 维度 | 别人（对标抽帧） | 我们（样例脚本） |",
        "|------|------------------|----------------|",
        "| 语速 | 多数 240+ WPM，字幕 450~700ms 切换 | 需按 Vxx 模板 + edge rate 执行 |",
        "| 开场 | 强钩子 3 秒内 | 已禁止「大家好」；需对齐 V01/V07 |",
        "| 总字数 | 190~250/条 | catalog 每套 total_chars 约束 |",
        "",
        "## 我方 V01–V20 样例口播（供听感/字数检查）",
        "",
    ]
    for s in ours.get("samples", []):
        cmp_lines.append(f"### {s.get('id')}")
        cmp_lines.append("")
        cmp_lines.append(f"- **TTS rate**：{s.get('edge_tts_rate')}")
        cmp_lines.append(f"- **目标 WPM**：{s.get('words_per_minute')}")
        cmp_lines.append(f"- **样例大纲**：")
        for line in s.get("outline", []):
            cmp_lines.append(f"  - {line}")
        cmp_lines.append("")

    CMP_DOC.write_text("\n".join(cmp_lines), encoding="utf-8")
    print(f"Wrote {REF_DOC}, {TMPL_DOC}, {CMP_DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
