"""
流水线门禁：任一步不达标则任务不得进入 ready_to_publish / 不得标记发布。

设计原则（fail-closed）：
- 渲染开启时：LLM 分镜、TTS、全平台成片、验收报告 全部通过
- 发布绑定有 warning 或 channels 为空 → 失败
- 与 orchestrator / API / publisher 共用同一套 assert
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .platform_presets import get_platform_preset, is_video_platform, video_platforms
from .publish_guard import PublishGuardError


class PipelineGateError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


def _fail(code: str, message: str, **details: Any) -> None:
    raise PipelineGateError(code, message, details=details)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _strict(cfg: PipelineConfig, *, strict: bool | None) -> bool:
    if strict is not None:
        return strict
    return bool(cfg.pipeline_fail_closed)


def assert_publish_pack_meta(task_dir: Path, cfg: PipelineConfig, *, strict: bool | None = None) -> None:
    """LLM 落盘质量（禁止静默 template / degraded 进生产）。"""
    meta = _load_json(task_dir / "publish_meta.json")
    source = str(meta.get("source") or "")
    if meta.get("llm_error") and not cfg.render_allow_template_fallback:
        _fail("llm_failed", str(meta["llm_error"])[:300])
    if cfg.render_enabled and _strict(cfg, strict=strict):
        if "fallback" in source or source == "template":
            _fail("llm_fallback_forbidden", f"publish_meta.source={source}")
        if cfg.llm_enabled and source != "pipeline_llm":
            _fail("llm_source_invalid", f"expected pipeline_llm, got {source or 'empty'}")


def assert_video_plans(task_dir: Path, cfg: PipelineConfig, *, strict: bool | None = None) -> None:
    platforms = [p.id for p in video_platforms(cfg.render_platforms)]
    for pid in platforms:
        plan_path = task_dir / "llm" / f"video_clips_{pid}.json"
        if not plan_path.is_file():
            _fail("plan_missing", f"缺少 {plan_path.name}")
        plan = _load_json(plan_path)
        clips = plan.get("clips") or []
        if len(clips) < 1:
            _fail("plan_empty", f"{pid} clips 为空")
        if _strict(cfg, strict=strict):
            status = str(plan.get("render_status") or "")
            if status != "ok":
                _fail("plan_render_status", f"{pid} render_status={status or 'missing'}")
            src = str(plan.get("source") or "")
            if "fallback" in src and not cfg.render_allow_template_fallback:
                _fail("plan_fallback", f"{pid} source={src}")


def assert_broll_ready(cfg: PipelineConfig) -> None:
    if not cfg.render_enabled:
        return
    broll = (cfg.broll_template or "").strip()
    if not broll:
        _fail("broll_missing", "未配置 broll_template")
    if not Path(broll).is_file():
        _fail("broll_missing", f"B-roll 不存在: {broll}")


def assert_all_platform_videos(task_dir: Path, cfg: PipelineConfig) -> dict[str, Any]:
    from .render_verify import MIN_VIDEO_BYTES, _quick_video_checks

    platforms = [p.id for p in video_platforms(cfg.render_platforms)]
    quick = _quick_video_checks(task_dir, platforms)
    if not quick.get("ok"):
        bad = [pid for pid, e in (quick.get("platforms") or {}).items() if not e.get("ok")]
        _fail("video_quick_check", f"成片验收失败: {bad}", quick=quick)
    for pid in platforms:
        p = task_dir / "videos" / f"{pid}.mp4"
        if not p.is_file() or p.stat().st_size < MIN_VIDEO_BYTES:
            _fail("video_missing", f"缺少或过小: videos/{pid}.mp4")
    return quick


def assert_verify_report(task_dir: Path, cfg: PipelineConfig, *, strict: bool | None = None) -> dict[str, Any]:
    report_path = task_dir / "verify_report.json"
    if not report_path.is_file():
        if cfg.render_enabled and _strict(cfg, strict=strict):
            _fail("verify_missing", "缺少 verify_report.json")
        return {}
    report = _load_json(report_path)
    if cfg.render_enabled and _strict(cfg, strict=strict):
        if report.get("ok") is not True:
            _fail("verify_failed", "verify_report.ok 不为 true", report=report)
        quick = report.get("quick") or {}
        if quick.get("ok") is not True:
            _fail("verify_quick_failed", "quick 验收失败", quick=quick)
        fx = report.get("effects_audit") or {}
        if fx.get("ok") is not True:
            _fail("effects_audit_failed", "effects_audit 失败", effects_audit=fx)
        if cfg.render_full_verify:
            for key in ("av_sync", "visual"):
                block = report.get(key) or {}
                if block.get("exit_code", 0) != 0:
                    _fail(f"{key}_failed", f"{key} exit_code != 0")
    return report


def assert_publish_bindings_dict(bindings: dict[str, Any] | None) -> None:
    if not bindings:
        _fail("bindings_missing", "无 publish_bindings")
    if bindings.get("warning"):
        _fail("bindings_warning", str(bindings.get("warning"))[:200])
    channels = bindings.get("channels") or {}
    if not channels:
        _fail("bindings_empty", "publish_bindings.channels 为空")


def assert_tts_artifacts(task_dir: Path, cfg: PipelineConfig) -> None:
    """渲染后检查各平台 plan 的 tts_durations（TTS 失败会缺项）。"""
    if not cfg.render_enabled or cfg.render_skip_tts:
        return
    for pid in [p.id for p in video_platforms(cfg.render_platforms)]:
        plan = _load_json(task_dir / "llm" / f"video_clips_{pid}.json")
        clips = plan.get("clips") or []
        tts_durs = plan.get("tts_durations") or []
        n_voice = sum(1 for c in clips if (c.get("tts_text") or "").strip())
        if n_voice and len(tts_durs) < n_voice:
            _fail("tts_incomplete", f"{pid}: tts_durations={len(tts_durs)} < clips={n_voice}")
        if n_voice and any(float(x or 0) <= 0 for x in tts_durs):
            _fail("tts_zero_duration", f"{pid}: 存在 0 时长 TTS")


def assert_task_ready_for_publish(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    brief_dict: dict[str, Any] | None = None,
    strict: bool | None = None,
) -> dict[str, Any]:
    """
    任务进入 ready_to_publish 前必须通过；发布 API / Playwright 发布前复用。
    返回摘要供写入 job / API。
    """
    task_dir = task_dir.resolve()
    if cfg.render_enabled:
        assert_broll_ready(cfg)
        assert_publish_pack_meta(task_dir, cfg, strict=strict)
        assert_video_plans(task_dir, cfg, strict=strict)
    brief = brief_dict or _load_json(task_dir / "brief.json")
    assert_publish_bindings_dict(brief.get("publish_bindings"))
    if cfg.render_enabled:
        quick = assert_all_platform_videos(task_dir, cfg)
        report = assert_verify_report(task_dir, cfg, strict=strict)
        assert_tts_artifacts(task_dir, cfg)
        return {"quick": quick, "verify": report, "bindings": brief.get("publish_bindings")}
    return {"bindings": brief.get("publish_bindings")}


def assert_channel_publishable(
    cfg: PipelineConfig,
    article_id: int,
    channel_id: str,
    *,
    job: dict[str, Any] | None = None,
) -> Path:
    """单渠道发布前：任务就绪 + 对应成片存在。"""
    from .models import content_key_for_article

    task_dir = cfg.output_root / str(article_id)
    if not task_dir.is_dir():
        if cfg.render_enabled:
            _fail("task_missing", f"任务目录不存在: {task_dir}")
        task_dir.mkdir(parents=True, exist_ok=True)

    if job:
        st = str(job.get("status") or "")
        if st not in ("ready_to_publish", "completed", "rendered", "packed"):
            _fail("job_not_ready", f"任务状态 {st} 不可发布")
        brief_raw = job.get("brief_json")
        brief: dict[str, Any] = {}
        if isinstance(brief_raw, dict):
            brief = brief_raw
        elif isinstance(brief_raw, str) and brief_raw.strip():
            try:
                brief = json.loads(brief_raw)
            except json.JSONDecodeError:
                pass
    else:
        brief = _load_json(task_dir / "brief.json")

    assert_task_ready_for_publish(cfg, task_dir, brief_dict=brief, strict=True)

    if not cfg.render_enabled:
        return task_dir

    if not is_video_platform(channel_id):
        preset = get_platform_preset(channel_id)
        if preset.publish_file:
            text_path = task_dir / "publish" / preset.publish_file
            if not text_path.is_file() or not text_path.read_text(encoding="utf-8").strip():
                _fail("channel_article_missing", f"缺少 {preset.publish_file}")
            return text_path
        _fail("channel_unknown", f"未知渠道 {channel_id}")

    video = task_dir / "videos" / f"{channel_id}.mp4"
    if not video.is_file():
        _fail("channel_video_missing", f"缺少 videos/{channel_id}.mp4")

    ck = content_key_for_article(article_id)
    if job and channel_id in ("douyin", "xhs", "toutiao", "douban"):
        from .publish_guard import validate_publish_target

        try:
            validate_publish_target(cfg, job, channel_id, None)
        except PublishGuardError as e:
            _fail(e.code, e.message)

    return video


def gate_summary(task_dir: Path, cfg: PipelineConfig) -> dict[str, Any]:
    """运行全部门禁，返回 ok / errors（不抛异常，供巡检脚本）。"""
    errors: list[dict[str, str]] = []
    try:
        assert_task_ready_for_publish(cfg, task_dir)
        return {"ok": True, "errors": []}
    except PipelineGateError as e:
        errors.append({"code": e.code, "message": e.message})
        return {"ok": False, "errors": errors}
    except Exception as e:
        errors.append({"code": type(e).__name__, "message": str(e)[:200]})
        return {"ok": False, "errors": errors}
