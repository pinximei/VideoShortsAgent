"""强制 LLM 润色：禁止中间层直接使用 Soul 原文或模板回退。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .pipeline_gates import PipelineGateError


def _fail(code: str, message: str) -> None:
    raise PipelineGateError(code, message)


def llm_polish_required(cfg: PipelineConfig) -> bool:
    return bool(cfg.llm_enabled and cfg.llm_require_polish)


def load_platform_copy(task_dir: Path) -> dict[str, Any]:
    path = task_dir / "llm" / "platform_copy.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def assert_llm_polished(task_dir: Path, cfg: PipelineConfig, *, strict: bool | None = None) -> None:
    """发布/渲染前：必须有 pipeline_llm 产物，且 platform_copy 非空。"""
    if not llm_polish_required(cfg):
        return
    task_dir = task_dir.resolve()
    meta_path = task_dir / "publish_meta.json"
    if not meta_path.is_file():
        _fail("llm_polish_missing", "缺少 publish_meta.json，须先跑 LLM 润色")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        _fail("llm_polish_invalid", f"publish_meta 无法解析: {e}")
    source = str(meta.get("source") or "")
    if source != "pipeline_llm":
        _fail("llm_polish_required", f"禁止非 LLM 文案进生产（source={source or 'empty'}）")
    if meta.get("llm_error"):
        _fail("llm_polish_failed", str(meta["llm_error"])[:300])

    copy = load_platform_copy(task_dir)
    if not copy:
        _fail("llm_polish_missing", "缺少 llm/platform_copy.json")

    dy = copy.get("douyin") or {}
    if not str(dy.get("script") or "").strip():
        _fail("llm_polish_incomplete", "douyin.script 为空，须 LLM 生成口播")
    if not str(dy.get("title") or "").strip():
        _fail("llm_polish_incomplete", "douyin.title 为空")

    for plat in ("toutiao", "douban"):
        block = copy.get(plat) or {}
        if not str(block.get("body") or "").strip():
            _fail("llm_polish_incomplete", f"{plat}.body 为空，须 LLM 润色")


def ensure_compose_uses_llm_copy(task_dir: Path, cfg: PipelineConfig) -> None:
    """若 platform_copy 比 slides_script 新，删除旧分镜以强制 Compose 重跑。"""
    if not llm_polish_required(cfg):
        return
    assert_llm_polished(task_dir, cfg)
    copy_path = task_dir / "llm" / "platform_copy.json"
    script_path = task_dir / "llm" / "slides_script.json"
    if not script_path.is_file():
        return
    if copy_path.stat().st_mtime > script_path.stat().st_mtime + 0.5:
        script_path.unlink(missing_ok=True)
        for p in task_dir.glob("slides_render_plan_*.json"):
            p.unlink(missing_ok=True)
