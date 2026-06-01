"""
动效风格目录 v2：按 motion_profile（动效档案）选型，而非配色变体。

catalog: templates/motion_templates/catalog.json（由 scripts/generate_motion_style_catalog.py 生成）
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_CATALOG_PATH = _REPO / "templates" / "motion_templates" / "catalog.json"
_GITHUB_DAILY_CATALOG = _REPO / "templates" / "github_daily_20" / "catalog.json"

# 资讯口播：优先抖音/TikTok 动效档案（非 GitHub 日更角标风）
NEWS_PROFILES_BY_SLIDE: dict[str, list[str]] = {
    "title_card": [
        "tiktok_word_pop",
        "tiktok_phrase_pages",
        "kinetic_slam_tight",
        "flash_hook_smash",
        "glitch_hook_clean",
        "minimal_headline",
        "shake_emphasis",
    ],
    "content_card": [
        "tiktok_phrase_pages",
        "bullet_stagger_up",
        "glass_card_stack",
        "bullet_rail_right",
        "minimal_headline",
        "marquee_ticker",
    ],
    "cta_card": [
        "cta_pulse_arrow",
        "shake_emphasis",
        "kinetic_slam_loose",
    ],
}

GITHUB_PROFILES_BY_SLIDE: dict[str, list[str]] = {
    "title_card": [
        "github_daily_hook",
        "episode_counter",
        "kinetic_slam_tight",
        "flash_hook_smash",
    ],
    "content_card": [
        "github_daily_bullets",
        "bullet_rail_right",
        "bullet_stagger_up",
    ],
    "cta_card": ["cta_pulse_arrow", "shake_emphasis"],
}


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"version": 2, "templates": []}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def list_templates(
    *,
    slide_type: str | None = None,
    motion_profile: str | None = None,
    feed_kind: str | None = None,
) -> list[dict[str, Any]]:
    items = list(load_catalog().get("templates") or [])
    if slide_type:
        items = [t for t in items if slide_type in (t.get("for_slide_types") or [])]
    if motion_profile:
        items = [t for t in items if t.get("motion_profile") == motion_profile]
    if feed_kind:
        fk = feed_kind.strip().lower()
        preferred = (
            NEWS_PROFILES_BY_SLIDE if fk == "news" else GITHUB_PROFILES_BY_SLIDE
        )
        if slide_type and slide_type in preferred:
            profs = set(preferred[slide_type])
            biased = [t for t in items if t.get("motion_profile") in profs]
            if biased:
                items = biased
    return items


def _seed_int(key: str) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def pick_template_for_slide(
    seed: str,
    slide_index: int,
    slide_type: str,
    *,
    feed_kind: str | None = None,
) -> dict[str, Any]:
    """按文章种子 + 镜号 + slide 类型 + 泳道选一套动效模板。"""
    pool = list_templates(slide_type=slide_type, feed_kind=feed_kind)
    if not pool:
        pool = list(load_catalog().get("templates") or [])
    if not pool:
        return _fallback_template(slide_type, feed_kind=feed_kind)
    idx = (_seed_int(f"{seed}:{feed_kind}:{slide_type}:{slide_index}") + slide_index * 13) % len(
        pool
    )
    return dict(pool[idx])


def _fallback_template(slide_type: str, *, feed_kind: str | None = None) -> dict[str, Any]:
    fk = (feed_kind or "").strip().lower()
    if fk == "news":
        profile = {
            "title_card": "tiktok_word_pop",
            "content_card": "bullet_stagger_up",
            "cta_card": "cta_pulse_arrow",
        }.get(slide_type, "minimal_headline")
        theme = "tiktok"
    else:
        profile = {
            "title_card": "github_daily_hook",
            "content_card": "github_daily_bullets",
            "cta_card": "cta_pulse_arrow",
        }.get(slide_type, "minimal_headline")
        theme = "github"
    return {
        "id": f"fallback_{profile}",
        "motion_profile": profile,
        "motion_params": {"staggerFrames": 5, "springDamping": 14, "springStiffness": 120},
        "theme": theme,
        "caption_style": "fade",
        "transition": "fade",
    }


def is_github_daily_brief(brief: dict[str, Any]) -> bool:
    fk = str(brief.get("feed_kind") or "").strip().lower()
    series = str(brief.get("series") or brief.get("series_tag") or "").lower()
    scene = str(brief.get("scene") or brief.get("render_scene") or "").lower()
    return (
        fk in ("github", "github_daily")
        or "github" in series
        or "每天" in series
        or scene in ("daily_github", "github_daily")
    )


def _enrich_github_daily_css(style: dict[str, Any], platform: str = "") -> list[str]:
    """catalog 里 css 过少时补齐预研装饰，避免纯色底无动效。"""
    base = list(style.get("css") or [])
    sid = str(style.get("id") or "")
    plat = (platform or "").strip().lower()
    extras: list[str] = []
    if sid in ("G06_tiktok_follow_caption", "G05_dark_top10_rank"):
        extras.extend(["grid-tunnel-bg", "github-badge", "daily-video-tag"])
    elif sid == "G01_cyber_hook_yellow" and plat != "douyin":
        extras.extend(["float-icon", "text-stroke-yellow"])
    elif sid == "G01_cyber_hook_yellow":
        extras.extend(["text-stroke-yellow"])
    elif sid == "G07_hook_glitch_github":
        extras.extend(["github-badge"])
    elif sid == "G03_minimal_white_series":
        if "plain-white-bg" not in base:
            extras.append("plain-white-bg")
        extras.extend(["repo-header", "pill-badge"])
    elif sid in ("G04_badge_pills_intro", "G20_clean_badge_orange"):
        extras.extend(["repo-header", "accent-orange-word"])
    elif sid == "G16_purple_gradient_soft":
        extras.append("soft-purple-gradient")
    if plat == "douyin" and "caption-bottom-safe" not in base + extras:
        extras.append("caption-bottom-safe")
    seen: set[str] = set()
    out: list[str] = []
    for x in base + extras:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _profile_for_github_slide(
    style: dict[str, Any], slide_type: str, *, platform: str = ""
) -> str:
    if slide_type == "title_card":
        return str(style.get("title_profile") or "github_daily_hook")
    if slide_type == "cta_card":
        return "cta_pulse_arrow"
    if slide_type == "content_card":
        prof = str(style.get("content_profile") or "").strip()
        if prof:
            return prof
        plat = (platform or "").strip().lower()
        return "tiktok_word_pop" if plat == "douyin" else "github_daily_bullets"
    return str(style.get("content_profile") or "github_daily_bullets")


def _theme_for_bg(bg: str) -> str:
    if bg in ("#000000", "#000"):
        return "tiktok"
    if bg in ("#f5f5f0", "#ececec", "#f0f0f0"):
        return "minimal"
    return "github"


def build_github_daily_slide_plan(
    brief: dict[str, Any], slides: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """整片选一套 Gxx，按镜类型映射 profile + 装饰。"""
    picked = pick_github_daily_style(brief)
    style = dict(picked.get("github_daily_style") or {})
    cap = str(picked.get("caption_style") or "spring")
    trans = str(picked.get("transition") or "fade")
    mparams = dict(picked.get("motion_params") or {})
    plan: list[dict[str, Any]] = []
    platform = str(brief.get("platform") or "").strip().lower()
    cap_ms = 500 if platform == "douyin" else int(style.get("wordsPerPageMs", 800))
    for i, slide in enumerate(slides):
        st = str(slide.get("type") or "content_card")
        if slide.get("motion_profile"):
            profile = str(slide["motion_profile"])
        else:
            profile = _profile_for_github_slide(style, st, platform=platform)
        if i == 0 and st == "title_card" and platform == "douyin":
            tp = str(style.get("title_profile") or "")
            if tp in ("kinetic_slam_tight", "kinetic_slam_loose", "github_daily_hook", "tiktok_word_pop"):
                profile = "flash_hook_smash"
            elif tp == "glitch_hook_clean":
                profile = "glitch_hook_clean"
        slide_trans = trans if i < len(slides) - 1 else ""
        plan.append(
            {
                "id": style.get("id"),
                "slide_index": i,
                "slide_type": st,
                "motion_profile": profile,
                "motion_params": {
                    "wordsPerPageMs": cap_ms if platform == "douyin" else style.get("wordsPerPageMs", mparams.get("wordsPerPageMs", 800)),
                    "staggerFrames": mparams.get("staggerFrames", 5),
                    "springDamping": mparams.get("springDamping", 14),
                    "springStiffness": mparams.get("springStiffness", 120),
                },
                "theme": _theme_for_bg(str(style.get("bg") or "#0d1117")),
                "background": slide.get("background_color") or style.get("bg"),
                "css_decorations": list(slide.get("css_decorations") or [])
                or _enrich_github_daily_css(style, platform),
                "github_daily_style_id": style.get("id"),
                "caption_style": cap,
                "transition": slide_trans,
            }
        )
    return picked, plan


def apply_github_daily_plan_to_slides(
    slides: list[dict[str, Any]], plan: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for i, slide in enumerate(slides):
        tpl = plan[i] if i < len(plan) else plan[-1]
        apply_template_to_slide(slide, tpl)
        vd = dict(slide.get("visual_design") or {})
        if slide.get("scene_focus") and slide.get("background_color"):
            bg = slide["background_color"]
        else:
            bg = tpl.get("background")
            slide["background_color"] = bg
        if slide.get("scene_focus"):
            dec = [d for d in (slide.get("css_decorations") or []) if d != "chart-line-rise"]
            for d in tpl.get("css_decorations") or []:
                if d not in dec and d != "chart-line-rise":
                    dec.append(d)
            slide["css_decorations"] = dec
        else:
            slide["background_color"] = tpl.get("background")
            slide["css_decorations"] = tpl.get("css_decorations") or []
        vd["background_color"] = slide.get("background_color") or bg
        if slide.get("show_chart") or slide.get("scene_focus") or slide.get("summary_lines"):
            slide["css_decorations"] = [
                d for d in (slide.get("css_decorations") or []) if d != "chart-line-rise"
            ]
        vd["css_decorations"] = slide.get("css_decorations") or []
        slide["visual_design"] = vd
        slide["github_daily_style_id"] = tpl.get("github_daily_style_id")
    return slides


def save_github_daily_style(task_dir: Path, picked: dict[str, Any], plan: list[dict[str, Any]]) -> Path:
    path = Path(task_dir) / "llm" / "github_daily_style.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "picked": picked,
                "per_slide": plan,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def apply_template_to_slide(slide: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    profile = str(template.get("motion_profile") or "github_daily_hook")
    params = dict(template.get("motion_params") or {})
    theme = str(template.get("theme") or "github")

    vd = dict(slide.get("visual_design") or {})
    vd["motion_profile"] = profile
    vd["motion_params"] = params
    vd["theme"] = theme
    vd["transition_to_next"] = template.get("transition", vd.get("transition_to_next", "fade"))
    vd["caption_style"] = template.get("caption_style", slide.get("caption_style", "spring"))
    vd["background_variant"] = profile
    vd["use_web3_background"] = False
    vd["particle_type"] = "none"
    vd["decoration_style"] = "none"
    vd["text_effect"] = "classic"
    if profile.startswith("tiktok") or profile in ("minimal_headline", "kinetic_slam_tight"):
        vd["layout_style"] = vd.get("layout_style") or "top-heavy"
    if template.get("background"):
        vd["background_color"] = template["background"]
    if template.get("css_decorations"):
        vd["css_decorations"] = template["css_decorations"]

    slide["visual_design"] = vd
    slide["motion_template_id"] = template.get("id")
    slide["motion_profile"] = profile
    slide["motion_params"] = params
    slide["caption_style"] = vd["caption_style"]
    slide["transition_to_next"] = vd["transition_to_next"]
    return slide


def build_slide_template_plan(
    brief: dict[str, Any],
    slides: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if is_github_daily_brief(brief):
        _, plan = build_github_daily_slide_plan(brief, slides)
        return plan
    seed = str(
        brief.get("content_key")
        or brief.get("article_id")
        or brief.get("title")
        or "default"
    )
    feed_kind = str(brief.get("feed_kind") or "news")
    plan: list[dict[str, Any]] = []
    for i, slide in enumerate(slides):
        st = str(slide.get("type") or "content_card")
        plan.append(pick_template_for_slide(seed, i, st, feed_kind=feed_kind))
    return plan


def apply_template_plan_to_slides(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
) -> list[dict[str, Any]]:
    if is_github_daily_brief(brief):
        _, plan = build_github_daily_slide_plan(brief, slides)
        return apply_github_daily_plan_to_slides(slides, plan)
    plan = build_slide_template_plan(brief, slides)
    for i, slide in enumerate(slides):
        apply_template_to_slide(slide, plan[i] if i < len(plan) else plan[-1])
    return slides


@lru_cache(maxsize=1)
def load_github_daily_catalog() -> dict[str, Any]:
    if not _GITHUB_DAILY_CATALOG.is_file():
        return {"styles": []}
    return json.loads(_GITHUB_DAILY_CATALOG.read_text(encoding="utf-8"))


# 平台画风池：抖音偏快切/暗色/TikTok；小红书偏浅底/卡片/柔和
_DOUYIN_G_IDS = frozenset(
    {
        "G01_cyber_hook_yellow",
        "G05_dark_top10_rank",
        "G06_tiktok_follow_caption",
        "G07_hook_glitch_github",
        "G11_kinetic_word_slam",
        "G13_marquee_topics",
    }
)
_XHS_G_IDS = frozenset(
    {
        "G02_chart_card_stat",
        "G03_minimal_white_series",
        "G04_badge_pills_intro",
        "G10_glass_three_points",
        "G16_purple_gradient_soft",
        "G20_clean_badge_orange",
    }
)


def pick_github_daily_style(brief: dict[str, Any]) -> dict[str, Any]:
    """「每天一个 GitHub」系列：从 20 套预研模板选一整片风格（按平台收窄池）。"""
    styles = list(load_github_daily_catalog().get("styles") or [])
    if not styles:
        return pick_intro_template(brief)
    from python_agent.platform_gv_defaults import resolve_platform_motion_style

    chosen = resolve_platform_motion_style(brief, styles)
    if chosen:
        style = dict(chosen)
        platform = str(brief.get("platform") or "").strip().lower()
        return {
            "id": style.get("id"),
            "github_daily_style": style,
            "motion_profile": style.get("title_profile", "github_daily_hook"),
            "motion_params": {
                "wordsPerPageMs": style.get("wordsPerPageMs", 800),
                "staggerFrames": 3 if platform == "douyin" else 5,
                "springDamping": 12 if platform == "douyin" else 14,
                "springStiffness": 180 if platform == "douyin" else 120,
            },
            "theme": _theme_for_bg(str(style.get("bg") or "#0d1117")),
            "caption_style": "fade" if platform == "xhs" else "spring",
            "transition": "dissolve" if platform == "xhs" else "wipeleft",
            "background": style.get("bg"),
            "css_decorations": _enrich_github_daily_css(style, platform),
        }
    seed = str(
        brief.get("content_key")
        or brief.get("article_id")
        or brief.get("title")
        or "github_daily"
    )
    platform = str(brief.get("platform") or "").strip().lower()
    pool = list(styles)
    idx = _seed_int(f"github_daily:{seed}:{platform or 'all'}") % len(pool)
    style = dict(pool[idx])
    return {
        "id": style.get("id"),
        "github_daily_style": style,
        "motion_profile": style.get("title_profile", "github_daily_hook"),
        "motion_params": {
            "wordsPerPageMs": style.get("wordsPerPageMs", 800),
            "staggerFrames": 5,
        },
        "theme": "github" if style.get("bg", "#000") != "#000000" else "tiktok",
        "caption_style": "fade" if platform == "xhs" else "spring",
        "transition": "dissolve" if platform == "xhs" else "fade",
        "background": style.get("bg"),
        "css_decorations": _enrich_github_daily_css(style, platform),
    }


def pick_intro_template(brief: dict[str, Any]) -> dict[str, Any]:
    """pipeline 片头 TitleCard 用同一套目录。"""
    seed = str(brief.get("content_key") or brief.get("article_id") or brief.get("title") or "intro")
    fk = str(brief.get("feed_kind") or "news")
    series = str(brief.get("series") or brief.get("series_tag") or "")
    if fk in ("github", "github_daily") or "github" in series.lower():
        return pick_github_daily_style(brief)
    return pick_template_for_slide(seed, 0, "title_card", feed_kind=fk)


def save_template_plan(task_dir: Path, plan: list[dict[str, Any]]) -> Path:
    path = Path(task_dir) / "llm" / "motion_template_plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 2, "templates": plan}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
