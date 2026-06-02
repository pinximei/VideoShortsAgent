#!/usr/bin/env python3
"""抖音内容镜版式四轮审核（静态分镜 + 可选成片探针）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUDIT_PASSES = (
    (
        "版式架构师",
        "禁止右侧小方框装饰；内容镜统一 glass_card_stack",
        lambda slides: _check_no_right_decor(slides),
    ),
    (
        "字体导演",
        "大标题 + 至少 2 条副标题卡片；禁止 bullet_rail_right",
        lambda slides: _check_title_cards(slides),
    ),
    (
        "动效导演",
        "viz 不抢卡片布局；summary_lines 与 heading 分离",
        lambda slides: _check_motion_split(slides),
    ),
    (
        "QA",
        "口播无套话；起播单句",
        lambda slides: _check_tts_opening(slides),
    ),
)


def _content_slides(slides: list[dict]) -> list[dict]:
    return [
        s
        for s in slides
        if str(s.get("type") or "") == "content_card" or s.get("scene_focus")
    ]


def _check_no_right_decor(slides: list[dict]) -> list[str]:
    issues: list[str] = []
    line_decor = frozenset({"corner-brackets", "glass-card", "scan-lines"})
    content = _content_slides(slides)
    profiles = {str(s.get("motion_profile") or "") for s in content}
    for i, s in enumerate(slides):
        dec = set(s.get("css_decorations") or [])
        hits = dec & line_decor
        if len(hits) > 1:
            issues.append(f"slide_{i}:line_decor_clash={sorted(hits)}")
        if "corner-brackets" in dec and ("glass-card" in dec or "scan-lines" in dec):
            issues.append(f"slide_{i}:corner_with_mid_lines")
    for i, s in enumerate(content):
        if str(s.get("motion_profile") or "") == "bullet_rail_right":
            issues.append(f"slide_{i}:bullet_rail_right")
    if len(content) >= 2 and len(profiles) < 2:
        issues.append("content_profiles_not_diverse")
    return issues


def _check_title_cards(slides: list[dict]) -> list[str]:
    issues: list[str] = []
    for i, s in enumerate(_content_slides(slides)):
        head = str(s.get("feature_label") or s.get("heading") or "").strip()
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if not head:
            issues.append(f"slide_{i}:missing_heading")
        if len(lines) < 2:
            issues.append(f"slide_{i}:summary_lines<2")
        if head and lines and head.strip() == lines[0].strip():
            issues.append(f"slide_{i}:heading_equals_card1")
    return issues


def _check_motion_split(slides: list[dict]) -> list[str]:
    issues: list[str] = []
    allowed_layouts = frozenset({"keywords", "steps", "compare", "framed", "none"})
    for i, s in enumerate(_content_slides(slides)):
        vt = str(s.get("viz_type") or "none").lower()
        if vt not in ("none", "", "stat"):
            issues.append(f"slide_{i}:viz_type={vt}")
        layout = str(s.get("mid_info_layout") or "").lower()
        if layout and layout not in allowed_layouts:
            issues.append(f"slide_{i}:layout={layout}")
        head = str(s.get("feature_label") or s.get("heading") or "").strip()
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if head and lines and head == lines[0]:
            issues.append(f"slide_{i}:heading_equals_card1")
    return issues


def _check_tts_opening(slides: list[dict]) -> list[str]:
    issues: list[str] = []
    if not slides:
        return ["no_slides"]
    s0 = slides[0]
    if str(s0.get("type")) == "title_card":
        tts = str(s0.get("tts_text") or "")
        if tts.count("。") + tts.count("！") > 2:
            issues.append("title_tts_too_many_sentences")
    from python_agent.tts_copy_rules import validate_slides_tts_copy

    issues.extend(validate_slides_tts_copy(slides))
    return issues


def run_audit(task_dir: Path) -> dict:
    plan_path = task_dir / "llm" / "slides_render_plan_douyin.json"
    script_path = task_dir / "llm" / "slides_script.json"
    slides: list[dict] = []
    if plan_path.is_file():
        slides = json.loads(plan_path.read_text(encoding="utf-8-sig")).get("slides") or []
    elif script_path.is_file():
        slides = json.loads(script_path.read_text(encoding="utf-8-sig")).get("slides") or []

    rounds: list[dict] = []
    all_issues: list[str] = []
    for role, goal, fn in AUDIT_PASSES:
        issues = fn(slides)
        rounds.append({"role": role, "goal": goal, "ok": not issues, "issues": issues})
        all_issues.extend([f"{role}:{x}" for x in issues])

    return {
        "ok": not all_issues,
        "rounds": rounds,
        "issues": all_issues,
        "pass_count": sum(1 for r in rounds if r["ok"]),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir", nargs="?", default="")
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT))

    if args.task_dir:
        task_dir = Path(args.task_dir)
    else:
        reports = sorted((ROOT / "reports" / "platform_verify").glob("*/task"))
        if not reports:
            print("No task dir")
            return 1
        task_dir = reports[-1]

    result = run_audit(task_dir)
    out = task_dir.parent / "DOUYIN_LAYOUT_AUDIT.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in result["rounds"]:
        mark = "OK" if r["ok"] else "FAIL"
        print(f"[{mark}] {r['role']}: {r['goal']}")
        for x in r["issues"]:
            print(f"    - {x}")

    print(f"\nAudit: {result['pass_count']}/4 passes -> {out}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
