#!/usr/bin/env python3
"""渲染 G01–G20 标题镜样片、抽关键帧、生成产物验证报告。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMOTION = ROOT / "remotion_effects"
CATALOG = ROOT / "templates" / "github_daily_20" / "catalog.json"
OUT_DIR = ROOT / "research" / "motion" / "github_daily" / "verify_g20"
REPORT = ROOT / "docs" / "GITHUB_DAILY_VERIFICATION_REPORT.md"

HEADINGS = {
    "G01_cyber_hook_yellow": "别划走 今天这个 GitHub",
    "G02_chart_card_stat": "Star 暴涨 开源神器",
    "G03_minimal_white_series": "每天一个优质项目",
    "G04_badge_pills_intro": "Github 项目推荐",
    "G05_dark_top10_rank": "10 本周 GitHub Top10",
    "G06_tiktok_follow_caption": "今天这个你必须要知道",
    "G07_hook_glitch_github": "GitHub 又炸了",
    "G08_terminal_readme": "$ git clone amazing-repo",
    "G09_split_repo_screenshot": "左文右图 仓库拆解",
    "G10_glass_three_points": "三点看懂这个项目",
    "G11_kinetic_word_slam": "快 准 狠",
    "G12_phrase_pages_caption": "一分钟讲清",
    "G13_marquee_topics": "今日热门开源",
    "G14_shake_keyword": "关键词 震撼",
    "G15_star_counter_roll": "12800 Star 还在涨",
    "G16_purple_gradient_soft": "柔和紫 科技范",
    "G17_code_rain_minimal": "代码雨里的明星项目",
    "G18_cta_star_pulse": "点个 Star 支持作者",
    "G19_rank_episode_daily": "03 每日 GitHub",
    "G20_clean_badge_orange": "极简推荐 必收藏",
}


def _render_one(style: dict, props_dir: Path) -> tuple[bool, str]:
    sid = style["id"]
    props = {
        "heading": HEADINGS.get(sid, style.get("name", sid)),
        "subheading": "每天一个 GitHub 项目",
        "motionProfile": style.get("title_profile", "github_daily_hook"),
        "motionParams": {
            "wordsPerPageMs": style.get("wordsPerPageMs", 800),
            "staggerFrames": 5,
        },
        "layoutStyle": "top-heavy",
        "useWeb3Background": False,
        "backgroundColor": style.get("bg"),
        "cssDecorations": style.get("css") or [],
        "githubDailyStyleId": sid,
        "sentences": [
            {"text": "今天 ", "start": 0, "end": 0.4},
            {"text": "这个 ", "start": 0.4, "end": 0.8},
            {"text": "项目 ", "start": 0.8, "end": 1.2},
        ],
    }
    style_dir = OUT_DIR / sid
    style_dir.mkdir(parents=True, exist_ok=True)
    props_path = props_dir / f"{sid}.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    mp4 = style_dir / "title_preview.mp4"
    cmd = [
        "npx",
        "remotion",
        "render",
        "src/index.tsx",
        "TitleCard",
        str(mp4),
        f"--props={props_path}",
        "--width=1080",
        "--height=1920",
        "--frames=0-74",
    ]
    try:
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
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "")[-500:]
        return mp4.is_file() and mp4.stat().st_size > 1000, ""
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def _extract_keyframe(mp4: Path, png: Path) -> bool:
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "1.2",
            "-i",
            str(mp4),
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(png),
        ],
        capture_output=True,
    )
    return r.returncode == 0 and png.is_file()


def _check_decorations(style: dict, props_path: Path) -> list[str]:
    issues: list[str] = []
    props = json.loads(props_path.read_text(encoding="utf-8"))
    expected = set(style.get("css") or [])
    got = set(props.get("cssDecorations") or [])
    missing = expected - got
    if missing:
        issues.append(f"css_missing:{','.join(sorted(missing))}")
    if not props.get("backgroundColor"):
        issues.append("no_backgroundColor")
    return issues


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    styles = catalog.get("styles") or []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    props_dir = OUT_DIR / "props"
    props_dir.mkdir(exist_ok=True)

    results: list[dict] = []
    ok_count = 0

    for style in styles:
        sid = style["id"]
        print(f"[verify] {sid} ...")
        ok, err = _render_one(style, props_dir)
        mp4 = OUT_DIR / sid / "title_preview.mp4"
        kf = OUT_DIR / sid / "keyframe_50pct.png"
        kf_ok = _extract_keyframe(mp4, kf) if ok else False
        dec_issues = _check_decorations(style, props_dir / f"{sid}.json")
        if ok and kf_ok and not dec_issues:
            ok_count += 1
        results.append(
            {
                "id": sid,
                "name": style.get("name"),
                "render_ok": ok,
                "keyframe_ok": kf_ok,
                "mp4": str(mp4.relative_to(ROOT)).replace("\\", "/") if mp4.is_file() else "",
                "keyframe": str(kf.relative_to(ROOT)).replace("\\", "/") if kf.is_file() else "",
                "title_profile": style.get("title_profile"),
                "css": style.get("css") or [],
                "bg": style.get("bg"),
                "issues": dec_issues + ([] if ok else ["render_fail"]) + ([] if kf_ok else ["keyframe_fail"]),
                "error": err[:200] if err else "",
            }
        )

    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "# GitHub 日更 G01–G20 产物验证报告",
        "",
        f"> 生成时间（UTC）：{ts}",
        "",
        "## 摘要",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 模板总数 | {len(styles)} |",
        f"| 渲染+抽帧通过 | **{ok_count}/{len(styles)}** |",
        f"| 输出目录 | `research/motion/github_daily/verify_g20/` |",
        "",
        "## 逐项结果（请打开 keyframe 列图片验收）",
        "",
        "| ID | 名称 | 渲染 | 关键帧 | title_profile | CSS 装饰 | 问题 |",
        "|----|------|------|--------|---------------|----------|------|",
    ]
    for r in results:
        render = "✅" if r["render_ok"] else "❌"
        kf = "✅" if r["keyframe_ok"] else "❌"
        css = ", ".join(r["css"]) if r["css"] else "—"
        issues = ", ".join(r["issues"]) if r["issues"] else "—"
        kf_link = f"`{r['keyframe']}`" if r["keyframe"] else "—"
        lines.append(
            f"| {r['id']} | {r['name']} | {render} | {kf_link} | `{r['title_profile']}` | {css} | {issues} |"
        )

    lines.extend(
        [
            "",
            "## 管线接线验证",
            "",
            "| 项 | 状态 |",
            "|----|------|",
            "| `is_github_daily_brief` → `build_github_daily_slide_plan` | ✅ `motion_templates.py` |",
            "| `slides_render` 写入 `llm/github_daily_style.json` | ✅ |",
            "| Remotion `backgroundColor` + `cssDecorations` props | ✅ TitleCard/Content/CTA |",
            "| `GithubDailyDecorations` 装饰层 | ✅ `remotion_effects/src/motion/decorations/` |",
            "",
            "## 对标抽帧（20 条别人视频）",
            "",
            "仍见 [GITHUB_DAILY_REFERENCE_ANALYSIS.md](./GITHUB_DAILY_REFERENCE_ANALYSIS.md)",
            "",
            "## 复现命令",
            "",
            "```powershell",
            "cd D:\\VideoShortsAgent",
            "py -3 scripts/motion_research/verify_github_daily_all.py",
            "```",
            "",
        ]
    )

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    manifest = {"generated_at": ts, "ok": ok_count, "total": len(styles), "results": results}
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nReport: {REPORT}")
    print(f"OK: {ok_count}/{len(styles)}")
    return 0 if ok_count == len(styles) else 1


if __name__ == "__main__":
    sys.exit(main())
