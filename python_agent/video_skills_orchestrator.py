"""多 Skill 视频编排：Compose → LLM 导演 → 拆镜 → 视觉补全 → TTS → Remotion 渲染。

遵循开源 Remotion Agent Skills（remotion-dev/skills）约束。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def remotion_skill_snippet() -> str:
    """Remotion 官方 /resources + skills 规则（见 remotion_resources.py）。"""
    from python_agent.remotion_resources import orchestration_prompt_block

    return orchestration_prompt_block()


def _brief_to_text(brief: dict[str, Any]) -> str:
    from pipeline.slides_render import brief_to_compose_text

    return brief_to_compose_text(brief)


def _collect_steps_from_artifacts(task_dir: Path, platform_id: str, video: str | None) -> list[dict]:
    """渲染完成后从 llm 产物反推各 Skill 状态。"""
    llm = task_dir / "llm"
    steps: list[dict] = []

    script_path = llm / "slides_script.json"
    steps.append(
        {
            "skill": "compose_skill",
            "ok": script_path.is_file(),
            "slides": len(json.loads(script_path.read_text(encoding="utf-8-sig")).get("slides", []))
            if script_path.is_file()
            else 0,
        }
    )

    plan = llm / f"slides_render_plan_{platform_id}.json"
    directed = 0
    viz: dict[str, int] = {}
    hook_beats: list = []
    if plan.is_file():
        slides = json.loads(plan.read_text(encoding="utf-8-sig")).get("slides") or []
        directed = sum(1 for s in slides if s.get("llm_directed"))
        hook_beats = (slides[0].get("hook_beats") or []) if slides else []
        for s in slides:
            vt = str(s.get("viz_type") or "none")
            viz[vt] = viz.get(vt, 0) + 1

    steps.append(
        {
            "skill": "slides_llm_director",
            "ok": directed > 0 or plan.is_file(),
            "llm_directed_scenes": directed,
            "hook_beats": hook_beats,
        }
    )
    steps.append(
        {
            "skill": "slides_scene_expander",
            "ok": plan.is_file(),
            "scene_focus_count": sum(
                1 for s in (json.loads(plan.read_text(encoding="utf-8-sig")).get("slides") or []) if s.get("scene_focus")
            )
            if plan.is_file()
            else 0,
        }
    )
    steps.append({"skill": "slides_ai_enricher", "ok": plan.is_file(), "viz_type_counts": viz})
    gv = llm / f"github_daily_style_{platform_id}.json"
    steps.append({"skill": "platform_gv_motion", "ok": gv.is_file()})
    gate_path = llm / f"slides_quality_gate_{platform_id}.json"
    gate_ok = True
    gate_warnings: list = []
    if gate_path.is_file():
        gate_data = json.loads(gate_path.read_text(encoding="utf-8-sig"))
        gate_ok = bool(gate_data.get("ok", True))
        gate_warnings = list(gate_data.get("warnings") or [])[:5]

    vp = Path(video) if video else None
    steps.append(
        {
            "skill": "slides_quality_gates",
            "ok": gate_ok,
            "warnings": gate_warnings,
        }
    )
    steps.append(
        {
            "skill": "dubbing_and_render_slides",
            "ok": bool(vp and vp.is_file() and vp.stat().st_size > 50_000),
            "path": video,
            "bytes": vp.stat().st_size if vp and vp.is_file() else 0,
            "remotion_skill": "remotion-dev/skills",
            "remotion_montage": os.environ.get("REMOTION_MONTAGE", "1") != "0",
            "caption_tts_sync": True,
        }
    )
    return steps


def orchestrate_slides_pipeline(
    *,
    task_dir: Path,
    brief: dict[str, Any],
    platform_id: str,
    cfg: Any,
    force_compose: bool = False,
) -> dict[str, Any]:
    """单平台：可选 Compose，再走 slides_render 全链路。"""
    from python_agent.skills.compose_skill import ComposeSkill
    from python_agent.template_loader import get_scene
    from python_agent.voice_content_templates import pick_voice_content_style, voice_style_prompt_block

    task_dir = task_dir.resolve()
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    script_path = llm_dir / "slides_script.json"

    if force_compose or not script_path.is_file():
        scene_key = (cfg.render_scene or "").strip() or "daily_github"
        style_key = (cfg.render_visual_style or "").strip() or get_scene(scene_key).get(
            "default_style", "github_dark"
        )
        b = dict(brief)
        b["platform"] = platform_id
        voice_style = pick_voice_content_style(b)
        compose_text = _brief_to_text(brief)
        compose_text += "\n\n" + voice_style_prompt_block(voice_style)
        compose_text += "\n\n【Remotion 官方 Skill 约束】\n" + remotion_skill_snippet()[:2000]

        script = ComposeSkill().execute(
            compose_text,
            scene_key,
            style_key,
            image_mode=cfg.render_slides_image_mode,
            motion_directed=True,
            voice_style=voice_style,
        )
        script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    from pipeline.slides_render import render_slides_video

    brief_run = {**brief, "platform": platform_id, "_remotion_skill_injected": True}
    gv_map = brief.get("_platform_gv") or {}
    if isinstance(gv_map, dict) and platform_id in gv_map:
        brief_run.update(gv_map[platform_id])
    (task_dir / "brief.json").write_text(
        json.dumps(brief_run, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    out_mp4 = render_slides_video(cfg, task_dir, platform_id=platform_id)
    steps = _collect_steps_from_artifacts(task_dir, platform_id, str(out_mp4))

    return {"platform": platform_id, "steps": steps, "video": str(Path(out_mp4).resolve())}


def run_full_orchestration(
    *,
    task_dir: Path,
    brief: dict[str, Any],
    cfg: Any,
    platforms: tuple[str, ...] = ("douyin", "xhs"),
    force_compose: bool = True,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    """双平台编排 + 汇总报告。"""
    task_dir = task_dir.resolve()
    report_dir = report_dir or task_dir.parent
    report_dir.mkdir(parents=True, exist_ok=True)

    platform_results = []
    for i, pid in enumerate(platforms):
        print(f"\n[Orchestrator] platform={pid}")
        platform_results.append(
            orchestrate_slides_pipeline(
                task_dir=task_dir,
                brief=brief,
                platform_id=pid,
                cfg=cfg,
                force_compose=force_compose and i == 0,
            )
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_dir": str(task_dir),
        "skills_stack": [
            {
                "id": "remotion-dev/skills",
                "role": "Remotion 官方最佳实践",
                "path": str(
                    __import__("python_agent.remotion_resources", fromlist=["_skill_dir"])._skill_dir()
                ),
                "install": "npx skills add remotion-dev/skills",
            },
            {"id": "compose_skill", "role": "LLM 分镜剧本"},
            {"id": "slides_llm_director", "role": "口播 + hook_beats + 中部 + viz_type"},
            {"id": "slides_scene_expander", "role": "多场景拆镜"},
            {"id": "slides_ai_enricher", "role": "视觉兜底"},
            {"id": "platform_gv_motion", "role": "G20 + V20"},
            {"id": "dubbing_skill", "role": "Edge TTS"},
            {"id": "slides_quality_gates", "role": "渲染前字幕/图表/中部门禁"},
            {"id": "render_slides_skill", "role": "Remotion TTS 字幕 + TransitionSeries Montage"},
            {"id": "video_orchestrate", "role": "SkillRegistry 入口 skills/video_orchestrate"},
        ],
        "remotion_mcp": "https://www.remotion.dev/docs/ai/mcp",
        "platforms": platform_results,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = report_dir / f"ORCHESTRATION_REPORT_{ts}.json"
    out_md = report_dir / f"ORCHESTRATION_REPORT_{ts}.md"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_report_markdown(report), encoding="utf-8")
    report["report_json"] = str(out_json)
    report["report_md"] = str(out_md)
    return report


def _report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# LLM 多 Skill 视频编排报告",
        "",
        f"- 时间: `{report['generated_at']}`",
        f"- 任务: `{report['task_dir']}`",
        "",
        "## Skill 栈",
        "",
        "| Skill | 职责 |",
        "|-------|------|",
    ]
    for s in report.get("skills_stack") or []:
        extra = f" (`{s['install']}`)" if s.get("install") else ""
        lines.append(f"| `{s['id']}`{extra} | {s['role']} |")
    lines.extend(["", "## 平台结果", ""])
    for pr in report.get("platforms") or []:
        lines.append(f"### {pr.get('platform')}")
        if pr.get("video"):
            lines.append(f"- 成片: `{pr['video']}`")
        for st in pr.get("steps") or []:
            ok = "OK" if st.get("ok") else "FAIL"
            meta = {k: v for k, v in st.items() if k not in ("skill", "ok")}
            lines.append(f"- **{st['skill']}** [{ok}] `{json.dumps(meta, ensure_ascii=False)}`")
        lines.append("")
    return "\n".join(lines)
