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


def _apply_platform_gv_to_slides(
    brief_dict: dict[str, Any],
    slides: list[dict[str, Any]],
    task_dir: Path,
    platform_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """按平台重套 G+V（双平台共用文案、分平台画风/口播参数）。"""
    from python_agent.motion_templates import (
        apply_github_daily_plan_to_slides,
        build_github_daily_slide_plan,
        is_github_daily_brief,
    )
    from python_agent.voice_content_templates import (
        expand_script_tts_to_minimum,
        pick_voice_content_style,
    )

    b = dict(brief_dict)
    b["platform"] = platform_id
    voice_style = pick_voice_content_style(b)
    expanded = expand_script_tts_to_minimum({"slides": [dict(s) for s in slides]}, voice_style)
    out_slides = list(expanded.get("slides") or slides)
    from python_agent.tts_copy_rules import sanitize_tts_text, tts_has_banned_phrase

    for s in out_slides:
        tts = str(s.get("tts_text") or "").strip()
        if tts_has_banned_phrase(tts):
            s["tts_text"] = sanitize_tts_text(tts) or tts
    from python_agent.slides_llm_director import direct_slides_script

    out_slides = direct_slides_script(out_slides, b, platform_id)

    from python_agent.slides_scene_expander import expand_platform_scenes

    out_slides = expand_platform_scenes(out_slides, platform_id)
    total_scenes = sum(1 for s in out_slides if s.get("scene_focus"))
    if total_scenes:
        for s in out_slides:
            if s.get("scene_focus"):
                s["scene_total"] = total_scenes

    if is_github_daily_brief(b):
        picked, plan = build_github_daily_slide_plan(b, out_slides)
        llm_dir = task_dir / "llm"
        llm_dir.mkdir(parents=True, exist_ok=True)
        (llm_dir / f"github_daily_style_{platform_id}.json").write_text(
            json.dumps({"picked": picked, "per_slide": plan}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        out_slides = apply_github_daily_plan_to_slides(out_slides, plan)
        from python_agent.capabilities.opening_hook import enforce_opening_hook_on_slides_script

        script_wrap = enforce_opening_hook_on_slides_script(
            {"slides": out_slides},
            brief=b,
            platform=platform_id,
        )
        out_slides = list(script_wrap.get("slides") or out_slides)
        if out_slides and out_slides[0].get("opening_burst"):
            plan0 = plan[0] if plan else {}
            plan0 = dict(plan0)
            plan0["motion_profile"] = "flash_hook_smash" if platform_id == "douyin" else plan0.get(
                "motion_profile"
            )
            out_slides[0]["motion_profile"] = plan0["motion_profile"]
            vd = dict(out_slides[0].get("visual_design") or {})
            vd["motion_profile"] = plan0["motion_profile"]
            out_slides[0]["visual_design"] = vd
        print(
            f"[SlidesRender] platform={platform_id} G={picked.get('id')} "
            f"V={voice_style.get('id')} caption={out_slides[0].get('caption_mode', 'spring')} "
            f"profiles={[s.get('motion_profile') for s in out_slides[:3]]}"
        )

    from python_agent.slides_ai_enricher import enrich_slides_visual_payload

    out_slides = enrich_slides_visual_payload(out_slides, b, platform_id)

    from python_agent.platform_caption_presets import apply_platform_presets_to_slides

    out_slides = apply_platform_presets_to_slides(out_slides, platform_id)
    if platform_id == "douyin":
        from python_agent.douyin_shot_stylist import (
            DouyinShotDesignError,
            apply_douyin_shot_styles,
            export_shot_plan,
        )

        try:
            out_slides = apply_douyin_shot_styles(out_slides, b)
        except DouyinShotDesignError as exc:
            raise RuntimeError(str(exc)) from exc
        plan_path = task_dir / "llm" / "douyin_shot_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        import json as _json

        plan_path.write_text(
            _json.dumps(export_shot_plan(out_slides), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    for s in out_slides:
        s["css_decorations"] = list(
            s.get("css_decorations") or (s.get("visual_design") or {}).get("css_decorations") or []
        )
    if out_slides:
        print(
            f"[SlidesRender] caption_platform={out_slides[0].get('caption_platform')} "
            f"mode={out_slides[0].get('caption_mode')}"
        )
    return out_slides, voice_style


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


def _load_or_build_slides_script(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platform_id: str,
) -> tuple[dict, dict, str, str, dict]:
    """返回 (script, brief_dict, scene_key, style_key, voice_style)。"""
    from python_agent.template_loader import get_scene

    script_path = task_dir / "llm" / "slides_script.json"
    brief_dict = load_brief(task_dir)
    from python_agent.tts_params import load_tts_from_task_dir

    brief_dict = {**brief_dict, **load_tts_from_task_dir(task_dir)}

    scene_key = (cfg.render_scene or "").strip() or _default_scene_for_feed(
        str(brief_dict.get("feed_kind") or "news")
    )
    style_key = (cfg.render_visual_style or "").strip() or get_scene(scene_key).get(
        "default_style", "github_dark"
    )

    from python_agent.voice_content_templates import (
        apply_voice_style_to_brief,
        is_voice_style_brief,
        pick_voice_content_style,
        save_voice_style,
        voice_style_prompt_block,
    )

    preset = get_platform_preset(platform_id)
    brief_dict["platform"] = platform_id
    voice_style: dict = {}
    if is_voice_style_brief(brief_dict) or platform_id in ("douyin", "xhs"):
        vpath = task_dir / "llm" / f"voice_content_style_{platform_id}.json"
        if vpath.is_file():
            data = json.loads(vpath.read_text(encoding="utf-8-sig"))
            voice_style = dict(data.get("style") or {})
        else:
            voice_style = pick_voice_content_style(brief_dict)
            save_voice_style(task_dir, voice_style)
            vpath.write_text(
                json.dumps({"version": 1, "style": voice_style}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        brief_dict = apply_voice_style_to_brief(
            brief_dict, voice_style, platform_voice=preset.voice
        )

    if script_path.is_file():
        script = json.loads(script_path.read_text(encoding="utf-8-sig"))
        if voice_style:
            from python_agent.voice_content_templates import expand_script_tts_to_minimum

            script = expand_script_tts_to_minimum(script, voice_style)
            _save_slides_artifact(task_dir, script)
        return script, brief_dict, scene_key, style_key, voice_style

    compose_text = brief_to_compose_text(brief_dict)
    if voice_style:
        compose_text += "\n\n" + voice_style_prompt_block(voice_style)
    if brief_dict.get("_remotion_skill_injected"):
        from python_agent.video_skills_orchestrator import remotion_skill_snippet

        compose_text += "\n\n【Remotion 官方 Skill】\n" + remotion_skill_snippet()[:1500]
    print(
        f"[SlidesRender] compose scene={scene_key} style={style_key} "
        f"voice={voice_style.get('id', '-')}"
    )

    from python_agent.skills.compose_skill import ComposeSkill

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
    if voice_style:
        from python_agent.voice_content_templates import ensure_script_tts_minimum

        from python_agent.voice_content_templates import expand_script_tts_to_minimum

        script = expand_script_tts_to_minimum(script, voice_style)
        script, actual, need = ensure_script_tts_minimum(script, voice_style)
        if actual < int(need * 0.6):
            raise RuntimeError(
                f"voice_script_too_short:{actual}<{need} — 口播过少，请检查素材或重新生成文案"
            )

    from python_agent.motion_templates import (
        apply_template_plan_to_slides,
        build_github_daily_slide_plan,
        build_slide_template_plan,
        is_github_daily_brief,
        save_github_daily_style,
        save_template_plan,
    )

    slides = script.get("slides") or []
    if is_github_daily_brief(brief_dict):
        picked, plan = build_github_daily_slide_plan(brief_dict, slides)
        save_github_daily_style(task_dir, picked, plan)
        print(f"[SlidesRender] github_daily style={picked.get('id')}")
    plan = build_slide_template_plan(brief_dict, slides)
    save_template_plan(task_dir, plan)
    script["slides"] = apply_template_plan_to_slides(script.get("slides") or [], brief_dict)
    from python_agent.slides_llm_director import direct_slides_script

    script["slides"] = direct_slides_script(script.get("slides") or [], brief_dict, platform_id)
    _save_slides_artifact(task_dir, script)
    return script, brief_dict, scene_key, style_key, voice_style


def render_slides_video(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platform_id: str = "douyin",
) -> Path:
    """Compose（仅首次）+ 分平台 TTS + RenderSlidesSkill → 成片。"""
    _configure_stdio_utf8()
    _ensure_repo_path()
    from python_agent.pipeline_media import prefetch_task_cover
    from python_agent.skills.dubbing_skill import DubbingSkill
    from python_agent.skills.image_resolver_skill import ImageResolverSkill
    from python_agent.skills.render_slides_skill import RenderSlidesSkill
    from python_agent.template_loader import get_bgm_path, get_scene, get_style
    from python_agent.tts_params import prepare_brief_tts

    task_dir = task_dir.resolve()
    preset = get_platform_preset(platform_id)
    visual_style = get_style(
        (cfg.render_visual_style or "").strip()
        or get_scene(
            (cfg.render_scene or "").strip()
            or _default_scene_for_feed(str(load_brief(task_dir).get("feed_kind") or "news"))
        ).get("default_style", "github_dark")
    )

    brief_dict = load_brief(task_dir)
    brief_dict["platform"] = platform_id
    script, brief_dict, scene_key, style_key, voice_style = _load_or_build_slides_script(
        cfg, task_dir, platform_id=platform_id
    )
    brief_dict["platform"] = platform_id
    import copy

    slides = copy.deepcopy(script.get("slides") or [])
    slides, voice_style = _apply_platform_gv_to_slides(
        brief_dict, slides, task_dir, platform_id
    )
    brief_dict = prepare_brief_tts(brief_dict, platform_id, voice_style=voice_style or None)
    for slide in slides:
        vd = dict(slide.get("visual_design") or {})
        if platform_id == "xhs":
            vd["caption_style"] = preset.effects.get("caption_style", "fade")
            slide["caption_style"] = vd["caption_style"]
        slide["visual_design"] = vd

    shared_work = task_dir / "videos" / "_slides_work"
    shared_work.mkdir(parents=True, exist_ok=True)
    images_dir = shared_work / "images"
    if not images_dir.is_dir() or not any(images_dir.iterdir()):
        cover = prefetch_task_cover(task_dir, brief_dict)
        _attach_cover_to_slides(slides, cover)
        resolver = ImageResolverSkill()
        slides = resolver.execute(
            slides,
            user_images_dir=None,
            image_mode=cfg.render_slides_image_mode,
            output_dir=str(images_dir),
        )
        script_for_disk = dict(script)
        script_for_disk["slides"] = slides
        llm_dir = task_dir / "llm"
        llm_dir.mkdir(parents=True, exist_ok=True)
        (llm_dir / f"slides_render_plan_{platform_id}.json").write_text(
            json.dumps(script_for_disk, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    work = task_dir / "videos" / f"_slides_work_{platform_id}"
    work.mkdir(parents=True, exist_ok=True)
    print(
        f"[SlidesRender] TTS platform={platform_id} voice={brief_dict.get('tts_voice')} "
        f"rate={brief_dict.get('tts_rate')} pitch={brief_dict.get('tts_pitch')}"
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
    tts_input = []
    for s in slides:
        row: dict = {"tts_text": s.get("tts_text", "")}
        for key in ("tts_rate", "tts_pitch", "sentence_pause_sec"):
            if s.get(key) is not None:
                row[key] = s[key]
        tts_input.append(row)
    tts_result = dubbing.execute(tts_input, str(work))
    if isinstance(tts_result, dict):
        tts_clips = tts_result.get("tts_clips", [])
    elif isinstance(tts_result, list):
        tts_clips = tts_result
    else:
        tts_clips = []

    bgm_key = (cfg.render_bgm or "").strip() or get_scene(scene_key).get("default_bgm", "upbeat_tech")
    bgm_path = get_bgm_path(bgm_key) if bgm_key and bgm_key != "none" else None

    from python_agent.slides_quality_gates import (
        auto_fix_slides,
        summarize_quality_gate,
        validate_slides_before_render,
    )

    slides = auto_fix_slides(slides, platform=platform_id, brief=brief_dict)

    from python_agent.tts_subtitle_bind import apply_tts_subtitle_bind

    slides = apply_tts_subtitle_bind(
        slides, tts_clips, platform=platform_id, brief=brief_dict
    )
    if platform_id == "douyin":
        from python_agent.layout_collision import fix_all_layout_collisions

        slides = fix_all_layout_collisions(slides)
    gate = validate_slides_before_render(slides, platform=platform_id, brief=brief_dict)
    if platform_id == "douyin":
        from python_agent.pinned_regression import validate_pinned_douyin_plan

        reg = validate_pinned_douyin_plan(slides, brief=brief_dict)
        gate.setdefault("pinned_regression", reg)
        if not reg.get("ok"):
            gate["ok"] = False
            gate.setdefault("errors", []).extend(reg.get("errors") or [])
    gate["summary"] = summarize_quality_gate(gate)
    gate_path = task_dir / "llm" / f"slides_quality_gate_{platform_id}.json"
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SlidesRender] {gate['summary'].split(chr(10))[0]}")
    if gate.get("warnings"):
        print(f"[SlidesRender] quality warnings: {gate['warnings'][:5]}")
    if not gate.get("ok"):
        raise RuntimeError(f"slides_quality_gate_failed: {gate.get('errors')}")

    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    plan_disk = {"slides": slides, "platform": platform_id}
    (llm_dir / f"slides_render_plan_{platform_id}.json").write_text(
        json.dumps(plan_disk, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if platform_id == "douyin":
        from python_agent.render_quality_score import score_douyin_render

        pre_score = score_douyin_render(slides, brief=brief_dict, gate=gate)
        score_path = task_dir / "RENDER_QUALITY_SCORE.json"
        score_path.write_text(
            json.dumps(pre_score, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"[SlidesRender] quality score (pre-render): {pre_score.get('score')} "
            f"grade={pre_score.get('grade')}"
        )
        if not pre_score.get("pass"):
            raise RuntimeError(f"render_quality_score_failed: {pre_score.get('deductions')}")

    renderer = RenderSlidesSkill(width=preset.width, height=preset.height)
    out_slides = renderer.execute(
        slides,
        tts_clips,
        visual_style,
        str(work),
        bgm_path,
        platform_id=platform_id,
    )

    videos_dir = task_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    target = videos_dir / f"{platform_id}.mp4"
    shutil.copy2(out_slides, target)

    if platform_id == "douyin":
        from python_agent.render_quality_score import score_douyin_render

        final_score = score_douyin_render(
            slides,
            brief=brief_dict,
            gate=gate,
            video_path=target,
        )
        score_path = task_dir / "RENDER_QUALITY_SCORE.json"
        score_path.write_text(
            json.dumps(final_score, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"[SlidesRender] quality score (final): {final_score.get('score')} "
            f"grade={final_score.get('grade')}"
        )

    return target


def render_task_slides_videos(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """为各平台生成成片（文案共用，分平台 TTS：抖音男声 / 小红书女声）。"""
    task_dir = task_dir.resolve()
    brief_dict = load_brief(task_dir)
    presets = video_platforms(platforms or cfg.render_platforms)
    platform_ids = [p.id for p in presets]

    from .render_lock import global_render_slot

    videos: list[dict[str, Any]] = []
    with global_render_slot(cfg.data_dir, max_slots=cfg.render_max_concurrent):
        script_path = task_dir / "llm" / "slides_script.json"
        for preset in presets:
            print(f"[SlidesRender] platform={preset.id} (per-platform TTS)")
            out_path = render_slides_video(cfg, task_dir, platform_id=preset.id)
            videos.append(
                {
                    "platform": preset.id,
                    "label": preset.label,
                    "path": str(out_path),
                    "content_kind": "video",
                    "render_engine": "remotion_slides",
                }
            )
        if script_path.is_file():
            all_slides = json.loads(script_path.read_text(encoding="utf-8")).get("slides") or []
            _stub_video_plans(task_dir, all_slides, platform_ids)

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
    if (
        cfg.render_enabled
        and cfg.render_verify_required
        and verify_report.get("ok") is not True
    ):
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
