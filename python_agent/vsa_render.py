"""
VSA 执行层：根据中间层 LLM 分镜 JSON 裁剪（保留全部特效能力）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from python_agent.capabilities.registry import merge_render_effects, platform_video_defaults
from python_agent.pipeline_input import save_video_clips_plan
from python_agent.pipeline_quality import effective_max_seconds
from python_agent.pipeline_render import (
    allocate_broll_timings,
    clips_need_broll_retiming,
    sync_broll_timings_to_clips,
    _probe_duration,
)
from python_agent.skills.dubbing_skill import DubbingSkill
from python_agent.skills.render_skill import RenderSkill


def _tts_by_clip_index(clips: list[dict], tts_clips: list[dict]) -> list[dict | None]:
    by_idx = {int(t.get("index", -1)): t for t in tts_clips if "index" in t}
    out: list[dict | None] = []
    for i, c in enumerate(clips):
        if i in by_idx:
            out.append(by_idx[i])
        elif i < len(tts_clips) and "index" not in tts_clips[i]:
            out.append(tts_clips[i])
        elif (c.get("tts_text") or "").strip():
            out.append(None)
        else:
            out.append(None)
    return out


def _trim_clips(clips: list[dict], tts_clips: list[dict], max_seconds: float):
    aligned = _tts_by_clip_index(clips, tts_clips)
    kept_c, kept_t, total = [], [], 0.0
    for c, t in zip(clips, aligned):
        if t is None:
            continue
        dur = float(t.get("duration") or 0)
        if dur <= 0 or total + dur > max_seconds + 0.25:
            break
        kept_c.append(c)
        kept_t.append(t)
        total += dur
    if not kept_c and any((c.get("tts_text") or "").strip() for c in clips):
        raise RuntimeError("tts_trim_empty: no valid TTS duration within max_seconds")
    return kept_c, kept_t


def _format_video(
    src: str, dst: str, width: int, height: int, platform: str, *, preset: str = "fast"
) -> None:
    import os
    import subprocess

    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    if platform == "xhs":
        vf += ",eq=brightness=0.03:saturation=1.08"
    cmd = [
        "ffmpeg", "-y", "-i", src, "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-movflags", "+faststart", "-preset", preset, dst,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.isfile(dst):
        raise RuntimeError(f"格式化失败: {(r.stderr or '')[-300:]}")


def render_from_plan(
    *,
    clips: list[dict[str, Any]],
    broll_path: str,
    output_path: str,
    platform: str = "douyin",
    voice: str | None = None,
    max_seconds: float | None = None,
    width: int | None = None,
    height: int | None = None,
    skip_tts: bool = False,
    work_dir: str | None = None,
    effects: dict[str, Any] | None = None,
    use_remotion: bool = True,
    task_dir: str | None = None,
    feed_kind: str = "news",
    bookends: str = "douyin",
    ffmpeg_preset: str = "fast",
) -> dict[str, Any]:
    import os

    if not clips:
        raise ValueError("clips 为空")
    if not os.path.isfile(broll_path):
        raise FileNotFoundError(f"B-roll 不存在: {broll_path}")

    defaults = platform_video_defaults(platform)
    from python_agent.platform_presets import get_platform_preset
    from python_agent.tts_params import load_tts_from_task_dir, resolve_tts_for_platform

    brief_for_tts: dict = {}
    if task_dir and Path(task_dir).is_dir():
        brief_for_tts = load_tts_from_task_dir(task_dir)
    tts_cfg = resolve_tts_for_platform(brief_for_tts, platform)
    voice = voice or brief_for_tts.get("tts_voice") or tts_cfg["tts_voice"] or defaults["voice"]
    tts_rate = str(brief_for_tts.get("tts_rate") or tts_cfg["tts_rate"])
    tts_pitch = str(brief_for_tts.get("tts_pitch") or tts_cfg["tts_pitch"])
    sent_pause = brief_for_tts.get("sentence_pause_sec", tts_cfg["sentence_pause_sec"])

    preset = get_platform_preset(platform)
    max_seconds = (
        effective_max_seconds(preset)
        if max_seconds is None
        else min(float(max_seconds), effective_max_seconds(preset))
    )
    width = width or defaults["width"]
    height = height or defaults["height"]

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(work_dir or out.parent / "_vsa_work" / platform)
    tmp.mkdir(parents=True, exist_ok=True)

    resolved_feed = (feed_kind or "news").strip()
    if task_dir and Path(task_dir).is_dir():
        brief_p = Path(task_dir) / "brief.json"
        if brief_p.is_file():
            try:
                resolved_feed = str(
                    json.loads(brief_p.read_text(encoding="utf-8-sig")).get("feed_kind") or resolved_feed
                )
            except Exception:
                pass
    feed_kind = resolved_feed
    plan_effects = dict(effects or {})
    render_effects = merge_render_effects(
        platform,
        clips,
        plan_effects,
        use_remotion=use_remotion,
        feed_kind=feed_kind,
        bookends=bookends,
    )
    render_effects["ffmpeg_preset"] = str(
        plan_effects.get("ffmpeg_preset") or ffmpeg_preset or "fast"
    )
    if task_dir and Path(task_dir).is_dir():
        from python_agent.pipeline_media import apply_intro_cover_from_brief, prefetch_task_cover

        brief_data: dict[str, Any] = {}
        brief_p = Path(task_dir) / "brief.json"
        if brief_p.is_file():
            try:
                brief_data = json.loads(brief_p.read_text(encoding="utf-8-sig"))
            except Exception:
                pass
        prefetch_task_cover(Path(task_dir), brief_data)
        render_effects = apply_intro_cover_from_brief(
            render_effects, Path(task_dir), brief_data
        )
    broll_dur = _probe_duration(broll_path)
    if sync_broll_timings_to_clips(clips, broll_dur):
        if task_dir and Path(task_dir).is_dir():
            plan_path = Path(task_dir) / "llm" / f"video_clips_{platform}.json"
            prev_source = "pipeline_llm"
            if plan_path.is_file():
                try:
                    prev_source = str(
                        json.loads(plan_path.read_text(encoding="utf-8-sig")).get("source") or prev_source
                    )
                except Exception:
                    pass
            save_video_clips_plan(
                task_dir,
                platform,
                clips,
                effects=plan_effects,
                source=prev_source,
                render_status="ok",
                extra={"broll_timings": "preflight_estimate"},
            )
    analysis = {"clips": clips}
    tts_info: dict[str, Any] = {"tts_clips": []}

    if not skip_tts:
        dubber = DubbingSkill(
            voice=voice,
            tts_rate=tts_rate,
            tts_pitch=tts_pitch,
            sentence_pause=float(sent_pause) if sent_pause is not None else None,
        )
        tts_info = dubber.execute(analysis, str(tmp), voice=voice)
        tts_list = list(tts_info.get("tts_clips") or [])
        expected = sum(1 for c in clips if (c.get("tts_text") or "").strip())
        if expected and len(tts_list) < expected:
            got = {int(t.get("index", -1)) for t in tts_list}
            missing = [i for i, c in enumerate(clips) if (c.get("tts_text") or "").strip() and i not in got]
            raise RuntimeError(
                f"tts_failed: expected {expected} clips, got {len(tts_list)}, missing indices {missing}"
            )
        clips, tts_list = _trim_clips(clips, tts_list, max_seconds)
        if not tts_list and expected:
            raise RuntimeError("tts_failed: all clips trimmed away or zero duration")
        analysis["clips"] = clips
        tts_info["tts_clips"] = tts_list
        if tts_list and clips_need_broll_retiming(clips):
            allocate_broll_timings(clips, tts_list, _probe_duration(broll_path))
        if task_dir and Path(task_dir).is_dir():
            plan_path = Path(task_dir) / "llm" / f"video_clips_{platform}.json"
            prev_source = "pipeline_llm"
            if plan_path.is_file():
                try:
                    prev_source = str(json.loads(plan_path.read_text(encoding="utf-8-sig")).get("source") or prev_source)
                except Exception:
                    pass
            save_video_clips_plan(
                task_dir,
                platform,
                clips,
                effects=render_effects,
                source=prev_source,
                render_status="degraded" if "fallback" in prev_source else "ok",
                extra={"tts_durations": [float(t.get("duration") or 0) for t in tts_list]},
            )

    renderer = RenderSkill()
    raw = renderer.execute(
        broll_path,
        analysis,
        str(tmp),
        effects=render_effects,
        tts_info=tts_info if tts_info.get("tts_clips") else None,
    )
    if not raw or not os.path.isfile(raw):
        raise RuntimeError("RenderSkill 未产出文件")

    _format_video(
        raw, str(out), width, height, platform,
        preset=str(render_effects.get("ffmpeg_preset") or ffmpeg_preset or "fast"),
    )

    if task_dir and Path(task_dir).is_dir():
        from python_agent.capabilities.registry import write_render_effects_audit

        write_render_effects_audit(
            Path(task_dir),
            platform,
            plan_effects=plan_effects,
            applied_effects=render_effects,
            clips=clips,
        )

    return {
        "ok": True,
        "path": str(out.resolve()),
        "platform": platform,
        "effects_applied": render_effects,
    }


def render_from_plan_file(plan_path: str, broll_path: str, output_path: str, **kwargs: Any) -> dict[str, Any]:
    data = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    clips = data.get("clips") or []
    effects = data.get("effects")
    platform = kwargs.pop("platform", None) or data.get("platform") or "douyin"
    return render_from_plan(
        clips=clips,
        broll_path=broll_path,
        output_path=output_path,
        platform=platform,
        effects=effects,
        **kwargs,
    )
