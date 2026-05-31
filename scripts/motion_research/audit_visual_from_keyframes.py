#!/usr/bin/env python3
"""
人工可核对的关键帧「画面文案」审计（非语速）— 只记录关键帧里肉眼可见的文字结构。
生成后必须由人打开 PNG 复核；每条带 evidence 路径。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
CAPTURES = ROOT / "research" / "motion" / "github_daily" / "captures"
OUT = ROOT / "research" / "voice_content" / "visual_keyframe_audit.json"

# 每条必须对应已打开核对的关键帧；subtitle_visible=是否在画面上看到口播字幕
AUDIT: list[dict] = [
    {
        "video_id": "7618932620755291433",
        "evidence": "research/motion/github_daily/captures/7618932620755291433/keyframes/key_03_055pct.png",
        "login_modal_blocks": True,
        "visible_slide_text": ["GitHub 1.7万颗星", "收藏飙增", "每天一个GitHub热门产品"],
        "subtitle_visible": False,
        "content_style": "数据图表+黄字强调（幻灯片）",
        "speech_measurable": False,
    },
    {
        "video_id": "7641485803578789172",
        "evidence": "research/motion/github_daily/captures/7641485803578789172/keyframes/key_02_035pct.png",
        "login_modal_blocks": True,
        "visible_slide_text": [
            "被低估的开源 AI Agent 项目",
            "Pi AI Agent Toolkit",
            "github.com/comet-works/pi",
            "48.8K",
            "MIT",
            "TypeScript",
        ],
        "subtitle_visible": False,
        "content_style": "浅底徽章+橙词「开源」+仓库头",
        "speech_measurable": False,
    },
    {
        "video_id": "7642633512055475313",
        "evidence": "research/motion/github_daily/captures/7642633512055475313/keyframes/key_02_035pct.png",
        "login_modal_blocks": True,
        "visible_slide_text": ["GitHub AI Skills 热榜 Top10"],
        "subtitle_visible": True,
        "subtitle_sample": "GitHub AI Skills热榜Top10来了，让我们看十月份的第一周，排位如何。",
        "video_duration_label": "01:14",
        "content_style": "黑底榜单+底字幕口播",
        "speech_measurable": False,
        "note": "字幕可见但无音轨，未测真实语速",
    },
    {
        "video_id": "7642198364225948962",
        "evidence": "research/motion/github_daily/captures/7642198364225948962/keyframes/key_02_035pct.png",
        "login_modal_blocks": True,
        "visible_slide_text": ["每天一个优质项目"],
        "subtitle_visible": False,
        "content_style": "米白极简标题（幻灯）",
        "speech_measurable": False,
    },
]


def main() -> int:
    corpus = {v["id"]: v for v in json.loads(CORPUS.read_text(encoding="utf-8"))["videos"]}
    rows = []
    for item in AUDIT:
        vid = item["video_id"]
        v = corpus.get(vid, {})
        ev = ROOT / item["evidence"]
        rows.append(
            {
                **item,
                "title": v.get("title", ""),
                "url": v.get("url", ""),
                "evidence_exists": ev.is_file(),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "画面文字审计，不是 ASR 语速；speech_measurable=false 表示尚未有音轨证明",
        "audited_count": len(rows),
        "items": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} items, verify PNGs manually)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
