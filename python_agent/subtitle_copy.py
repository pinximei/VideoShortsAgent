"""中区主标题 / 框线子标题文案规范化（去重、长度、与口播分工）。"""
from __future__ import annotations

import re
from typing import Any

SUBTITLE_MIN_CHARS = 4
SUBTITLE_MAX_CHARS = 14
HERO_MAX_CHARS = 14
SUBTITLE_FALLBACKS = ("核心能力", "一步上手", "值得收藏", "省时省力")
SUBTITLE_SLOT_FALLBACKS = ("解决痛点", "核心能力", "立刻见效")

_MID_LAYOUT_ROTATION = ("steps", "framed", "keywords", "compare", "steps", "framed", "keywords")

# 版式 → 允许的 motion_profile（优先第一项）
LAYOUT_PROFILE_BIND: dict[str, tuple[str, ...]] = {
    "steps": ("bullet_stagger_up", "shake_emphasis", "glass_card_stack"),
    "framed": ("bullet_stagger_up", "shake_emphasis", "glass_card_stack"),
    "compare": ("shake_emphasis", "bullet_stagger_up"),
    "keywords": ("bullet_stagger_up", "shake_emphasis", "glass_card_stack"),
}

SUBTITLE_SLOT_LABELS = ("痛点", "能力", "结果")


def _norm_key(s: str) -> str:
    return re.sub(r"[\s\W_]+", "", (s or "").strip().lower())


def _clamp_subtitle(text: str) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    if not t:
        return ""
    t = t.replace("Sta", "Star").replace("star", "Star")
    if len(t) > SUBTITLE_MAX_CHARS:
        t = t[:SUBTITLE_MAX_CHARS]
    if len(t) < SUBTITLE_MIN_CHARS:
        return ""
    return t


def _clamp_hero(text: str) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    return t[:HERO_MAX_CHARS] if t else ""


def _too_similar(a: str, b: str) -> bool:
    ka, kb = _norm_key(a), _norm_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    if len(ka) >= 4 and len(kb) >= 4 and (ka in kb or kb in ka):
        return True
    return False


def _char_overlap_ratio(a: str, b: str) -> float:
    ka, kb = _norm_key(a), _norm_key(b)
    if not ka or not kb:
        return 0.0
    if ka == kb:
        return 1.0
    shorter, longer = (ka, kb) if len(ka) <= len(kb) else (kb, ka)
    if shorter in longer:
        return len(shorter) / max(len(longer), 1)
    common = sum(1 for ch in shorter if ch in longer)
    return common / max(len(shorter), 1)


def _overlaps_tts(card: str, tts: str) -> bool:
    """仅过滤与口播整句高度复述的子标题（避免误杀 shot_design 卡片）。"""
    c, t = _plain_strip(card), _plain_strip(tts)
    if not c or not t or len(c) < 5:
        return False
    if len(c) >= 12 and c in t:
        return True
    for chunk in re.split(r"[。！？；\n]", tts):
        chunk_k = _plain_strip(chunk)
        if len(chunk_k) < 10:
            continue
        if c == chunk_k:
            return True
        if len(c) >= 10 and c in chunk_k and len(c) / max(len(chunk_k), 1) >= 0.55:
            return True
        if _char_overlap_ratio(c, chunk_k) >= 0.82:
            return True
    return False


def _plain_strip(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def bind_motion_profile_to_layout(slide: dict[str, Any]) -> dict[str, Any]:
    s = dict(slide)
    layout = str(s.get("mid_info_layout") or "framed").lower()
    prof = str(s.get("motion_profile") or "")
    allowed = LAYOUT_PROFILE_BIND.get(layout, LAYOUT_PROFILE_BIND["framed"])
    if prof not in allowed:
        s["motion_profile"] = allowed[0]
        vd = dict(s.get("visual_design") or {})
        vd["motion_profile"] = allowed[0]
        s["visual_design"] = vd
    return s


def trim_subtitles_for_viz(slide: dict[str, Any]) -> dict[str, Any]:
    s = dict(slide)
    vt = str(s.get("viz_type") or "none").lower()
    if vt in ("line", "bar"):
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if len(lines) > 2:
            s["summary_lines"] = lines[:2]
    return s


def _subtitle_sources(slide: dict[str, Any]) -> list[str]:
    shot = slide.get("shot_design") or {}
    design_cards = (
        list(shot.get("subtitle_cards") or []) if isinstance(shot, dict) else []
    )
    lines = [str(x).strip() for x in (slide.get("summary_lines") or []) if str(x).strip()]
    merged: list[str] = []
    for raw in design_cards + lines:
        t = str(raw).strip()
        if t and t not in merged:
            merged.append(t)
    return merged


def _fill_from_kinetic(
    hero: str,
    subs: list[str],
    slide: dict[str, Any],
    *,
    tts: str = "",
    target: int = 3,
) -> list[str]:
    out = list(subs)
    for raw in slide.get("kinetic_phrases") or []:
        if len(out) >= target:
            break
        c = _clamp_subtitle(str(raw))
        if not c:
            continue
        if _too_similar(c, hero) or any(_too_similar(c, x) for x in out):
            continue
        if _overlaps_tts(c, tts):
            continue
        out.append(c)
    return out


def infer_mid_layout_from_tts(tts: str) -> str:
    """按口播结构选中部版式（列举 / 对比 / 默认框线）。"""
    t = (tts or "").strip()
    if re.search(r"对比|相比|更.+(?:好|快|省|稳)|不如|胜过", t):
        return "compare"
    if re.search(r"第一|第二|第三|步骤|首先|其次|最后|一是|二是", t):
        return "steps"
    if re.search(r"关键词|标签|三个词|三个特点", t):
        return "keywords"
    return "framed"


def dedupe_subtitles_across_slides(
    slides: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """跨镜去重子标题，避免连续内容镜复述同一句。"""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for s in slides:
        slide = dict(s)
        if not (slide.get("scene_focus") or str(slide.get("type")) == "content_card"):
            out.append(slide)
            continue
        slide = normalize_slide_mid_copy(slide, brief)
        hero = str(slide.get("feature_label") or "")
        lines: list[str] = []
        for raw in slide.get("summary_lines") or []:
            c = _clamp_subtitle(str(raw))
            if not c or _too_similar(c, hero):
                continue
            nk = _norm_key(c)
            if nk in seen:
                continue
            lines.append(c)
            seen.add(nk)
        min_c, max_c = _subtitle_card_budget(slide)
        tts = str(slide.get("tts_text") or "")
        if len(lines) < min_c:
            _, filled = normalize_subtitle_cards(hero, lines, tts=tts, min_cards=min_c, max_cards=max_c)
            for c in filled:
                nk = _norm_key(c)
                if nk not in seen and not any(_too_similar(c, x) for x in lines):
                    lines.append(c)
                    seen.add(nk)
                if len(lines) >= max_c:
                    break
        slide["summary_lines"] = lines[:max_c]
        out.append(slide)
    return out


def _clause_cards_from_tts(tts: str, hero: str, *, max_n: int = 4) -> list[str]:
    """从口播按停顿拆短句，补全子标题（与 hero 不重复）。"""
    out: list[str] = []
    for part in re.split(r"[，,、；;。！？\n]", tts):
        c = _clamp_subtitle(part)
        if not c or len(c) < 4:
            continue
        if _too_similar(c, hero) or any(_too_similar(c, x) for x in out):
            continue
        out.append(c)
        if len(out) >= max_n:
            break
    return out


def normalize_subtitle_cards(
    hero: str,
    cards: list[str],
    *,
    tts: str = "",
    min_cards: int = 3,
    max_cards: int = 3,
    protected: frozenset[str] | None = None,
) -> tuple[str, list[str]]:
    """主标题 + 子标题去重、限长；子标题不与主标题/口播复述。"""
    hero_out = _clamp_hero(hero)
    prot = {_norm_key(x) for x in (protected or frozenset())}
    out: list[str] = []
    for raw in cards or []:
        c = _clamp_subtitle(str(raw))
        if not c:
            continue
        if _too_similar(c, hero_out):
            continue
        if _norm_key(c) not in prot and _overlaps_tts(c, tts):
            continue
        if any(_too_similar(c, x) for x in out):
            continue
        out.append(c)

    for clause in _clause_cards_from_tts(tts, hero_out, max_n=max_cards):
        if len(out) >= max_cards:
            break
        if not any(_too_similar(clause, x) for x in out):
            out.append(clause)

    for fb in list(SUBTITLE_SLOT_FALLBACKS) + list(SUBTITLE_FALLBACKS):
        if len(out) >= min_cards:
            break
        if not _too_similar(fb, hero_out) and not any(_too_similar(fb, x) for x in out):
            if not tts or not _overlaps_tts(fb, tts):
                out.append(fb)

    return hero_out, out[:max_cards]


def normalize_shot_design_copy(design: Any) -> Any:
    """ShotDesign 或 dict。"""
    hero = getattr(design, "hero_title", None) or (design.get("hero_title") if isinstance(design, dict) else "")
    cards = getattr(design, "subtitle_cards", None) or (
        design.get("subtitle_cards") if isinstance(design, dict) else []
    )
    h, subs = normalize_subtitle_cards(str(hero or ""), list(cards or []))
    if hasattr(design, "hero_title"):
        design.hero_title = h
        design.subtitle_cards = subs
        if getattr(design, "stagger_frames", 14) < 16:
            design.stagger_frames = 18
    elif isinstance(design, dict):
        design["hero_title"] = h
        design["subtitle_cards"] = subs
        design["stagger_frames"] = max(18, int(design.get("stagger_frames") or 18))
    return design


def _subtitle_card_budget(slide: dict[str, Any]) -> tuple[int, int]:
    if slide.get("scene_focus") or str(slide.get("type")) == "content_card":
        return 3, 4
    layout = str(slide.get("mid_info_layout") or "framed").lower()
    if layout in ("steps", "framed", "keywords", "compare"):
        return 3, 4
    return 3, 3


def normalize_slide_mid_copy(slide: dict[str, Any], brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """写回 slide 的 feature_label / summary_lines 等。"""
    s = dict(slide)
    tts = str(s.get("tts_text") or "")
    hero = str(s.get("feature_label") or s.get("heading") or "").strip()
    from python_agent.hero_copy import is_generic_hero, sanitize_hero_title

    hero = str(s.get("feature_label") or s.get("heading") or "").strip()
    if is_generic_hero(hero):
        hero = sanitize_hero_title(
            hero,
            tts=tts,
            repo_name=str((brief or {}).get("repo_name") or (brief or {}).get("title") or ""),
        )
    lines = _subtitle_sources(s)
    shot = s.get("shot_design") or {}
    protected = frozenset(
        str(x).strip()
        for x in ((shot.get("subtitle_cards") or []) if isinstance(shot, dict) else [])
        if str(x).strip()
    )
    min_c, max_c = _subtitle_card_budget(s)
    h, subs = normalize_subtitle_cards(
        hero, lines, tts=tts, min_cards=min_c, max_cards=max_c, protected=protected
    )
    subs = _fill_from_kinetic(h, subs, s, tts=tts, target=max_c)
    if len(subs) < min_c:
        h2, subs2 = normalize_subtitle_cards(
            h, subs, tts="", min_cards=min_c, max_cards=max_c, protected=protected
        )
        subs = subs2
        h = h2
    s["feature_label"] = h
    s["heading"] = h
    s["summary_lines"] = subs

    mp = dict(s.get("motion_params") or {})
    plat = str(s.get("platform") or s.get("caption_platform") or "").lower()
    if plat == "douyin":
        mp["staggerFrames"] = min(16, max(14, int(mp.get("staggerFrames") or 14)))
    else:
        mp["staggerFrames"] = max(18, int(mp.get("staggerFrames") or 18))
    if len(subs) >= 3:
        mp["midSafeBottomRatio"] = max(float(mp.get("midSafeBottomRatio") or 0.36), 0.42)
    else:
        mp["midSafeBottomRatio"] = max(float(mp.get("midSafeBottomRatio") or 0.36), 0.40)
    mp.setdefault("midHeroFontScale", 1.0)
    s["motion_params"] = mp
    s = bind_motion_profile_to_layout(s)
    s = trim_subtitles_for_viz(s)
    return s


def ensure_douyin_content_diversity(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """内容镜：版式 / 动效档案尽量不重复。"""
    out = [dict(s) for s in slides]
    content_idxs = [
        i
        for i, s in enumerate(out)
        if s.get("scene_focus") or str(s.get("type")) == "content_card"
    ]
    if len(content_idxs) < 2:
        return out

    used_layouts: set[str] = set()
    used_profiles: set[str] = set()
    for n, i in enumerate(content_idxs):
        s = out[i]
        if not s.get("shot_design_source"):
            tts = str(s.get("tts_text") or "")
            layout = infer_mid_layout_from_tts(tts)
        else:
            layout = str(s.get("mid_info_layout") or "").lower()
        if layout in used_layouts or layout not in _MID_LAYOUT_ROTATION:
            picked = None
            for cand in _MID_LAYOUT_ROTATION:
                if cand not in used_layouts:
                    picked = cand
                    break
            layout = picked or _MID_LAYOUT_ROTATION[n % len(_MID_LAYOUT_ROTATION)]
        s["mid_info_layout"] = layout
        used_layouts.add(layout)

        prof = str(s.get("motion_profile") or "")
        if prof in used_profiles:
            from python_agent.douyin_layout_registry import layout_for_content_index

            pack = layout_for_content_index(n + len(used_profiles))
            s["motion_profile"] = str(pack.get("motion_profile") or prof)
            s["css_decorations"] = list(pack.get("css") or s.get("css_decorations") or [])
        used_profiles.add(str(s.get("motion_profile") or ""))
        out[i] = bind_motion_profile_to_layout(normalize_slide_mid_copy(s))

    return out
