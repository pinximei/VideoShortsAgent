"""
抖音口播/文案风格目录：语速、句停顿、字数、钩子句式（20 套）。

catalog: templates/voice_content_20/catalog.json
与 motion_templates.github_daily_20 可组合使用。
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_CATALOG_PATH = _REPO / "templates" / "voice_content_20" / "catalog.json"


@lru_cache(maxsize=1)
def load_voice_catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"styles": []}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _seed_int(key: str) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def is_voice_style_brief(brief: dict[str, Any]) -> bool:
    fk = str(brief.get("feed_kind") or "").strip().lower()
    series = str(brief.get("series") or brief.get("series_tag") or "").lower()
    platform = str(brief.get("platform") or "").strip().lower()
    return (
        fk in ("github", "github_daily", "news")
        or "github" in series
        or "每天" in series
        or platform in ("douyin", "")
    )


def pick_voice_content_style(brief: dict[str, Any]) -> dict[str, Any]:
    styles = list(load_voice_catalog().get("styles") or [])
    if not styles:
        return _fallback_style()
    seed = str(
        brief.get("content_key")
        or brief.get("article_id")
        or brief.get("title")
        or "voice_default"
    )
    motion_id = str(brief.get("github_daily_style_id") or brief.get("motion_style_id") or "")
    if motion_id:
        for s in styles:
            if s.get("reference_motion") and motion_id.startswith(str(s["reference_motion"])):
                return dict(s)
    idx = _seed_int(f"voice_content:{seed}") % len(styles)
    return dict(styles[idx])


def _fallback_style() -> dict[str, Any]:
    return {
        "id": "V01_burst_hook_fast",
        "edge_tts_rate": "+12%",
        "sentence_pause_sec": 0.2,
        "words_per_minute": 240,
        "total_chars": [180, 260],
        "hook_pattern": "别划走",
        "tone": "口语快节奏",
    }


def voice_style_prompt_block(style: dict[str, Any]) -> str:
    """供 ComposeSkill / platform_llm 注入的口播约束。"""
    tc = style.get("total_chars") or [180, 260]
    slide = style.get("slide_chars") or {}
    sc_lines = []
    for st, rng in slide.items():
        if isinstance(rng, list) and len(rng) >= 2:
            sc_lines.append(f"  - {st}: {rng[0]}~{rng[1]} 字")
    slide_block = "\n".join(sc_lines) if sc_lines else "  - 每镜 30~65 字"
    return f"""
【口播风格模板 {style.get('id', '')} — {style.get('name', '')}】
- 语气：{style.get('tone', '口语化')}
- 钩子句式参考：{style.get('hook_pattern', '悬念/反差')}
- 全片总字数：{tc[0]}~{tc[1]} 字（60秒内）
- 目标语速：约 {style.get('words_per_minute', 230)} 字/分钟
- 每镜字数：
{slide_block}
- 禁止开场：「大家好」「今天给大家介绍」
- 第1镜前2句必须含钩子（疑问/数字/利益）
- 句长：口语短句，单句尽量 ≤18 字；多用「你」「这个」「真的」
""".strip()


def apply_voice_style_to_brief(
    brief: dict[str, Any],
    style: dict[str, Any],
    *,
    platform_voice: str = "zh-CN-YunxiNeural",
) -> dict[str, Any]:
    from python_agent.tts_params import resolve_tts_params

    out = dict(brief)
    out["voice_content_style_id"] = style.get("id")
    out["voice_content_style"] = style
    tts = resolve_tts_params(style, platform_voice=platform_voice)
    out["tts_voice"] = tts["tts_voice"]
    out["tts_rate"] = tts["tts_rate"]
    out["tts_pitch"] = tts["tts_pitch"]
    out["sentence_pause_sec"] = tts["sentence_pause_sec"]
    return out


def save_voice_style(task_dir: Path, style: dict[str, Any], *, analysis: dict | None = None) -> Path:
    path = Path(task_dir) / "llm" / "voice_content_style.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "style": style}
    if analysis:
        payload["reference_analysis"] = analysis
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def clamp_tts_text_for_style(text: str, style: dict[str, Any], slide_type: str = "content_card") -> str:
    slide_chars = style.get("slide_chars") or {}
    rng = slide_chars.get(slide_type) or style.get("total_chars") or [30, 70]
    max_c = int(rng[1]) if isinstance(rng, list) and len(rng) > 1 else 70
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= max_c:
        return t
    cut = t[: max_c - 1].rstrip("，,。 ")
    return cut + "。"
