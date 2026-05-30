"""场景注册表：新功能在此登记，UI 与授权按场景扩展。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

Phase = Literal["mvp", "phase2", "phase3", "planned"]
ApiNeed = Literal["none", "llm", "llm_and_transcribe"]


@dataclass(frozen=True)
class Scenario:
    id: str
    tab_label: str
    title: str
    summary: str
    phase: Phase
    api_need: ApiNeed
    license_feature: str  # licensing.check_feature 用
    platforms: tuple[str, ...]  # douyin, ecommerce, general, ...


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="pipeline_render",
        tab_label="🔗 Pipeline 出片",
        title="Pipeline 口播包出片",
        summary="中间层 LLM 生成文案与分镜；VSA 只执行 TTS+渲染。",
        phase="mvp",
        api_need="none",
        license_feature="manual_clip",
        platforms=("douyin", "xhs", "kuaishou", "channels"),
    ),
    Scenario(
        tab_label="✂️ 本地裁剪",
        title="本地裁剪",
        summary="按时间段裁剪拼接，无需 API，适合所有平台素材预处理。",
        phase="mvp",
        api_need="none",
        license_feature="manual_clip",
        platforms=("general", "douyin", "ecommerce"),
    ),
    Scenario(
        id="douyin_pack",
        tab_label="📱 抖音发布包",
        title="抖音 / 快手竖屏包",
        summary="9:16 竖屏、时长建议、导出命名；零 API，专为短视频发布。",
        phase="mvp",
        api_need="none",
        license_feature="manual_clip",
        platforms=("douyin", "kuaishou", "channels"),
    ),
    Scenario(
        id="ecommerce",
        tab_label="🛒 电商切片",
        title="电商讲解切片",
        summary="商品讲解长片 → 多段卖点短片（Phase 3：静音切分 + 竖版商品图视频）。",
        phase="phase3",
        api_need="none",
        license_feature="manual_clip",
        platforms=("ecommerce", "taobao", "douyin_shop"),
    ),
    Scenario(
        id="ai_highlights",
        tab_label="🤖 AI 智能切片",
        title="AI 精彩片段",
        summary="自动转录、挑钩子、配音字幕；需用户在设置中填写 DeepSeek/Groq Key。",
        phase="mvp",
        api_need="llm_and_transcribe",
        license_feature="ai_agent",
        platforms=("general", "douyin", "bilibili", "youtube"),
    ),
    Scenario(
        id="subtitle_cn",
        tab_label="📝 翻译配音",
        title="全片中文配音",
        summary="外语视频 → 中文配音 + 烧录字幕；需用户 API Key。",
        phase="mvp",
        api_need="llm_and_transcribe",
        license_feature="ai_subtitle",
        platforms=("general", "education", "cross_border"),
    ),
)


def list_scenarios(*, phase: Phase | None = None, platform: str | None = None) -> list[Scenario]:
    out: list[Scenario] = []
    for s in SCENARIOS:
        if phase and s.phase != phase:
            continue
        if platform and platform not in s.platforms:
            continue
        out.append(s)
    return out


def get_scenario(scenario_id: str) -> Scenario | None:
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def roadmap_markdown() -> str:
    lines = ["| 场景 | 阶段 | API | 说明 |", "|------|------|-----|------|"]
    for s in SCENARIOS:
        api = {"none": "不需要", "llm": "DeepSeek", "llm_and_transcribe": "DeepSeek+Groq(可选)"}[s.api_need]
        lines.append(f"| {s.title} | {s.phase} | {api} | {s.summary} |")
    return "\n".join(lines)
