#!/usr/bin/env python3
"""固定 brief 评测：分句、字幕页、门禁（可选轻量渲染）。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _serious_caption_issues(issues: list[str]) -> list[str]:
    """merge_candidate 为提示项，不计入 CI 失败。"""
    return [i for i in issues if not str(i).startswith("merge_candidate:")]


def _load_fixtures() -> list[dict]:
    path = ROOT / "python_agent" / "tests" / "fixtures" / "slides_eval_briefs.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _eval_brief(brief: dict, *, platform: str, mock: bool = False) -> dict:
    from python_agent.caption_timeline import prepare_slide_captions, validate_caption_pages
    from python_agent.platform_caption_presets import apply_platform_presets_to_slides
    from python_agent.slides_llm_director import direct_slides_script
    from python_agent.slides_quality_gates import auto_fix_slides, validate_slides_before_render
    from python_agent.slides_scene_expander import expand_platform_scenes

    if mock:
        from python_agent.eval_mock_compose import mock_compose_from_brief

        script = mock_compose_from_brief(brief)
    else:
        from python_agent.skills.compose_skill import ComposeSkill

        compose_text = "\n".join(
            filter(
                None,
                [
                    f"标题：{brief.get('title', '')}",
                    f"钩子：{brief.get('hook', '')}",
                    *[f"- {p}" for p in brief.get("talking_points") or []],
                    f"引导：{brief.get('cta', '')}",
                ],
            )
        )
        script = ComposeSkill().execute(
            compose_text,
            "daily_github",
            "github_dark",
            motion_directed=True,
        )
    slides = expand_platform_scenes(script.get("slides") or [], platform)
    slides = direct_slides_script(slides, {**brief, "platform": platform}, platform)
    slides = apply_platform_presets_to_slides(auto_fix_slides(slides, platform=platform), platform)

    # 模拟 TTS 句轴（每镜一整段口播，与线上一句一页策略一致）
    mock_clips = []
    t = 0.0
    for s in slides:
        text = str(s.get("tts_text") or "").strip()
        if not text:
            mock_clips.append({"sentences": [], "duration": 1.0})
            continue
        dur = max(1.2, len(text) * 0.12)
        sents = [{"text": text, "start": t, "end": t + dur}]
        t += dur + 0.25
        mock_clips.append({"sentences": sents, "duration": max(1.0, t)})

    caption_stats = []
    for i, slide in enumerate(slides):
        raw = mock_clips[i]["sentences"] if i < len(mock_clips) else []
        _, pages = prepare_slide_captions(raw, slide, platform=platform)
        caption_stats.append(
            {
                "slide": i,
                "type": slide.get("type"),
                "pages": len(pages),
                "texts": [p.get("text") for p in pages],
                "issues": validate_caption_pages(pages),
                "issues_blocking": _serious_caption_issues(validate_caption_pages(pages)),
            }
        )

    gate = validate_slides_before_render(slides, platform=platform)
    viz = {}
    for s in slides:
        vt = str(s.get("viz_type") or "none")
        viz[vt] = viz.get(vt, 0) + 1

    return {
        "brief_id": brief.get("id"),
        "platform": platform,
        "slide_count": len(slides),
        "viz_counts": viz,
        "gate_ok": gate.get("ok"),
        "gate_warnings": gate.get("warnings"),
        "captions": caption_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Slides pipeline eval")
    parser.add_argument("--platform", default="douyin", choices=("douyin", "xhs", "both"))
    parser.add_argument(
        "--mock",
        action="store_true",
        help="离线 mock 分镜（CI 默认，无需 LLM API）",
    )
    args = parser.parse_args()
    mock = args.mock or os.environ.get("EVAL_MOCK_COMPOSE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    platforms = ("douyin", "xhs") if args.platform == "both" else (args.platform,)
    results = []
    for brief in _load_fixtures():
        for plat in platforms:
            print(f"[eval] {brief.get('id')} / {plat} mock={mock}")
            results.append(_eval_brief(brief, platform=plat, mock=mock))

    out_dir = ROOT / "reports" / "slides_eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"eval_{ts}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [r for r in results if not r.get("gate_ok")]
    cap_issues = sum(
        len(c.get("issues_blocking") or _serious_caption_issues(c.get("issues") or []))
        for r in results
        for c in r.get("captions") or []
    )
    print(f"\nWrote {out_path}")
    print(f"cases={len(results)} gate_fail={len(failed)} caption_issues={cap_issues}")
    return 1 if failed or cap_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
