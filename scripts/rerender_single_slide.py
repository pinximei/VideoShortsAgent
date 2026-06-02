#!/usr/bin/env python3
"""重渲染 task 中指定 slide（复用已有 TTS，不重跑 Compose）。"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_slides(task_dir: Path, platform: str) -> list[dict]:
    for name in (f"slides_render_plan_{platform}.json", "slides_script.json"):
        p = task_dir / "llm" / name
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8-sig"))
            return list(data.get("slides") or [])
    raise FileNotFoundError(f"no slides plan under {task_dir / 'llm'}")


def _load_tts_clips(work: Path, slide_count: int) -> list[dict]:
    tts_dir = work / "tts"
    clips: list[dict] = []
    for i in range(slide_count):
        mp3 = tts_dir / f"tts_clip_{i}.mp3"
        if not mp3.is_file():
            raise FileNotFoundError(f"missing TTS: {mp3} — run full rerender_task_slides first")
        from python_agent.skills.render_slides_skill import RenderSlidesSkill

        skill = RenderSlidesSkill()
        dur = skill._get_duration(str(mp3))  # noqa: SLF001
        clips.append({"path": str(mp3), "duration": dur, "sentences": [], "index": i})
    return clips


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: py -3.12 scripts/rerender_single_slide.py <task_dir> <slide_index> "
            "[douyin|xhs]  (0-based index)"
        )
        return 2
    task_dir = Path(sys.argv[1]).resolve()
    indices = [int(x) for x in sys.argv[2].split(",")]
    platform = (sys.argv[3] if len(sys.argv) > 3 else "douyin").lower()

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "middle"))

    from pipeline.config import load_config
    from python_agent.skills.render_slides_skill import RenderSlidesSkill
    from python_agent.slides_quality_gates import auto_fix_slides, validate_slides_before_render
    from middle.pipeline.platform_presets import get_platform_preset
    from middle.pipeline.task_pack import load_brief
    from python_agent.template_loader import get_bgm_path, get_scene, get_style

    cfg = load_config(ROOT / "middle" / "config.yaml")
    brief = load_brief(task_dir)
    brief["platform"] = platform
    slides = _load_slides(task_dir, platform)
    slides = auto_fix_slides(copy.deepcopy(slides), platform=platform, brief=brief)
    gate = validate_slides_before_render(slides, platform=platform, brief=brief)
    if not gate.get("ok"):
        print(f"quality gate failed: {gate.get('errors')}")
        return 1

    work = task_dir / "videos" / f"_slides_work_{platform}"
    work.mkdir(parents=True, exist_ok=True)
    tts_clips = _load_tts_clips(work, len(slides))

    preset = get_platform_preset(platform)
    scene_key = (cfg.render_scene or "").strip() or "github_daily"
    visual_style = get_style(
        (cfg.render_visual_style or "").strip()
        or get_scene(scene_key).get("default_style", "github_dark")
    )
    bgm_key = (cfg.render_bgm or "").strip() or get_scene(scene_key).get("default_bgm", "upbeat_tech")
    bgm_path = get_bgm_path(bgm_key) if bgm_key and bgm_key != "none" else None

    print(f"[rerender-slide] platform={platform} indices={indices}")
    out = RenderSlidesSkill(width=preset.width, height=preset.height).execute(
        slides,
        tts_clips,
        visual_style,
        str(work),
        bgm_path,
        platform_id=platform,
        slide_indices=indices,
    )
    target = task_dir / "videos" / f"{platform}.mp4"
    import shutil

    shutil.copy2(out, target)
    print(f"  -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
