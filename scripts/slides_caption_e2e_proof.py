#!/usr/bin/env python3
"""Slides 模式端到端：TTS 分句 + Remotion 成片 + 字幕单行检查。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = ROOT / "reports" / "slides_caption_proof"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _ffprobe_duration(path: Path) -> float:
    p = subprocess.run(
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
    if p.returncode != 0:
        return 0.0
    try:
        return float((p.stdout or "0").strip())
    except ValueError:
        return 0.0


def _check_sentences(tts_clips: list, max_chars: int = 14) -> dict:
    issues: list[str] = []
    total = 0
    max_len = 0
    for ci, clip in enumerate(tts_clips):
        for si, s in enumerate(clip.get("sentences") or []):
            total += 1
            t = str(s.get("text", "") or "")
            if "\n" in t:
                issues.append(f"clip{ci} sent{si}: contains newline")
            ln = len(t.replace("\n", ""))
            max_len = max(max_len, ln)
            if ln > max_chars:
                issues.append(f"clip{ci} sent{si}: len={ln} > {max_chars}")
    return {
        "sentence_count": total,
        "max_line_chars": max_len,
        "issues": issues,
        "ok": len(issues) == 0 and total > 0,
    }


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = REPORT_BASE / ts
    task_dir = report_dir / "task"
    work = task_dir / "videos" / "_slides_work_douyin"
    work.mkdir(parents=True, exist_ok=True)
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(ROOT))
    from python_agent.display_text import CAPTION_LINE_MAX_CHARS, split_caption_sentences
    from python_agent.motion_templates import (
        apply_template_plan_to_slides,
        build_github_daily_slide_plan,
        save_github_daily_style,
    )
    from python_agent.skills.dubbing_skill import DubbingSkill
    from python_agent.skills.render_slides_skill import RenderSlidesSkill
    from python_agent.template_loader import get_style

    brief = {
        "title": "Slides 字幕+动效证明",
        "platform": "douyin",
        "feed_kind": "github_daily",
        "series": "每天一个GitHub项目",
        "tts_voice": "zh-CN-YunyangNeural",
        "tts_rate": "+14%",
        "tts_pitch": "+8Hz",
    }

    slides = [
        {
            "type": "title_card",
            "heading": "GitHub爆款",
            "hook_text": "别划走",
            "tts_text": "别划走，今天这个 GitHub 项目 Star 涨了一万，三分钟讲清它为什么火。",
            "motion_profile": "github_daily_hook",
            "visual_design": {"caption_style": "spring", "transition_to_next": "slideup"},
        },
        {
            "type": "content_card",
            "heading": "日更神器",
            "bullets": [{"text": "自动抓趋势", "trigger": "自动"}],
            "tts_text": "它能自动抓趋势、生成短视频脚本，还支持一键配音，适合日更科技号。",
            "motion_profile": "github_daily_bullets",
            "visual_design": {"caption_style": "spring", "transition_to_next": "fade"},
        },
        {
            "type": "cta_card",
            "heading": "关注",
            "cta_text": "评论区要链接",
            "tts_text": "链接在评论区，点个关注，明天继续拆榜。",
            "motion_profile": "github_daily_cta",
            "visual_design": {"caption_style": "spring", "transition_to_next": ""},
        },
    ]
    picked, gplan = build_github_daily_slide_plan(brief, slides)
    slides = apply_template_plan_to_slides(slides, brief)
    save_github_daily_style(task_dir, picked, gplan)
    style_id = picked.get("id") or slides[0].get("github_daily_style_id")
    print(f"[motion] github_daily style={style_id} title_profile={picked.get('motion_profile')}")

    script = {"slides": slides}
    (llm_dir / "slides_script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (task_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[1/3] Dubbing (split spoken phrases)…")
    dubbing = DubbingSkill(voice="zh-CN-YunyangNeural", tts_rate="+14%", tts_pitch="+8Hz")
    tts_input = [{"tts_text": s["tts_text"]} for s in slides]
    tts_result = dubbing.execute(tts_input, str(work))
    tts_clips = tts_result.get("tts_clips", []) if isinstance(tts_result, dict) else tts_result
    if not tts_clips:
        print("FAIL: no tts_clips")
        return 1

    # 渲染前分句（与 RenderSlidesSkill 一致）
    for clip in tts_clips:
        clip["sentences"] = split_caption_sentences(clip.get("sentences", []))

    sent_check = _check_sentences(tts_clips, max_chars=CAPTION_LINE_MAX_CHARS + 2)
    print(f"  sentences: {sent_check['sentence_count']}, max_chars={sent_check['max_line_chars']}")
    if sent_check["issues"]:
        for i in sent_check["issues"][:10]:
            print(f"  WARN: {i}")

    print("[2/3] Remotion slides render…")
    visual_style = get_style("github_dark")
    renderer = RenderSlidesSkill()
    out_path = renderer.execute(slides, tts_clips, visual_style, str(work), bgm_path=None)
    out_mp4 = Path(out_path)
    if not out_mp4.is_file() or out_mp4.stat().st_size < 10000:
        print(f"FAIL: bad output {out_mp4}")
        return 1

    target = task_dir / "videos" / "douyin.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy2(out_mp4, target)

    dur = _ffprobe_duration(target)
    proof = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "caption_check": sent_check,
        "cap_line_max": CAPTION_LINE_MAX_CHARS,
        "motion_style_id": style_id,
        "motion_profiles": [s.get("motion_profile") for s in slides],
        "css_decorations": [s.get("css_decorations") for s in slides],
        "output": {
            "path": str(target.resolve()),
            "bytes": target.stat().st_size,
            "sha256": _sha256(target),
            "duration_sec": dur,
        },
        "sample_sentences": [
            s
            for c in tts_clips[:2]
            for s in (c.get("sentences") or [])[:4]
        ],
    }
    (report_dir / "PROOF.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[3/3] OK: {target} ({target.stat().st_size:,} B, {dur:.1f}s)")
    print(f"  sha256={proof['output']['sha256'][:16]}…")
    print(f"  report: {report_dir / 'PROOF.json'}")
    return 0 if sent_check["ok"] and dur > 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
