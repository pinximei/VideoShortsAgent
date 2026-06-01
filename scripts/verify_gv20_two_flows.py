#!/usr/bin/env python3
"""
20 套 G + 20 套 V 真实验收（顺序执行，不伪造）：

  流程 1：模板矩阵 — G01–G20 Remotion 标题镜 + V01–V20 Edge TTS 短样
  流程 2：生产管线 — middle slides_render 双平台成片（Compose 文案 + Dubbing + Remotion）

用法:
  py -3 scripts/verify_gv20_two_flows.py
  py -3 scripts/verify_gv20_two_flows.py --flow1-only
  py -3 scripts/verify_gv20_two_flows.py --flow2-only
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLE = ROOT / "middle"
REPORT_BASE = ROOT / "reports" / "gv20_two_flows"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _log(msg: str, lines: list[str]) -> None:
    print(msg)
    lines.append(msg)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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


def flow1_catalog_audit(lines: list[str]) -> dict:
    """检查 20+20 目录与 profile 接线。"""
    sys.path.insert(0, str(ROOT))
    from python_agent.motion_templates import load_github_daily_catalog
    from python_agent.voice_content_templates import load_voice_catalog
    g_styles = list(load_github_daily_catalog().get("styles") or [])
    v_styles = list(load_voice_catalog().get("styles") or [])
    mt_cat = json.loads(
        (ROOT / "templates" / "motion_templates" / "catalog.json").read_text(encoding="utf-8")
    )
    profiles_ok = set(mt_cat.get("profiles") or [])
    profiles_ok.update({"github_daily_hook", "github_daily_bullets"})

    issues: list[str] = []
    if len(g_styles) != 20:
        issues.append(f"github_daily count={len(g_styles)} expected 20")
    if len(v_styles) != 20:
        issues.append(f"voice_content count={len(v_styles)} expected 20")

    for s in g_styles:
        for key in ("title_profile", "content_profile", "bg"):
            if key not in s:
                issues.append(f"{s.get('id')}: missing {key}")
        if "css" not in s:
            issues.append(f"{s.get('id')}: missing css (may be empty)")
        for prof in (s.get("title_profile"), s.get("content_profile")):
            if prof and prof not in profiles_ok:
                issues.append(f"{s.get('id')}: unknown profile {prof}")

    for s in v_styles:
        ref = str(s.get("reference_motion") or "")
        if ref and not any(str(g.get("id") or "").startswith(ref) for g in g_styles):
            issues.append(f"{s.get('id')}: reference_motion {ref} has no G")

    seed_ids: list[str] = []
    for i in range(40):
        from python_agent.motion_templates import pick_github_daily_style

        picked = pick_github_daily_style(
            {"content_key": f"seed_{i}", "feed_kind": "github_daily", "platform": "douyin"}
        )
        seed_ids.append(str(picked.get("id") or ""))
    unique_g = len(set(seed_ids))

    seed_v: list[str] = []
    for i in range(40):
        from python_agent.voice_content_templates import pick_voice_content_style

        v = pick_voice_content_style(
            {"content_key": f"seed_{i}", "feed_kind": "github_daily", "platform": "douyin"}
        )
        seed_v.append(str(v.get("id") or ""))
    unique_v = len(set(seed_v))

    out = {
        "g_count": len(g_styles),
        "v_count": len(v_styles),
        "unique_g_from_40_seeds": unique_g,
        "unique_v_from_40_seeds": unique_v,
        "issues": issues,
        "ok": not issues and len(g_styles) == 20 and len(v_styles) == 20,
    }
    _log(f"[Flow1a] catalog G={len(g_styles)} V={len(v_styles)} unique_g={unique_g} unique_v={unique_v}", lines)
    for iss in issues:
        _log(f"  ISSUE: {iss}", lines)
    return out


def flow1_g20_render(report_dir: Path, lines: list[str]) -> dict:
    """真实跑 G01–G20 Remotion（复用 verify_github_daily_all）。"""
    _log("[Flow1b] G01-G20 Remotion render (real npx)...", lines)
    script = ROOT / "scripts" / "motion_research" / "verify_github_daily_all.py"
    log_path = report_dir / "flow1_g20_stdout.log"
    p = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )
    log_path.write_text((p.stdout or "") + "\n" + (p.stderr or ""), encoding="utf-8")
    manifest = ROOT / "research" / "motion" / "github_daily" / "verify_g20" / "manifest.json"
    ok = 0
    total = 20
    results = []
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        ok = int(data.get("ok") or 0)
        total = int(data.get("total") or 20)
        results = data.get("results") or []
    _log(f"[Flow1b] G20 render: {ok}/{total} (log {log_path.name})", lines)
    return {
        "ok": ok,
        "total": total,
        "exit_code": p.returncode,
        "manifest": str(manifest),
        "results": results,
        "stdout_log": str(log_path),
    }


def flow1_v20_tts(report_dir: Path, lines: list[str]) -> dict:
    """真实 Edge TTS：每套 V 一句口播样音。"""
    sys.path.insert(0, str(ROOT))
    from python_agent.skills.dubbing_skill import DubbingSkill
    from python_agent.tts_params import resolve_tts_params
    from python_agent.voice_content_templates import load_voice_catalog

    out_dir = report_dir / "flow1_v20_audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    _log("[Flow1c] V01-V20 Edge TTS (real audio)...", lines)

    styles = list(load_voice_catalog().get("styles") or [])
    results: list[dict] = []
    ok = 0
    text = "别划走，今天这个 GitHub 项目三分钟讲清，评论区要链接。"

    for s in styles:
        sid = s["id"]
        tts = resolve_tts_params(s, platform_voice="zh-CN-YunyangNeural")
        dub = DubbingSkill(
            voice=tts["tts_voice"],
            tts_rate=tts["tts_rate"],
            tts_pitch=tts["tts_pitch"],
            sentence_pause=float(tts.get("sentence_pause_sec") or 0.14),
        )
        work = out_dir / sid
        work.mkdir(exist_ok=True)
        row = {"id": sid, "tts_voice": tts["tts_voice"], "tts_rate": tts["tts_rate"]}
        try:
            batch = dub._generate_tts_batch([text], str(work), 0)
            path = batch[0]["path"] if batch else ""
            mp3 = Path(path)
            if mp3.is_file() and mp3.stat().st_size > 500:
                dur = dub._get_audio_duration(str(mp3))
                row["ok"] = True
                row["bytes"] = mp3.stat().st_size
                row["duration_sec"] = round(dur, 2)
                row["sha256"] = _sha256(mp3)
                row["path"] = str(mp3.resolve())
                ok += 1
            else:
                row["ok"] = False
                row["error"] = "empty_mp3"
        except Exception as exc:
            row["ok"] = False
            row["error"] = str(exc)[:200]
        results.append(row)
        mark = "OK" if row.get("ok") else "FAIL"
        _log(f"  [{mark}] {sid} {row.get('tts_rate')} {row.get('duration_sec', '-')}s", lines)

    manifest = {"ok": ok, "total": len(styles), "results": results}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _log(f"[Flow1c] V20 TTS: {ok}/{len(styles)}", lines)
    return manifest


def flow2_slides_production(report_dir: Path, lines: list[str]) -> dict:
    """真实 middle slides 管线：双平台各渲一条成片。"""
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(MIDDLE))
    from pipeline.config import load_config
    from pipeline.slides_render import render_slides_video

    task_dir = report_dir / "flow2_task"
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)

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
    from python_agent.voice_content_templates import (
        expand_script_tts_to_minimum,
        pick_voice_content_style,
        script_tts_char_total,
    )

    brief = {
        "title": "GV20 流程2 生产验收",
        "feed_kind": "github_daily",
        "series": "每天一个GitHub项目",
        "content_key": "gv20_flow2_prod",
    }
    (task_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    expanded = expand_script_tts_to_minimum(
        {"slides": slides},
        pick_voice_content_style({**brief, "platform": "douyin"}),
    )
    script = {"slides": expanded["slides"]}
    (llm_dir / "slides_script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tts_chars = script_tts_char_total(script["slides"])
    _log(f"[Flow2] slides_script ready, tts_chars={tts_chars}", lines)

    cfg_path = MIDDLE / "config.yaml"
    if not cfg_path.is_file():
        return {"ok": False, "error": "missing middle/config.yaml"}
    cfg = load_config(cfg_path)
    cfg.render_mode = "slides"
    cfg.render_enabled = True

    videos: dict[str, dict] = {}
    for platform in ("douyin", "xhs"):
        _log(f"[Flow2] slides_render platform={platform} ...", lines)
        try:
            out = render_slides_video(cfg, task_dir, platform_id=platform)
            mp4 = Path(out)
            gpath = llm_dir / f"github_daily_style_{platform}.json"
            vpath = llm_dir / f"voice_content_style_{platform}.json"
            g_id = v_id = ""
            if gpath.is_file():
                g_id = json.loads(gpath.read_text(encoding="utf-8")).get("picked", {}).get("id", "")
            if vpath.is_file():
                v_id = json.loads(vpath.read_text(encoding="utf-8")).get("style", {}).get("id", "")
            ok = mp4.is_file() and mp4.stat().st_size > 100_000
            videos[platform] = {
                "ok": ok,
                "path": str(mp4.resolve()),
                "bytes": mp4.stat().st_size if ok else 0,
                "duration_sec": _probe_duration(mp4) if ok else 0,
                "sha256": _sha256(mp4) if ok else "",
                "G": g_id,
                "V": v_id,
            }
            _log(
                f"  [{platform}] {'OK' if ok else 'FAIL'} G={g_id} V={v_id} "
                f"{videos[platform].get('bytes', 0)}B {videos[platform].get('duration_sec', 0):.1f}s",
                lines,
            )
        except Exception as exc:
            videos[platform] = {"ok": False, "error": str(exc)[:400]}
            _log(f"  [{platform}] FAIL {exc}", lines)

    all_ok = all(v.get("ok") for v in videos.values())
    return {"ok": all_ok, "videos": videos, "tts_chars": tts_chars, "task_dir": str(task_dir)}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--flow1-only", action="store_true")
    ap.add_argument("--flow2-only", action="store_true")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = REPORT_BASE / ts
    report_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    proof: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "report_dir": str(report_dir)}

    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    ).stdout.strip()
    proof["git_head"] = git_head

    exit_code = 0

    if not args.flow2_only:
        _log("\n========== 流程 1：20 G + 20 V 模板矩阵（真实渲染/配音）==========", lines)
        proof["flow1"] = {}
        proof["flow1"]["catalog"] = flow1_catalog_audit(lines)
        if not proof["flow1"]["catalog"].get("ok"):
            exit_code = 1
        proof["flow1"]["g20"] = flow1_g20_render(report_dir, lines)
        if proof["flow1"]["g20"].get("ok", 0) < 20:
            exit_code = 1
        proof["flow1"]["v20"] = flow1_v20_tts(report_dir, lines)
        if proof["flow1"]["v20"].get("ok", 0) < 20:
            exit_code = 1

    if not args.flow1_only:
        _log("\n========== 流程 2：生产 slides 管线（douyin + xhs 成片）==========", lines)
        proof["flow2"] = flow2_slides_production(report_dir, lines)
        if not proof["flow2"].get("ok"):
            exit_code = 1

    (report_dir / "PROOF.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (report_dir / "console.log").write_text("\n".join(lines), encoding="utf-8")

    md = [
        "# G20+V20 双流程真实验收",
        "",
        f"- UTC: {proof['generated_at']}",
        f"- Git: `{git_head}`",
        f"- 目录: `{report_dir}`",
        "",
        "## 流程 1（模板矩阵）",
        "",
    ]
    f1 = proof.get("flow1") or {}
    if f1:
        c = f1.get("catalog") or {}
        g = f1.get("g20") or {}
        v = f1.get("v20") or {}
        md.append(f"- 目录检查: {'PASS' if c.get('ok') else 'FAIL'} (G={c.get('g_count')} V={c.get('v_count')})")
        md.append(f"- G20 Remotion: **{g.get('ok')}/{g.get('total')}**")
        md.append(f"- V20 TTS: **{v.get('ok')}/{v.get('total')}**")
    f2 = proof.get("flow2") or {}
    if f2:
        md.extend(["", "## 流程 2（slides 生产）", ""])
        for plat, row in (f2.get("videos") or {}).items():
            md.append(
                f"- **{plat}**: {'PASS' if row.get('ok') else 'FAIL'} "
                f"G=`{row.get('G')}` V=`{row.get('V')}` "
                f"[{row.get('path', '')}]({row.get('path', '')})"
            )
    (report_dir / "PROOF.md").write_text("\n".join(md), encoding="utf-8")

    _log(f"\n报告: {report_dir / 'PROOF.md'}", lines)
    _log(f"exit={exit_code}", lines)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
