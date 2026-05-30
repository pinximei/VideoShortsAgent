"""中间层大模型：各平台文案 + 视频分镜（引用 VSA 统一能力目录）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .config import PipelineConfig, repo_root
from .llm_client import PipelineLLM
from .models import VideoBrief
from .publish_pack import write_publish_pack_templates
from .article_content import collect_article_text, is_placeholder_summary, plain_without_urls

# 同仓库：python_agent.capabilities
_root = repo_root()
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from python_agent.capabilities.registry import llm_capabilities_section, save_catalog_snapshot

SYSTEM_PROMPT = """你是多平台内容运营与短视频剪辑策划专家。
根据站内文章生成各平台可发布终稿，并为抖音/小红书规划视频分镜与特效参数。
特效与样式必须从文末「VSA 能力目录」中选择合法值，不得自造字段。
只返回 JSON。"""

USER_TEMPLATE = """## 原文信息
标题：{title}
钩子：{hook}
要点：
{points}
引导：{cta}
标签：{tags}
详情链接：{detail_url}
feed：{feed_kind}
内容赛道：{theme_label}（{theme_id}）
{broll_section}

## 输出 JSON（严格遵守字段名）
{{
  "douyin": {{
    "title": "55字内标题",
    "tags": ["话题1"],
    "script": "60秒内口播稿",
    "effects": {{
      "preset": "活力",
      "gradient": false,
      "intro_card": true,
      "outro_card": true,
      "transition_duration": 0.22
    }},
    "clips": [
      {{
        "start": 0.0,
        "end": 10.0,
        "hook_text": "屏上字幕",
        "bullets": ["要点一", "要点二"],
        "tts_text": "配音词",
        "caption_style": "spring",
        "transition_to_next": "circleopen"
      }}
    ]
  }},
  "xhs": {{
    "title": "40字内标题",
    "body": "900字内笔记",
    "video_script": "60秒口播稿",
    "effects": {{ "preset": "情感", "gradient": false, "intro_card": false, "outro_card": true }},
    "clips": [{{"start": 0, "end": 10, "hook_text": "...", "tts_text": "...", "caption_style": "fade", "transition_to_next": "dissolve"}}]
  }},
  "toutiao": {{ "title": "...", "body": "微头条短文" }},
  "douban": {{ "title": "...", "body": "豆瓣笔记" }}
}}

视频 clips：2~4 段；口播总字数≤220；段间转场 0.2~0.3 秒；start/end 在 B-roll 时长内且各段 start 应错开。
每段 `hook_text` 为屏上短字幕（≤24 字）；正文段可用要点式 hook_text。
**effects.preset 必填**；按 feed_kind 选 preset（见能力目录）；pixelize/diag* 实验转场全片最多 1 次。

{capabilities_section}"""

BROLL_SECTION = """
## B-roll 素材
总时长约 {broll_seconds:.0f} 秒"""


def _points_md(points: list[str]) -> str:
    return "\n".join(f"- {p}" for p in points) if points else "- （无）"


def generate_platform_copy(
    brief: VideoBrief,
    article: dict[str, Any] | None,
    cfg: PipelineConfig,
    *,
    broll_seconds: float | None = None,
) -> dict[str, Any]:
    llm = PipelineLLM(cfg)
    broll_section = ""
    if broll_seconds and broll_seconds > 0:
        broll_section = BROLL_SECTION.format(broll_seconds=broll_seconds)

    theme = next((t for t in cfg.themes if t.id == brief.theme_id), None)
    theme_label = theme.label if theme else (brief.theme_id or "未分类")

    user = USER_TEMPLATE.format(
        title=brief.title,
        hook=brief.hook,
        points=_points_md(brief.talking_points),
        cta=brief.cta,
        tags=", ".join(brief.tags),
        detail_url=brief.detail_url,
        feed_kind=brief.feed_kind,
        theme_id=brief.theme_id or "default",
        theme_label=theme_label,
        broll_section=broll_section,
        capabilities_section=llm_capabilities_section(feed_kind=brief.feed_kind),
    )
    if article:
        excerpt = collect_article_text(article, max_chars=4500)
        plain_excerpt = plain_without_urls(excerpt)
        min_excerpt = 40 if (article.get("article_body") or "").strip() else 60
        if len(plain_excerpt) >= min_excerpt:
            user += f"\n\n## 文章正文（必读，勿仅根据标题编造）\n{excerpt[:4500]}"
        else:
            summary = (article.get("summary") or article.get("card_description") or "")[:600]
            if summary and not is_placeholder_summary(summary):
                user += f"\n\n## 文章摘要（补充）\n{summary}"
            repl = article.get("replication_analysis") or {}
            if isinstance(repl, dict) and repl.get("value_summary"):
                user += f"\n\n## 变现价值摘要\n{repl.get('value_summary')}"
            user += (
                "\n\n## 注意\n"
                "站内正文过短，可能仅为外链卡片；请基于已有字段保守生成，"
                "勿编造具体产品细节；引导用户点击详情链接。"
            )

    from python_agent.capabilities.plan_validate import repair_prompt_note, validate_platform_copy

    user_base = user
    last_err = ""
    max_attempts = max(1, int(getattr(cfg, "llm_plan_retries", 2)) + 1) if cfg else 2
    for attempt in range(max_attempts):
        u = user_base + (repair_prompt_note(last_err) if attempt else "")
        copy = llm.chat_json(SYSTEM_PROMPT, u)
        ok, msg = validate_platform_copy(copy, broll_seconds=broll_seconds)
        if ok:
            return copy
        last_err = msg
    raise ValueError(f"platform_copy_invalid: {last_err}")


def _save_video_clip_files(output_dir: Path, copy: dict[str, Any]) -> None:
    llm_dir = output_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    for platform in ("douyin", "xhs"):
        block = copy.get(platform) or {}
        clips = block.get("clips")
        if not clips:
            continue
        payload = {
            "clips": clips,
            "platform": platform,
            "effects": block.get("effects") or {},
            "source": "pipeline_llm",
        }
        (llm_dir / f"video_clips_{platform}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def write_fallback_video_plans(brief: VideoBrief, output_dir: Path, cfg: PipelineConfig) -> None:
    """LLM 不可用时：规则分镜 + 平台特效（需 render.allow_template_fallback）。"""
    import sys

    root = repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from python_agent.capabilities.registry import merge_render_effects
    from python_agent.pipeline_input import brief_to_clips, save_video_clips_plan
    from python_agent.platform_presets import get_platform_preset

    llm_dir = output_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    brief_dict = brief.to_dict()
    for platform in ("douyin", "xhs"):
        if platform not in (cfg.render_platforms or []):
            continue
        preset = get_platform_preset(platform)
        clips = brief_to_clips(brief_dict, preset)
        effects = merge_render_effects(
            platform,
            clips,
            preset.effects,
            use_remotion=cfg.render_use_remotion,
            feed_kind=brief.feed_kind,
            bookends=cfg.render_bookends,
        )
        save_video_clips_plan(
            output_dir,
            platform,
            clips,
            effects=effects,
            source="brief_to_clips_fallback",
            render_status="degraded",
        )


def write_publish_pack(
    brief: VideoBrief,
    output_dir: Path,
    *,
    platform_copy: dict[str, Any] | None = None,
    cfg: PipelineConfig | None = None,
    article: dict[str, Any] | None = None,
    broll_seconds: float | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    save_catalog_snapshot(output_dir, feed_kind=brief.feed_kind)

    meta: dict[str, Any] = {"source": "template", "llm_error": None}
    copy = platform_copy
    if copy is None:
        if cfg and cfg.llm_enabled:
            try:
                copy = generate_platform_copy(brief, article, cfg, broll_seconds=broll_seconds)
                meta["source"] = "pipeline_llm"
                llm_dir = output_dir / "llm"
                llm_dir.mkdir(parents=True, exist_ok=True)
                (llm_dir / "platform_copy.json").write_text(
                    json.dumps(copy, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                _save_video_clip_files(output_dir, copy)
            except Exception as e:
                meta["llm_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                copy = {}
                if cfg.render_allow_template_fallback:
                    write_fallback_video_plans(brief, output_dir, cfg)
                    meta["source"] = "brief_to_clips_fallback"
        else:
            copy = {}

    if copy:
        _write_from_llm(brief, output_dir, copy)
    else:
        write_publish_pack_templates(brief, output_dir)
        if cfg and cfg.render_allow_template_fallback:
            write_fallback_video_plans(brief, output_dir, cfg)
            meta["source"] = "brief_to_clips_fallback"

    meta_path = output_dir / "publish_meta.json"
    if meta_path.is_file():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
        existing.update(meta)
        meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    return meta


def _write_from_llm(brief: VideoBrief, output_dir: Path, copy: dict[str, Any]) -> Path:
    from .publish_pack import _write_text, script_text

    publish = output_dir / "publish"
    publish.mkdir(parents=True, exist_ok=True)

    _write_text(
        output_dir / "brief.json",
        json.dumps(brief.to_dict(), ensure_ascii=False, indent=2),
    )

    dy = copy.get("douyin") or {}
    xhs = copy.get("xhs") or {}
    tt = copy.get("toutiao") or {}
    db = copy.get("douban") or {}

    script = (dy.get("script") or "").strip() or script_text(brief)
    _write_text(output_dir / "script.txt", script)

    xhs_video_script = (xhs.get("video_script") or "").strip()
    if xhs_video_script:
        _write_text(output_dir / "script_xhs.txt", xhs_video_script)

    _write_text(publish / "douyin_title.txt", str(dy.get("title") or brief.hook)[:55])
    tags = dy.get("tags") or brief.tags
    tag_line = " ".join(f"#{t}" if not str(t).startswith("#") else str(t) for t in tags[:8])
    _write_text(publish / "douyin_tags.txt", tag_line)

    _write_text(publish / "xhs_title.txt", str(xhs.get("title") or brief.hook)[:60])
    _write_text(publish / "xhs_body.txt", str(xhs.get("body") or script)[:2000])

    tt_body = str(tt.get("body") or "")
    if not tt_body:
        tt_body = f"{brief.title}\n\n" + "\n".join(f"· {p}" for p in brief.talking_points) + f"\n\n{brief.cta}"
    _write_text(publish / "toutiao_micro.txt", tt_body[:2500])

    db_body = str(db.get("body") or "")
    if not db_body:
        db_body = f"《{brief.title}》\n\n" + "\n".join(brief.talking_points)
    _write_text(publish / "douban_note.txt", db_body[:2000])

    meta = {
        "source": "pipeline_llm",
        "llm_owner": "VideoShortsAgent/middle",
        "platforms": list(copy.keys()),
        "video_plans": ["douyin", "xhs"] if any((copy.get(p) or {}).get("clips") for p in ("douyin", "xhs")) else [],
    }
    _write_text(output_dir / "publish_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))

    return publish
