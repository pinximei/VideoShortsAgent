"""
统一能力注册表：聚合 Remotion 特效、转场、风格预设、平台默认值、场景。

中间层 LLM 生成文案/分镜时必须引用本目录中的合法取值；
VSA 渲染时通过 merge_render_effects() 还原完整 effects，不削减任何能力。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EFFECTS_JSON = _REPO_ROOT / "remotion_effects" / "effects_config.json"

# 平台视频默认（与 middle.pipeline.platform_presets 对齐，供无 LLM 字段时兜底）
PLATFORM_VIDEO_DEFAULTS: dict[str, dict[str, Any]] = {
    "douyin": {
        "width": 1080,
        "height": 1920,
        "max_seconds": 60.0,
        "voice": "zh-CN-YunxiNeural",
        "default_preset": "活力",
        "default_caption_style": "spring",
        "default_transition": "circleopen",
        "use_remotion": True,
    },
    "xhs": {
        "width": 1080,
        "height": 1920,
        "max_seconds": 60.0,
        "voice": "zh-CN-XiaoxiaoNeural",
        "default_preset": "情感",
        "default_caption_style": "fade",
        "default_transition": "dissolve",
        "use_remotion": True,
    },
}

VALID_CAPTION_STYLES = ("spring", "fade", "typewriter")
VALID_TRANSITIONS = (
    "fade", "circleopen", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideup", "slidedown", "slideleft", "slideright", "dissolve",
    "pixelize", "diagtl", "diagtr", "diagbl", "diagbr",
)
STYLE_PRESETS = ("科技", "情感", "叙事", "活力", "严肃")

# 默认 Remotion 字幕/渐变（需 remotion_effects 下 npm install）；yaml render.use_remotion: false 可退回 ASS
DEFAULT_USE_REMOTION = True


def resolve_caption_style(
    raw: str | None,
    *,
    preset_spec: dict[str, Any] | None = None,
    default: str = "spring",
) -> str:
    """将 LLM/平台误写的风格名（如「情感」）映射为 CaptionOverlay 合法值。"""
    s = (raw or "").strip()
    if s in VALID_CAPTION_STYLES:
        return s
    cat = effects_catalog()
    if s in STYLE_PRESETS:
        spec = (cat.get("presets") or {}).get(s) or {}
        cs = str(spec.get("caption_style") or "").strip()
        if cs in VALID_CAPTION_STYLES:
            return cs
    if preset_spec:
        cs = str(preset_spec.get("caption_style") or "").strip()
        if cs in VALID_CAPTION_STYLES:
            return cs
    return default if default in VALID_CAPTION_STYLES else "spring"


@lru_cache(maxsize=1)
def effects_catalog() -> dict[str, Any]:
    if not _EFFECTS_JSON.is_file():
        return {"caption_styles": {}, "transitions": {}, "presets": {}, "overlays": {}}
    return json.loads(_EFFECTS_JSON.read_text(encoding="utf-8"))


def platform_video_defaults(platform_id: str) -> dict[str, Any]:
    return dict(PLATFORM_VIDEO_DEFAULTS.get(platform_id, PLATFORM_VIDEO_DEFAULTS["douyin"]))


def llm_capabilities_section() -> str:
    """注入大模型 prompt 的能力说明（完整列举，不删减）。"""
    cat = effects_catalog()
    lines = [
        "## VSA 视频能力目录（clips / effects 只能使用下列合法值）",
        "",
        "### caption_style（字幕动画）",
    ]
    for k, desc in (cat.get("caption_styles") or {}).items():
        lines.append(f"- `{k}`: {desc}")
    lines.append("")
    lines.append("### transition_to_next（段间转场）")
    for k, desc in (cat.get("transitions") or {}).items():
        lines.append(f"- `{k}`: {desc}")
    lines.append("")
    lines.append("### style_preset（整片风格包，可选，写入 effects.preset）")
    for name, spec in (cat.get("presets") or {}).items():
        lines.append(f"- `{name}`: {json.dumps(spec, ensure_ascii=False)}")
    lines.append("")
    lines.append("### effects 对象（平台级，可选）")
    lines.append(
        '- `use_remotion`: 默认 true（Remotion 句级字幕 + 渐变，与 TTS 时间轴对齐）；false 仅调试时用 ASS\n'
        '- `gradient`: true/false 渐变氛围层\n'
        '- `gradient_colors`: ["#from", "#to"]\n'
        '- `transition_duration`: 0.3~0.8 秒\n'
        '- `preset`: 上表风格名之一'
    )
    lines.append("")
    lines.append("### 平台建议")
    for pid, d in PLATFORM_VIDEO_DEFAULTS.items():
        lines.append(
            f"- `{pid}`: 默认 preset={d['default_preset']}, "
            f"caption={d['default_caption_style']}, transition={d['default_transition']}"
        )
    return "\n".join(lines)


def merge_render_effects(
    platform_id: str,
    clips: list[dict[str, Any]],
    plan_effects: dict[str, Any] | None = None,
    *,
    use_remotion: bool | None = None,
) -> dict[str, Any]:
    """
    将 LLM 输出的 effects + 每段 clip 字段合并为 RenderSkill 所需 effects dict。
    保留 Remotion / 渐变 / 转场等全部能力。
    """
    cat = effects_catalog()
    defaults = platform_video_defaults(platform_id)
    pe = dict(plan_effects or {})
    preset_name = pe.get("preset") or defaults.get("default_preset")
    preset_spec = (cat.get("presets") or {}).get(preset_name) or {}
    # 以 render.use_remotion / 调用方为准；不采用 LLM 分镜里的 use_remotion: false
    remotion_on = DEFAULT_USE_REMOTION if use_remotion is None else bool(use_remotion)

    cap_default = defaults.get("default_caption_style") or "spring"
    try:
        from python_agent.platform_presets import get_platform_preset

        preset_td = float(get_platform_preset(platform_id).effects.get("transition_duration", 0.25))
    except Exception:
        preset_td = 0.25
    plan_td = pe.get("transition_duration")
    transition_duration = float(plan_td) if plan_td is not None else preset_td
    if transition_duration > preset_td + 0.08:
        transition_duration = preset_td

    effects: dict[str, Any] = {
        "use_remotion": remotion_on,
        "caption_style": resolve_caption_style(
            pe.get("caption_style"),
            preset_spec=preset_spec,
            default=cap_default,
        ),
        "transition": pe.get("transition") or preset_spec.get("transition") or defaults["default_transition"],
        "transition_duration": transition_duration,
        "gradient": bool(pe.get("gradient", preset_spec.get("gradient", False))),
        "gradient_colors": pe.get("gradient_colors") or preset_spec.get("gradient_colors"),
    }

    # 每段 clip 可覆盖 caption_style / transition_to_next（RenderSkill 已支持）
    for clip in clips:
        clip["caption_style"] = resolve_caption_style(
            clip.get("caption_style"),
            preset_spec=preset_spec,
            default=effects["caption_style"],
        )
        tr = clip.get("transition_to_next")
        if tr and tr not in VALID_TRANSITIONS:
            clip["transition_to_next"] = effects["transition"]

    return effects


def save_catalog_snapshot(output_dir: Path) -> Path:
    """任务目录保存能力目录快照，便于审计与重渲。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "catalog": effects_catalog(),
        "platform_defaults": PLATFORM_VIDEO_DEFAULTS,
        "valid_caption_styles": list(VALID_CAPTION_STYLES),
        "valid_transitions": list(VALID_TRANSITIONS),
    }
    path = output_dir / "llm" / "vsa_capabilities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
