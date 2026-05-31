#!/usr/bin/env python3
"""生成我方 20 套口播样例大纲（字数/钩子对齐 catalog）。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "templates" / "voice_content_20" / "catalog.json"
OUT = ROOT / "research" / "voice_content" / "ours_samples.json"

SAMPLES = {
    "V01_burst_hook_fast": [
        "别划走！今天这个 GitHub 项目真的狠。",
        "一行命令就能部署，Star 昨晚又涨了一万。",
        "评论区扣 1，我把链接发你。",
    ],
    "V02_tiktok_follow_punch": [
        "今天这个。你必须知道。",
        "开源神器。一分钟讲清。",
        "记得收藏。",
    ],
    "V03_top10_listing": [
        "本周 GitHub Top10 来了。",
        "第三名最适合小白，第一名太硬核。",
        "你猜今天冠军是谁？",
    ],
    "V04_minimal_calm": [
        "每天一个优质开源项目。",
        "今天这个很轻量，但解决大问题。",
        "值得 Star。",
    ],
}


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    samples = []
    for s in catalog.get("styles", []):
        sid = s["id"]
        outline = SAMPLES.get(sid) or [
            f"【{s.get('name')}】钩子句。",
            "项目亮点一句。",
            "引导关注或 Star。",
        ]
        total = sum(len(x) for x in outline)
        samples.append(
            {
                "id": sid,
                "name": s.get("name"),
                "edge_tts_rate": s.get("edge_tts_rate"),
                "words_per_minute": s.get("words_per_minute"),
                "total_chars": total,
                "outline": outline,
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"samples": samples}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(samples)} samples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
