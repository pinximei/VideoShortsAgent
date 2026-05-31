#!/usr/bin/env python3
"""
【已废弃 · 勿用于资讯口播】生成 Web3/配色变体目录（mesh-aurora + 商务色板）。

口播动效请用: scripts/generate_motion_style_catalog.py
预研报告: docs/MOTION_PRESEARCH_REPORT.md
"""
import sys

print(
    "ERROR: generate_motion_templates.py 产出配色变体，不是抖音动效预研目录。\n"
    "请使用: py -3 scripts/generate_motion_style_catalog.py",
    file=sys.stderr,
)
raise SystemExit(2)
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "templates" / "motion_templates" / "catalog.json"

VARIANTS = [
    ("mesh-aurora", "极光网格", ["spring", "neon", "glitch"]),
    ("liquid-orbs", "液态光球", ["neon", "cinematic", "classic"]),
    ("neon-grid", "霓虹地网", ["glitch", "neon", "classic"]),
    ("plasma-wave", "等离子环", ["neon", "spring", "cinematic"]),
    ("starfield-warp", "星域穿梭", ["cinematic", "neon", "classic"]),
    ("duotone-flow", "双色流光", ["classic", "spring", "fade"]),
    ("hex-tunnel", "六边形隧道", ["glitch", "neon", "spring"]),
    ("gradient-mesh", "渐变网格", ["spring", "neon", "classic"]),
]

PALETTES = [
    ("web3_cyan", ["#030712", "#0c1929", "#132f4c"], "#22d3ee", "#a855f7", "orb", "cyber-grid"),
    ("web3_green", ["#020617", "#052e16", "#14532d"], "#4ade80", "#22d3ee", "dot", "none"),
    ("web3_purple", ["#0a0118", "#1e1033", "#312e81"], "#c084fc", "#f472b6", "glow", "cyber-grid"),
    ("web3_orange", ["#1a0a00", "#431407", "#7c2d12"], "#fb923c", "#facc15", "bokeh", "film-grain"),
    ("web3_gold", ["#0f0a02", "#292211", "#3f3316"], "#fbbf24", "#f59e0b", "ring", "cinematic-bars"),
    ("web3_rose", ["#18050c", "#3b0a1e", "#500724"], "#fb7185", "#e879f9", "glow", "none"),
    ("web3_ice", ["#020617", "#0f172a", "#1e3a5f"], "#38bdf8", "#818cf8", "starfield", "none"),
    ("web3_matrix", ["#000a00", "#001a0a", "#0a2e1a"], "#00ff88", "#00d4ff", "matrix", "cyber-grid"),
    ("github_daily", ["#050508", "#0d1117", "#161b22"], "#58a6ff", "#3fb950", "dot", "cyber-grid"),
    ("douyin_pop", ["#120018", "#2d0a3d", "#4a1942"], "#ff2d55", "#25f4ee", "glow", "none"),
    ("xhs_soft", ["#1a1020", "#2d1f3d", "#3d2a4f"], "#ff6b9d", "#c4b5fd", "bokeh", "film-grain"),
    ("mono_silver", ["#0a0a0c", "#18181b", "#27272a"], "#e4e4e7", "#a1a1aa", "ring", "none"),
]

TRANSITIONS = ["circleopen", "wipeleft", "slideup", "smoothleft", "dissolve", "fade"]
CAPTIONS = ["spring", "typewriter", "fade"]
CAMERAS = ["zoom-in", "zoom-out", "pan-left", "scale-rotate", "pan-up"]

TAGS_BY_PALETTE = {
    "github_daily": ["github", "opensource", "tech", "daily"],
    "douyin_pop": ["douyin", "viral", "hook"],
    "xhs_soft": ["xhs", "lifestyle", "soft"],
    "web3_matrix": ["hacker", "matrix", "cyber"],
}


def _tags(palette_id: str, variant: str) -> list[str]:
    base = list(TAGS_BY_PALETTE.get(palette_id, ["tech", "web3"]))
    base.append(variant.replace("-", "_"))
    return sorted(set(base))


def generate() -> list[dict]:
    templates: list[dict] = []
    idx = 0
    for (variant, vlabel, text_effects), (pid, colors, acc, acc2, particle, deco) in product(
        VARIANTS, PALETTES
    ):
        idx += 1
        te = text_effects[idx % len(text_effects)]
        tid = f"{pid}_{variant}_{idx:03d}"
        templates.append(
            {
                "id": tid,
                "name": f"{vlabel}·{pid}",
                "category": "web3" if pid.startswith("web3") or pid == "github_daily" else "social",
                "tags": _tags(pid, variant),
                "background": {
                    "variant": variant,
                    "colors": colors,
                    "accentColor": acc,
                    "accentColor2": acc2,
                    "particleType": particle,
                    "decorationStyle": deco,
                    "cameraPan": CAMERAS[idx % len(CAMERAS)],
                    "overlayOpacity": 0.1 if pid in ("github_daily", "web3_cyan") else 0.14,
                },
                "text": {
                    "textEffect": te,
                    "captionStyle": CAPTIONS[idx % len(CAPTIONS)],
                    "layoutStyle": ["center", "top-heavy", "split-left"][idx % 3],
                },
                "transition": TRANSITIONS[idx % len(TRANSITIONS)],
            }
        )
    return templates


def main() -> int:
    templates = generate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    catalog = {
        "version": 1,
        "count": len(templates),
        "description": "Remotion 竖屏动效母版：Web3 背景 + 粒子 + 转场。文章渲染时按 id/hash 选型。",
        "variants": [v[0] for v in VARIANTS],
        "palettes": [p[0] for p in PALETTES],
        "templates": templates,
    }
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(templates)} templates -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
