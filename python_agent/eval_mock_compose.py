"""评测用离线分镜（不调用 LLM Compose）：GitHub 日更真稿结构，无套话。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.tts_copy_rules import sanitize_tts_text, tts_has_banned_phrase


def _screen_cards(point: str) -> tuple[str, str]:
    """从价值句拆两条屏显副标题（≤12字）。"""
    p = re.sub(r"\s+", "", (point or "").strip())
    if len(p) <= 12:
        return p[:12], "省时好用"
    mid = max(4, len(p) // 2)
    for i in range(mid, max(4, len(p) - 4)):
        if p[i] in "，,。！？；、":
            a, b = p[:i].strip("，,。！？；、"), p[i + 1 :].strip("，,。！？；、")
            if len(a) >= 4 and len(b) >= 4:
                return a[:12], b[:12]
    return p[:12], p[12:24] if len(p) > 12 else "上手很快"


def mock_compose_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    from python_agent.douyin_shot_stylist import github_daily_opening_hook

    repo = str(brief.get("repo_name") or brief.get("title") or "AI 桌面助手").strip()[:24]
    hook = str(brief.get("hook") or "").strip()
    if not hook or str(brief.get("feed_kind") or "") == "github_daily":
        hook = github_daily_opening_hook(
            repo_name=repo,
            title=str(brief.get("title") or ""),
            hook=hook,
            stars=str(brief.get("stars") or ""),
        )
    points = [str(p).strip() for p in (brief.get("talking_points") or []) if str(p).strip()]
    if len(points) < 3:
        points = [
            "用自然语言描述任务，它会生成可运行的桌面小程序，不用从零搭界面",
            "文档和处理过程留在本机，适合处理合同、表格等敏感资料",
            "适合日报汇总、批量改名、格式转换这类重复办公琐事",
        ]
    cta = str(brief.get("cta") or "想看同类神器记得关注，下期继续拆趋势项目").strip()[:48]

    slides: list[dict[str, Any]] = [
        {
            "type": "title_card",
            "heading": repo[:14],
            "hook_text": hook[:22],
            "tts_text": f"{hook.rstrip('。！？?!')}！",
            "hook_beats": [hook[:18], repo[:14]],
            "opening_burst": True,
            "repo_name": repo,
            "repo_url": str(brief.get("repo_url") or ""),
            "stars": str(brief.get("stars") or ""),
        },
    ]
    for i, p in enumerate(points[:3]):
        line = sanitize_tts_text(p) or p
        slides.append(
            {
                "type": "content_card",
                "tts_text": f"{line.rstrip('。！？?!')}。",
                "bullets": [],
                "scene_focus": True,
                "scene_index": i,
            }
        )
    slides.append(
        {
            "type": "cta_card",
            "heading": "值得试试",
            "cta_text": cta[:16],
            "tts_text": f"{cta.rstrip('。！？?!')}。",
            "css_decorations": ["pulse-button", "github-badge"],
        }
    )
    for s in slides:
        tts = str(s.get("tts_text") or "")
        if tts_has_banned_phrase(tts):
            s["tts_text"] = sanitize_tts_text(tts) or "帮你少做重复性杂活。"
    from python_agent.platform_caption_presets import apply_platform_presets_to_slides

    out_slides = apply_platform_presets_to_slides(slides, "douyin")
    # 分镜 100% LLM 细设计在 slides_render 阶段执行（须 llm_api_key）
    return {"slides": out_slides}
