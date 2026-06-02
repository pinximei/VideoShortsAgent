#!/usr/bin/env python3
"""
十角色 × 十轮：每轮独立提示 → 检查 → 修改分镜 → 记录意见。

  py -3.12 scripts/douyin_ten_round_loop.py
  py -3.12 scripts/douyin_ten_round_loop.py --render
  py -3.12 scripts/douyin_ten_round_loop.py --task-dir reports/.../task
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_slides(task_dir: Path | None) -> list[dict]:
    sys.path.insert(0, str(ROOT))
    if task_dir:
        for name in ("slides_render_plan_douyin.json", "slides_script.json"):
            p = task_dir / "llm" / name
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8-sig")).get("slides") or []

    from python_agent.eval_mock_compose import mock_compose_from_brief

    brief = {"platform": "douyin", "feed_kind": "github_daily"}
    return mock_compose_from_brief(brief).get("slides") or []


def _run(cmd: list[str], *, timeout: int = 3600) -> int:
    r = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if r.stdout:
        print(r.stdout[-5000:])
    if r.stderr:
        print(r.stderr[-2000:], file=sys.stderr)
    return r.returncode


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--task-dir", default="", help="已有 task 目录则基于其 plan 迭代")
    ap.add_argument("--render", action="store_true", help="十轮结束后渲染 douyin 成片")
    ap.add_argument("--rounds", type=int, default=10, help="最少 10 轮（默认跑满十角色）")
    ap.add_argument(
        "--write-task-plan",
        action="store_true",
        help="将终稿写入 --task-dir/llm/slides_render_plan_douyin.json",
    )
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from python_agent.douyin_ten_agent_rounds import AGENT_ROUNDS, run_ten_rounds

    task_dir = Path(args.task_dir) if args.task_dir else None
    slides = _load_slides(task_dir)
    if not slides:
        print("No slides to review")
        return 1

    n_rounds = max(10, int(args.rounds))
    specs = list(AGENT_ROUNDS)
    if n_rounds > len(specs):
        specs = specs + specs * ((n_rounds // len(specs)) + 1)
    specs = specs[:n_rounds]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "reports" / "douyin_ten_round" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    current = slides
    rounds_log: list[dict] = []

    for spec in specs:
        from python_agent.douyin_ten_agent_rounds import run_ten_rounds as _run_one

        # 单轮：只跑该角色
        single = [x for x in AGENT_ROUNDS if x["round"] == spec["round"]]
        if not single:
            continue
        one_spec = single[0]
        issues = one_spec["check"](current)
        fixed, applied = one_spec["fix"](current, issues)
        current = fixed
        row = {
            "round": one_spec["round"],
            "role": one_spec["role"],
            "layout_tier": one_spec["layout_tier"],
            "prompt": one_spec["prompt"],
            "issues_before": issues,
            "fixes_applied": applied,
            "issues_after": one_spec["check"](current),
            "ok_after": not one_spec["check"](current),
        }
        rounds_log.append(row)
        mark = "OK" if row["ok_after"] else "FIXED"
        print(f"\n[Round {row['round']}/10] {row['role']} ({row['layout_tier']}) — {mark}")
        print(f"  提示: {row['prompt']}")
        if issues:
            print(f"  意见: {issues[:6]}")
        if applied:
            print(f"  修改: {applied[:6]}")

    from python_agent.douyin_layout_registry import layout_assignment_table

    final_report = {
        "generated_at": stamp,
        "rounds_requested": n_rounds,
        "rounds_executed": len(rounds_log),
        "ok": all(r.get("ok_after") for r in rounds_log),
        "rounds": rounds_log,
        "layout_assignments": layout_assignment_table(current),
        "layout_catalog": [
            {"id": x["id"], "name": x["name"]}
            for x in __import__(
                "python_agent.douyin_layout_registry", fromlist=["DOUYIN_CONTENT_LAYOUTS"]
            ).DOUYIN_CONTENT_LAYOUTS
        ],
    }

    plan_path = out_dir / "slides_after_ten_rounds.json"
    plan_path.write_text(
        json.dumps({"slides": current}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path = out_dir / "TEN_ROUND_AGENT_REPORT.json"
    report_path.write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n--- 排型分配表 ({len(final_report['layout_assignments'])} 镜) ---")
    for row in final_report["layout_assignments"]:
        print(
            f"  slide {row['slide']}: {row.get('layout_id')} / {row.get('name')} "
            f"profile={row.get('motion_profile', '-')}"
        )
    print(f"\n报告: {report_path}")
    print(f"终稿分镜: {plan_path}")

    if args.write_task_plan and task_dir:
        task_dir = task_dir.resolve()
        llm = task_dir / "llm"
        llm.mkdir(parents=True, exist_ok=True)
        dest = llm / "slides_render_plan_douyin.json"
        dest.write_text(
            json.dumps({"slides": current, "platform": "douyin"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"已写入 task plan: {dest}")

    rc = _run([sys.executable, "-m", "pytest", "python_agent/tests/test_douyin_ten_rounds.py", "-q"], timeout=120)
    if rc != 0:
        return rc

    if args.render:
        if task_dir:
            rc = _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "full_task_qa.py"),
                    str(task_dir.resolve()),
                ],
                timeout=3600,
            )
        else:
            rc = _run(
                [sys.executable, str(ROOT / "scripts" / "render_platform_verify.py"), "--douyin-only"],
                timeout=2400,
            )
        if rc != 0:
            return rc

    return 0 if final_report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
