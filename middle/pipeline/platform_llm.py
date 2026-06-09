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

from python_agent.capabilities.opening_hook import OPENING_HOOK_RULES, enforce_opening_hook_on_copy
from python_agent.capabilities.registry import llm_capabilities_section, save_catalog_snapshot
from python_agent.voice_content_templates import (
    is_voice_style_brief,
    pick_voice_content_style,
    voice_style_prompt_block,
)

SYSTEM_PROMPT = """你是多平台内容运营与短视频剪辑策划专家。
根据 Soul 站内文章**润色改写**为各平台可发布终稿，并为抖音/小红书规划视频分镜与特效参数。
硬性要求：须用自己的话重组信息，禁止大段照抄原文/摘要/标签页文案；标题、口播、微头条、豆瓣笔记均须为改写后的终稿。
抖音/小红书视频：口播 script、clips.hook_text、屏上字幕**禁止**出现 http(s) 链接、站外域名、Product Hunt、ai-trends 等；禁止「点击链接」「评论区有完整拆解」「去官网/其它平台」等导流表述；片尾仅可写「关注，每天一条 AI 资讯」类站内留存引导。
特效与样式必须从文末「VSA 能力目录」中选择合法值，不得自造字段。
开篇前 3～8 秒必须抓住注意力（悬念/反差/数字/利益），禁止「大家好」「今天介绍」式开场。
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
    "effects": {{ "preset": "情感", "gradient": false, "intro_card": true, "outro_card": true }},
    "clips": [{{"start": 0, "end": 10, "hook_text": "...", "tts_text": "...", "caption_style": "fade", "transition_to_next": "dissolve"}}]
  }},
  "toutiao": {{
    "title": "18字内吸睛标题",
    "body": "微头条正文（Markdown）：首段钩子；空行；## 小标题；分段正文； - 要点列表；**重点词**；末行单独放链接 URL"
  }},
  "douban": {{
    "title": "笔记标题",
    "body": "豆瓣正文（Markdown）：## 小节；分段； - 要点；**重点**；文末链接单独一行"
  }}
}}

toutiao.body / douban.body 排版要求：必须用空行分段（\\n\\n），每段不超过 4 行；至少 1 个 ## 小标题、1 组 - 要点列表；核心句用 **加粗**；禁止整段不换行的大块文字。

视频 clips：feed_kind=news 时**必须 3~4 段**、apps 时 2~4 段；口播总字数 180~260；段间转场 0.2~0.3 秒；start/end 在 B-roll 时长内且各段 start 应错开。
每段 `hook_text` 为屏上短字幕（≤24 字）；正文段可用要点式 hook_text。
**effects.preset 必填**；按 feed_kind 选 preset（见能力目录）；pixelize/diag* 实验转场全片最多 1 次。

{opening_hook_rules}

{voice_content_rules}

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

    brief_dict = brief.to_dict() if hasattr(brief, "to_dict") else {}
    voice_rules = ""
    if is_voice_style_brief(brief_dict):
        from python_agent.douyin_news_style import is_news_brief
        from python_agent.tts_voice_presets import compose_voice_style_from_preset

        if is_news_brief(brief_dict):
            voice_rules = voice_style_prompt_block(compose_voice_style_from_preset(brief_dict))
        else:
            voice_rules = voice_style_prompt_block(pick_voice_content_style(brief_dict))

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
        opening_hook_rules=OPENING_HOOK_RULES,
        voice_content_rules=voice_rules or "（口播：180~260字，快节奏短句，禁止废话开场）",
        capabilities_section=llm_capabilities_section(feed_kind=brief.feed_kind),
    )
    if getattr(brief, "cover_image_url", ""):
        user += "\n\n## 封面图\n文章有封面图，抖音片头 intro_card 可设为 true（系统会自动挂载）。"
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
                "勿编造具体产品细节；视频口播勿引导点击外链或站外平台。"
            )

    from python_agent.capabilities.plan_validate import repair_prompt_note, validate_platform_copy

    user_base = user
    last_err = ""
    max_attempts = max(1, int(getattr(cfg, "llm_plan_retries", 2)) + 1) if cfg else 2
    for attempt in range(max_attempts):
        u = user_base + (repair_prompt_note(last_err) if attempt else "")
        copy = llm.chat_json(SYSTEM_PROMPT, u)
        from python_agent.capabilities.clip_text import enrich_apps_platform_copy

        copy = enrich_apps_platform_copy(copy, feed_kind=brief.feed_kind)
        copy = enforce_opening_hook_on_copy(
            copy,
            brief_hook=brief.hook,
            title=brief.title,
            feed_kind=brief.feed_kind,
            talking_points=brief.talking_points,
        )
        from python_agent.platform_traffic_rules import (
            sanitize_video_platform_block,
            validate_video_copy_no_traffic,
        )

        for pid in ("douyin", "xhs"):
            block = copy.get(pid)
            if isinstance(block, dict):
                copy[pid] = sanitize_video_platform_block(block)
        traffic_issues = validate_video_copy_no_traffic(copy, "douyin") + validate_video_copy_no_traffic(
            copy, "xhs"
        )
        if traffic_issues:
            last_err = ",".join(traffic_issues)
            continue
        ok, msg = validate_platform_copy(
            copy, broll_seconds=broll_seconds, feed_kind=brief.feed_kind
        )
        if ok:
            return copy
        last_err = msg
    raise ValueError(f"platform_copy_invalid: {last_err}")


def _save_video_clip_files(
    output_dir: Path,
    copy: dict[str, Any],
    *,
    broll_seconds: float | None = None,
) -> None:
    from python_agent.pipeline_input import save_video_clips_plan
    from python_agent.pipeline_render import sync_broll_timings_to_clips

    feed_kind = ""
    brief_p = output_dir / "brief.json"
    if brief_p.is_file():
        try:
            feed_kind = str(json.loads(brief_p.read_text(encoding="utf-8-sig")).get("feed_kind") or "")
        except Exception:
            pass
    for platform in ("douyin", "xhs"):
        block = copy.get(platform) or {}
        clips = block.get("clips")
        if not clips:
            continue
        effects = dict(block.get("effects") or {})
        if feed_kind in ("apps", "news"):
            effects["gradient"] = False
        if broll_seconds and broll_seconds > 0:
            sync_broll_timings_to_clips(clips, float(broll_seconds))
        save_video_clips_plan(
            output_dir,
            platform,
            clips,
            effects=effects,
            source="pipeline_llm",
            render_status="ok",
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
        copy_stub = {
            platform: {
                "clips": clips,
                "effects": effects,
                "title": brief_dict.get("title") or "",
            }
        }
        copy_stub = enforce_opening_hook_on_copy(
            copy_stub,
            brief_hook=str(brief_dict.get("hook") or ""),
            title=str(brief_dict.get("title") or ""),
            feed_kind=str(brief_dict.get("feed_kind") or "news"),
            talking_points=brief_dict.get("talking_points") or [],
        )
        block = copy_stub.get(platform) or {}
        clips = block.get("clips") or clips
        effects = block.get("effects") or effects
        if broll_seconds and broll_seconds > 0:
            sync_broll_timings_to_clips(clips, float(broll_seconds))
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

    from .llm_polish import llm_polish_required

    meta: dict[str, Any] = {"source": "template", "llm_error": None}
    copy = platform_copy
    if copy is None:
        if not cfg or not cfg.llm_enabled:
            if cfg and llm_polish_required(cfg):
                from .pipeline_gates import PipelineGateError

                raise PipelineGateError("llm_disabled", "生产环境禁止 llm.enabled=false")
            copy = {}
        else:
            try:
                copy = generate_platform_copy(brief, article, cfg, broll_seconds=broll_seconds)
                meta["source"] = "pipeline_llm"
                llm_dir = output_dir / "llm"
                llm_dir.mkdir(parents=True, exist_ok=True)
                (llm_dir / "platform_copy.json").write_text(
                    json.dumps(copy, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                _save_video_clip_files(output_dir, copy, broll_seconds=broll_seconds)
            except Exception as e:
                meta["llm_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                copy = {}
                if cfg.render_allow_template_fallback and not llm_polish_required(cfg):
                    write_fallback_video_plans(brief, output_dir, cfg)
                    meta["source"] = "brief_to_clips_fallback"

    if copy:
        _write_from_llm(brief, output_dir, copy)
    elif cfg and llm_polish_required(cfg):
        from .pipeline_gates import PipelineGateError

        raise PipelineGateError(
            "llm_polish_required",
            meta.get("llm_error") or "LLM 润色失败，禁止模板/Soul 直出",
        )
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

    _prefetch_cover_if_needed(output_dir, brief)

    if cfg and cfg.render_enabled and cfg.pipeline_fail_closed:
        from .pipeline_gates import assert_publish_pack_meta

        assert_publish_pack_meta(output_dir, cfg)
        if meta.get("llm_error") and not cfg.render_allow_template_fallback:
            from .pipeline_gates import PipelineGateError

            raise PipelineGateError("llm_failed", str(meta["llm_error"])[:300])

    return meta


def _prefetch_cover_if_needed(output_dir: Path, brief: VideoBrief) -> None:
    from python_agent.pipeline_media import prefetch_task_cover

    if getattr(brief, "cover_image_url", ""):
        prefetch_task_cover(output_dir, brief.to_dict())


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

    script = (dy.get("script") or "").strip()
    if not script:
        from .pipeline_gates import PipelineGateError

        raise PipelineGateError("llm_polish_incomplete", "douyin.script 为空，禁止回退 Soul brief")
    _write_text(output_dir / "script.txt", script)

    xhs_video_script = (xhs.get("video_script") or "").strip()
    if xhs_video_script:
        _write_text(output_dir / "script_xhs.txt", xhs_video_script)

    from publisher.scripts.format_copy import format_douban_note, format_douyin_title_desc, format_toutiao_micro

    dy_title_raw = str(dy.get("title") or "").strip()[:55]
    if not dy_title_raw:
        from .pipeline_gates import PipelineGateError

        raise PipelineGateError("llm_polish_incomplete", "douyin.title 为空")
    tt_raw = str(tt.get("body") or "")
    db_raw = str(db.get("body") or "")
    dy_short, dy_desc = format_douyin_title_desc(dy_title_raw, db_raw or tt_raw)
    _write_text(publish / "douyin_title.txt", dy_short)
    _write_text(publish / "douyin_desc.txt", dy_desc)
    tags = dy.get("tags") or brief.tags
    tag_line = " ".join(f"#{t}" if not str(t).startswith("#") else str(t) for t in tags[:8])
    _write_text(publish / "douyin_tags.txt", tag_line)

    xhs_title = str(xhs.get("title") or "").strip()[:60]
    xhs_body = str(xhs.get("body") or "").strip()[:2000]
    if not xhs_title or not xhs_body:
        from .pipeline_gates import PipelineGateError

        raise PipelineGateError("llm_polish_incomplete", "xhs.title/body 为空")
    _write_text(publish / "xhs_title.txt", xhs_title)
    _write_text(publish / "xhs_body.txt", xhs_body)

    from python_agent.capabilities.opening_hook import scroll_stopping_hook

    tt_title = str(tt.get("title") or "").strip() or scroll_stopping_hook(
        title=brief.title, hook=brief.hook, feed_kind=brief.feed_kind
    )
    tt_body = str(tt.get("body") or "").strip()
    if not tt_body:
        from .pipeline_gates import PipelineGateError

        raise PipelineGateError("llm_polish_incomplete", "toutiao.body 为空")
    _write_text(
        publish / "toutiao_micro.txt",
        format_toutiao_micro(tt_title, tt_body)[:2500],
    )

    db_title = str(db.get("title") or brief.title or brief.hook).strip()[:80]
    if not str(db_raw).strip():
        from .pipeline_gates import PipelineGateError

        raise PipelineGateError("llm_polish_incomplete", "douban.body 为空")
    _write_text(publish / "douban_note.txt", format_douban_note(db_title, db_raw)[:2000])

    meta = {
        "source": "pipeline_llm",
        "llm_owner": "VideoShortsAgent/middle",
        "platforms": list(copy.keys()),
        "video_plans": ["douyin", "xhs"] if any((copy.get(p) or {}).get("clips") for p in ("douyin", "xhs")) else [],
    }
    _write_text(output_dir / "publish_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))

    return publish
