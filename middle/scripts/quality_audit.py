#!/usr/bin/env python3
"""质量自检：不重渲，只读任务目录产出（视频 + 文案 + 钩子规则）。"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_HOOK_PATTERNS = (
    re.compile(r"[？?]"),
    re.compile(r"\d"),
    re.compile(r"居然|竟然|别再|为什么|怎么|值不值|刚刚|首发|免费", re.I),
)


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _ffprobe_duration(path: Path) -> float | None:
    if not path.is_file():
        return None
    try:
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
            timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception:
        pass
    return None


def _hook_score(text: str) -> tuple[int, list[str]]:
    t = (text or "").strip()
    issues: list[str] = []
    score = 10
    if len(t) < 6:
        issues.append("钩子过短")
        score -= 4
    if len(t) > 28:
        issues.append(f"钩子 {len(t)} 字，建议 ≤28")
        score -= 2
    if not any(p.search(t) for p in _HOOK_PATTERNS):
        issues.append("缺少疑问/数字/反差词（吸引力偏弱）")
        score -= 3
    bad = ("大家好", "今天介绍", "本期", "分享一下", "付费记录对话")
    if any(b in t for b in bad):
        issues.append("含平淡开场用语")
        score -= 2
    return max(0, score), issues


def _clip_opening_score(clips: list, *, feed_kind: str = "news") -> tuple[int, list[str]]:
    issues: list[str] = []
    score = 10
    if not clips:
        return 0, ["无 clips 计划"]
    c0 = clips[0] if isinstance(clips[0], dict) else {}
    ht = str(c0.get("hook_text") or "")
    tts = str(c0.get("tts_text") or "")
    start_raw = c0.get("start")
    if start_raw is None or float(start_raw) != 0.0:
        issues.append("第 1 段 start 不是 0")
        score -= 3
    if len(ht) > 18:
        issues.append(f"第 1 段 hook_text {len(ht)} 字，建议 ≤18")
        score -= 2
    hs, hi = _hook_score(ht)
    if hs < 7:
        issues.extend([f"屏显: {x}" for x in hi])
        score -= 2
    if tts.startswith(("大家好", "今天", "本期", "Bluedot")):
        issues.append("口播首句偏介绍体，缺悬念")
        score -= 2
    cap = str(c0.get("caption_style") or "")
    trans = str(c0.get("transition_to_next") or "")
    if cap != "spring":
        issues.append(f"第 1 段 caption_style={cap or '默认'}，建议 spring")
        score -= 1
    if (feed_kind or "news").strip().lower() != "news" and trans not in ("circleopen", "slideup"):
        issues.append(f"第 1 段转场={trans or '默认'}，建议 circleopen/slideup")
        score -= 1
    return max(0, score), issues


def audit_task(task_dir: Path) -> dict:
    from python_agent.capabilities.opening_hook import scroll_stopping_hook

    brief = _load_json(task_dir / "brief.json") or {}
    platform = _load_json(task_dir / "llm" / "platform_copy.json") or {}
    verify = _load_json(task_dir / "verify_report.json") or {}

    title = str(brief.get("title") or "")
    raw_hook = str(brief.get("hook") or "")
    ideal_hook = scroll_stopping_hook(
        title=title, hook=raw_hook, feed_kind=str(brief.get("feed_kind") or "news")
    )

    brief_score, brief_issues = _hook_score(raw_hook)
    ideal_score, _ = _hook_score(ideal_hook)

    copy_scores: dict[str, dict] = {}
    for plat in ("douyin", "xhs"):
        block = platform.get(plat) if isinstance(platform, dict) else {}
        if not isinstance(block, dict):
            continue
        clips = block.get("clips") or []
        cs, ci = _clip_opening_score(
            clips if isinstance(clips, list) else [], feed_kind=str(brief.get("feed_kind") or "news")
        )
        fx = block.get("effects") or {}
        intro = bool(fx.get("intro_card"))
        copy_scores[plat] = {
            "clip_opening_score": cs,
            "clip_issues": ci,
            "intro_card": intro,
            "title": str(block.get("title") or "")[:60],
            "title_first_line_hook": _hook_score(str(block.get("title") or ""))[0] >= 7,
        }

    videos: dict[str, dict] = {}
    for plat in ("douyin", "xhs"):
        vp = task_dir / "videos" / f"{plat}.mp4"
        dur = _ffprobe_duration(vp)
        videos[plat] = {
            "exists": vp.is_file(),
            "duration_sec": round(dur, 2) if dur else None,
            "size_mb": round(vp.stat().st_size / 1e6, 1) if vp.is_file() else None,
        }

    verify_ok = verify.get("ok")
    quick_ok = (verify.get("quick") or {}).get("ok")
    visual_ok = (verify.get("visual") or {}).get("exit_code") == 0
    av_tail = str((verify.get("av_sync") or {}).get("stdout_tail") or "")

    article_score = int(round((brief_score + ideal_score) / 2))
    video_plan_score = 0
    if copy_scores:
        video_plan_score = int(
            round(sum(v["clip_opening_score"] for v in copy_scores.values()) / len(copy_scores))
        )

    tech_ok = bool(quick_ok) and bool(visual_ok) and verify_ok is True
    opening_ok = brief_score >= 7 and video_plan_score >= 7 and all(
        v.get("intro_card") for v in copy_scores.values() if v
    )

    from pipeline.quality_rules import evaluate_task_quality, min_clips_for_feed

    fk = str(brief.get("feed_kind") or "news")
    qr = evaluate_task_quality(task_dir, feed_kind=fk)
    rules_ok = bool(qr.get("ok"))

    return {
        "task_dir": str(task_dir),
        "article_id": brief.get("article_id"),
        "title": title[:80],
        "worth_score": brief.get("worth_score"),
        "brief_hook": raw_hook,
        "ideal_hook_suggestion": ideal_hook,
        "brief_hook_score": brief_score,
        "brief_hook_issues": brief_issues,
        "platform_copy": copy_scores,
        "videos": videos,
        "verify": {
            "ok": verify_ok,
            "quick_ok": quick_ok,
            "visual_ok": visual_ok,
            "av_sync_tail": av_tail[-500:] if av_tail else "",
        },
        "scores": {
            "article_hook": article_score,
            "video_plan_opening": video_plan_score,
            "tech_verify": 10 if tech_ok else (6 if quick_ok and visual_ok else 3),
            "quality_rules": 10 if rules_ok else 4,
        },
        "quality_rules": qr,
        "verdict": {
            "good_enough": tech_ok and opening_ok and article_score >= 7 and rules_ok,
            "needs_rerender": not tech_ok or not rules_ok or video_plan_score < 8,
            "needs_copy_refresh": brief_score < 7 or video_plan_score < 7 or not rules_ok,
        },
    }


def _print_report(report: dict) -> None:
    v = report["verdict"]
    print("=" * 60)
    print(f"质量自检 · 文章 #{report.get('article_id')} ")
    print(f"目录: {report['task_dir']}")
    print("=" * 60)
    print(f"\n标题: {report['title']}")
    print(f"worth_score: {report.get('worth_score')}")
    print(f"\n【文章钩子】得分 {report['scores']['article_hook']}/10")
    print(f"  brief.hook: {report['brief_hook']}")
    if report["brief_hook_issues"]:
        for i in report["brief_hook_issues"]:
            print(f"    ⚠ {i}")
    print(f"  建议钩子: {report['ideal_hook_suggestion']}")

    print(f"\n【视频文案/分镜开场】得分 {report['scores']['video_plan_opening']}/10")
    for plat, info in (report.get("platform_copy") or {}).items():
        print(f"  [{plat}] intro_card={info.get('intro_card')} title={info.get('title')}")
        for i in info.get("clip_issues") or []:
            print(f"    ⚠ {i}")

    print("\n【成片文件】")
    for plat, info in (report.get("videos") or {}).items():
        ex = "有" if info.get("exists") else "无"
        print(f"  {plat}: {ex}  {info.get('duration_sec')}s  {info.get('size_mb')}MB")

    ver = report.get("verify") or {}
    print(f"\n【技术验收】得分 {report['scores']['tech_verify']}/10")
    print(f"  verify.ok={ver.get('ok')} quick={ver.get('quick_ok')} visual={ver.get('visual_ok')}")
    if ver.get("av_sync_tail"):
        print("  av_sync 摘要:")
        for line in ver["av_sync_tail"].splitlines()[-6:]:
            if line.strip():
                print(f"    {line}")

    print("\n" + "=" * 60)
    qr_issues = (report.get("quality_rules") or {}).get("issues") or []
    if qr_issues:
        print("\n【质量规则】")
        for i in qr_issues:
            print(f"  ⚠ {i}")

    if v["good_enough"]:
        print("总评: ✅ 当前样本可进入发布前人工抽检")
    else:
        print("总评: ⚠️ 建议先优化再发布")
        if v["needs_copy_refresh"]:
            print("  → 文案/钩子：重新跑 pipeline 或至少重生成 platform_copy")
        if v["needs_rerender"]:
            print("  → 成片：用最新代码重渲（片头片尾 + 开场 spring）")
    print("=" * 60)
    print(f"\n本地打开视频:")
    td = Path(report["task_dir"])
    for plat in ("douyin", "xhs"):
        p = td / "videos" / f"{plat}.mp4"
        if p.is_file():
            print(f"  {p}")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="质量自检（不重渲）")
    ap.add_argument("task", help="任务目录或文章 ID，如 885 或 data/output/885")
    args = ap.parse_args()

    raw = Path(args.task)
    if raw.is_dir():
        task_dir = raw.resolve()
    elif str(args.task).isdigit():
        task_dir = (ROOT / "data" / "output" / args.task).resolve()
    else:
        task_dir = (ROOT / args.task).resolve()

    if not task_dir.is_dir():
        print(f"目录不存在: {task_dir}", file=sys.stderr)
        return 1

    report = audit_task(task_dir)
    _print_report(report)
    out = task_dir / "quality_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入: {out}")
    return 0 if report["verdict"]["good_enough"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
