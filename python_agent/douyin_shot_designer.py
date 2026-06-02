"""抖音分镜 100% LLM 细设计（无规则引擎降级）。"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from python_agent.douyin_layout_registry import DOUYIN_CONTENT_LAYOUTS, css_pack


class DouyinShotDesignError(RuntimeError):
    """未配置 LLM 或分镜设计调用失败时抛出。"""


@dataclass
class ContentSignals:
    """从口播文本提取的叙事信号。"""
    has_star_trend: bool = False
    has_compare: bool = False
    has_steps: bool = False
    has_speed: bool = False
    has_privacy_local: bool = False
    has_ai_build: bool = False
    has_number_stat: bool = False
    has_free_opensource: bool = False
    has_problem_pain: bool = False
    has_result_benefit: bool = False
    number_hint: str = ""


@dataclass
class ShotDesign:
    """单镜视觉方案（落盘到 slide.shot_design）。"""
    hero_title: str
    subtitle_cards: list[str]
    mid_info_layout: str
    mid_effect: str
    motion_profile: str
    css_decorations: list[str]
    viz_type: str = "none"
    show_chart: bool = False
    chart_series: list[float] = field(default_factory=list)
    chart_label: str = ""
    stat_value: str = ""
    kinetic_phrases: list[str] = field(default_factory=list)
    mid_icon: str = ""
    show_kinetic_wall: bool = False
    stagger_frames: int = 18
    design_rationale: str = ""
    layout_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def analyze_tts_signals(tts: str, *, brief: dict[str, Any] | None = None) -> ContentSignals:
    t = _plain(tts)
    b = brief or {}
    sig = ContentSignals()
    if not t:
        return sig

    sig.has_star_trend = bool(
        re.search(r"Star|star|⭐|涨|火爆|趋势|破万|万\+|热度|上榜", t, re.I)
    ) or bool(b.get("stars"))
    sig.has_compare = bool(re.search(r"对比|VS|vs|之前|原来|现在|以前|升级|替代", t))
    sig.has_steps = bool(
        re.search(r"第[一二三四五1-5]步|步骤|流程|先.+再|如何|怎么.+用|照着", t)
    )
    sig.has_speed = bool(re.search(r"快|秒|实时|一键|马上|立刻|效率", t))
    sig.has_privacy_local = bool(re.search(r"本地|离线|隐私|不上传|本机|内网", t))
    sig.has_ai_build = bool(re.search(r"AI|智能|模型|生成|自然语言|对话|Agent|助手", t, re.I))
    sig.has_free_opensource = bool(re.search(r"免费|开源|MIT|Apache|GPL", t, re.I))
    sig.has_problem_pain = bool(re.search(r"麻烦|痛点|重复|加班|低效|头疼|繁琐", t))
    sig.has_result_benefit = bool(re.search(r"省时|省力|少踩坑|搞定|完成|提升|翻倍", t))

    m = re.search(r"(\d+[\d.]*)\s*([万千kK%]|倍|分钟|小时|天)?", t)
    if m:
        sig.has_number_stat = True
        sig.number_hint = m.group(0)[:12]

    return sig


def _split_subtitles(tts: str, *, max_card: int = 12) -> tuple[str, list[str]]:
    """大标题 + 框线副标题（按语义断句，非机械切半）。"""
    t = re.sub(r"\s+", "", (tts or "").strip())
    if not t:
        return "核心亮点", ["一步上手", "值得收藏"]

    clauses = [c for c in re.split(r"(?<=[。！？；])", t) if c.strip()]
    if len(clauses) >= 2:
        hero = clauses[0].strip("，,。！？；、")[:12]
        subs = [c.strip("，,。！？；、")[:max_card] for c in clauses[1:3]]
        subs = [x for x in subs if len(x) >= 4] or subs
        if hero and subs:
            return hero, subs[:2]

    for i in range(max(4, len(t) // 3), max(4, len(t) - 3)):
        if t[i] in "，,。！？；、":
            a, b = t[:i].strip("，,。！？；、"), t[i + 1 :].strip("，,。！？；、")
            if len(a) >= 4 and len(b) >= 4:
                return a[:12], [b[:max_card], (b[max_card : max_card * 2] or "值得试试")[:max_card]]

    mid = max(4, len(t) // 2)
    return t[:12], [t[12 : 12 + max_card] or "上手很快", "值得收藏"]


def _kinetic_from_signals(sig: ContentSignals, subs: list[str]) -> list[str]:
    pool: list[str] = []
    if sig.has_star_trend:
        pool.extend(["Star↑", "趋势", "开源热"])
    if sig.has_speed:
        pool.extend(["快", "一键", "省时"])
    if sig.has_privacy_local:
        pool.extend(["本地", "隐私", "不上传"])
    if sig.has_ai_build:
        pool.extend(["AI", "生成", "对话"])
    if sig.has_free_opensource:
        pool.extend(["免费", "开源"])
    if sig.has_result_benefit:
        pool.extend(["省力", "好用"])
    for s in subs:
        w = s[:6]
        if w and w not in pool:
            pool.append(w)
    return pool[:4] or ["开源", "好用"]


def _pick_layout(sig: ContentSignals, *, used: set[str]) -> str:
    candidates: list[str] = []
    if sig.has_compare:
        candidates.append("compare")
    if sig.has_steps:
        candidates.append("steps")
    if sig.has_star_trend or sig.has_number_stat or sig.has_problem_pain:
        candidates.append("framed")
    candidates.extend(["framed", "keywords", "steps", "compare"])
    for c in candidates:
        if c not in used:
            return c
    for c in ("framed", "steps", "compare", "keywords"):
        if c not in used:
            return c
    return "keywords"


def _pick_effect(layout: str, sig: ContentSignals, *, used: set[str]) -> str:
    if layout == "compare":
        pool = ["bracket_slam", "glow_ring"]
    elif layout == "steps":
        pool = ["glow_scan", "glow_ring", "typewriter"]
    elif sig.has_star_trend:
        pool = ["typewriter", "particle_dust", "glow_ring"]
    elif sig.has_speed:
        pool = ["particle_dust", "bracket_slam"]
    elif sig.has_ai_build:
        pool = ["typewriter", "glow_scan"]
    else:
        pool = ["glow_ring", "typewriter", "particle_dust", "bracket_slam", "glow_scan"]
    for e in pool:
        if e not in used:
            return e
    return pool[0]


def _pick_profile(sig: ContentSignals, layout: str, *, used: set[str]) -> tuple[str, str]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for pack in DOUYIN_CONTENT_LAYOUTS:
        score = 0
        prof = str(pack.get("motion_profile") or "")
        if prof in used:
            score -= 3
        if sig.has_star_trend and "glass" in prof:
            score += 3
        if sig.has_compare and prof in ("shake_emphasis", "kinetic_slam_tight"):
            score += 3
        if sig.has_steps and prof in ("bullet_stagger_up", "glass_card_stack"):
            score += 3
        if sig.has_speed and prof in ("kinetic_slam_tight", "tiktok_phrase_pages"):
            score += 2
        if layout == "compare" and prof == "shake_emphasis":
            score += 4
        if layout == "steps" and prof == "bullet_stagger_up":
            score += 4
        if layout == "framed" and "glass" in prof:
            score += 2
        scored.append((score, pack))
    scored.sort(key=lambda x: -x[0])
    pack = scored[0][1] if scored else dict(DOUYIN_CONTENT_LAYOUTS[0])
    return str(pack.get("motion_profile") or "glass_card_stack"), str(pack.get("id") or "")


def _pick_css(sig: ContentSignals, layout: str, profile: str, *, is_first_github: bool) -> list[str]:
    dec: list[str] = []
    if sig.has_star_trend or is_first_github:
        dec.extend(["odometer-stars", "github-badge", "daily-video-tag"])
    if sig.has_compare:
        dec.extend(["text-stroke-yellow", "accent-orange-word"])
    if sig.has_steps:
        dec.append("float-icon")
    if sig.has_speed:
        dec.extend(["sparkle-dots", "marquee-top"])
    if sig.has_privacy_local:
        dec.append("soft-purple-gradient")
    if sig.has_ai_build:
        dec.extend(["accent-orange-word", "cursor-blink"])
    if "glass" in profile:
        dec.append("soft-purple-gradient")
    if layout == "framed":
        dec.append("sparkle-dots")
    if sig.has_number_stat and "odometer-stars" not in dec:
        dec.append("stat-pill-row")
    if not dec:
        dec = ["sparkle-dots"]
    return css_pack(dec)


def _pick_viz(sig: ContentSignals, tts: str, *, stars_raw: str) -> tuple[str, list[float], str, str]:
    if sig.has_star_trend and stars_raw:
        return "stat", [], "", str(stars_raw)[:20]
    if sig.has_compare:
        return "bar", [40.0, 88.0, 72.0, 95.0], "对比", ""
    if sig.has_star_trend:
        return "line", [30.0, 45.0, 62.0, 78.0, 92.0, 100.0], "Star 走势", ""
    if sig.has_number_stat and sig.number_hint:
        return "stat", [], "", sig.number_hint
    return "none", [], "", ""


def design_shot_from_content(
    *,
    tts: str,
    brief: dict[str, Any] | None,
    shot_index: int,
    used_layouts: set[str],
    used_effects: set[str],
    used_profiles: set[str],
    is_first_content: bool = False,
    stars_raw: str = "",
) -> ShotDesign:
    """规则引擎：根据本镜口播语义产出完整视觉方案。"""
    sig = analyze_tts_signals(tts, brief=brief)
    hero, subs = _split_subtitles(tts)
    layout = _pick_layout(sig, used=used_layouts)
    effect = _pick_effect(layout, sig, used=used_effects)
    profile, layout_id = _pick_profile(sig, layout, used=used_profiles)
    css = _pick_css(sig, layout, profile, is_first_github=is_first_content)
    viz, series, chart_label, stat = _pick_viz(sig, tts, stars_raw=stars_raw)

    kin = _kinetic_from_signals(sig, subs)
    icon = ""
    if sig.has_star_trend:
        icon = "⭐"
    elif sig.has_ai_build:
        icon = "🤖"
    elif sig.has_speed:
        icon = "⚡"
    elif sig.has_privacy_local:
        icon = "🔒"
    elif sig.has_steps:
        icon = "🛠️"

    rationale_parts = []
    if sig.has_star_trend:
        rationale_parts.append("口播含 Star/趋势 → 数字滚动+框线副标题")
    if sig.has_compare:
        rationale_parts.append("含对比叙事 → 左右对比版式+冲击动效")
    if sig.has_steps:
        rationale_parts.append("含步骤/流程 → 步骤条版式")
    if sig.has_ai_build:
        rationale_parts.append("含 AI/生成 → 打字机/科技装饰")
    if not rationale_parts:
        rationale_parts.append(f"语义默认 → {layout}+{effect}")

    pack = next((p for p in DOUYIN_CONTENT_LAYOUTS if p.get("id") == layout_id), None)
    stagger = int((pack or {}).get("stagger_frames") or 14)

    return ShotDesign(
        hero_title=hero,
        subtitle_cards=subs[:3],
        mid_info_layout=layout,
        mid_effect=effect,
        motion_profile=profile,
        css_decorations=css,
        viz_type=viz,
        show_chart=viz in ("line", "bar"),
        chart_series=series,
        chart_label=chart_label,
        stat_value=stat,
        kinetic_phrases=kin,
        mid_icon=icon,
        show_kinetic_wall=layout == "compare" or (viz == "none" and len(kin) >= 3),
        stagger_frames=stagger,
        design_rationale="；".join(rationale_parts),
        layout_id=layout_id or "",
    )


def _llm_client():
    from python_agent.config import get_config
    from python_agent.llm_client import create_llm_client

    cfg = get_config()
    if not (cfg.llm_api_key or "").strip():
        return None, None
    return create_llm_client(cfg.llm_api_key, cfg.llm_base_url), cfg.llm_model


_ALLOWED_LAYOUTS = frozenset({"framed", "steps", "compare", "keywords"})
_ALLOWED_EFFECTS = frozenset(
    {"typewriter", "glow_ring", "particle_dust", "bracket_slam", "glow_scan", "none"}
)
_ALLOWED_PROFILES = frozenset(
    {
        "glass_card_stack",
        "bullet_stagger_up",
        "kinetic_slam_tight",
        "shake_emphasis",
        "tiktok_phrase_pages",
        "flash_hook_smash",
    }
)


def _row_to_shot_design(row: dict[str, Any]) -> ShotDesign:
    layout = str(row.get("mid_info_layout") or "framed").lower()
    if layout not in _ALLOWED_LAYOUTS:
        layout = "framed"
    effect = str(row.get("mid_effect") or "glow_ring").lower()
    if effect not in _ALLOWED_EFFECTS:
        effect = "glow_ring"
    profile = str(row.get("motion_profile") or "glass_card_stack")
    if profile not in _ALLOWED_PROFILES:
        profile = "glass_card_stack"
    viz = str(row.get("viz_type") or "none").lower()
    if viz not in ("none", "stat", "line", "bar"):
        viz = "none"
    return ShotDesign(
        hero_title=str(row.get("hero_title") or "")[:14],
        subtitle_cards=[
            str(x)[:12] for x in (row.get("subtitle_cards") or []) if str(x).strip()
        ][:3],
        mid_info_layout=layout,
        mid_effect=effect,
        motion_profile=profile,
        css_decorations=css_pack(list(row.get("css_decorations") or [])),
        viz_type=viz,
        show_chart=viz in ("line", "bar"),
        chart_series=[float(x) for x in (row.get("chart_series") or []) if x][:8],
        chart_label=str(row.get("chart_label") or "")[:20],
        stat_value=str(row.get("stat_value") or "")[:24],
        kinetic_phrases=[str(x)[:10] for x in (row.get("kinetic_phrases") or [])][:5],
        mid_icon=str(row.get("mid_icon") or "")[:4],
        show_kinetic_wall=bool(row.get("show_kinetic_wall")),
        stagger_frames=max(18, int(row.get("stagger_frames") or 18)),
        design_rationale=str(row.get("design_rationale") or "LLM 细设计")[:200],
        layout_id=str(row.get("layout_id") or "")[:32],
    )


def llm_design_all_shots(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
) -> dict[int, ShotDesign]:
    """100% LLM 逐镜细设计；失败抛 DouyinShotDesignError。"""
    client, model = _llm_client()
    if not client:
        raise DouyinShotDesignError(
            "抖音分镜细设计需要 LLM：请配置 llm_api_key / llm_base_url（无规则引擎降级）"
        )

    items = []
    for i, s in enumerate(slides):
        st = str(s.get("type") or "")
        if st not in ("title_card", "content_card", "cta_card") and not s.get("scene_focus"):
            continue
        items.append(
            {
                "i": i,
                "type": st or ("content_card" if s.get("scene_focus") else ""),
                "tts_text": str(s.get("tts_text") or "")[:360],
                "hook_text": str(s.get("hook_text") or "")[:40],
                "heading": s.get("heading"),
            }
        )
    if not items:
        raise DouyinShotDesignError("无可用分镜草稿，无法调用 LLM 细设计")

    brief_compact = {
        k: brief.get(k)
        for k in ("title", "repo_name", "repo_url", "stars", "hook", "feed_kind", "talking_points")
        if brief.get(k)
    }

    prompt = f"""你是抖音/GitHub 日更短视频的「分镜美术导演」。必须对每一镜单独细设计，禁止全片统一模板。

【brief】
{json.dumps(brief_compact, ensure_ascii=False)}

【分镜草稿（含片头/内容/片尾）】
{json.dumps(items, ensure_ascii=False)}

返回 JSON（只返回 JSON）：
{{
  "shots": [
    {{
      "i": 镜序号(与草稿一致),
      "slide_role": "title|content|cta",
      "hero_title": "中部或片头主标题≤14字",
      "subtitle_cards": ["框线副标题6~14字","写能力/结果","勿与主标题同义"],
      "hook_beats": ["仅 title 填 2~3 条屏显爆点≤18字"],
      "mid_info_layout": "framed|steps|compare|keywords",
      "mid_effect": "typewriter|glow_ring|particle_dust|bracket_slam|glow_scan",
      "motion_profile": "flash_hook_smash|glass_card_stack|bullet_stagger_up|kinetic_slam_tight|shake_emphasis|tiktok_phrase_pages",
      "css_decorations": ["2~5个: odometer-stars,text-stroke-yellow,float-icon,sparkle-dots,github-badge,daily-video-tag,accent-orange-word,soft-purple-gradient,stat-pill-row,corner-brackets,pulse-button"],
      "viz_type": "none|stat|line|bar",
      "stat_value": "",
      "chart_series": [],
      "chart_label": "",
      "kinetic_phrases": ["2~4个关键词"],
      "mid_icon": "emoji或空",
      "show_kinetic_wall": false,
      "stagger_frames": 10~18,
      "design_rationale": "≥20字：说明本镜口播语义→为何选此版式/动效/装饰"
    }}
  ]
}}

【铁律】
1. 每个 content 镜 design_rationale 必须不同，且引用该镜口播里的具体词（Star/对比/步骤/本地/AI 等）。
2. 三镜 content 的 mid_info_layout 必须两两不同。
3. 片头 title：必须含 repo_name，hook_beats 2~3 条；口播风格「每日一个GitHub项目/项目推荐」；decor 含 github-badge + corner-brackets 或 daily-video-tag。
4. 讲 Star/热度 → 该镜 css 含 odometer-stars，viz stat 或 line；讲对比 → compare + shake_emphasis；讲步骤 → steps + glow_scan。
5. subtitle_cards 是「主标题下方的框线子标题」：每条 6~14 字，写能力/结果/场景；不得与 hero_title 同义重复；不得与底栏口播逐字相同。
6. hero_title 禁止空洞词「核心亮点」「核心能力」；必须根据该镜口播提炼，如「自然语言生成」「本机更安全」「办公自动化」。
7. 禁止三镜 content 的 motion_profile 与 mid_info_layout 两两完全相同。
8. 禁止三镜都用 glass_card_stack + framed 完全相同组合。
9. Star 数字全片只用 brief.stars 一个值，勿自创 1.3万/12k 等不一致写法。
10. stagger_frames 建议 16~20。"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.55,
            max_tokens=4096,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        raise DouyinShotDesignError(f"LLM 分镜细设计请求失败: {exc}") from exc

    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise DouyinShotDesignError(f"LLM 未返回 JSON 分镜方案: {raw[:200]}")
    try:
        rows = json.loads(m.group(0)).get("shots") or []
    except json.JSONDecodeError as exc:
        raise DouyinShotDesignError(f"LLM 分镜 JSON 解析失败: {exc}") from exc

    out: dict[int, ShotDesign] = {}
    for row in rows:
        try:
            i = int(row.get("i", -1))
        except (TypeError, ValueError):
            continue
        if i < 0:
            continue
        out[i] = _row_to_shot_design(row)

    if not out:
        raise DouyinShotDesignError("LLM 返回空 shots 列表")

    return out


# 兼容旧名
llm_design_content_shots = llm_design_all_shots


def apply_shot_design_to_slide(
    slide: dict[str, Any],
    design: ShotDesign,
    *,
    preserve_llm_copy: bool,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from python_agent.douyin_shot_stylist import resolve_content_hero_title
    from python_agent.subtitle_copy import (
        normalize_shot_design_copy,
        normalize_slide_mid_copy,
        normalize_subtitle_cards,
    )

    design = normalize_shot_design_copy(design)
    s = copy.deepcopy(slide)
    tts = str(s.get("tts_text") or "")
    hero_src = resolve_content_hero_title(s, brief, design_hero=design.hero_title)
    if not preserve_llm_copy or not s.get("summary_lines"):
        h, subs = normalize_subtitle_cards(hero_src, list(design.subtitle_cards), tts=tts)
        s["feature_label"] = h
        s["heading"] = h
        s["summary_lines"] = subs
    else:
        h, subs = normalize_subtitle_cards(
            hero_src,
            list(s.get("summary_lines") or []),
            tts=tts,
        )
        s["feature_label"] = h
        s["heading"] = h
        s["summary_lines"] = subs

    s["mid_info_layout"] = design.mid_info_layout
    s["mid_effect"] = design.mid_effect
    s["motion_profile"] = design.motion_profile
    s["css_decorations"] = list(design.css_decorations)
    s["viz_type"] = design.viz_type
    s["show_chart"] = design.show_chart
    s["chart_series"] = design.chart_series
    s["chart_bars"] = list(design.chart_series)
    s["chart_label"] = design.chart_label
    s["stat_value"] = design.stat_value
    s["kinetic_phrases"] = design.kinetic_phrases
    s["mid_icon"] = design.mid_icon
    s["show_kinetic_wall"] = design.show_kinetic_wall
    s["shot_design"] = design.to_dict()
    s["shot_design_source"] = "llm_shot_designer"

    mp = dict(s.get("motion_params") or {})
    mp["staggerFrames"] = design.stagger_frames
    mp.setdefault("captionLetterSpacing", 0)
    s["motion_params"] = mp

    vd = dict(s.get("visual_design") or {})
    vd["broadcast_frame"] = False
    vd["motion_profile"] = design.motion_profile
    s["visual_design"] = vd
    return normalize_slide_mid_copy(s)


def build_content_shot_plans(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None,
    **_: Any,
) -> dict[int, ShotDesign]:
    """100% LLM 细设计；无 key / 调用失败即抛错。"""
    b = dict(brief or {})
    all_plans = llm_design_all_shots(slides, b)

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

    layouts = {all_plans[i].mid_info_layout for i in content_idxs if i in all_plans}
    profiles = {all_plans[i].motion_profile for i in content_idxs if i in all_plans}
    if len(content_idxs) >= 2 and len(layouts) < 2:
        raise DouyinShotDesignError(
            f"LLM 分镜版式缺乏差异: layouts={layouts}，请重试"
        )
    if len(content_idxs) >= 2 and len(profiles) < 2:
        raise DouyinShotDesignError(
            f"LLM 分镜动效缺乏差异: profiles={profiles}，请重试"
        )

    return {i: all_plans[i] for i in content_idxs}


def build_all_shot_plans(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None,
) -> dict[int, ShotDesign]:
    """片头+内容+片尾 全镜 LLM 方案。"""
    return llm_design_all_shots(slides, dict(brief or {}))
