"""抖音十排型 × 十角色 × 最多十轮大循环：真实渲片 + 截图 + 报告 + 修改证明 + 前后对比。"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from python_agent.douyin_campaign_state import (
    CampaignState,
    apply_state_to_slides,
    tune_state_from_issues,
)
from python_agent.douyin_layout_registry import (
    DOUYIN_CONTENT_LAYOUTS,
    TITLE_LAYOUT,
    layout_assignment_table,
    layout_for_content_index,
)
from python_agent.douyin_cycle_review import (
    ROLE_SPECS as AGENT_ROUNDS,
    cycle_context,
    run_role_review_rounds,
    slides_digest,
)
from python_agent.eval_mock_compose import mock_compose_from_brief
from python_agent.platform_caption_presets import reconcile_platform_slides

SlideList = list[dict[str, Any]]


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _probe_duration(video: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    try:
        return float((r.stdout or "30").strip())
    except ValueError:
        return 30.0


def extract_frame(video: Path, t_sec: float, out_png: Path) -> bool:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(max(0.0, t_sec)),
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out_png),
        ],
        capture_output=True,
        timeout=90,
    )
    return out_png.is_file() and out_png.stat().st_size > 4000


def slide_midpoints_sec(task_dir: Path, slide_count: int) -> list[float]:
    """按各 slide 独立片段时长估算整片时间轴中点（秒）。"""
    work = task_dir / "videos" / "_slides_work_douyin"
    durs: list[float] = []
    for i in range(slide_count):
        found = 0.0
        for pat in (
            work / f"_parallel_{i}" / f"slide_{i}_video.mp4",
            work / f"slide_{i}_video.mp4",
        ):
            if pat.is_file():
                found = _probe_duration(pat)
                break
        durs.append(max(2.0, found))
    mids: list[float] = []
    t = 0.0
    for d in durs:
        mids.append(t + d * 0.52)
        t += d
    return mids


def render_layout_still(root: Path, layout: dict[str, Any], out_png: Path) -> bool:
    """Remotion 单帧：未出现在成片中的排型仍出真实预览图。"""
    remotion = root / "remotion_effects"
    if not remotion.is_dir():
        return False
    sys.path.insert(0, str(root))
    from python_agent.platform_caption_presets import apply_platform_caption_preset

    slide = apply_platform_caption_preset(
        {
            "type": "content_card",
            "heading": "产品价值演示",
            "feature_label": "产品价值演示",
            "scene_focus": True,
            "scene_index": 1,
            "scene_total": 3,
            "summary_lines": ["说需求就生成", "本机处理更安心", "办公场景好用"],
            "motion_profile": layout["motion_profile"],
            "css_decorations": list(layout["css"]),
            "mid_effect": layout.get("mid_effect") or "typewriter",
        },
        "douyin",
    )
    vd = slide.get("visual_design") or {}
    mp = slide.get("motion_params") or {}
    props = {
        "heading": slide.get("heading", ""),
        "subheading": "",
        "bullets": slide.get("summary_lines") or [],
        "featureLabel": slide.get("feature_label", ""),
        "summaryLines": slide.get("summary_lines") or [],
        "motionProfile": layout["motion_profile"],
        "motionParams": {**mp, "staggerFrames": layout.get("stagger_frames", 14)},
        "backgroundColor": slide.get("background_color", "#120908"),
        "cssDecorations": slide.get("css_decorations") or layout["css"],
        "captionMode": "tiktok",
        "captionPlatform": "douyin",
        "colorMood": vd.get("color_mood", "warm"),
        "particleType": vd.get("particle_type", "warm"),
        "broadcastFrame": False,
        "accentColor": vd.get("accent_color", "#FF9F43"),
        "accentColor2": vd.get("accent_color2", "#FFD93D"),
        "textColor": vd.get("text_color", "#fff8f0"),
        "midInfoLayout": "keywords",
        "sentences": [{"text": "说需求就生成工具", "start": 0.0, "end": 2.5}],
        "bulletStartFrames": [18, 34, 50],
        "headingStartFrame": 0,
    }
    props_path = out_png.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = [
        "npx",
        "remotion",
        "still",
        "src/index.tsx",
        "ContentCard",
        str(out_png.resolve()).replace("\\", "/"),
        f"--props={props_path.resolve()}".replace("\\", "/"),
        "--frame=55",
        "--width=1080",
        "--height=1920",
    ]
    r = subprocess.run(
        cmd,
        cwd=str(remotion),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        shell=True,
    )
    return r.returncode == 0 and out_png.is_file() and out_png.stat().st_size > 8000


def capture_ten_type_screenshots(
    root: Path,
    video: Path | None,
    slides: SlideList,
    task_dir: Path | None,
    out_dir: Path,
) -> list[dict[str, str]]:
    """十种排型各一张真实截图（成片抽帧优先，否则 Remotion still）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    assign = {r["layout_id"]: r for r in layout_assignment_table(slides)}
    assign[TITLE_LAYOUT["id"]] = {"slide": "0", "layout_id": TITLE_LAYOUT["id"], "name": TITLE_LAYOUT["name"]}
    mids = slide_midpoints_sec(task_dir, len(slides)) if task_dir and video else []
    rows: list[dict[str, str]] = []

    for layout in DOUYIN_CONTENT_LAYOUTS:
        lid = layout["id"]
        png = out_dir / f"{lid}.png"
        src = "remotion_still"
        row = assign.get(lid)
        if video and video.is_file() and row and row.get("slide") is not None:
            si = int(row["slide"])
            if si < len(mids) and extract_frame(video, mids[si], png):
                src = "video_frame"
        if not png.is_file():
            ok = render_layout_still(root, layout, png)
            src = "remotion_still" if ok else "missing"
        rows.append(
            {
                "layout_id": lid,
                "name": layout["name"],
                "path": str(png) if png.is_file() else "",
                "source": src,
            }
        )
    return rows


def capture_role_screenshots(video: Path, out_dir: Path, roles: tuple) -> list[dict[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dur = _probe_duration(video)
    rows: list[dict[str, str]] = []
    for i, spec in enumerate(roles):
        t = dur * (0.08 + 0.84 * i / max(1, len(roles) - 1))
        png = out_dir / f"R{i + 1:02d}_{spec['role']}.png"
        ok = extract_frame(video, t, png)
        rows.append(
            {
                "round": spec["round"],
                "role": spec["role"],
                "prompt": spec["prompt"],
                "time_sec": round(t, 2),
                "path": str(png) if ok else "",
            }
        )
    return rows


def compare_video_slides(
    before: Path,
    after: Path,
    mids: list[float],
    out_dir: Path,
    slide_labels: list[str],
) -> list[dict[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for i, (t, label) in enumerate(zip(mids, slide_labels)):
        b = out_dir / f"slide_{i:02d}_{label}_BEFORE.png"
        a = out_dir / f"slide_{i:02d}_{label}_AFTER.png"
        extract_frame(before, t, b)
        extract_frame(after, t, a)
        rows.append(
            {
                "slide": str(i),
                "label": label,
                "time_sec": round(t, 2),
                "before": str(b) if b.is_file() else "",
                "after": str(a) if a.is_file() else "",
            }
        )
    html = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>前后对比</title>",
        "<style>body{font-family:sans-serif;background:#111;color:#eee}",
        ".pair{display:flex;gap:12px;margin:24px 0;flex-wrap:wrap}",
        ".pair img{max-width:320px;border-radius:8px}",
        "h2{color:#FF9F43}</style></head><body><h1>成片修改前后对比</h1>",
    ]
    for r in rows:
        html.append(f"<h2>Slide {r['slide']} — {r['label']} @ {r['time_sec']}s</h2><div class='pair'>")
        if r["before"]:
            html.append(f"<div><p>BEFORE</p><img src='{Path(r['before']).name}'/></div>")
        if r["after"]:
            html.append(f"<div><p>AFTER</p><img src='{Path(r['after']).name}'/></div>")
        html.append("</div>")
    html.append("</body></html>")
    (out_dir / "COMPARE.html").write_text("\n".join(html), encoding="utf-8")
    return rows


def write_modification_proof(
    slides_before: SlideList,
    slides_after: SlideList,
    round_logs: list[dict],
    video_before: Path | None,
    video_after: Path,
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    before_txt = json.dumps(slides_before, ensure_ascii=False, indent=2).splitlines()
    after_txt = json.dumps(slides_after, ensure_ascii=False, indent=2).splitlines()
    diff = list(difflib.unified_diff(before_txt, after_txt, fromfile="slides_before", tofile="slides_after"))
    (out_dir / "slides_before.json").write_text(
        json.dumps({"slides": slides_before}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "slides_after.json").write_text(
        json.dumps({"slides": slides_after}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "slides.diff").write_text("\n".join(diff[:800]), encoding="utf-8")
    fixes: list[str] = []
    for r in round_logs:
        fixes.extend(r.get("fixes_applied") or [])
    proof = {
        "fixes_applied": fixes,
        "round_count": len(round_logs),
        "diff_line_count": len(diff),
        "video_before_sha256": _sha256_file(video_before) if video_before else "",
        "video_after_sha256": _sha256_file(video_after),
        "video_before_bytes": video_before.stat().st_size if video_before and video_before.is_file() else 0,
        "video_after_bytes": video_after.stat().st_size if video_after.is_file() else 0,
    }
    (out_dir / "MODIFICATION_PROOF.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return proof


def render_slides_to_video(root: Path, task_dir: Path, slides: SlideList) -> Path:
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "middle"))
    llm = task_dir / "llm"
    llm.mkdir(parents=True, exist_ok=True)
    (llm / "slides_script.json").write_text(
        json.dumps({"slides": slides}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    from pipeline.config import load_config
    from pipeline.slides_render import render_slides_video

    cfg = load_config(root / "middle" / "config.yaml")
    cfg.render_mode = "slides"
    cfg.render_enabled = True
    out = render_slides_video(cfg, task_dir, platform_id="douyin")
    dest = task_dir / "videos" / "douyin.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if Path(out).resolve() != dest.resolve():
        shutil.copy2(out, dest)
    return dest


def run_agent_rounds(
    slides: SlideList, *, cycle: int = 1
) -> tuple[SlideList, list[dict], list[str]]:
    ctx = cycle_context(cycle)
    return run_role_review_rounds(slides, ctx)


def write_cycle_report(
    cycle_dir: Path,
    cycle: int,
    round_logs: list[dict],
    layout_before: list[dict],
    layout_shots: list[dict],
    role_shots: list[dict],
    proof: dict,
    compare_rows: list[dict],
    converged: bool,
) -> None:
    md = [
        f"# 第 {cycle} 轮大循环报告",
        "",
        f"- 收敛: **{'是' if converged else '否'}**",
        "",
        "## 1. 十种排型截图",
        "",
    ]
    md.append("### 修改前（十种排型）")
    for row in layout_before:
        md.append(
            f"- **{row.get('layout_id')}** {row.get('name')}: `{row.get('path')}` ({row.get('source')})"
        )
    md.append("")
    md.append("### 修改后（十种排型）")
    for row in layout_shots:
        p = row.get("path") or ""
        md.append(f"- **{row.get('layout_id')}** {row.get('name')} ({row.get('source')}): `{p}`")
    md.extend(["", "## 2. 十角色评审意见", ""])
    for r in round_logs:
        md.append(f"### 第{r['round']}轮 — {r['role']}")
        md.append(f"- 评审提示: {r['prompt']}")
        if r.get("expected_layouts"):
            md.append(f"- 本轮目标排型: {', '.join(r['expected_layouts'])}")
        if r.get("issues_before"):
            md.append("- 意见:")
            for x in r["issues_before"]:
                md.append(f"  - {x}")
        else:
            md.append("- 意见: （已达标，本轮无修改）")
        if r.get("fixes_applied"):
            md.append("- 已执行修改:")
            for x in r["fixes_applied"]:
                md.append(f"  - {x}")
        md.append("")
    md.extend(
        [
            "## 3. 修改证明",
            "",
            f"- 见 `{cycle_dir / 'proof' / 'MODIFICATION_PROOF.json'}`",
            f"- diff: `{cycle_dir / 'proof' / 'slides.diff'}`",
            f"- 成片 hash 前→后: `{proof.get('video_before_sha256')}` → `{proof.get('video_after_sha256')}`",
            "",
            "## 4. 成片前后对比截图",
            "",
        ]
    )
    for c in compare_rows:
        md.append(
            f"- Slide {c.get('slide')} `{c.get('label')}` @ {c.get('time_sec')}s: "
            f"BEFORE `{c.get('before')}` | AFTER `{c.get('after')}`"
        )
    md.append(f"\n- 对比页: `{cycle_dir / 'compare' / 'COMPARE.html'}`")
    md.extend(["", "## 5. 十角色视角抽帧", ""])
    for r in role_shots:
        md.append(f"- {r.get('role')}: `{r.get('path')}` @ {r.get('time_sec')}s")
    (cycle_dir / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    (cycle_dir / "AGENT_ROUNDS.json").write_text(
        json.dumps(round_logs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_campaign(
    root: Path,
    *,
    max_cycles: int = 10,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    camp_dir = root / "reports" / "douyin_campaign" / stamp
    camp_dir.mkdir(parents=True, exist_ok=True)

    brief = brief or {
        "title": "Wandesk 类桌面助手",
        "repo_name": "AI 桌面助手",
        "hook": "GitHub 趋势客户端：用自然语言搭桌面工具",
        "feed_kind": "github_daily",
        "talking_points": [
            "用自然语言说清你要做什么，它会直接生成可运行的桌面小工具",
            "处理文件和对话都在本机完成，适合合同、表格等不方便上传的资料",
            "适合日报汇总、批量改文件名、表格格式转换这类重复办公活",
        ],
        "cta": "想看同类神器记得关注，下期继续拆趋势项目",
        "platform": "douyin",
    }
    (camp_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    slides = reconcile_platform_slides(
        mock_compose_from_brief(brief)["slides"], "douyin"
    )
    state = CampaignState()
    state_path = camp_dir / "campaign_state.json"

    prev_video: Path | None = None
    cycle_summaries: list[dict] = []
    converged_at: int | None = None

    for cycle in range(1, max_cycles + 1):
        print(f"\n{'=' * 60}\n  CAMPAIGN CYCLE {cycle}/{max_cycles}\n{'=' * 60}")
        cycle_dir = camp_dir / f"cycle_{cycle:02d}"
        task_dir = cycle_dir / "task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "brief.json").write_text(
            json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        ctx = cycle_context(cycle)
        state.cycle = cycle
        slides = apply_state_to_slides(slides, state)
        slides_before = copy.deepcopy(slides)
        digest_before = slides_digest(slides_before)

        if prev_video and prev_video.is_file():
            video_before = cycle_dir / "video_BEFORE.mp4"
            shutil.copy2(prev_video, video_before)
        else:
            print("[cycle] 渲染修改前基线成片...")
            video_before = render_slides_to_video(root, task_dir, slides_before)
            shutil.copy2(video_before, cycle_dir / "video_BEFORE.mp4")

        slides_after, round_logs, pre_issues = run_agent_rounds(slides_before, cycle=cycle)
        digest_after = slides_digest(slides_after)
        slides_changed = digest_before != digest_after
        roles_with_opinions = sum(1 for r in round_logs if r.get("had_real_opinion"))

        slides = slides_after
        state = tune_state_from_issues(state, pre_issues)
        (state_path).write_text(
            json.dumps({**state.to_dict(), "cycle_targets": list(ctx.content_layout_ids)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        skipped_render = False
        if not slides_changed:
            skipped_render = True
            print(f"[cycle {cycle}] 分镜未变，跳过渲片（避免空跑）")
            video_after = cycle_dir / "video_AFTER.mp4"
            shutil.copy2(prev_video or video_before, video_after)
            task_after = cycle_dir / "task_after"
            task_after.mkdir(parents=True, exist_ok=True)
        else:
            print(f"[cycle {cycle}] 分镜已变 roles_with_opinions={roles_with_opinions}，渲染修改后成片...")
            task_after = cycle_dir / "task_after"
            task_after.mkdir(parents=True, exist_ok=True)
            (task_after / "brief.json").write_text(
                json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            video_after = render_slides_to_video(root, task_after, slides_after)
            shutil.copy2(video_after, cycle_dir / "video_AFTER.mp4")
        prev_video = cycle_dir / "video_AFTER.mp4"

        mids = slide_midpoints_sec(task_after, len(slides_after))
        labels = [
            str(s.get("type") or f"slide{i}")[:12] for i, s in enumerate(slides_after)
        ]

        layout_before = capture_ten_type_screenshots(
            root,
            Path(video_before) if Path(video_before).is_file() else None,
            slides_before,
            task_dir if (task_dir / "videos").is_dir() else None,
            cycle_dir / "screenshots" / "layouts_BEFORE",
        )
        layout_shots = capture_ten_type_screenshots(
            root, video_after, slides_after, task_after, cycle_dir / "screenshots" / "layouts_AFTER"
        )
        role_shots = capture_role_screenshots(
            video_after, cycle_dir / "screenshots" / "roles", AGENT_ROUNDS
        )
        proof = write_modification_proof(
            slides_before,
            slides_after,
            round_logs,
            video_before if Path(video_before).is_file() else None,
            video_after,
            cycle_dir / "proof",
        )
        compare_rows = compare_video_slides(
            Path(video_before) if Path(video_before).is_file() else video_after,
            video_after,
            mids,
            cycle_dir / "compare",
            labels,
        )

        converged = len(pre_issues) == 0 and roles_with_opinions == 0
        write_cycle_report(
            cycle_dir,
            cycle,
            round_logs,
            layout_before,
            layout_shots,
            role_shots,
            proof,
            compare_rows,
            converged,
        )
        cycle_summaries.append(
            {
                "cycle": cycle,
                "converged": converged,
                "pre_issue_count": len(pre_issues),
                "roles_with_opinions": roles_with_opinions,
                "slides_changed": slides_changed,
                "skipped_render": skipped_render,
                "expected_layouts": list(ctx.content_layout_ids),
                "video_before": str(cycle_dir / "video_BEFORE.mp4"),
                "video_after": str(cycle_dir / "video_AFTER.mp4"),
                "report": str(cycle_dir / "REPORT.md"),
            }
        )
        print(
            f"[cycle {cycle}] opinions={roles_with_opinions}/10 "
            f"issues={len(pre_issues)} changed={slides_changed} "
            f"skip_render={skipped_render} converged={converged}"
        )

        if converged:
            converged_at = cycle
            break
        if cycle >= max_cycles:
            break

    final = {
        "campaign_dir": str(camp_dir),
        "cycles_run": len(cycle_summaries),
        "converged_at_cycle": converged_at,
        "cycle_summaries": cycle_summaries,
        "final_video": cycle_summaries[-1]["video_after"] if cycle_summaries else "",
        "final_state": state.to_dict(),
    }
    (camp_dir / "CAMPAIGN_FINAL.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary_md = [
        "# 十轮大循环总览",
        "",
        f"- 目录: `{camp_dir}`",
        f"- 执行轮数: {len(cycle_summaries)}",
        f"- 收敛轮次: {converged_at or '未收敛（已达上限）'}",
        "",
        "## 各轮入口",
        "",
    ]
    for s in cycle_summaries:
        summary_md.append(
            f"- 第 {s['cycle']} 轮: 报告 `{camp_dir}/cycle_{s['cycle']:02d}/REPORT.md` | "
            f"成片 `{s['video_after']}` | 收敛={s['converged']}"
        )
    (camp_dir / "FINAL_DELIVERABLE.md").write_text("\n".join(summary_md), encoding="utf-8")
    return final
