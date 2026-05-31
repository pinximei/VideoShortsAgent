#!/usr/bin/env python3
"""生成对标分析文档（20 条视频 × 6 张关键帧路径）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITHUB_DAILY = ROOT / "research" / "motion" / "github_daily"
CAPTURES = GITHUB_DAILY / "captures"
CORPUS = GITHUB_DAILY / "video_corpus.json"
OUT = ROOT / "docs" / "GITHUB_DAILY_REFERENCE_ANALYSIS.md"

# 人工看图后的风格标注（抖音 8 条 + B站 12 条补样本）
STYLE_BY_ID: dict[str, dict] = {
    "7618932620755291433": {
        "style_id": "S01",
        "how": "深紫网格隧道背景(CSS动画) + 居中黄字黑描边 + 可选吉祥物；中段白卡片+折线图",
        "remotion": "ProfileBackground网格 + AnimatedHeading + CSS chart",
    },
    "7641485803578789172": {
        "style_id": "S02",
        "how": "浅灰底幻灯片；顶栏 Logo+仓库URL；标题黑字关键词橙色；底部 pill 徽章(Star/MIT/TS)",
        "remotion": "glass_card + flex badges + spring 入场",
    },
    "7642198364225948962": {
        "style_id": "S03",
        "how": "极简米白底；两行居中黑标题；系列感「每天一个优质项目」",
        "remotion": "minimal_headline + 无装饰",
    },
    "7642633512055475313": {
        "style_id": "S04",
        "how": "纯黑底；DAILY VIDEO 小标签；Top10 榜单标题；口播字幕在底部",
        "remotion": "dark bg + episode_counter + TikTokCaption",
    },
    "7641791711051647030": {
        "style_id": "S04",
        "how": "同热榜/榜单口播系列（黑底白字）",
        "remotion": "同 S04",
    },
    "7643092805896032739": {
        "style_id": "S04",
        "how": "榜单类 Star 排名",
        "remotion": "同 S04",
    },
    "7643043013397623478": {
        "style_id": "S04",
        "how": "AI GitHub Top10",
        "remotion": "同 S04",
    },
    "7641861418416901414": {
        "style_id": "S03",
        "how": "每周精选，偏浅色标题卡",
        "remotion": "minimal_headline",
    },
}


def _keyframes(vid: str) -> list[str]:
    kf_dir = CAPTURES / vid / "keyframes"
    if not kf_dir.is_dir():
        return []
    return [str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted(kf_dir.glob("*.png"))]


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    videos = corpus.get("videos", [])

    lines = [
        "# 「每天一个 GitHub」对标视频抽帧分析（20 条）",
        "",
        f"> 生成：{datetime.now(timezone.utc).isoformat()}",
        "> **请你直接打开下面每条里的图片路径检查**（仓库内相对路径）。",
        "",
        "## 0. 样本说明",
        "",
        "| 来源 | 数量 | 目录 |",
        "|------|------|------|",
        f"| 抖音 | 8 | `research/motion/github_daily/captures/<video_id>/` |",
        f"| B站（补足同赛道剪辑参考） | 12 | 同上，ID 为 BV 号 |",
        "",
        "每条视频抽取 **6 张关键帧**：0% / 15% / 35% / 55% / 75% / 100% 进度。",
        "原始序列帧在 `captures/<id>/f_*.png`（各 20 张）。",
        "",
        "采集命令：",
        "```powershell",
        "py -3 scripts/motion_research/capture_douyin_frames.py --harvest-search --frames 20",
        "py -3 scripts/motion_research/capture_bilibili_frames.py",
        "```",
        "",
        "## 1. 别人怎么做 — 共性（Remotion + CSS）",
        "",
        "| 层级 | 别人做法 | 技术实现 |",
        "|------|----------|----------|",
        "| 背景 | 深色纯黑 / 浅灰米白 / 紫蓝网格隧道 | CSS `linear-gradient` + `@keyframes` 移动网格线 |",
        "| 标题 | 大字居中，黄字黑描边 或 黑字橙强调 | Remotion `spring` 按词砸入 |",
        "| 数据 | Star 数、MIT 徽章、语言标签 | Flex row + 圆角 pill（纯 CSS） |",
        "| 图表 | 折线上涨、卡片浮层 | SVG/Canvas 或 div+CSS 动画高度 |",
        "| 口播字幕 | 底部白字 或 绿字跟读 | `TikTokActiveCaption` / ASS |",
        "| 结构 | 钩子(0-3s)→项目名→3要点→引导 | 3~5 个 Sequence 镜 |",
        "",
        "## 2. 逐条视频（抽帧 + 制作拆解）",
        "",
    ]

    for i, v in enumerate(videos, 1):
        vid = str(v["id"])
        kfs = _keyframes(vid)
        meta = STYLE_BY_ID.get(vid, {
            "style_id": "S00",
            "how": "（请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）",
            "remotion": "待标注",
        })
        lines.append(f"### {i}. {v.get('title', vid)}")
        lines.append("")
        lines.append(f"- **平台**：{v.get('platform', 'douyin')}")
        lines.append(f"- **ID**：`{vid}`")
        lines.append(f"- **URL**：{v.get('url', '')}")
        lines.append(f"- **归纳风格**：`{meta['style_id']}` — {meta['how']}")
        lines.append(f"- **Remotion/CSS**：{meta['remotion']}")
        lines.append("")
        if kfs:
            lines.append("**关键帧（请逐张打开）：**")
            lines.append("")
            labels = ["0% 开头", "15%", "35%", "55%", "75%", "100% 末尾"]
            for label, rel in zip(labels, kfs):
                lines.append(f"- {label}: `{rel}`")
        else:
            lines.append("- ❌ 无关键帧")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## 3. 风格聚类（→ 20 套模板）",
        "",
        "见 [GITHUB_DAILY_20_TEMPLATES.md](./GITHUB_DAILY_20_TEMPLATES.md)",
        "",
        "## 4. 我方当前样片抽帧（对照用）",
        "",
        "目录：`research/motion/github_daily/ours/`",
        "",
        "- 成片：`research/motion/github_daily/ours/preview_title_tiktok.mp4`",
        "- 关键帧：`research/motion/github_daily/ours/keyframes/key_*.png`",
        "",
        "对比重点：我们是否已是 **纯黑底 + 绿字跟读**，是否缺 **黄字描边/徽章/网格背景**。",
        "",
    ])

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(videos)} videos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
