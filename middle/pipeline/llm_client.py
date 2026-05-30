"""Pipeline LLM 客户端（OpenAI 兼容，默认 DeepSeek）。"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

from .config import PipelineConfig


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    for candidate in (text, re.sub(r"```(?:json)?\s*", "", text).strip()):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        obj = json.loads(match.group())
        if isinstance(obj, dict):
            return obj
    raise ValueError(f"LLM 返回非 JSON: {text[:240]}")


class PipelineLLM:
    def __init__(self, cfg: PipelineConfig):
        if not cfg.llm_enabled:
            raise RuntimeError("llm.enabled=false")
        key = (cfg.llm_api_key or os.getenv(cfg.llm_api_key_env) or "").strip()
        if not key:
            raise RuntimeError(f"未配置 LLM API Key（环境变量 {cfg.llm_api_key_env}）")
        self._client = OpenAI(api_key=key, base_url=cfg.llm_base_url, timeout=120.0)
        self._model = cfg.llm_model

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        return _extract_json_object(content)
