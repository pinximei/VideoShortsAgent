"""
统一能力注册表：聚合 Remotion 特效、转场、风格预设、平台默认值。

中间层 LLM 生成文案/分镜时必须引用本目录中的合法取值；
VSA 渲染时通过 merge_render_effects() 还原完整 effects。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EFFECTS_JSON = _REPO_ROOT / "remotion_effects" / "effects_config.json"

PLATFORM_VIDEO_DEFAULTS: dict[str, dict[str, Any]] = {
    "douyin": {
        "width": 1080,
        "height": 1920,
        "max_seconds": 45.0,
        "voice": "zh-CN-YunxiNeural",
        "default_preset": "活力",
        "default_caption_style": "spring",
        "default_transition": "slideup",
        "use_remotion": True,
    },
    "xhs": {
        "width": 1080,
        "height": 1920,
        "max_seconds": 55.0,
        "voice": "zh-CN-XiaoxiaoNeural",
        "default_preset": "情感",
        "default_caption_style": "fade",
        "default_transition": "dissolve",
        "use_remotion": True,
    },
}

VALID_CAPTION_STYLES = ("spring", "fade", "typewriter")
STYLE_PRESETS = ("科技", "情感", "叙事", "活力", "严肃")
DEFAULT_USE_REMOTION = True

# FFmpeg xfade 与 effects_config 对齐（单一来源：catalog transitions 键）
_FALLBACK_TRANSITIONS = (
    "fade", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideup", "slidedown", "slideleft", "slideright",
    "circleopen", "circleclose", "pixelize",
    "diagtl", "diagtr", "diagbl", "diagbr",
    "smoothleft", "smoothright", "smoothup", "smoothdown",
    "horzopen", "horzclose", "vertopen", "vertclose",
)

EFFECT_SELECTION_RULES = """
### 特效选型规则（必须遵守）
1. **必须**为每个视频平台填写 `effects.preset`（科技/情感/叙事/活力/严肃之一），不要只写零散字段。
2. **feed_kind=news**（资讯）：优先 preset=严肃 或 叙事；`gradient` 必须为 false；字幕由系统走 FFmpeg ASS 快路径（勿依赖 Remotion 动画）；末段 `transition_to_next` 用 fade。
3. **feed_kind=apps**（应用/变现）：优先 preset=科技 或 活力；钩子段 `caption_style=spring`，`transition_to_next=circleopen` 或 slideup。
4. **段角色**：第 1 段=钩子（可 spring/circleopen）；中间段=正文（wipe/slide/dissolve）；**最后一段** `transition_to_next` 必须为 fade 或 dissolve。
5. **禁止**使用目录外的转场名；禁止 pixelize/diag* 连续出现超过 1 次。
6. `gradient` 默认 false（加速渲染）；仅情感向、小红书氛围稿可设 true，并配 `gradient_colors`。
7. 可选 `intro_card` / `outro_card`（bool）：抖音/活力 preset 可 intro=true；结尾 CTA 可 outro=true。
""".strip()


@lru_cache(maxsize=1)
def effects_catalog() -> dict[str, Any]:
    if not _EFFECTS_JSON.is_file():
        return {"caption_styles": {}, "transitions": {}, "presets": {}, "overlays": {}}
    return json.loads(_EFFECTS_JSON.read_text(encoding="utf-8"))


def valid_transitions() -> tuple[str, ...]:
    cat = effects_catalog()
    keys = tuple((cat.get("transitions") or {}).keys())
    return keys if keys else _FALLBACK_TRANSITIONS


# 模块加载后固定，供 render_skill 等 import
VALID_TRANSITIONS = valid_transitions()


def resolve_transition(raw: str | None, *, default: str = "fade") -> str:
    t = (raw or "").strip()
    if t in VALID_TRANSITIONS:
        return t
    return default if default in VALID_TRANSITIONS else "fade"


def resolve_caption_style(
    raw: str | None,
    *,
    preset_spec: dict[str, Any] | None = None,
    default: str = "spring",
) -> str:
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


def suggest_preset_for_feed(feed_kind: str) -> str:
    fk = (feed_kind or "news").strip().lower()
    hints = (effects_catalog().get("feed_kind_hints") or {}).get(fk) or {}
    p = str(hints.get("preset") or "").strip()
    return p if p in STYLE_PRESETS else ("严肃" if fk == "news" else "科技")


def platform_video_defaults(platform_id: str) -> dict[str, Any]:
    return dict(PLATFORM_VIDEO_DEFAULTS.get(platform_id, PLATFORM_VIDEO_DEFAULTS["douyin"]))


def llm_capabilities_section(*, feed_kind: str = "news") -> str:
    cat = effects_catalog()
    fk = (feed_kind or "news").strip().lower()
    hint = (cat.get("feed_kind_hints") or {}).get(fk) or {}
    lines = [
        "## VSA 视频能力目录（clips / effects 只能使用下列合法值）",
        "",
        f"**当前 feed_kind={fk}**：建议 preset=`{suggest_preset_for_feed(fk)}`。"
        + (f" {hint.get('note')}" if hint.get("note") else ""),
        "",
        "### caption_style（字幕动画）",
    ]
    for k, desc in (cat.get("caption_styles") or {}).items():
        lines.append(f"- `{k}`: {desc}")
    lines.append("")
    lines.append("### transition_to_next（段间转场，完整列表）")
    for k, desc in (cat.get("transitions") or {}).items():
        lines.append(f"- `{k}`: {desc}")
    lines.append("")
    lines.append("### style_preset（必填，写入 effects.preset）")
    for name, spec in (cat.get("presets") or {}).items():
        lines.append(f"- `{name}`: {json.dumps(spec, ensure_ascii=False)}")
    lines.append("")
    lines.append("### effects 对象（平台级）")
    lines.append(
        "- `preset`: **必填**，上表风格名之一\n"
        "- `use_remotion`: 由系统配置，LLM 可省略\n"
        "- `gradient`: 默认 false\n"
        "- `gradient_colors`: [\"#from\", \"#to\"]\n"
        "- `transition_duration`: 0.2~0.3\n"
        "- `intro_card` / `outro_card`: 是否加片头 TitleCard / 片尾 CTACard（bool）"
    )
    lines.append("")
    lines.append("### Remotion 卡片（片头/片尾，由 intro_card/outro_card 触发）")
    lines.append("- TitleCard: 片头标题（heading=首段 hook_text）")
    lines.append("- CTACard: 片尾行动号召（ctaText=末段 hook_text 或 CTA）")
    lines.append("")
    lines.append("### 平台建议")
    for pid, d in PLATFORM_VIDEO_DEFAULTS.items():
        lines.append(
            f"- `{pid}`: 默认 preset={d['default_preset']}, "
            f"caption={d['default_caption_style']}, transition={d['default_transition']}"
        )
    lines.append("")
    lines.append(EFFECT_SELECTION_RULES)
    return "\n".join(lines)


def _normalize_clip_transitions(clips: list[dict[str, Any]], default_tr: str) -> None:
    n = len(clips)
    for i, clip in enumerate(clips):
        if not isinstance(clip, dict):
            continue
        if i == n - 1:
            clip["transition_to_next"] = "fade"
        else:
            clip["transition_to_next"] = resolve_transition(
                clip.get("transition_to_next"),
                default=default_tr,
            )


def _apply_bookends_policy(
    effects: dict[str, Any],
    platform_id: str,
    *,
    bookends: str = "douyin",
) -> None:
    """bookends: douyin | both | none — 控制片头片尾 Remotion 卡片。"""
    mode = (bookends or "douyin").strip().lower()
    if mode == "none":
        effects["intro_card"] = False
        effects["outro_card"] = False
    elif mode == "douyin":
        if platform_id != "douyin":
            effects["intro_card"] = False
            effects["outro_card"] = False
    # both: 保留 merge 结果


def merge_render_effects(
    platform_id: str,
    clips: list[dict[str, Any]],
    plan_effects: dict[str, Any] | None = None,
    *,
    use_remotion: bool | None = None,
    feed_kind: str = "news",
    bookends: str = "douyin",
) -> dict[str, Any]:
    cat = effects_catalog()
    defaults = platform_video_defaults(platform_id)
    pe = dict(plan_effects or {})

    preset_name = str(pe.get("preset") or "").strip()
    if preset_name not in STYLE_PRESETS:
        preset_name = suggest_preset_for_feed(feed_kind) or defaults.get("default_preset") or "活力"
    preset_spec = dict((cat.get("presets") or {}).get(preset_name) or {})

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

    default_tr = resolve_transition(
        pe.get("transition") or preset_spec.get("transition") or defaults["default_transition"],
        default="fade",
    )

    gradient = pe.get("gradient")
    if gradient is None:
        gradient = bool(preset_spec.get("gradient", False))
    else:
        gradient = bool(gradient)
    fk = (feed_kind or "news").strip().lower()
    if fk == "news":
        gradient = False
        remotion_on = False

    effects: dict[str, Any] = {
        "use_remotion": remotion_on,
        "preset": preset_name,
        "caption_style": resolve_caption_style(
            pe.get("caption_style"),
            preset_spec=preset_spec,
            default=cap_default,
        ),
        "transition": default_tr,
        "transition_duration": transition_duration,
        "gradient": gradient,
        "gradient_colors": pe.get("gradient_colors") or preset_spec.get("gradient_colors"),
        "intro_card": bool(pe.get("intro_card", preset_spec.get("intro_card", False))),
        "outro_card": bool(pe.get("outro_card", preset_spec.get("outro_card", False))),
    }

    for clip in clips:
        if not isinstance(clip, dict):
            continue
        clip["caption_style"] = resolve_caption_style(
            clip.get("caption_style"),
            preset_spec=preset_spec,
            default=effects["caption_style"],
        )

    _normalize_clip_transitions(clips, default_tr)

    _apply_bookends_policy(effects, platform_id, bookends=bookends)

    if clips:
        if effects["intro_card"] and not pe.get("intro_heading"):
            effects["intro_heading"] = str(clips[0].get("hook_text") or clips[0].get("tts_text") or "")[:80]
        if effects["outro_card"] and not pe.get("outro_cta"):
            effects["outro_cta"] = str(clips[-1].get("hook_text") or clips[-1].get("tts_text") or "关注我")[:80]

    return effects


def save_catalog_snapshot(output_dir: Path, *, feed_kind: str = "news") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "catalog": effects_catalog(),
        "platform_defaults": PLATFORM_VIDEO_DEFAULTS,
        "valid_caption_styles": list(VALID_CAPTION_STYLES),
        "valid_transitions": list(VALID_TRANSITIONS),
        "selection_rules": EFFECT_SELECTION_RULES,
        "feed_kind": feed_kind,
    }
    path = output_dir / "llm" / "vsa_capabilities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_render_effects_audit(
    task_dir: Path,
    platform_id: str,
    *,
    plan_effects: dict[str, Any] | None,
    applied_effects: dict[str, Any],
    clips: list[dict[str, Any]],
) -> Path:
    """对比 LLM 计划与实际渲染参数，写入 llm/render_effects_{platform}.json。"""
    transitions = [
        resolve_transition(c.get("transition_to_next"), default=applied_effects.get("transition", "fade"))
        for c in clips
        if isinstance(c, dict)
    ]
    payload = {
        "platform": platform_id,
        "plan_effects": plan_effects or {},
        "applied_effects": applied_effects,
        "clip_caption_styles": [c.get("caption_style") for c in clips if isinstance(c, dict)],
        "clip_transitions": transitions,
    }
    path = task_dir / "llm" / f"render_effects_{platform_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
