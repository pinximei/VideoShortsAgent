"""Remotion 幻灯片渲染（抖音「每天一个 GitHub」类风格）。"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .config import PipelineConfig, repo_root
from .platform_presets import get_platform_preset, video_platforms
from .task_pack import article_manifest_entries, load_brief


def is_slides_render_mode(cfg: PipelineConfig) -> bool:
    return (cfg.render_mode or "pipeline").strip().lower() in (
        "slides",
        "remotion_slides",
        "github_daily",
    )


def _ensure_repo_path() -> None:
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def _default_scene_for_feed(feed_kind: str) -> str:
    fk = (feed_kind or "news").strip().lower()
    return "ai_news" if fk == "news" else "daily_github"


def brief_to_compose_text(brief: dict[str, Any]) -> str:
    parts: list[str] = []
    title = str(brief.get("title") or "").strip()
    hook = str(brief.get("hook") or "").strip()
    if title:
        parts.append(f"标题：{title}")
    if hook:
        parts.append(f"钩子：{hook}")
    for p in brief.get("talking_points") or []:
        s = str(p).strip()
        if s:
            parts.append(f"- {s}")
    cta = str(brief.get("cta") or "").strip()
    if cta:
        parts.append(f"引导：{cta}")
    url = str(brief.get("detail_url") or "").strip()
    if url:
        parts.append(f"链接：{url}")
    return "\n".join(parts).strip() or title or hook or "（无正文）"


def _attach_cover_to_slides(slides: list[dict], cover_path: Path | None) -> None:
    if not cover_path or not cover_path.is_file() or not slides:
        return
    first = slides[0]
    if first.get("type") in ("title_card", "content_card"):
        first["image_path"] = str(cover_path.resolve())
        first.setdefault("needs_image", True)


def _save_slides_artifact(task_dir: Path, script: dict[str, Any]) -> Path:
    path = task_dir / "llm" / "slides_script.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _stub_video_plans(task_dir: Path, slides: list[dict], platforms: list[str]) -> None:
    """slides 模式不写 clip 分镜，仅落盘占位供门禁/调试。"""
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    for pid in platforms:
        stub = {
            "clips": [{"start": 0, "end": 1, "tts_text": s.get("tts_text", "")[:80]} for s in slides[:4]],
            "effects": {"preset": "科技", "gradient": False, "intro_card": False, "outro_card": False},
            "source": "slides_render",
            "render_status": "ok",
        }
        (llm_dir / f"video_clips_{pid}.json").write_text(
            json.dumps(stub, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def render_slides_video(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platform_id: str = "douyin",
) -> Path:
    """ComposeSkill + RenderSlidesSkill → 单条成片。"""
    _configure_stdio_utf8()
    _ensure_repo_path()
    from python_agent.pipeline_media import prefetch_task_cover
    from python_agent.skills.compose_skill import ComposeSkill
    from python_agent.skills.dubbing_skill import DubbingSkill
    from python_agent.skills.image_resolver_skill import ImageResolverSkill
    from python_agent.skills.render_slides_skill import RenderSlidesSkill
    from python_agent.template_loader import get_bgm_path, get_scene, get_style

    task_dir = task_dir.resolve()
    brief_dict = load_brief(task_dir)

    scene_key = (cfg.render_scene or "").strip() or _default_scene_for_feed(
        str(brief_dict.get("feed_kind") or "news")
    )
    style_key = (cfg.render_visual_style or "").strip() or get_scene(scene_key).get(
        "default_style", "github_dark"
    )
    visual_style = get_style(style_key)

    from python_agent.voice_content_templates import (
        apply_voice_style_to_brief,
        is_voice_style_brief,
        pick_voice_content_style,
        save_voice_style,
        voice_style_prompt_block,
    )

    voice_style: dict = {}
    preset = get_platform_preset(platform_id)
    if is_voice_style_brief(brief_dict):
        voice_style = pick_voice_content_style(brief_dict)
        brief_dict = apply_voice_style_to_brief(
            brief_dict, voice_style, platform_voice=preset.voice
        )
        save_voice_style(task_dir, voice_style)

    compose_text = brief_to_compose_text(brief_dict)
    if voice_style:
        compose_text += "\n\n" + voice_style_prompt_block(voice_style)
    print(f"[SlidesRender] scene={scene_key} style={style_key} platform={platform_id} voice={voice_style.get('id', '-')}")

    script = ComposeSkill().execute(
        compose_text,
        scene_key,
        style_key,
        image_filenames=None,
        image_mode=cfg.render_slides_image_mode,
        motion_directed=True,
        voice_style=voice_style or None,
    )
    slides = script.get("slides") or []
    if len(slides) < 2:
        raise RuntimeError("slides_script_too_short")

    from python_agent.motion_templates import (
        apply_template_plan_to_slides,
        build_github_daily_slide_plan,
        build_slide_template_plan,
        is_github_daily_brief,
        save_github_daily_style,
        save_template_plan,
    )

    if is_github_daily_brief(brief_dict):
        picked, plan = build_github_daily_slide_plan(brief_dict, slides)
        save_github_daily_style(task_dir, picked, plan)
        print(f"[SlidesRender] github_daily style={picked.get('id')}")
    plan = build_slide_template_plan(brief_dict, slides)
    save_template_plan(task_dir, plan)
    slides = apply_template_plan_to_slides(slides, brief_dict)
    script["slides"] = slides

    cover = prefetch_task_cover(task_dir, brief_dict)
    _attach_cover_to_slides(slides, cover)
    _save_slides_artifact(task_dir, script)

    work = task_dir / "videos" / "_slides_work"
    work.mkdir(parents=True, exist_ok=True)

    resolver = ImageResolverSkill()
    slides = resolver.execute(
        slides,
        user_images_dir=None,
        image_mode=cfg.render_slides_image_mode,
        output_dir=str(work / "images"),
    )

    voice = str(brief_dict.get("tts_voice") or preset.voice)
    tts_rate = str(brief_dict.get("tts_rate") or "+12%")
    tts_pitch = str(brief_dict.get("tts_pitch") or "+0Hz")
    sent_pause = brief_dict.get("sentence_pause_sec")
    dubbing = DubbingSkill(
        voice=voice,
        tts_rate=tts_rate,
        tts_pitch=tts_pitch,
        sentence_pause=float(sent_pause) if sent_pause is not None else None,
    )
    tts_input = [{"tts_text": s.get("tts_text", "")} for s in slides]
    tts_result = dubbing.execute(tts_input, str(work))
    if isinstance(tts_result, dict):
        tts_clips = tts_result.get("tts_clips", [])
    elif isinstance(tts_result, list):
        tts_clips = tts_result
    else:
        tts_clips = []

    bgm_key = (cfg.render_bgm or "").strip() or get_scene(scene_key).get("default_bgm", "upbeat_tech")
    bgm_path = get_bgm_path(bgm_key) if bgm_key and bgm_key != "none" else None

    renderer = RenderSlidesSkill(width=preset.width, height=preset.height)
    out_slides = renderer.execute(slides, tts_clips, visual_style, str(work), bgm_path)

    videos_dir = task_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    target = videos_dir / f"{platform_id}.mp4"
    shutil.copy2(out_slides, target)
    return target


def render_task_slides_videos(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """为各平台生成成片（首平台渲染，其余复用同文件）。"""
    task_dir = task_dir.resolve()
    brief_dict = load_brief(task_dir)
    presets = video_platforms(platforms or cfg.render_platforms)
    platform_ids = [p.id for p in presets]

    from .render_lock import global_render_slot

    videos: list[dict[str, Any]] = []
    with global_render_slot(cfg.data_dir, max_slots=cfg.render_max_concurrent):
        primary_id = platform_ids[0] if platform_ids else "douyin"
        primary_path = render_slides_video(cfg, task_dir, platform_id=primary_id)
        script_path = task_dir / "llm" / "slides_script.json"
        if script_path.is_file():
            all_slides = json.loads(script_path.read_text(encoding="utf-8")).get("slides") or []
            _stub_video_plans(task_dir, all_slides, platform_ids)
        for preset in presets:
            dest = task_dir / "videos" / f"{preset.id}.mp4"
            if preset.id != primary_id:
                shutil.copy2(primary_path, dest)
            videos.append(
                {
                    "platform": preset.id,
                    "label": preset.label,
                    "path": str(dest),
                    "content_kind": "video",
                    "render_engine": "remotion_slides",
                }
            )

    articles = article_manifest_entries(task_dir)
    manifest = {
        "content_key": brief_dict.get("content_key"),
        "article_id": brief_dict.get("article_id"),
        "title": brief_dict.get("title"),
        "videos": videos,
        "articles": articles,
        "executor": "pipeline.slides_render.render_task_slides_videos",
        "render_mode": "slides",
        "scene": cfg.render_scene or _default_scene_for_feed(str(brief_dict.get("feed_kind") or "news")),
    }
    manifest_path = task_dir / "videos" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    from .render_verify import run_post_render_verify

    verify_report = run_post_render_verify(
        task_dir,
        platforms=cfg.render_platforms,
        full_verify=cfg.render_full_verify,
    )
    if cfg.render_enabled and verify_report.get("ok") is not True:
        raise RuntimeError(
            f"verify_failed: {json.dumps(verify_report, ensure_ascii=False)[:400]}"
        )

    primary = task_dir / "videos" / "douyin.mp4"
    legacy = task_dir / "video.mp4"
    if primary.is_file():
        legacy.write_bytes(primary.read_bytes())

    return {
        "status": "ok",
        "task_dir": str(task_dir),
        "manifest": str(manifest_path),
        "videos": videos,
        "articles": articles,
        "primary_video": str(legacy) if legacy.is_file() else None,
        "verify": verify_report,
    }
