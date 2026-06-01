#!/usr/bin/env python3
"""
双平台爆款对标自检：语速(WPM)、口播语义(字数/钩子)、画风(G/V/Remotion)。

用法:
  py -3 scripts/platform_burst_audit.py
  py -3 scripts/platform_burst_audit.py --skip-render   # 仅分析已有报告目录
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLE = ROOT / "middle"
REPORT_BASE = ROOT / "reports" / "platform_burst_audit"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 对标 research/voice_content/asr_analysis.json 科技口播中位
DOUYIN_WPM_TARGET = (300, 380)
XHS_WPM_TARGET = (260, 340)
DOUYIN_CHARS_TARGET = (180, 260)
XHS_CHARS_TARGET = (160, 240)


def _probe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def _extract_audio(mp4: Path, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "16000", str(out)],
        capture_output=True,
        timeout=120,
    )


def _asr_wpm(audio: Path) -> dict | None:
    script = ROOT / "scripts" / "motion_research" / "asr_dashscope_one.py"
    if not script.is_file():
        return None
    env = os.environ.copy()
    sys.path.insert(0, str(ROOT / "scripts" / "motion_research"))
    try:
        from dashscope_asr_util import load_env

        load_env()
    except Exception:
        pass
    if not os.getenv("DASHSCOPE_API_KEY", "").strip():
        return None
    p = subprocess.run(
        [sys.executable, str(script), str(audio)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT / "scripts" / "motion_research"),
        timeout=180,
    )
    if p.returncode != 0:
        return {"error": (p.stderr or "")[-300:]}
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def _hook_ok(text: str, pattern: str) -> bool:
    universal = ("别划", "你绝对", "三分钟", "真的", "居然", "刚刚", "突发", "暴涨", "破万", "Top")
    if any(u in text for u in universal):
        return True
    if not pattern:
        return "你" in text
    parts = re.split(r"[|｜]", pattern)
    return any(p.strip() and p.strip() in text for p in parts)


def _score_platform(
    platform: str,
    *,
    tts_chars: int,
    duration: float,
    voice: str,
    rate: str,
    motion_id: str,
    voice_id: str,
    profiles: list[str],
    remotion_ok: bool,
    hook_text: str,
    hook_pattern: str,
    asr: dict | None,
) -> dict:
    wpm_est = int(tts_chars / duration * 60) if duration > 1 else 0
    wpm = (asr or {}).get("chars_per_minute") or wpm_est
    wlo, whi = DOUYIN_WPM_TARGET if platform == "douyin" else XHS_WPM_TARGET
    clo, chi = DOUYIN_CHARS_TARGET if platform == "douyin" else XHS_CHARS_TARGET

    issues: list[str] = []
    if wpm < wlo and platform == "douyin":
        issues.append(f"语速偏慢: {wpm} 字/分 < {wlo}（爆款区间 {wlo}~{whi}）")
    elif wpm < wlo - 30 and platform == "xhs":
        issues.append(f"小红书语速偏慢: {wpm} 字/分 < {wlo - 30}")
    elif wpm > whi + 40:
        issues.append(f"语速偏快: {wpm} 字/分 > {whi}")
    if tts_chars < clo:
        issues.append(f"口播过短: {tts_chars} 字 < {clo}（信息密度不足）")
    elif tts_chars > chi + 80:
        issues.append(f"口播过长: {tts_chars} 字 > {chi}")

    if platform == "douyin":
        if "Yunxi" in voice and "Yunyang" not in voice:
            issues.append("抖音音色偏沉(Yunxi)，应对标 Yunyang")
        if rate in ("+0%", "+5%", "0%"):
            issues.append(f"抖音语速 rate 过慢: {rate}")
        if not any("tiktok" in p or "kinetic" in p or "marquee" in p or "github_daily_hook" in p for p in profiles):
            issues.append(f"画风偏静: profiles={profiles}")
    else:
        if "Xiaoxiao" not in voice and "Xiaoyi" not in voice:
            issues.append(f"小红书应女声，当前: {voice}")
        if not any("minimal" in p or "glass" in p or "bullet" in p for p in profiles):
            if not any(motion_id.startswith(x) for x in ("G02", "G03", "G04", "G10", "G16", "G20")):
                issues.append(f"小红书画风偏硬: G={motion_id} profiles={profiles}")

    if not remotion_ok:
        issues.append("未走 Remotion（可能 FFmpeg 降级）")
    if not _hook_ok(hook_text, hook_pattern):
        issues.append("首镜缺少爆款钩子句式")

    return {
        "platform": platform,
        "wpm": wpm,
        "wpm_estimated": wpm_est,
        "wpm_target": [wlo, whi],
        "tts_chars": tts_chars,
        "chars_target": [clo, chi],
        "duration_sec": round(duration, 2),
        "tts_voice": voice,
        "tts_rate": rate,
        "motion_style_id": motion_id,
        "voice_style_id": voice_id,
        "motion_profiles": profiles,
        "remotion_ok": remotion_ok,
        "asr": asr,
        "issues": issues,
        "ok": len(issues) == 0,
    }


def _render_platform(task_dir: Path, platform: str, slides: list, brief: dict, voice_style: dict) -> dict:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(MIDDLE))
    from python_agent.display_text import split_caption_sentences
    from python_agent.motion_templates import apply_template_plan_to_slides, build_github_daily_slide_plan
    from python_agent.skills.dubbing_skill import DubbingSkill
    from python_agent.skills.render_slides_skill import RenderSlidesSkill
    from python_agent.template_loader import get_style
    from python_agent.tts_params import prepare_brief_tts
    from middle.pipeline.platform_presets import get_platform_preset

    b = dict(brief)
    b["platform"] = platform
    picked, _ = build_github_daily_slide_plan(b, slides)
    plat_slides = apply_template_plan_to_slides([dict(s) for s in slides], b)
    preset = get_platform_preset(platform)
    for slide in plat_slides:
        vd = dict(slide.get("visual_design") or {})
        if platform == "xhs":
            vd["caption_style"] = preset.effects.get("caption_style", "fade")
            slide["caption_style"] = vd["caption_style"]
        slide["visual_design"] = vd

    b = prepare_brief_tts(b, platform, voice_style=voice_style)
    work = task_dir / "videos" / f"_audit_{platform}"
    work.mkdir(parents=True, exist_ok=True)

    dubbing = DubbingSkill(
        voice=str(b.get("tts_voice") or preset.voice),
        tts_rate=str(b.get("tts_rate") or "+12%"),
        tts_pitch=str(b.get("tts_pitch") or "+0Hz"),
        sentence_pause=float(b.get("sentence_pause_sec") or 0.16),
    )
    tts_result = dubbing.execute([{"tts_text": s["tts_text"]} for s in plat_slides], str(work))
    tts_clips = tts_result.get("tts_clips", []) if isinstance(tts_result, dict) else tts_result
    for clip in tts_clips:
        clip["sentences"] = split_caption_sentences(clip.get("sentences", []))

    renderer = RenderSlidesSkill()
    visual_style = get_style("github_dark")
    out = Path(renderer.execute(plat_slides, tts_clips, visual_style, str(work), None))
    target = task_dir / "videos" / f"{platform}.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy2(out, target)

    return {
        "picked": picked,
        "slides": plat_slides,
        "brief_tts": b,
        "mp4": target,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-render", action="store_true")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = REPORT_BASE / ts
    task_dir = report_dir / "task"
    task_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(MIDDLE))
    from python_agent.voice_content_templates import (
        pick_voice_content_style,
        script_tts_char_total,
        voice_style_prompt_block,
    )

    brief = {
        "title": "平台爆款对标自检",
        "feed_kind": "github_daily",
        "series": "每天一个GitHub项目",
        "content_key": "burst_audit_sample",
    }
    slides = [
        {
            "type": "title_card",
            "heading": "Star破万",
            "hook_text": "别划走",
            "tts_text": (
                "别划走！这个 GitHub 神器一夜涨了一万 Star，"
                "三分钟讲清它为什么火、普通人也能直接拿来干嘛，"
                "结尾我会告诉你怎么一键部署，小白也能跟着做。"
            ),
        },
        {
            "type": "content_card",
            "heading": "日更神器",
            "bullets": [{"text": "自动盯趋势", "trigger": "自动"}],
            "tts_text": (
                "它能自动盯热点、生成短视频脚本，还能一键配音出片，"
                "特别适合科技号日更，一个人也能干一个团队的活，"
                "省掉写稿剪辑的整块时间，还能把 README 要点自动讲明白。"
            ),
        },
        {
            "type": "cta_card",
            "heading": "评论区",
            "cta_text": "要链接",
            "tts_text": (
                "完整项目在评论区，先收藏别走丢，"
                "点个关注我们明天继续拆榜，错过就亏大了。"
            ),
        },
    ]
    tts_chars = script_tts_char_total(slides)
    hook_text = slides[0]["tts_text"]

    results: dict[str, dict] = {}
    if not args.skip_render:
        for platform in ("douyin", "xhs"):
            print(f"\n=== 渲染 {platform} ===")
            b = dict(brief)
            b["platform"] = platform
            voice_style = pick_voice_content_style(b)
            print(f"  V={voice_style.get('id')} G池=platform:{platform}")
            print(f"  TTS预设: {voice_style_prompt_block(voice_style)[:120]}...")
            row = _render_platform(task_dir, platform, slides, b, voice_style)
            results[platform] = row

    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    ).stdout.strip()

    scores: list[dict] = []
    for platform in ("douyin", "xhs"):
        mp4 = task_dir / "videos" / f"{platform}.mp4"
        if not mp4.is_file():
            scores.append({"platform": platform, "ok": False, "issues": ["缺少成片"]})
            continue
        dur = _probe_duration(mp4)
        row = results.get(platform) or {}
        picked = row.get("picked") or {}
        plat_slides = row.get("slides") or []
        btts = row.get("brief_tts") or {}
        voice_style = pick_voice_content_style({**brief, "platform": platform})
        audio = task_dir / "audio" / f"{platform}.m4a"
        audio.parent.mkdir(parents=True, exist_ok=True)
        _extract_audio(mp4, audio)
        asr = _asr_wpm(audio) if audio.is_file() else None

        profiles = [str(s.get("motion_profile") or "") for s in plat_slides]
        remotion_ok = mp4.stat().st_size > 200_000 and dur > 8
        scores.append(
            _score_platform(
                platform,
                tts_chars=tts_chars,
                duration=dur,
                voice=str(btts.get("tts_voice") or ""),
                rate=str(btts.get("tts_rate") or ""),
                motion_id=str(picked.get("id") or plat_slides[0].get("github_daily_style_id") or ""),
                voice_id=str(voice_style.get("id") or ""),
                profiles=profiles,
                remotion_ok=remotion_ok,
                hook_text=hook_text,
                hook_pattern=str(voice_style.get("hook_pattern") or ""),
                asr=asr,
            )
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "tts_script_chars": tts_chars,
        "benchmark": {
            "douyin_wpm": DOUYIN_WPM_TARGET,
            "xhs_wpm": XHS_WPM_TARGET,
            "median_ref_asr": 369,
        },
        "scores": scores,
        "videos": {p: str((task_dir / "videos" / f"{p}.mp4").resolve()) for p in ("douyin", "xhs")},
    }
    (report_dir / "AUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# 双平台爆款对标自检", "", f"- Git: `{git_head}`", ""]
    all_ok = True
    for s in scores:
        md.append(f"## {s['platform']}")
        md.append(f"- 通过: **{'是' if s.get('ok') else '否'}**")
        if s.get("wpm"):
            md.append(f"- 语速: **{s['wpm']}** 字/分（目标 {s.get('wpm_target')}）")
        md.append(f"- 口播字数: {s.get('tts_chars')}（目标 {s.get('chars_target')}）")
        md.append(f"- 音色/rate: `{s.get('tts_voice')}` `{s.get('tts_rate')}`")
        md.append(f"- 画风 G: `{s.get('motion_style_id')}` profiles={s.get('motion_profiles')}")
        md.append(f"- 口播 V: `{s.get('voice_style_id')}`")
        for iss in s.get("issues") or []:
            md.append(f"  - ⚠ {iss}")
            all_ok = False
        md.append("")
    (report_dir / "AUDIT.md").write_text("\n".join(md), encoding="utf-8")

    print("\n=== 结论 ===")
    for s in scores:
        status = "PASS" if s.get("ok") else "FAIL"
        print(f"  [{status}] {s['platform']}: wpm={s.get('wpm')} issues={s.get('issues')}")
    print(f"\n报告: {report_dir / 'AUDIT.md'}")
    return 0 if all(s.get("ok") for s in scores) else 1


if __name__ == "__main__":
    raise SystemExit(main())
