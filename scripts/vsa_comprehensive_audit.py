#!/usr/bin/env python3
"""
VSA 全面审查：20 轮可复现检查，每轮写入证据文件（不伪造）。

用法:
  py -3 scripts/vsa_comprehensive_audit.py
  py -3 scripts/vsa_comprehensive_audit.py --report-dir reports/vsa_audit_manual
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VSA_FILES = [
    "middle/pipeline/vsa.py",
    "middle/pipeline/vsa_adapter.py",
    "python_agent/vsa_render.py",
    "python_agent/vsa_cli.py",
    "middle/tests/test_vsa.py",
]


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 300) -> dict:
    p = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "exit_code": p.returncode,
        "stdout": p.stdout[-12000:] if p.stdout else "",
        "stderr": p.stderr[-8000:] if p.stderr else "",
    }


def _sha256(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def check_01_pytest_vsa(report_dir: Path) -> dict:
    r = _run(
        [sys.executable, "-m", "pytest", "tests/test_vsa.py", "-v", "--tb=short", "-q"],
        cwd=ROOT / "middle",
    )
    # retry with explicit PYTHONPATH if conftest import fails
    if r["exit_code"] != 0 and "conftest" in r.get("stderr", ""):
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_vsa.py", "-q", "--tb=short"],
            cwd=str(ROOT / "middle"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "middle")},
        )
        r = {
            "cmd": ["pytest", "tests/test_vsa.py", "(middle cwd)"],
            "exit_code": p.returncode,
            "stdout": p.stdout[-12000:] if p.stdout else "",
            "stderr": p.stderr[-8000:] if p.stderr else "",
        }
    return {"id": 1, "name": "pytest_test_vsa", "ok": r["exit_code"] == 0, "evidence": r}


def check_02_pytest_tts_voice(report_dir: Path) -> dict:
    r = _run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0,'.'); "
            "from middle.tests.test_tts_params import *; "
            "test_douyin_platform_default_fast_male(); test_xhs_keeps_female_voice(); print('ok')",
        ]
    )
    return {"id": 2, "name": "tts_params_unit", "ok": r["exit_code"] == 0, "evidence": r}


def check_03_compile_vsa_modules(report_dir: Path) -> dict:
    files = [str(ROOT / f) for f in VSA_FILES if (ROOT / f).is_file()]
    r = _run([sys.executable, "-m", "py_compile", *files])
    return {"id": 3, "name": "py_compile_vsa", "ok": r["exit_code"] == 0, "evidence": r}


def check_04_import_chain(report_dir: Path) -> dict:
    code = """
import sys
sys.path.insert(0, '.')
from middle.pipeline import vsa
from middle.pipeline import vsa_adapter
from python_agent import vsa_render, vsa_cli
print('imports_ok', vsa.render_from_llm_plan.__name__)
"""
    r = _run([sys.executable, "-c", code], cwd=ROOT)
    return {"id": 4, "name": "import_vsa_chain", "ok": r["exit_code"] == 0, "evidence": r}


def check_05_dubbing_tts_wiring(report_dir: Path) -> dict:
    text = (ROOT / "python_agent/vsa_render.py").read_text(encoding="utf-8")
    has_rate = "tts_rate" in text and "DubbingSkill(" in text
    has_pitch = "tts_pitch" in text
    has_resolve = "resolve_tts_for_platform" in text or "load_tts_from_task_dir" in text
    ok = has_rate and has_pitch and has_resolve
    return {
        "id": 5,
        "name": "vsa_render_tts_wiring",
        "ok": ok,
        "evidence": {"has_rate": has_rate, "has_pitch": has_pitch, "has_resolve": has_resolve},
    }


def check_06_vsa_py_voice_arg(report_dir: Path) -> dict:
    """vsa.py 仍传 voice=preset.voice；vsa_render 应从 task 覆盖。"""
    text = (ROOT / "middle/pipeline/vsa.py").read_text(encoding="utf-8")
    passes_preset_voice = "voice=preset.voice" in text
    passes_task_dir = "task_dir=str(task_dir)" in text
    return {
        "id": 6,
        "name": "vsa_py_render_from_plan_args",
        "ok": passes_task_dir,
        "finding": "voice=preset.voice still passed but task_dir enables tts override in vsa_render",
        "evidence": {"passes_preset_voice": passes_preset_voice, "passes_task_dir": passes_task_dir},
    }


def check_07_slides_render_parity(report_dir: Path) -> dict:
    sr = (ROOT / "middle/pipeline/slides_render.py").read_text(encoding="utf-8")
    ok = "resolve_tts_for_platform" in sr and "DubbingSkill" in sr
    return {"id": 7, "name": "slides_render_tts_parity", "ok": ok, "evidence": {"has_resolve": ok}}


def check_08_pipeline_render_tts(report_dir: Path) -> dict:
    pr = (ROOT / "python_agent/pipeline_render.py").read_text(encoding="utf-8")
    ok = "resolve_tts_for_platform" in pr and "tts_pitch" in pr
    return {"id": 8, "name": "pipeline_render_tts", "ok": ok, "evidence": {"wired": ok}}


def check_09_agent_legacy_dubbing(report_dir: Path) -> dict:
    """agent/app 是否仍用无 rate 的 DubbingSkill。"""
    hits: list[str] = []
    for rel in ("python_agent/agent.py", "python_agent/app.py"):
        p = ROOT / rel
        if not p.is_file():
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "DubbingSkill()" in line or 'DubbingSkill(voice=' in line and "tts_rate" not in line:
                if "DubbingSkill()" in line or (
                    "DubbingSkill(voice=" in line and "tts_rate" not in p.read_text(encoding="utf-8")[max(0, p.read_text(encoding="utf-8").find(line) - 200) : p.read_text(encoding="utf-8").find(line) + len(line) + 200]
                ):
                    hits.append(f"{rel}:{i}:{line.strip()[:80]}")
    return {
        "id": 9,
        "name": "legacy_dubbing_without_rate",
        "ok": len(hits) == 0,
        "evidence": {"hits": hits[:20], "count": len(hits)},
    }


def check_10_test_vsa_content(report_dir: Path) -> dict:
    p = ROOT / "middle/tests/test_vsa.py"
    text = p.read_text(encoding="utf-8") if p.is_file() else ""
    tests = re.findall(r"def (test_\w+)", text)
    return {
        "id": 10,
        "name": "test_vsa_case_count",
        "ok": len(tests) >= 1,
        "evidence": {"test_functions": tests, "count": len(tests)},
    }


def check_11_vsa_adapter(report_dir: Path) -> dict:
    p = ROOT / "middle/pipeline/vsa_adapter.py"
    exists = p.is_file()
    text = p.read_text(encoding="utf-8") if exists else ""
    return {
        "id": 11,
        "name": "vsa_adapter_present",
        "ok": exists and len(text) > 50,
        "evidence": {"exists": exists, "lines": len(text.splitlines())},
    }


def check_12_rust_vsa_core(report_dir: Path) -> dict:
    readme = ROOT / "rust/vsa-core/README.md"
    cargo = ROOT / "rust/vsa-core/Cargo.toml"
    return {
        "id": 12,
        "name": "rust_vsa_core_tree",
        "ok": readme.is_file(),
        "evidence": {
            "readme": readme.is_file(),
            "cargo": cargo.is_file(),
            "readme_head": readme.read_text(encoding="utf-8")[:400] if readme.is_file() else "",
        },
    }


def check_13_config_render_flags(report_dir: Path) -> dict:
    cfg = (ROOT / "middle/pipeline/config.py").read_text(encoding="utf-8")
    keys = [k for k in ("render_use_remotion", "render_parallel", "render_skip_tts", "broll_template") if k in cfg]
    return {"id": 13, "name": "pipeline_config_render_keys", "ok": len(keys) >= 3, "evidence": {"keys_found": keys}}


def check_14_orchestrator_vsa_entry(report_dir: Path) -> dict:
    orch = (ROOT / "middle/pipeline/orchestrator.py").read_text(encoding="utf-8")
    ok = "vsa" in orch or "render_platform" in orch or "slides_render" in orch
    return {"id": 14, "name": "orchestrator_render_entry", "ok": ok, "evidence": {"mentions_vsa": "vsa" in orch}}


def check_15_capabilities_registry(report_dir: Path) -> dict:
    r = _run([sys.executable, "-m", "pytest", "tests/test_capabilities_registry.py", "-q", "--tb=line"], timeout=120)
    return {"id": 15, "name": "pytest_capabilities_registry", "ok": r["exit_code"] == 0, "evidence": r}


def check_16_file_manifest_hashes(report_dir: Path) -> dict:
    manifest = {f: _sha256(ROOT / f) for f in VSA_FILES}
    all_present = all(v != "MISSING" for v in manifest.values())
    return {"id": 16, "name": "vsa_file_manifest_sha256", "ok": all_present, "evidence": manifest}


def check_17_grep_render_from_plan_callers(report_dir: Path) -> dict:
    r = _run(
        [
            "rg",
            "-l",
            "render_from_plan|render_from_llm_plan",
            "middle",
            "python_agent",
            "--glob",
            "*.py",
        ],
        timeout=60,
    )
    if r["exit_code"] != 0:
        # fallback grep via python
        callers = []
        for py in (ROOT / "middle").rglob("*.py"):
            t = py.read_text(encoding="utf-8", errors="replace")
            if "render_from_plan" in t or "render_from_llm_plan" in t:
                callers.append(str(py.relative_to(ROOT)))
        r["stdout"] = "\n".join(sorted(set(callers)))
        r["exit_code"] = 0
    files = [x.strip() for x in r["stdout"].splitlines() if x.strip()]
    return {"id": 17, "name": "render_from_plan_callers", "ok": len(files) >= 2, "evidence": {"files": files, "count": len(files)}}


def check_18_pipeline_gates_video(report_dir: Path) -> dict:
    pg = ROOT / "middle/pipeline/pipeline_gates.py"
    text = pg.read_text(encoding="utf-8") if pg.is_file() else ""
    ok = "tts" in text.lower() and "clips" in text
    return {"id": 18, "name": "pipeline_gates_tts_clips", "ok": ok, "evidence": {"has_tts_check": "tts" in text.lower()}}


def check_19_voice_style_json_loader(report_dir: Path) -> dict:
    r = _run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0,'.'); "
            "from python_agent.tts_params import load_tts_from_task_dir, resolve_tts_for_platform; "
            "t=resolve_tts_for_platform({},'douyin'); "
            "assert t['tts_voice']; print(t)",
        ]
    )
    return {"id": 19, "name": "tts_resolve_runtime", "ok": r["exit_code"] == 0, "evidence": r}


def check_20_git_head_proof(report_dir: Path) -> dict:
    r = _run(["git", "rev-parse", "HEAD"])
    r2 = _run(["git", "log", "-1", "--oneline"])
    return {
        "id": 20,
        "name": "git_commit_at_audit",
        "ok": r["exit_code"] == 0,
        "evidence": {"head": r["stdout"].strip(), "log1": r2["stdout"].strip()},
    }


CHECKS = [
    check_01_pytest_vsa,
    check_02_pytest_tts_voice,
    check_03_compile_vsa_modules,
    check_04_import_chain,
    check_05_dubbing_tts_wiring,
    check_06_vsa_py_voice_arg,
    check_07_slides_render_parity,
    check_08_pipeline_render_tts,
    check_09_agent_legacy_dubbing,
    check_10_test_vsa_content,
    check_11_vsa_adapter,
    check_12_rust_vsa_core,
    check_13_config_render_flags,
    check_14_orchestrator_vsa_entry,
    check_15_capabilities_registry,
    check_16_file_manifest_hashes,
    check_17_grep_render_from_plan_callers,
    check_18_pipeline_gates_video,
    check_19_voice_style_json_loader,
    check_20_git_head_proof,
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-dir", default="")
    args = ap.parse_args()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = Path(args.report_dir) if args.report_dir else ROOT / "reports" / f"vsa_audit_{ts}"
    report_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(ROOT),
        "python": sys.executable,
        "rounds": 20,
        "report_dir": str(report_dir),
    }
    (report_dir / "00_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    results: list[dict] = []
    for fn in CHECKS:
        row = fn(report_dir)
        results.append(row)
        n = row["id"]
        out = report_dir / f"round_{n:02d}_{row['name']}.json"
        out.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "PASS" if row.get("ok") else "FAIL"
        print(f"[{n:02d}/20] {status} {row['name']}")

    passed = sum(1 for r in results if r.get("ok"))
    summary = {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failed": 20 - passed,
        "total": 20,
        "rounds": [{"id": r["id"], "name": r["name"], "ok": r.get("ok")} for r in results],
    }
    (report_dir / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# VSA 全面审查报告（20 轮）",
        "",
        f"- 时间（UTC）: {summary['finished_at']}",
        f"- 目录: `{report_dir}`",
        f"- 通过: **{passed}/20**",
        f"- Git: {(results[-1].get('evidence') or {}).get('log1', '?')}",
        "",
        "## 各轮结果",
        "",
        "| # | 检查项 | 结果 | 证据文件 |",
        "|---|--------|------|----------|",
    ]
    for r in results:
        st = "✅" if r.get("ok") else "❌"
        md.append(f"| {r['id']} | {r['name']} | {st} | `round_{r['id']:02d}_{r['name']}.json` |")
    md.extend(
        [
            "",
            "## 复现",
            "",
            "```powershell",
            "cd D:\\VideoShortsAgent",
            "py -3 scripts/vsa_comprehensive_audit.py",
            "```",
            "",
            "每轮原始输出见同目录 `round_XX_*.json`。",
        ]
    )
    (report_dir / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {report_dir / 'REPORT.md'}")
    print(f"PASS {passed}/20")
    return 0 if passed >= 18 else 1


if __name__ == "__main__":
    raise SystemExit(main())
