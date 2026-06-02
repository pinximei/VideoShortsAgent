#!/usr/bin/env python3
"""
先出关键帧预览图 → 自动美观检查 → 通过后再建议跑 render_best_demo。

  py -3 scripts/visual_style_preview.py
  py -3 scripts/visual_style_preview.py --render-video   # 预览通过后自动成片
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTION = ROOT / "remotion_effects"
OUT_BASE = ROOT / "reports" / "visual_preview"

SCENES = (
    ("douyin_title", "TitleCard", "douyin", "title"),
    ("douyin_content", "ContentCard", "douyin", "content"),
    ("xhs_title", "TitleCard", "xhs", "title"),
    ("xhs_content", "ContentCard", "xhs", "content"),
)


def _base_props(platform: str, role: str) -> dict:
    sys.path.insert(0, str(ROOT))
    from python_agent.platform_caption_presets import apply_platform_caption_preset

    slide = apply_platform_caption_preset(
        {
            "type": "title_card" if role == "title" else "content_card",
            "heading": "一夜破万 Star" if role == "title" else "它能干什么",
            "hook_text": "你绝对不知道！",
            "scene_focus": role == "content",
            "scene_index": 1 if role == "content" else 0,
            "scene_total": 3,
            "summary_lines": ["自动盯趋势", "一键出片"] if role == "content" else [],
            "kinetic_phrases": ["开源", "好用"] if role == "content" else [],
            "opening_burst": role == "title",
        },
        platform,
    )
    vd = slide.get("visual_design") or {}
    mp = slide.get("motion_params") or {}
    warm = platform == "douyin"
    return {
        "heading": slide.get("heading", ""),
        "subheading": "",
        "bullets": ["自动盯趋势", "一键出片", "省一整块时间"] if role == "content" else [],
        "ctaText": "",
        "hookText": slide.get("hook_text", "你绝对不知道！"),
        "captionStyle": vd.get("caption_style", "spring"),
        "colors": ["#1a100c", "#2d1810"] if warm else ["#1a1028", "#251828"],
        "textColor": vd.get("text_color", "#fff8f0"),
        "accentColor": vd.get("accent_color", "#FF9F43"),
        "accentColor2": vd.get("accent_color2", "#FFD93D"),
        "motionProfile": "flash_hook_smash" if warm and role == "title" else (
            "tiktok_phrase_pages" if warm else "kinetic_slam_tight" if role == "title" else "glass_card_stack"
        ),
        "motionParams": mp,
        "backgroundColor": slide.get("background_color", "#120908"),
        "cssDecorations": slide.get("css_decorations") or ["daily-video-tag"],
        "captionMode": slide.get("caption_mode", "tiktok"),
        "captionPlatform": slide.get("caption_platform", platform),
        "sceneFocus": bool(slide.get("scene_focus")),
        "sceneIndex": int(slide.get("scene_index") or 0),
        "sceneTotal": int(slide.get("scene_total") or 3),
        "featureLabel": "一键生成短视频脚本" if role == "content" else "",
        "summaryLines": slide.get("summary_lines") or [],
        "kineticPhrases": slide.get("kinetic_phrases") or [],
        "colorMood": vd.get("color_mood", "warm"),
        "particleType": vd.get("particle_type", "warm"),
        "broadcastFrame": bool(vd.get("broadcast_frame")),
        "openingBurst": role == "title",
        "midInfoLayout": slide.get("mid_info_layout", "keywords"),
        "midHeroMaxChars": slide.get("mid_hero_max_chars", 14),
        "midHeroFontScale": mp.get("midHeroFontScale", 0.82),
        "sentences": [
            {"text": "你绝对不知道", "start": 0.0, "end": 1.2},
            {"text": "昨晚 Star 破万", "start": 1.2, "end": 2.8},
        ],
        "bulletStartFrames": [12, 28, 44],
        "headingStartFrame": 0,
    }


def _render_still(composition: str, props: dict, out_png: Path, frame: int = 45) -> bool:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    props_path = out_png.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = [
        "npx",
        "remotion",
        "still",
        "src/index.tsx",
        composition,
        str(out_png.resolve()).replace("\\", "/"),
        f"--props={props_path.resolve()}".replace("\\", "/"),
        f"--frame={frame}",
        "--width=1080",
        "--height=1920",
    ]
    r = subprocess.run(
        cmd,
        cwd=str(REMOTION),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        shell=True,
    )
    ok = r.returncode == 0 and out_png.is_file() and out_png.stat().st_size > 8000
    if not ok:
        print((r.stderr or r.stdout or "")[-400:])
    return ok


def _audit_png(path: Path, platform: str) -> dict:
    """轻量检查：文件可读 + 体积；小红书额外要求非空文件。"""
    row = {"path": str(path), "bytes": 0, "ok": False, "notes": []}
    if not path.is_file():
        row["notes"].append("missing_file")
        return row
    row["bytes"] = path.stat().st_size
    row["ok"] = row["bytes"] > 12_000
    if platform == "xhs" and row["bytes"] < 12_000:
        row["notes"].append("xhs_preview_too_small_maybe_blank")
    return row


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--render-video", action="store_true")
    args = ap.parse_args()

    if not (REMOTION / "node_modules").is_dir():
        print("ERROR: remotion node_modules missing")
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUT_BASE / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for key, comp, plat, role in SCENES:
        png = out_dir / f"{key}.png"
        props = _base_props(plat, role)
        print(f"[preview] {key} ...")
        rendered = _render_still(comp, props, png)
        audit = _audit_png(png, plat)
        audit["key"] = key
        audit["rendered"] = rendered
        audit["ok"] = audit["ok"] and rendered
        results.append(audit)
        print(f"  {'OK' if audit['ok'] else 'FAIL'} {png.name} {audit.get('bytes', 0)}B")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out_dir),
        "all_ok": all(r["ok"] for r in results),
        "results": results,
        "review_hint": "请人工打开 PNG：抖音暖色粒子+底栏绿字；小红书暖紫底+珊瑚高亮+底栏字幕不与中屏叠字",
    }
    (out_dir / "AUDIT.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = ["# 视觉预览审计", "", f"- 目录: `{out_dir}`", ""]
    for r in results:
        md.append(f"- **{r['key']}**: {'PASS' if r['ok'] else 'FAIL'} `{r['path']}`")
    (out_dir / "README.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n预览目录: {out_dir}")
    print(f"审计: {'PASS' if summary['all_ok'] else 'FAIL'}")

    if args.render_video and summary["all_ok"]:
        print("\n[preview] 审计通过，开始成片 ...")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_best_demo.py")], cwd=str(ROOT))
        return r.returncode

    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
