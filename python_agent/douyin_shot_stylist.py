"""抖音分镜造型：100% LLM 细设计（须配置 llm_api_key）。"""
from __future__ import annotations

import copy
import re
from typing import Any

from python_agent.douyin_shot_designer import (
    DouyinShotDesignError,
    ShotDesign,
    apply_shot_design_to_slide,
    build_all_shot_plans,
)

__all__ = [
    "DouyinShotDesignError",
    "apply_douyin_shot_styles",
    "build_github_daily_hook_beats",
    "export_shot_plan",
    "github_daily_opening_hook",
    "parse_star_count",
    "short_repo_name",
]


def short_repo_name(name: str, *, max_len: int = 18) -> str:
    s = re.sub(r"\s+", " ", (name or "").strip())
    if not s:
        return "这个仓库"
    s = re.split(r"[：:｜|—\-]", s, maxsplit=1)[0].strip()
    return s[:max_len]


def parse_star_count(raw: Any) -> int:
    if raw is None or raw == "":
        return 0
    if isinstance(raw, (int, float)):
        return max(100, int(raw))
    s = str(raw).strip().lower().replace(",", "").replace(" ", "")
    m = re.search(r"([\d.]+)\s*万", s)
    if m:
        return max(100, int(float(m.group(1)) * 10000))
    m = re.search(r"([\d.]+)\s*k", s)
    if m:
        return max(100, int(float(m.group(1)) * 1000))
    m = re.search(r"(\d+)", s)
    if m:
        v = int(m.group(1))
        return v * 10000 if v < 500 else v
    return 0


def format_stars_display(count: int) -> str:
    """统一 Star 展示文案（与 odometer-stars 一致）。"""
    if count <= 0:
        return ""
    if count >= 10000:
        wan = count / 10000
        text = f"{wan:.1f}".rstrip("0").rstrip(".")
        return f"{text}万"
    if count >= 1000:
        return f"{count / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(count)


from python_agent.hero_copy import is_generic_hero, sanitize_hero_title
from python_agent.pinned_template import GENERIC_HERO_TITLES


def resolve_content_hero_title(
    slide: dict[str, Any],
    brief: dict[str, Any] | None = None,
    *,
    design_hero: str = "",
) -> str:
    """内容镜主标题：拒绝空洞「核心亮点」，从口播/仓库名推导。"""
    from python_agent.douyin_shot_designer import _split_subtitles

    b = brief or {}
    candidates: list[str] = [
        str(design_hero or ""),
        str(slide.get("feature_label") or ""),
        str(slide.get("heading") or ""),
        str((slide.get("shot_design") or {}).get("hero_title") or ""),
    ]
    for raw in candidates:
        h = re.sub(r"\s+", "", (raw or "").strip())[:14]
        if not is_generic_hero(h):
            return h

    return sanitize_hero_title(
        "",
        tts=str(slide.get("tts_text") or ""),
        repo_name=str(b.get("repo_name") or b.get("title") or ""),
    )


def sync_github_stars_on_slides(
    slides: list[dict[str, Any]], brief: dict[str, Any] | None
) -> None:
    """全片统一 star_count / stat_value，避免 1.2万 vs 1.3万 不一致。"""
    b = brief or {}
    raw = b.get("stars") or b.get("star_count") or ""
    star_n = parse_star_count(raw)
    if not star_n:
        return
    label = format_stars_display(star_n)
    title_stars = f"{label} Star" if label else ""

    for s in slides:
        s["star_count"] = star_n
        if label and str(s.get("type")) == "title_card":
            s["stars"] = title_stars or label
        vt = str(s.get("viz_type") or "none").lower()
        if vt == "stat" and label:
            s["stat_value"] = label[:12]
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        cleaned: list[str] = []
        for line in lines:
            if re.search(r"star|⭐|万\s*star", line, re.I) or (
                label and label in line
            ):
                continue
            cleaned.append(line)
        if cleaned != lines:
            s["summary_lines"] = cleaned


def github_daily_opening_hook(
    *,
    repo_name: str,
    title: str = "",
    hook: str = "",
    stars: str = "",
) -> str:
    repo = short_repo_name(repo_name or title)
    h = re.sub(r"\s+", " ", (hook or "").strip())
    if h and repo in h and 10 <= len(h) <= 28:
        return h[:28]
    star_n = parse_star_count(stars)
    star_label = format_stars_display(star_n) if star_n else re.sub(r"\s+", "", str(stars))[:8]
    templates = (
        f"别划走！{repo}火了？",
        f"{repo} Star{star_label}还在涨" if star_label else f"今天讲{repo}，别划走",
        f"每日一个GitHub项目：{repo}",
        f"开源神器{repo}，{star_label}你试过吗" if star_label else f"开源神器{repo}，值得现在就看",
    )
    for t in templates:
        if len(t) <= 28:
            return t
    return f"每日一个GitHub项目：{repo}"[:28]


def build_github_daily_hook_beats(
    *,
    repo_name: str,
    title: str = "",
    hook: str = "",
    stars: str = "",
) -> list[str]:
    """片头双 beat：悬念 + 项目名/Star（各 ≤18 字）。"""
    repo = short_repo_name(repo_name or title)[:12]
    star_n = parse_star_count(stars)
    star_label = format_stars_display(star_n) if star_n else ""
    h = re.sub(r"\s+", " ", (hook or "").strip())

    suspense_candidates = (
        f"别划走！{repo}火了？",
        f"{repo}你还没试过？",
        f"还在找同类工具？",
    )
    if h and 4 <= len(h) <= 18 and ("？" in h or "?" in h or "别" in h):
        beat1 = h[:18]
    else:
        beat1 = next((t for t in suspense_candidates if len(t) <= 18), suspense_candidates[0][:18])

    if star_label:
        beat2 = f"Star {star_label}"[:18]
    else:
        beat2 = f"每日GitHub·{repo}"[:18]

    beats: list[str] = []
    seen: set[str] = set()
    for b in (beat1, beat2):
        key = re.sub(r"\s+", "", b)[:8]
        if key and key not in seen:
            seen.add(key)
            beats.append(b)
    return beats[:2] or [beat1[:18]]


def export_shot_plan(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, s in enumerate(slides):
        sd = s.get("shot_design")
        if not sd:
            continue
        rows.append(
            {
                "slide": i,
                "type": s.get("type"),
                "tts_excerpt": str(s.get("tts_text") or "")[:48],
                "hero_title": sd.get("hero_title"),
                "subtitle_cards": sd.get("subtitle_cards"),
                "mid_info_layout": sd.get("mid_info_layout"),
                "mid_effect": sd.get("mid_effect"),
                "motion_profile": sd.get("motion_profile"),
                "css_decorations": sd.get("css_decorations"),
                "viz_type": sd.get("viz_type"),
                "design_rationale": sd.get("design_rationale"),
                "source": s.get("shot_design_source"),
            }
        )
    return rows


def apply_douyin_shot_styles(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """100% LLM 逐镜细设计；无 API 抛 DouyinShotDesignError。"""
    b = dict(brief or {})
    repo = short_repo_name(str(b.get("repo_name") or b.get("title") or ""))
    stars_raw = b.get("stars") or b.get("star_count") or ""
    star_n = parse_star_count(stars_raw)
    repo_url = str(b.get("repo_url") or b.get("github_url") or "").strip()
    if not repo_url and repo and repo != "这个仓库":
        slug = re.sub(r"\s+", "-", repo.lower())[:40]
        repo_url = f"github.com/{slug}"

    all_plans = build_all_shot_plans(slides, b)
    content_idxs = [
        i
        for i, s in enumerate(slides)
        if s.get("scene_focus") or str(s.get("type")) == "content_card"
    ]
    missing = [i for i in content_idxs if i not in all_plans]
    if missing:
        raise DouyinShotDesignError(
            f"LLM 未覆盖内容镜 index={missing}，需重试或检查返回 JSON"
        )
    layouts = {all_plans[i].mid_info_layout for i in content_idxs}
    if len(content_idxs) >= 2 and len(layouts) < 2:
        raise DouyinShotDesignError(
            f"LLM 分镜版式缺乏差异: layouts={layouts}，请重试"
        )
    content_plans = {i: all_plans[i] for i in content_idxs}
    content_total = len(content_plans)
    ci = 0

    out: list[dict[str, Any]] = []
    for i, s in enumerate(slides):
        slide = copy.deepcopy(s)
        st = str(slide.get("type") or "")

        if st == "title_card" and i in all_plans:
            td = all_plans[i]
            slide["heading"] = td.hero_title or repo[:14]
            slide["repo_name"] = repo
            slide["star_count"] = star_n
            if repo_url:
                slide["repo_url"] = repo_url
            if td.css_decorations:
                slide["css_decorations"] = list(td.css_decorations)
            if td.motion_profile:
                slide["motion_profile"] = td.motion_profile
            slide["shot_design"] = td.to_dict()
            slide["shot_design_source"] = "llm_shot_designer"
            out.append(slide)
            continue

        if i not in content_plans:
            if st == "title_card":
                slide["heading"] = repo[:14] or slide.get("heading")
                slide["repo_name"] = repo
                slide["star_count"] = star_n
                if repo_url:
                    slide["repo_url"] = repo_url
            out.append(slide)
            continue

        design: ShotDesign = content_plans[i]
        preserve = bool(slide.get("llm_directed")) and bool(slide.get("summary_lines"))
        slide = apply_shot_design_to_slide(slide, design, preserve_llm_copy=preserve, brief=b)
        hero = resolve_content_hero_title(slide, b, design_hero=design.hero_title)
        slide["feature_label"] = hero
        slide["heading"] = hero
        if isinstance(slide.get("shot_design"), dict):
            slide["shot_design"]["hero_title"] = hero
        slide["scene_index"] = ci
        slide["scene_total"] = max(content_total, 3)
        ci += 1
        if design.viz_type == "stat" and stars_raw:
            slide["star_count"] = star_n
        if repo_url:
            slide["repo_url"] = repo_url
        out.append(slide)

    sync_github_stars_on_slides(out, b)

    if content_total:
        from python_agent.slides_llm_director import _enforce_viz_budget

        _enforce_viz_budget(out)

    return out
