"""大循环评审上下文：每轮有明确排型目标，角色只对「未达标项」提意见并修改。"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from python_agent.douyin_layout_registry import (
    CTA_LAYOUT,
    DOUYIN_CONTENT_LAYOUTS,
    TITLE_LAYOUT,
    css_pack,
    layout_assignment_table,
    layout_for_content_index,
)
from python_agent.display_text import find_unsafe_caption_splits
from python_agent.platform_caption_presets import reconcile_platform_slides
from python_agent.slides_quality_gates import auto_fix_slides
from python_agent.tts_copy_rules import (
    tts_has_meta_filler,
    validate_slides_tts_copy,
)

SlideList = list[dict[str, Any]]
IssueList = list[str]


@dataclass(frozen=True)
class CycleReviewContext:
    cycle: int
    content_layout_ids: tuple[str, str, str]
    target_stagger: int
    target_max_chars: int
    target_caption_bottom: int
    target_opening_frames: int


def cycle_context(cycle: int) -> CycleReviewContext:
    """每轮轮换 3 种内容排型 + 递进参数，保证后续轮次有真实评审点。"""
    c = max(1, cycle)
    base = (c - 1) * 3
    ids = tuple(
        DOUYIN_CONTENT_LAYOUTS[(base + i) % len(DOUYIN_CONTENT_LAYOUTS)]["id"]
        for i in range(3)
    )
    return CycleReviewContext(
        cycle=c,
        content_layout_ids=ids,
        target_stagger=max(10, 16 - (c - 1)),
        target_max_chars=24,
        target_caption_bottom=min(380, 300 + (c - 1) * 4),
        target_opening_frames=165,
    )


def slides_digest(slides: SlideList) -> str:
    payload = json.dumps(slides, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _content(slides: SlideList) -> list[tuple[int, dict]]:
    return [
        (i, s)
        for i, s in enumerate(slides)
        if str(s.get("type")) == "content_card" or s.get("scene_focus")
    ]


def _layout_by_id(lid: str) -> dict[str, Any]:
    for x in DOUYIN_CONTENT_LAYOUTS:
        if x["id"] == lid:
            return dict(x)
    return dict(DOUYIN_CONTENT_LAYOUTS[0])


# --- 十角色检查（均依赖 CycleReviewContext）---


def check_douyin_ops(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    s0 = slides[0] if slides else {}
    if str(s0.get("type")) != "title_card":
        issues.append("missing_title_card")
        return issues
    frames = int(s0.get("opening_duration_frames") or 0)
    if frames < ctx.target_opening_frames:
        issues.append(f"opening_frames_low:{frames}<{ctx.target_opening_frames}")
    tts = str(s0.get("tts_text") or "")
    if tts.count("。") + tts.count("！") > 1:
        issues.append("title_tts_multi_sentence")
    if "绝对不知道" in tts or "你绝对" in tts:
        issues.append("title_tts_clickbait_banned")
    if not str(s0.get("hook_text") or "").strip():
        issues.append("missing_hook_text")
    return issues


def check_line_director(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    corner_n = 0
    line_decor = frozenset({"corner-brackets", "glass-card", "scan-lines", "grid-tunnel-bg"})
    for i, s in enumerate(slides):
        dec = set(s.get("css_decorations") or [])
        if "corner-brackets" in dec:
            corner_n += 1
        if len(dec & line_decor) > 1:
            issues.append(f"slide_{i}:line_decor_stack={sorted(dec & line_decor)}")
        if "corner-brackets" in dec and dec & {"glass-card", "scan-lines", "grid-tunnel-bg"}:
            issues.append(f"slide_{i}:corner_with_mid_lines")
        if str(s.get("type")) == "content_card" and (s.get("visual_design") or {}).get(
            "broadcast_frame"
        ):
            issues.append(f"slide_{i}:content_broadcast_frame")
    if corner_n > 1:
        issues.append(f"corner_on_{corner_n}_slides_need_only_title")
    return issues


def check_layout_architect(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    content = _content(slides)
    for n, (i, s) in enumerate(content):
        expected = ctx.content_layout_ids[n] if n < len(ctx.content_layout_ids) else ""
        pack = _layout_by_id(expected) if expected else {}
        prof = str(s.get("motion_profile") or "")
        if expected and prof != pack.get("motion_profile"):
            issues.append(f"slide_{i}:profile_want_{pack.get('motion_profile')}_got_{prof}")
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if len(lines) < 2:
            issues.append(f"slide_{i}:summary_lines_lt_2")
        head = str(s.get("feature_label") or s.get("heading") or "").strip()
        if head and lines and head == lines[0]:
            issues.append(f"slide_{i}:heading_equals_card1")
        mp = s.get("motion_params") or {}
        if int(mp.get("staggerFrames") or 99) != ctx.target_stagger:
            issues.append(
                f"slide_{i}:stagger_want_{ctx.target_stagger}_got_{mp.get('staggerFrames')}"
            )
    if len(content) >= 2:
        profs = {str(s.get("motion_profile") or "") for _, s in content}
        if len(profs) < 2:
            issues.append("content_profiles_need_diversity")
    return issues


def check_caption_advisor(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(slides):
        mp = s.get("motion_params") or {}
        mc = int(mp.get("maxCharsPerPage") or 20)
        if mc != ctx.target_max_chars:
            issues.append(f"slide_{i}:max_chars_want_{ctx.target_max_chars}_got_{mc}")
        ls = int(mp.get("captionLetterSpacing") or 0)
        if ls > 1:
            issues.append(f"slide_{i}:caption_letter_spacing_wide:{ls}")
        for iss in find_unsafe_caption_splits(
            [str(s.get("tts_text") or "")]
        ):
            issues.append(f"slide_{i}:{iss}")
    return issues


def check_motion_director(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    actual = []
    for i, s in _content(slides):
        dec = set(s.get("css_decorations") or [])
        actual.append(
            {
                "slide": i,
                "profile": str(s.get("motion_profile") or ""),
                "decor": sorted(dec),
            }
        )
    for n, lid in enumerate(ctx.content_layout_ids):
        pack = _layout_by_id(lid)
        row = actual[n] if n < len(actual) else {}
        if row and row["profile"] != pack.get("motion_profile"):
            issues.append(
                f"cycle{ctx.cycle}_content{n}:need_profile_{pack.get('motion_profile')}"
            )
        want_css = set(pack.get("css") or [])
        if row and want_css - set(row.get("decor") or []):
            issues.append(f"cycle{ctx.cycle}_content{n}:missing_decor={sorted(want_css - set(row.get('decor') or []))}")
    return issues


def check_visual_designer(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(slides):
        if str(s.get("type")) != "content_card":
            continue
        mp = s.get("motion_params") or {}
        bottom = int(mp.get("captionBottomPx") or 0)
        if bottom < ctx.target_caption_bottom:
            issues.append(
                f"slide_{i}:caption_bottom_want_{ctx.target_caption_bottom}_got_{bottom}"
            )
        ratio = float(mp.get("midSafeBottomRatio") or 0)
        if ratio < 0.36:
            issues.append(f"slide_{i}:mid_safe_bottom_low:{ratio}")
    return issues


def check_voice_director(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    issues.extend(validate_slides_tts_copy(slides))
    banned = ("MIT", "部署", "评论区", "安装依赖", "克隆仓库")
    for i, s in enumerate(slides):
        tts = str(s.get("tts_text") or "")
        if tts_has_meta_filler(tts):
            issues.append(f"slide_{i}:meta_filler_tts")
        for w in banned:
            if w in tts:
                issues.append(f"slide_{i}:banned_word_{w}")
    title = next((s for s in slides if str(s.get("type")) == "title_card"), None)
    if title:
        repo = str(title.get("repo_name") or title.get("heading") or "").strip()
        tts0 = str(title.get("tts_text") or "")
        if repo and len(repo) >= 2 and repo not in tts0:
            issues.append("opening_missing_repo_name")
        if not any(
            x in tts0
            for x in ("GitHub", "github", "开源", "每日", "项目推荐", "今天介绍")
        ):
            issues.append("opening_not_github_series_style")
    layouts = {
        str(s.get("mid_info_layout") or "")
        for s in slides
        if str(s.get("type")) == "content_card" or s.get("scene_focus")
    }
    if len(layouts) < 2:
        issues.append("content_mid_layout_not_diverse")
    return issues


def check_product_manager(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(slides):
        if str(s.get("caption_mode") or "") != "tiktok" and str(s.get("type")) != "cta_card":
            issues.append(f"slide_{i}:caption_mode_not_tiktok")
        if str(s.get("platform") or "") not in ("", "douyin"):
            issues.append(f"slide_{i}:platform_not_douyin")
    return issues


def check_brand_designer(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    title = next((s for s in slides if str(s.get("type")) == "title_card"), None)
    if title and "corner-brackets" not in (title.get("css_decorations") or []):
        issues.append("title_missing_corner_brackets")
    for i, s in _content(slides):
        if "corner-brackets" in (s.get("css_decorations") or []):
            issues.append(f"slide_{i}:content_has_corner_brackets")
    cta = next((s for s in slides if str(s.get("type")) == "cta_card"), None)
    if cta and "pulse-button" not in (cta.get("css_decorations") or []):
        issues.append("cta_missing_pulse_button")
    return issues


def check_qa_director(slides: SlideList, ctx: CycleReviewContext) -> IssueList:
    issues: IssueList = []
    for fn in (
        check_line_director,
        check_layout_architect,
        check_caption_advisor,
        check_voice_director,
    ):
        issues.extend(fn(slides, ctx))
    return issues


# --- 按意见修改（无 issue 则不改）---


def fix_douyin_ops(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = copy.deepcopy(slides)
    applied: list[str] = []
    for s in out:
        if str(s.get("type")) == "title_card":
            s["opening_duration_frames"] = ctx.target_opening_frames
            applied.append(f"opening_duration={ctx.target_opening_frames}")
            if not s.get("hook_beats"):
                s["hook_beats"] = [str(s.get("hook_text") or s.get("heading") or "")[:18]]
                applied.append("hook_beats")
    return out, applied


def fix_line_director(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = copy.deepcopy(slides)
    applied: list[str] = []
    clash = frozenset({"glass-card", "scan-lines", "grid-tunnel-bg"})
    for i, s in enumerate(out):
        dec = list(s.get("css_decorations") or [])
        st = str(s.get("type") or "")
        if st == "title_card" and "corner-brackets" not in dec:
            continue
        if st == "content_card" or s.get("scene_focus"):
            dec = [d for d in dec if d != "corner-brackets"]
            vd = dict(s.get("visual_design") or {})
            vd["broadcast_frame"] = False
            s["visual_design"] = vd
        if "corner-brackets" in dec:
            dec = [d for d in dec if d not in clash]
        s["css_decorations"] = dec
        applied.append(f"slide_{i}:line_cleanup")
    return out, applied


def fix_layout_architect(
    slides: SlideList, issues: IssueList, ctx: CycleReviewContext
) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    return apply_cycle_layout_plan(slides, ctx)


def fix_caption_advisor(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = copy.deepcopy(slides)
    applied: list[str] = []
    for s in out:
        mp = dict(s.get("motion_params") or {})
        mp["maxCharsPerPage"] = ctx.target_max_chars
        mp["captionLetterSpacing"] = 0
        if str(s.get("type")) == "content_card":
            mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 0), ctx.target_caption_bottom)
        s["motion_params"] = mp
        s["caption_use_tts_timeline"] = True
        s["caption_mode"] = "tiktok"
        applied.append(f"maxChars={ctx.target_max_chars}")
    return out, applied


def fix_motion_director(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    return apply_cycle_layout_plan(slides, ctx)


def fix_visual_designer(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = copy.deepcopy(slides)
    applied: list[str] = []
    for s in out:
        mp = dict(s.get("motion_params") or {})
        mp["midSafeBottomRatio"] = max(float(mp.get("midSafeBottomRatio") or 0), 0.38)
        if str(s.get("type")) == "content_card":
            mp["captionBottomPx"] = ctx.target_caption_bottom
        s["motion_params"] = mp
        applied.append("caption_safe_lift")
    return out, applied


def fix_voice_director(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    from python_agent.douyin_shot_stylist import apply_douyin_shot_styles, github_daily_opening_hook
    from python_agent.tts_copy_rules import strip_meta_filler_clauses

    out = copy.deepcopy(slides)
    applied: list[str] = []
    for s in out:
        tts = str(s.get("tts_text") or "")
        cleaned = strip_meta_filler_clauses(tts)
        if cleaned != tts:
            s["tts_text"] = cleaned
            applied.append("strip_meta_filler")
    if any("opening_" in x for x in issues):
        title = next((s for s in out if str(s.get("type")) == "title_card"), None)
        if title:
            repo = str(title.get("repo_name") or title.get("heading") or "").strip()
            hook = github_daily_opening_hook(
                repo_name=repo,
                title=repo,
                hook=str(title.get("hook_text") or ""),
                stars=str(title.get("stars") or ""),
            )
            title["hook_text"] = hook[:22]
            core = hook.rstrip("。！？?!")
            if repo and repo not in core:
                core = f"每日一个GitHub项目，{repo}，{core}"
            title["tts_text"] = (core + "？") if not core.endswith(("？", "?", "！")) else core + "！"
            applied.append("github_opening_hook")
    if "content_mid_layout_not_diverse" in issues:
        brief_guess = {}
        if title:
            brief_guess["repo_name"] = title.get("repo_name") or title.get("heading")
            brief_guess["stars"] = title.get("stars")
            brief_guess["star_count"] = title.get("star_count")
        out = apply_douyin_shot_styles(out, brief_guess or None)
        applied.append("reshuffle_mid_layouts")
    return out, applied


def fix_product_manager(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = reconcile_platform_slides(copy.deepcopy(slides), "douyin")
    return out, ["reconcile_platform_slides"]


def fix_brand_designer(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = copy.deepcopy(slides)
    applied: list[str] = []
    for s in out:
        st = str(s.get("type") or "")
        if st == "title_card":
            dec = list(s.get("css_decorations") or [])
            for d in TITLE_LAYOUT["css"]:
                if d not in dec:
                    dec.append(d)
            s["css_decorations"] = css_pack(dec)
            applied.append("title_brand")
        elif st == "content_card" or s.get("scene_focus"):
            s["css_decorations"] = [d for d in (s.get("css_decorations") or []) if d != "corner-brackets"]
        elif st == "cta_card":
            s["css_decorations"] = list(CTA_LAYOUT["css"])
            applied.append("cta_brand")
    return out, applied


def fix_qa_director(slides: SlideList, issues: IssueList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    if not issues:
        return slides, []
    out = auto_fix_slides(copy.deepcopy(slides), platform="douyin")
    out = reconcile_platform_slides(out, "douyin")
    return out, ["auto_fix", "reconcile"]


def apply_cycle_layout_plan(slides: SlideList, ctx: CycleReviewContext) -> tuple[SlideList, list[str]]:
    out = copy.deepcopy(slides)
    applied: list[str] = []
    ci = 0
    for i, s in enumerate(out):
        st = str(s.get("type") or "")
        if st not in ("content_card",) and not s.get("scene_focus"):
            continue
        lid = ctx.content_layout_ids[ci] if ci < len(ctx.content_layout_ids) else ""
        pack = _layout_by_id(lid)
        ci += 1
        mp = dict(s.get("motion_params") or {})
        mp["staggerFrames"] = ctx.target_stagger
        mp["maxCharsPerPage"] = ctx.target_max_chars
        mp["captionLetterSpacing"] = 0
        mp["captionBottomPx"] = ctx.target_caption_bottom
        s["motion_params"] = mp
        applied.append(f"slide_{i}:{pack['id']}")
    brief_guess: dict[str, Any] = {}
    title = next((x for x in out if str(x.get("type")) == "title_card"), None)
    if title:
        brief_guess["repo_name"] = title.get("repo_name") or title.get("heading")
        brief_guess["stars"] = title.get("stars")
        brief_guess["star_count"] = title.get("star_count")
        brief_guess["repo_url"] = title.get("repo_url")
    from python_agent.douyin_shot_stylist import apply_douyin_shot_styles

    out = apply_douyin_shot_styles(out, brief_guess or None)
    applied.append("douyin_shot_styles")
    return out, applied


ROLE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "round": 1,
        "role": "抖音运营",
        "layout_tier": "L00_title_hook",
        "prompt": "片头：opening≥目标帧、单句口播、禁「你绝对不知道」、hook 必填。",
        "check": check_douyin_ops,
        "fix": fix_douyin_ops,
    },
    {
        "round": 2,
        "role": "线条导演",
        "layout_tier": "线条克制",
        "prompt": "仅片头可有 corner；内容镜无播报横线；线条装饰不叠两层。",
        "check": check_line_director,
        "fix": fix_line_director,
    },
    {
        "round": 3,
        "role": "版式架构师",
        "layout_tier": "本轮排型目标",
        "prompt": "三镜内容必须匹配本轮 Lxx 排型表；竖卡≥2条；stagger 精确达标。",
        "check": check_layout_architect,
        "fix": fix_layout_architect,
    },
    {
        "round": 4,
        "role": "字幕顾问",
        "layout_tier": "底栏语义",
        "prompt": f"maxCharsPerPage 必须等于本轮目标；口播无拆词风险。",
        "check": check_caption_advisor,
        "fix": fix_caption_advisor,
    },
    {
        "round": 5,
        "role": "动效导演",
        "layout_tier": "profile+装饰",
        "prompt": "每镜 profile/css 与本轮排型包一致，不得沿用上一轮。",
        "check": check_motion_director,
        "fix": fix_motion_director,
    },
    {
        "round": 6,
        "role": "视觉设计",
        "layout_tier": "层级留白",
        "prompt": "内容镜 captionBottom 达本轮目标；中区不被底栏压扁。",
        "check": check_visual_designer,
        "fix": fix_visual_designer,
    },
    {
        "round": 7,
        "role": "配音导演",
        "layout_tier": "价值口播",
        "prompt": "无 MIT/部署/评论区；讲清产品场景价值。",
        "check": check_voice_director,
        "fix": fix_voice_director,
    },
    {
        "round": 8,
        "role": "产品经理",
        "layout_tier": "抖音专属",
        "prompt": "caption_mode=tiktok；platform=douyin。",
        "check": check_product_manager,
        "fix": fix_product_manager,
    },
    {
        "round": 9,
        "role": "品牌设计",
        "layout_tier": "片头角标",
        "prompt": "片头 corner+光点；内容无角标；CTA 有 pulse-button。",
        "check": check_brand_designer,
        "fix": fix_brand_designer,
    },
    {
        "round": 10,
        "role": "QA总监",
        "layout_tier": "终检",
        "prompt": "复核线条/版式/字幕/口播四项硬指标。",
        "check": check_qa_director,
        "fix": fix_qa_director,
    },
)


def run_role_review_rounds(
    slides: SlideList, ctx: CycleReviewContext
) -> tuple[SlideList, list[dict[str, Any]], list[str]]:
    """十角色：有 issue 才 fix；返回轮次日志与全部修改前意见。"""
    current = copy.deepcopy(slides)
    logs: list[dict[str, Any]] = []
    all_pre: list[str] = []

    for spec in ROLE_SPECS:
        check_fn: Callable[..., IssueList] = spec["check"]
        fix_fn = spec["fix"]
        issues = check_fn(current, ctx)
        all_pre.extend([f"{spec['role']}:{x}" for x in issues])
        applied: list[str] = []
        if issues:
            current, applied = fix_fn(current, issues, ctx)
        logs.append(
            {
                "round": spec["round"],
                "role": spec["role"],
                "layout_tier": spec["layout_tier"],
                "prompt": spec["prompt"],
                "cycle": ctx.cycle,
                "expected_layouts": list(ctx.content_layout_ids),
                "issues_before": issues,
                "fixes_applied": applied,
                "issues_after": check_fn(current, ctx),
                "ok_after": not check_fn(current, ctx),
                "had_real_opinion": bool(issues),
            }
        )

    return current, logs, all_pre
