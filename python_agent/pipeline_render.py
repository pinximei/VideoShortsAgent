"""
Pipeline 驱动渲染：只执行中间层已生成的口播稿 + 分镜 JSON（VSA 不调大模型）。

流程：Pipeline LLM → llm/video_clips_*.json + script.txt → TTS → RenderSkill
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ is None:
    _ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)

from python_agent.licensing import record_export
from python_agent.pipeline_input import (
    article_platform_manifest,
    brief_to_clips,
    load_pipeline_pack,
    load_video_clips,
    resolve_video_platforms,
    save_video_clips_plan,
)
from python_agent.pipeline_quality import brief_is_renderable, effective_max_seconds
from python_agent.platform_presets import PlatformPreset, is_video_platform
from python_agent.skills.dubbing_skill import DubbingSkill
from python_agent.skills.render_skill import RenderSkill


def _probe_duration(video_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return max(1.0, float(result.stdout.strip()))
    except Exception:
        return 60.0


def estimate_tts_durations_from_clips(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按口播字数估算每段时长（渲染前写回 B-roll 时间轴）。"""
    out: list[dict[str, Any]] = []
    for clip in clips:
        text = str(clip.get("tts_text") or clip.get("hook_text") or "").strip()
        chars = max(1, len(text))
        dur = max(2.5, min(18.0, chars / 3.8))
        out.append({"duration": round(dur, 3)})
    return out


def sync_broll_timings_to_clips(
    clips: list[dict[str, Any]],
    broll_duration: float,
    *,
    tts_clips: list[dict[str, Any]] | None = None,
) -> bool:
    """若分镜需重算 B-roll 起点，原地修改 clips 并返回是否已更新。"""
    if not clips or broll_duration <= 0:
        return False
    if not clips_need_broll_retiming(clips):
        return False
    tts = tts_clips if tts_clips else estimate_tts_durations_from_clips(clips)
    allocate_broll_timings(clips, tts, broll_duration)
    return True


def clips_need_broll_retiming(clips: list[dict[str, Any]]) -> bool:
    """brief_to_clips 占位 start=0/end=5 等也需按 TTS 重算 B-roll 时间轴。"""
    if not clips or not all("start" in c and "end" in c for c in clips):
        return True
    starts = [float(c.get("start") or 0) for c in clips]
    ends = [float(c.get("end") or 0) for c in clips]
    if len(set(round(s, 2) for s in starts)) <= 1:
        return True
    if max(ends or [0]) <= 10.0:
        return True
    return False


def allocate_broll_timings(
    clips: list[dict[str, Any]],
    tts_clips: list[dict[str, Any]],
    broll_duration: float,
) -> None:
    """按 TTS 时长在 B-roll 上分配 start/end（原地修改 clips）。"""
    if not clips:
        return

    total_tts = sum(float(t.get("duration") or 0) for t in tts_clips) or float(len(clips) * 5)
    usable = max(1.0, broll_duration - 1.0)
    cursor = 0.0

    for i, clip in enumerate(clips):
        dur = float(tts_clips[i]["duration"]) if i < len(tts_clips) else 5.0
        if total_tts > 0:
            start = (cursor / total_tts) * max(0.0, usable - dur)
        else:
            start = (i * usable) / max(1, len(clips))
        start = min(start, max(0.0, broll_duration - dur))
        clip["start"] = round(start, 3)
        clip["end"] = round(start + dur, 3)
        cursor += dur


def trim_to_max_duration(
    clips: list[dict[str, Any]],
    tts_clips: list[dict[str, Any]],
    max_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept_clips: list[dict[str, Any]] = []
    kept_tts: list[dict[str, Any]] = []
    total = 0.0
    for clip, tts in zip(clips, tts_clips):
        dur = float(tts.get("duration") or 0)
        if dur <= 0:
            continue
        if total + dur > max_seconds + 0.25:
            break
        kept_clips.append(clip)
        kept_tts.append(tts)
        total += dur
    return kept_clips or clips[:1], kept_tts or tts_clips[:1]


def _format_for_platform(src: str, dst: str, preset: PlatformPreset) -> None:
    w, h = preset.width, preset.height
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    if preset.id == "xhs":
        vf += ",eq=brightness=0.03:saturation=1.08"
    elif preset.id == "douban":
        vf += ",eq=contrast=1.02:saturation=0.95"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-preset",
        "fast",
        dst,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not os.path.isfile(dst):
        raise RuntimeError(f"平台格式化失败 ({preset.id}): {(result.stderr or '')[-400:]}")


def _build_analysis(
    *,
    task_dir: Path,
    brief: dict[str, Any],
    preset: PlatformPreset,
    script: str,
    allow_template_fallback: bool,
) -> dict[str, Any]:
    """优先读中间层 llm/video_clips_{platform}.json；仅调试时回退模板。"""
    planned = load_video_clips(task_dir, preset.id)
    if planned and planned.get("clips"):
        return {
            "clips": planned["clips"],
            "source": str(planned.get("source") or "pipeline_llm"),
        }

    if not allow_template_fallback:
        raise FileNotFoundError(
            f"缺少中间层分镜文件: {task_dir / 'llm' / f'video_clips_{preset.id}.json'}。"
            "请先在 Pipeline 开启 llm.enabled 并重新跑任务。"
        )

    plat_brief = brief
    from python_agent.pipeline_quality import brief_for_platform

    clips = brief_to_clips(brief_for_platform(brief, preset), preset)
    return {"clips": clips, "source": "brief_to_clips_fallback"}


def render_platform_video(
    *,
    source_video: str,
    task_dir: Path,
    brief: dict[str, Any],
    preset: PlatformPreset,
    output_dir: str,
    script: str = "",
    publish_meta: dict[str, str] | None = None,
    use_remotion: bool = True,
    skip_tts: bool = False,
    allow_template_fallback: bool = False,
) -> dict[str, Any]:
    """为单个平台渲染成片（执行中间层分镜，本模块不调大模型）。"""
    if not os.path.isfile(source_video):
        raise FileNotFoundError(f"B-roll 不存在: {source_video}")

    ok, reason = brief_is_renderable(brief)
    if not ok:
        raise ValueError(f"口播不可渲染: {reason}")

    os.makedirs(output_dir, exist_ok=True)
    broll_duration = _probe_duration(source_video)
    script_body = (script or "").strip() or str(brief.get("hook") or "")
    analysis = _build_analysis(
        task_dir=task_dir,
        brief=brief,
        preset=preset,
        script=script_body,
        allow_template_fallback=allow_template_fallback,
    )
    clips = analysis.get("clips") or []
    plan_source = str(analysis.get("source") or "pipeline_llm")
    max_sec = effective_max_seconds(preset)
    render_status = "degraded" if "fallback" in plan_source else "ok"
    tts_info: dict[str, Any] = {"tts_clips": []}
    if not skip_tts:
        dubber = DubbingSkill(voice=preset.voice)
        tts_info = dubber.execute(analysis, output_dir, voice=preset.voice)
        clips, tts_list = trim_to_max_duration(clips, tts_info.get("tts_clips") or [], max_sec)
        analysis["clips"] = clips
        tts_info["tts_clips"] = tts_list
        if tts_list and clips_need_broll_retiming(clips):
            allocate_broll_timings(clips, tts_list, broll_duration)
        if "fallback" in plan_source:
            render_status = "degraded"
        save_video_clips_plan(
            task_dir,
            preset.id,
            clips,
            effects=effects,
            source=plan_source,
            render_status=render_status,
            extra={"tts_durations": [float(t.get("duration") or 0) for t in tts_list]},
        )
    else:
        fake_tts = [
            {
                "duration": max(
                    1.0,
                    float(clip.get("end", 5.0)) - float(clip.get("start", 0.0)),
                )
            }
            for clip in clips
        ]
        clips, fake_tts = trim_to_max_duration(clips, fake_tts, max_sec)
        analysis["clips"] = clips
        if allow_template_fallback and clips_need_broll_retiming(clips):
            allocate_broll_timings(clips, fake_tts, broll_duration)

    effects = dict(preset.effects)
    effects["use_remotion"] = bool(use_remotion)

    renderer = RenderSkill()
    raw_path = renderer.execute(
        source_video,
        analysis,
        output_dir,
        effects=effects,
        tts_info=tts_info if tts_info.get("tts_clips") else None,
    )
    if not raw_path or not os.path.isfile(raw_path):
        raise RuntimeError(f"渲染失败: {preset.id}")

    platform_out = os.path.join(output_dir, f"{preset.id}.mp4")
    _format_for_platform(raw_path, platform_out, preset)
    final_path = record_export(platform_out, feature="manual_clip") or platform_out

    title = ""
    if publish_meta:
        title = (
            publish_meta.get("douyin_title")
            or publish_meta.get("xhs_title")
            or publish_meta.get("toutiao_micro")
            or publish_meta.get("douban_note")
            or ""
        ).split("\n")[0][:80]

    return {
        "platform": preset.id,
        "label": preset.label,
        "path": final_path,
        "title": title or (brief.get("title") or ""),
        "width": preset.width,
        "height": preset.height,
        "content_kind": preset.content_kind,
        "render_status": render_status if not skip_tts else "preview",
        "plan_source": plan_source,
    }


def render_pipeline_task(
    task_dir: str | Path,
    source_video: str,
    *,
    platforms: list[str] | None = None,
    use_remotion: bool = True,
    skip_tts: bool = False,
    allow_template_fallback: bool = False,
) -> dict[str, Any]:
    """
    从 Pipeline 任务目录渲染多平台视频（仅视频渠道）。

    头条 / 豆瓣为文章渠道，文案已在 publish/*.txt，写入 manifest.articles，不出 mp4。

    输出::
        {task_dir}/videos/douyin.mp4
        {task_dir}/videos/xhs.mp4
        {task_dir}/videos/manifest.json
        {task_dir}/video.mp4  (默认抖音，兼容旧逻辑)
    """
    pack = load_pipeline_pack(task_dir)
    brief = pack["brief"]
    root = Path(pack["task_dir"])
    videos_dir = root / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    skipped_articles: list[str] = []
    for pid in platforms or []:
        if not is_video_platform(pid):
            skipped_articles.append(pid)

    script_text = pack.get("script_text") or ""

    for preset in resolve_video_platforms(platforms):
        plat_dir = videos_dir / preset.id
        plat_dir.mkdir(parents=True, exist_ok=True)
        publish_meta = (pack.get("publish") or {}).get(preset.id)

        plat_script = pack.get("script_xhs") if preset.id == "xhs" else script_text
        if preset.id == "xhs" and not (plat_script or "").strip():
            plat_script = script_text

        info = render_platform_video(
            source_video=source_video,
            task_dir=root,
            brief=brief,
            preset=preset,
            output_dir=str(plat_dir),
            script=plat_script or script_text,
            publish_meta=publish_meta,
            use_remotion=use_remotion,
            skip_tts=skip_tts,
            allow_template_fallback=allow_template_fallback,
        )
        # 统一放到 videos/{platform}.mp4
        unified = videos_dir / f"{preset.id}.mp4"
        src = Path(info["path"])
        if src.resolve() != unified.resolve():
            unified.write_bytes(src.read_bytes())
        info["path"] = str(unified)
        results.append(info)

    articles = article_platform_manifest(root, pack.get("publish") or {})

    manifest = {
        "content_key": brief.get("content_key"),
        "article_id": brief.get("article_id"),
        "title": brief.get("title"),
        "videos": results,
        "articles": articles,
    }
    if skipped_articles:
        manifest["skipped_article_platforms"] = skipped_articles
    manifest_path = videos_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 兼容：主视频默认抖音
    primary = videos_dir / "douyin.mp4"
    legacy = root / "video.mp4"
    if primary.is_file():
        legacy.write_bytes(primary.read_bytes())

    return {
        "status": "ok",
        "task_dir": str(root),
        "manifest": str(manifest_path),
        "videos": results,
        "articles": articles,
        "primary_video": str(legacy) if legacy.is_file() else None,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline 口播包 → 多平台视频")
    parser.add_argument("--task-dir", "-t", required=True)
    parser.add_argument("--source", "-s", required=True)
    parser.add_argument("--platforms", "-p", default="douyin,xhs", help="视频渠道，逗号分隔（douyin,xhs）")
    parser.add_argument("--remotion", action="store_true")
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument(
        "--allow-template-fallback",
        action="store_true",
        help="调试：无中间层分镜时回退模板",
    )
    cli_args = parser.parse_args()

    if not os.path.isfile(cli_args.source):
        raise SystemExit(f"源视频不存在: {cli_args.source}")

    plat = [x.strip() for x in cli_args.platforms.split(",") if x.strip()]
    out = render_pipeline_task(
        cli_args.task_dir,
        cli_args.source,
        platforms=plat,
        use_remotion=cli_args.remotion,
        skip_tts=cli_args.skip_tts,
        allow_template_fallback=cli_args.allow_template_fallback,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
