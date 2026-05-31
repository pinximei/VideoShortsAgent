"""
PlatformScriptSkill - 根据 Pipeline 口播稿 + 平台风格，用大模型生成剪辑方案。

与 AnalysisSkill（基于视频转录）不同：输入是文章/brief 与 B-roll 时长，
输出 clips JSON 供 RenderSkill 使用。
"""
from __future__ import annotations

import json
from typing import Any

from python_agent.llm_client import create_llm_client
from python_agent.config import get_config

PLATFORM_PROMPTS: dict[str, str] = {
    "douyin": "抖音竖屏短视频：强钩子、快节奏、口语化，总口播≤60秒，前3秒必须抓人。",
    "xhs": "小红书视频笔记：真实分享感、可带轻微情绪，节奏适中，总口播≤60秒。",
}

SYSTEM = """你是短视频剪辑策划。根据给定口播素材与 B-roll 总时长，规划分镜剪辑方案。
必须只返回 JSON，不要 markdown。"""

USER_TEMPLATE = """## 平台
{platform_label}：{platform_guide}

## B-roll 素材
总时长约 {broll_seconds:.0f} 秒（无对白画面，按叙述节奏分配起止时间）

## 口播稿
{script}

## 要求
1. 将口播拆为 2~4 个 clips，每段 tts_text 完整可配音
2. 为每段分配 start/end（秒），分布在 0 ~ {broll_seconds:.0f} 内，且不重叠过多
3. hook_text 为屏上短字幕（≤20字）
4. 根据平台选择 caption_style: spring|fade|typewriter
5. transition_to_next: fade|circleopen|dissolve 等
6. 总 tts_text 字数：抖音/小红书不超过 220 字

返回格式：
{{"clips":[{{"start":0,"end":8,"hook_text":"...","tts_text":"...","caption_style":"spring","transition_to_next":"fade"}}]}}"""


class PlatformScriptSkill:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        cfg = get_config()
        self.model = model or cfg.llm_model
        self.client = create_llm_client(api_key=api_key)

    def execute(
        self,
        *,
        platform_id: str,
        script: str,
        broll_seconds: float,
        title: str = "",
    ) -> dict[str, Any]:
        guide = PLATFORM_PROMPTS.get(platform_id, "通用短视频")
        label = {"douyin": "抖音", "xhs": "小红书"}.get(platform_id, platform_id)
        user = USER_TEMPLATE.format(
            platform_label=label,
            platform_guide=guide,
            broll_seconds=broll_seconds,
            script=script.strip(),
        )
        if title:
            user = f"标题：{title}\n\n" + user

        print(f"[PlatformScriptSkill] LLM 剪辑策划 ({platform_id}, model={self.model})...")
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        result = json.loads(raw)
        clips = result.get("clips") or []
        if not clips:
            raise ValueError("LLM 未返回 clips")
        print(f"[PlatformScriptSkill] ✓ {len(clips)} 个片段")
        return result
