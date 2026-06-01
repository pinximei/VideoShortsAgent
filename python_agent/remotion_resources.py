"""Remotion 官方资源索引 + 本地 skills 规则加载（https://www.remotion.dev/docs/resources）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# 提交到 Git 的 vendor 副本优先；本地 .agents 为 Cursor 可选缓存
def _skill_dir() -> Path:
    vendor = ROOT / "vendor" / "remotion-best-practices"
    if (vendor / "SKILL.md").is_file():
        return vendor
    agents = ROOT / ".agents" / "skills" / "remotion-best-practices"
    return agents if (agents / "SKILL.md").is_file() else vendor


SKILL_DIR = _skill_dir()
RULES_DIR = SKILL_DIR / "rules"

# 与 https://www.remotion.dev/docs/resources 对齐的常用官方能力
OFFICIAL_RESOURCES: list[dict[str, str]] = [
    {
        "id": "agent-skills",
        "title": "Agent Skills",
        "url": "https://www.remotion.dev/docs/ai/skills",
        "install": "npx skills add remotion-dev/skills",
        "use_in_project": "vendor/remotion-best-practices（py -3 scripts/sync_remotion_official_skills.py 更新）",
    },
    {
        "id": "mcp",
        "title": "Remotion MCP",
        "url": "https://www.remotion.dev/docs/ai/mcp",
        "install": "npx @remotion/mcp@latest",
        "use_in_project": ".cursor/mcp.json → remotion-documentation",
    },
    {
        "id": "transitions",
        "title": "@remotion/transitions",
        "url": "https://www.remotion.dev/docs/transitions",
        "install": "npx remotion add @remotion/transitions",
        "use_in_project": "TransitionSeries 替代 FFmpeg xfade（演进）",
    },
    {
        "id": "google-fonts",
        "title": "@remotion/google-fonts",
        "url": "https://www.remotion.dev/docs/google-fonts",
        "install": "npm i @remotion/google-fonts",
        "use_in_project": "图表/标题字体加载",
    },
    {
        "id": "media",
        "title": "@remotion/media",
        "url": "https://www.remotion.dev/docs/media",
        "install": "npm i @remotion/media",
        "use_in_project": "Video/Audio 组件",
    },
    {
        "id": "captions",
        "title": "Captions / display-captions",
        "url": "https://www.remotion.dev/docs/captions",
        "install": "见 skills rules/display-captions.md",
        "use_in_project": "底栏口播字幕规范",
    },
    {
        "id": "light-leaks",
        "title": "@remotion/light-leaks",
        "url": "https://www.remotion.dev/docs/light-leaks",
        "install": "npx remotion add @remotion/light-leaks",
        "use_in_project": "切镜 Overlay 光效",
    },
    {
        "id": "timing",
        "title": "Timing & spring",
        "url": "https://www.remotion.dev/docs/animation",
        "install": "内置 remotion",
        "use_in_project": "spring/interpolate；禁止 CSS animation",
    },
]

# LLM 编排时按场景加载的 rules（对应官方 skills 分包）
TOPIC_RULE_FILES: dict[str, list[str]] = {
    "compose": ["timing.md", "text-animations.md", "compositions.md"],
    "director": ["display-captions.md", "text-animations.md", "voiceover.md", "parameters.md"],
    "charts": ["timing.md"],
    "transitions": ["transitions.md"],
    "audio": ["audio.md", "voiceover.md", "sfx.md"],
    "render": ["ffmpeg.md", "get-audio-duration.md", "sequencing.md"],
}


def load_skill_rules(topics: list[str], *, max_chars_per_file: int = 700) -> str:
    """从已安装的 remotion-dev/skills 读取规则片段。"""
    if not RULES_DIR.is_dir():
        return _fallback_rules(topics)

    seen: set[str] = set()
    chunks: list[str] = []
    for topic in topics:
        for fname in TOPIC_RULE_FILES.get(topic, []):
            if fname in seen:
                continue
            seen.add(fname)
            path = RULES_DIR / fname
            if path.is_file():
                chunks.append(f"### {fname}\n{path.read_text(encoding='utf-8')[:max_chars_per_file]}")
    return "\n\n".join(chunks) if chunks else _fallback_rules(topics)


def _fallback_rules(topics: list[str]) -> str:
    base = (
        "Remotion: useCurrentFrame+spring/interpolate; no CSS animation; "
        "assets in public/ via staticFile(); captions per display-captions skill."
    )
    if "transitions" in topics:
        base += " Prefer @remotion/transitions fade/slide/wipe."
    return base


def resources_index_markdown() -> str:
    lines = ["| 资源 | 文档 | 安装 | 本项目 |", "|------|------|------|--------|"]
    for r in OFFICIAL_RESOURCES:
        lines.append(
            f"| {r['title']} | [{r['id']}]({r['url']}) | `{r['install']}` | {r['use_in_project']} |"
        )
    return "\n".join(lines)


def map_transition_to_official(ffmpeg_name: str) -> str:
    """FFmpeg xfade 名 → 官方 @remotion/transitions 推荐类型（文档对照）。"""
    m = (ffmpeg_name or "fade").strip().lower()
    if m in ("fade", "dissolve"):
        return "fade"
    if m.startswith("slide") or m in ("slideup", "slidedown", "slideleft", "slideright"):
        return "slide"
    if m.startswith("wipe") or m == "circleopen":
        return "wipe"
    return "fade"


def orchestration_prompt_block() -> str:
    """注入 Compose / LLM 导演的 Remotion 官方约束块。"""
    rules = load_skill_rules(["compose", "director", "charts", "transitions"], max_chars_per_file=500)
    return (
        "【Remotion 官方资源约束 /resources】\n"
        + resources_index_markdown()
        + "\n\n【规则摘录】\n"
        + rules[:3500]
    )
