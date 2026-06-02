"""十角色 × 十轮：评审提示 + 启发式检查 + 分镜修补。"""
from __future__ import annotations

import copy
import re
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
from python_agent.tts_copy_rules import tts_has_meta_filler, validate_slides_tts_copy

SlideList = list[dict[str, Any]]
IssueList = list[str]
CheckFn = Callable[[SlideList], IssueList]
FixFn = Callable[[SlideList, IssueList], tuple[SlideList, list[str]]]


def _content(slides: SlideList) -> SlideList:
    return [s for s in slides if str(s.get("type")) == "content_card" or s.get("scene_focus")]


def _line_decor_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    corner_n = 0
    line_decor = frozenset({"corner-brackets", "glass-card", "scan-lines"})
    for i, s in enumerate(slides):
        dec = set(s.get("css_decorations") or [])
        if "corner-brackets" in dec:
            corner_n += 1
        hits = dec & line_decor
        if len(hits) > 1:
            issues.append(f"slide_{i}:too_many_line_decor={sorted(hits)}")
        if "corner-brackets" in dec and dec & {"glass-card", "scan-lines"}:
            issues.append(f"slide_{i}:corner_clash")
        st = str(s.get("type") or "")
        if st == "content_card" and (s.get("visual_design") or {}).get("broadcast_frame"):
            issues.append(f"slide_{i}:content_broadcast_frame")
    if corner_n > 1:
        issues.append(f"too_many_corner_slides={corner_n}")
    return issues


def _hook_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    if not slides:
        return ["no_slides"]
    s0 = slides[0]
    if str(s0.get("type")) != "title_card":
        issues.append("missing_title_card")
        return issues
    frames = int(s0.get("opening_duration_frames") or 0)
    if frames < 150:
        issues.append(f"opening_too_fast:{frames}f")
    tts = str(s0.get("tts_text") or "")
    if tts.count("。") + tts.count("！") > 1:
        issues.append("title_tts_multi_sentence")
    if not str(s0.get("hook_text") or "").strip():
        issues.append("missing_hook_text")
    return issues


def _cards_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(_content(slides)):
        head = str(s.get("feature_label") or s.get("heading") or "").strip()
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if len(lines) < 2:
            issues.append(f"content_{i}:summary_lines<2")
        if head and lines and head == lines[0]:
            issues.append(f"content_{i}:heading_equals_card1")
        mp = s.get("motion_params") or {}
        if int(mp.get("staggerFrames") or 99) > 16:
            issues.append(f"content_{i}:stagger_too_slow")
    return issues


def _caption_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(slides):
        tts = str(s.get("tts_text") or "")
        parts = re.split(r"[。！？]", tts)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            issues.extend(f"slide_{i}:{x}" for x in find_unsafe_caption_splits([p]))
        mp = s.get("motion_params") or {}
        if int(mp.get("captionLetterSpacing") or 0) > 1:
            issues.append(f"slide_{i}:caption_letter_spacing_wide")
        if int(mp.get("maxCharsPerPage") or 20) < 18:
            issues.append(f"slide_{i}:caption_chars_too_few")
    return issues


def _profile_issues(slides: SlideList) -> IssueList:
    content = _content(slides)
    prof = {str(s.get("motion_profile") or "") for s in content}
    issues: IssueList = []
    if len(content) >= 2 and len(prof) < 2:
        issues.append("content_profiles_not_diverse")
    assigned = {layout_for_content_index(i)["motion_profile"] for i in range(len(content))}
    if len(content) >= 3 and len(assigned & prof) < 2:
        issues.append("layout_profile_mismatch")
    return issues


def _hierarchy_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(_content(slides)):
        mp = s.get("motion_params") or {}
        bottom = int(mp.get("captionBottomPx") or 0)
        if bottom and bottom < 300:
            issues.append(f"slide_{i}:caption_bottom_too_low:{bottom}")
    return issues


def _tts_issues(slides: SlideList) -> IssueList:
    issues = list(validate_slides_tts_copy(slides))
    for i, s in enumerate(slides):
        if tts_has_meta_filler(str(s.get("tts_text") or "")):
            issues.append(f"slide_{i}:meta_filler_tts")
    return issues


def _platform_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    for i, s in enumerate(slides):
        if str(s.get("caption_mode") or "") != "tiktok" and str(s.get("type")) != "cta_card":
            issues.append(f"slide_{i}:not_tiktok_caption")
        if str(s.get("caption_platform") or "") not in ("", "douyin"):
            issues.append(f"slide_{i}:caption_platform_not_douyin")
    return issues


def _brand_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    title = next((s for s in slides if str(s.get("type")) == "title_card"), None)
    if title and "corner-brackets" not in (title.get("css_decorations") or []):
        issues.append("title_missing_corner_brand")
    for i, s in enumerate(_content(slides)):
        if "corner-brackets" in (s.get("css_decorations") or []):
            issues.append(f"slide_{i}:content_should_not_have_corner")
    return issues


def _qa_issues(slides: SlideList) -> IssueList:
    issues: IssueList = []
    issues.extend(_line_decor_issues(slides))
    issues.extend(_hook_issues(slides))
    issues.extend(_cards_issues(slides))
    issues.extend(_tts_issues(slides))
    return issues


def _fix_hook(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = copy.deepcopy(slides)
    for s in out:
        if str(s.get("type")) == "title_card":
            if int(s.get("opening_duration_frames") or 0) < 150:
                s["opening_duration_frames"] = 165
                applied.append("title_opening_duration=165")
            if not s.get("hook_beats"):
                hook = str(s.get("hook_text") or s.get("heading") or "别划走")[:18]
                s["hook_beats"] = [hook]
                applied.append("title_hook_beats")
    return out, applied


def _fix_lines(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = copy.deepcopy(slides)
    clash = frozenset({"glass-card", "scan-lines", "grid-tunnel-bg"})
    for i, s in enumerate(out):
        dec = list(s.get("css_decorations") or [])
        if "corner-brackets" in dec:
            dec = [d for d in dec if d not in clash]
            s["css_decorations"] = dec
            applied.append(f"slide_{i}:strip_line_clash_with_corner")
        st = str(s.get("type") or "")
        if st == "content_card":
            vd = dict(s.get("visual_design") or {})
            if vd.get("broadcast_frame"):
                vd["broadcast_frame"] = False
                s["visual_design"] = vd
                applied.append(f"slide_{i}:broadcast_frame_off")
    return out, applied


def _fix_cards(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = copy.deepcopy(slides)
    ci = 0
    for s in out:
        if not (str(s.get("type")) == "content_card" or s.get("scene_focus")):
            continue
        pack = layout_for_content_index(ci)
        ci += 1
        applied.append(f"content_{ci}:{pack['id']}")
    brief_guess: dict[str, Any] = {}
    title = next((x for x in out if str(x.get("type")) == "title_card"), None)
    if title:
        brief_guess["repo_name"] = title.get("repo_name") or title.get("heading")
        brief_guess["stars"] = title.get("stars")
        brief_guess["star_count"] = title.get("star_count")
    from python_agent.douyin_shot_stylist import apply_douyin_shot_styles

    out = apply_douyin_shot_styles(out, brief_guess or None)
    applied.append("douyin_shot_styles")
    return out, applied


def _fix_caption(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = copy.deepcopy(slides)
    for s in out:
        mp = dict(s.get("motion_params") or {})
        if int(mp.get("captionLetterSpacing") or 0) > 0:
            mp["captionLetterSpacing"] = 0
            applied.append("captionLetterSpacing=0")
        if int(mp.get("maxCharsPerPage") or 20) < 20:
            mp["maxCharsPerPage"] = 20
            applied.append("maxCharsPerPage=20")
        if str(s.get("type")) == "content_card" and int(mp.get("captionBottomPx") or 0) < 320:
            mp["captionBottomPx"] = 340
            applied.append("captionBottomPx=340")
        s["motion_params"] = mp
        s["caption_use_tts_timeline"] = True
        s["caption_mode"] = "tiktok"
    return out, applied


def _fix_profiles(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    return _fix_cards(slides, issues)


def _fix_hierarchy(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = copy.deepcopy(slides)
    for s in out:
        mp = dict(s.get("motion_params") or {})
        mp.setdefault("midSafeBottomRatio", 0.38)
        mp.setdefault("midHeroFontScale", 0.88)
        if str(s.get("type")) == "content_card":
            mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 0), 340)
        s["motion_params"] = mp
    applied.append("mid_safe_and_caption_lift")
    return out, applied


def _fix_tts(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    from python_agent.tts_copy_rules import strip_meta_filler_clauses

    applied: list[str] = []
    out = copy.deepcopy(slides)
    for s in out:
        tts = str(s.get("tts_text") or "")
        cleaned = strip_meta_filler_clauses(tts)
        if cleaned != tts:
            s["tts_text"] = cleaned
            applied.append("strip_meta_filler")
    return out, applied


def _fix_platform(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = reconcile_platform_slides(copy.deepcopy(slides), "douyin")
    applied.append("reconcile_platform_slides")
    return out, applied


def _fix_brand(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    applied: list[str] = []
    out = copy.deepcopy(slides)
    for s in out:
        st = str(s.get("type") or "")
        if st == "title_card":
            dec = list(s.get("css_decorations") or [])
            for d in TITLE_LAYOUT["css"]:
                if d not in dec:
                    dec.append(d)
            s["css_decorations"] = css_pack(dec)
            applied.append("title_brand_decor")
        elif st == "content_card" or s.get("scene_focus"):
            dec = [d for d in (s.get("css_decorations") or []) if d != "corner-brackets"]
            if "sparkle-dots" not in dec:
                dec.append("sparkle-dots")
            s["css_decorations"] = dec
        elif st == "cta_card":
            s["css_decorations"] = list(CTA_LAYOUT["css"])
            applied.append("cta_layout")
    return out, applied


def _fix_qa(slides: SlideList, issues: IssueList) -> tuple[SlideList, list[str]]:
    out = auto_fix_slides(copy.deepcopy(slides), platform="douyin")
    out = reconcile_platform_slides(out, "douyin")
    return out, ["auto_fix_slides", "reconcile_platform_slides"]


AGENT_ROUNDS: tuple[dict[str, Any], ...] = (
    {
        "round": 1,
        "role": "抖音运营",
        "layout_tier": "L00_title_hook",
        "prompt": "前3秒必须有清晰卖点大字与单句口播，禁止空场和「你绝对不知道」类空话。",
        "check": _hook_issues,
        "fix": _fix_hook,
    },
    {
        "round": 2,
        "role": "线条导演",
        "layout_tier": "线条克制",
        "prompt": "画面只保留一层边框感；corner 不与 glass/scan/grid 叠用；内容镜不要播报横线。",
        "check": _line_decor_issues,
        "fix": _fix_lines,
    },
    {
        "round": 3,
        "role": "版式架构师",
        "layout_tier": "L01–L10 排型",
        "prompt": "大标题居中 + 至少两条竖排副标题卡；按十种排型分配 motion_profile 与装饰。",
        "check": _cards_issues,
        "fix": _fix_cards,
    },
    {
        "round": 4,
        "role": "字幕顾问",
        "layout_tier": "底栏语义行",
        "prompt": "底栏按语义断行，禁止「在本机完/成」拆词；每页字数≤15。",
        "check": _caption_issues,
        "fix": _fix_caption,
    },
    {
        "round": 5,
        "role": "动效导演",
        "layout_tier": "profile 多样",
        "prompt": "内容镜至少两种动效 profile，与排型表一致，禁止全片同一动效。",
        "check": _profile_issues,
        "fix": _fix_profiles,
    },
    {
        "round": 6,
        "role": "视觉设计",
        "layout_tier": "层级留白",
        "prompt": "中区主标题+卡片为视觉中心，底栏字幕不压过主标题安全区。",
        "check": _hierarchy_issues,
        "fix": _fix_hierarchy,
    },
    {
        "round": 7,
        "role": "配音导演",
        "layout_tier": "价值口播",
        "prompt": "口播讲产品价值与场景，去掉协议/部署/评论区套话。",
        "check": _tts_issues,
        "fix": _fix_tts,
    },
    {
        "round": 8,
        "role": "产品经理",
        "layout_tier": "抖音专属",
        "prompt": "caption_mode=tiktok、暖色竖卡、与小红书方案可区分。",
        "check": _platform_issues,
        "fix": _fix_platform,
    },
    {
        "round": 9,
        "role": "品牌设计",
        "layout_tier": "片头角标",
        "prompt": "品牌感靠片头对角激光+光点；内容镜不放四角线框。",
        "check": _brand_issues,
        "fix": _fix_brand,
    },
    {
        "round": 10,
        "role": "QA总监",
        "layout_tier": "终检合流",
        "prompt": "汇总前十轮意见，跑 auto_fix + reconcile，确保可渲染。",
        "check": _qa_issues,
        "fix": _fix_qa,
    },
)


def run_ten_rounds(slides: SlideList) -> dict[str, Any]:
    """执行十轮评审→修补，返回报告与终稿 slides。"""
    current = copy.deepcopy(slides)
    rounds_out: list[dict[str, Any]] = []

    for spec in AGENT_ROUNDS:
        issues = spec["check"](current)
        fixed, applied = spec["fix"](current, issues)
        current = fixed
        rounds_out.append(
            {
                "round": spec["round"],
                "role": spec["role"],
                "layout_tier": spec["layout_tier"],
                "prompt": spec["prompt"],
                "issues_before": issues,
                "fixes_applied": applied,
                "ok_after": not spec["check"](current),
                "issues_after": spec["check"](current),
            }
        )

    assignment = layout_assignment_table(current)
    return {
        "ok": all(r["ok_after"] for r in rounds_out),
        "rounds": rounds_out,
        "layout_assignments": assignment,
        "slides": current,
        "layout_catalog": [{"id": x["id"], "name": x["name"]} for x in DOUYIN_CONTENT_LAYOUTS],
    }
