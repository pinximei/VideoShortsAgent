"""DeepSeek / LLM 配置读写（.env + 连通性测试）。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import PipelineConfig, repo_root


def env_file_path() -> Path:
    return repo_root() / ".env"


def mask_api_key(key: str) -> str:
    k = (key or "").strip()
    if not k:
        return ""
    if len(k) <= 10:
        return "***"
    return f"{k[:6]}...{k[-4:]}"


def read_env_dict(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip()
    return out


def write_env_updates(updates: dict[str, str]) -> Path:
    """合并写入仓库根 .env，并同步当前进程环境变量。"""
    path = env_file_path()
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    remaining = {k: v for k, v in updates.items() if v is not None}
    new_lines: list[str] = []
    seen: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line if line.endswith("\n") else line + "\n")
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in remaining:
            new_lines.append(f"{key}={remaining.pop(key)}\n")
            seen.add(key)
        else:
            new_lines.append(line if line.endswith("\n") else line + "\n")

    if remaining:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append("\n# LLM (DeepSeek)\n")
        for key, value in remaining.items():
            new_lines.append(f"{key}={value}\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(new_lines), encoding="utf-8")

    for key, value in updates.items():
        if value is not None:
            os.environ[key] = value
    return path


def llm_settings_public(cfg: PipelineConfig) -> dict[str, Any]:
    key = (cfg.llm_api_key or os.getenv(cfg.llm_api_key_env) or os.getenv("DEEPSEEK_API_KEY") or "").strip()
    return {
        "enabled": cfg.llm_enabled,
        "api_key_env": cfg.llm_api_key_env,
        "api_key_set": bool(key),
        "api_key_masked": mask_api_key(key),
        "base_url": cfg.llm_base_url,
        "model": cfg.llm_model,
        "env_path": str(env_file_path()),
    }


def save_llm_settings(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    enabled: bool | None = None,
    config_yaml: Path | None = None,
) -> dict[str, Any]:
    updates: dict[str, str] = {}
    if api_key is not None and api_key.strip() and "..." not in api_key:
        updates["DEEPSEEK_API_KEY"] = api_key.strip()
    if base_url is not None and base_url.strip():
        updates["LLM_BASE_URL"] = base_url.strip().rstrip("/")
        if not updates["LLM_BASE_URL"].endswith("/v1"):
            updates["LLM_BASE_URL"] += "/v1"
    if model is not None and model.strip():
        updates["LLM_MODEL"] = model.strip()

    env_path = None
    if updates:
        env_path = str(write_env_updates(updates))

    if config_yaml and config_yaml.is_file() and enabled is not None:
        import yaml

        raw = yaml.safe_load(config_yaml.read_text(encoding="utf-8")) or {}
        llm = dict(raw.get("llm") or {})
        llm["enabled"] = bool(enabled)
        if model:
            llm["model"] = model.strip()
        if base_url:
            llm["base_url"] = updates.get("LLM_BASE_URL") or base_url.strip()
        raw["llm"] = llm
        config_yaml.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )

    return {"saved": True, "env_path": env_path, "updated_keys": list(updates.keys())}


def test_llm_connection(cfg: PipelineConfig) -> dict[str, Any]:
    from .llm_client import PipelineLLM

    llm = PipelineLLM(cfg)
    data = llm.chat_json(
        "你只返回 JSON。",
        '返回 {"ok": true, "provider": "deepseek"}',
    )
    return {
        "ok": bool(data.get("ok")),
        "model": cfg.llm_model,
        "base_url": cfg.llm_base_url,
        "sample": data,
    }
