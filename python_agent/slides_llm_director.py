"""LLM 分镜导演：口播、开场爆点、中部屏显；图表/图标仅在有叙事理由时出现。"""
from __future__ import annotations

import json
import re
from typing import Any

_VIZ_TYPES = frozenset({"none", "line", "bar", "stat"})
# 全片图表预算（硬上限，防止每镜都折线图）
_VIZ_BUDGET = {"line": 2, "bar": 1, "stat": 2}


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _split_hook_beats(hook: str, tts: str, *, n: int = 4) -> list[str]:
    parts: list[str] = []
    for src in (hook, tts):
        for chunk in re.split(r"(?<=[。！？?!，,])", src):
            c = _plain(chunk).strip("，,。！？?! ")
            if 4 <= len(c) <= 18:
                parts.append(c)
            if len(parts) >= n:
                break
        if len(parts) >= n:
            break
    return parts[:n] or [_plain(hook)[:18] or "别划走"]


def _client():
    from python_agent.config import get_config
    from python_agent.llm_client import create_llm_client

    cfg = get_config()
    if not (cfg.llm_api_key or "").strip():
        return None, None
    return create_llm_client(cfg.llm_api_key, cfg.llm_base_url), cfg.llm_model


def _llm_direct_script(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    platform: str,
) -> list[dict[str, Any]] | None:
    client, model = _client()
    if not client:
        return None

    n_content = sum(
        1 for s in slides if s.get("scene_focus") or str(s.get("type")) == "content_card"
    )

    compact = []
    for i, s in enumerate(slides):
        compact.append(
            {
                "i": i,
                "type": s.get("type"),
                "heading": s.get("heading"),
                "feature_label": s.get("feature_label"),
                "tts_text": (s.get("tts_text") or "")[:280],
                "bullets": [
                    b.get("text") if isinstance(b, dict) else str(b)
                    for b in (s.get("bullets") or [])[:6]
                ],
            }
        )

    try:
        from python_agent.remotion_resources import load_skill_rules

        remotion_hint = "\n【Remotion】\n" + load_skill_rules(
            ["director", "charts"], max_chars_per_file=400
        )
    except Exception:
        remotion_hint = ""

    prompt = f"""你是短视频视觉导演（平台={platform}，内容镜约{n_content}个）。
{remotion_hint}

brief 标题={brief.get('title','')} hook={brief.get('hook','')}

草稿：
{json.dumps(compact, ensure_ascii=False)}

返回 JSON：{{"slides":[...]}}

每镜字段：
- tts_text, heading(≤14字)
- title_card: hook_beats 3~4 条（每条不同）
- content_card / scene_focus:
  - summary_lines: 2~3 条中部大字（≤12字，不是口播复述）
  - kinetic_phrases: 0~4 个短词（可选，无图表镜可 3~5 个）
  - mid_icon: 单个 emoji 或空字符串（仅强调概念时，如 📈 ⚡ 🛠️）
  - mid_effect: glow_ring | typewriter | particle_dust | bracket_slam | glow_scan | none
  - mid_info_layout: none | keywords | steps | compare（viz=none 时优先 steps/compare/keywords，禁止连续 2 镜全空）
  - viz_type: none | line | bar | stat
  - chart_series: 仅 line/bar 且口播含趋势/增长/对比数据时填写 4~6 个数
  - chart_label, stat_value: 仅对应 viz 时填

【图表铁律 — 必须遵守】
1. 默认 viz_type=none。全片最多 { _VIZ_BUDGET['line'] } 个 line、{ _VIZ_BUDGET['bar'] } 个 bar、{ _VIZ_BUDGET['stat'] } 个 stat。
2. line 仅用于：Star 增长、热度趋势、效率曲线等「时间序列」叙事。
3. bar 仅用于：两项/多项对比（before/after）。
4. stat 仅用于：一个醒目数字（如 Star 1.2万）。
5. 无数字、无趋势、讲功能/流程的镜 → 必须 none，用 summary_lines + mid_icon，禁止 chart。
6. 中部屏显不得与底栏口播逐字相同。

只返回 JSON。"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.45,
            max_tokens=2800,
        )
        raw = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        return json.loads(m.group(0)).get("slides")
    except Exception:
        return None


def _strip_bottom_chart(dec: list[str]) -> list[str]:
    return [d for d in dec if d != "chart-line-rise"]


def _tts_has_trend_narrative(tts: str) -> bool:
    return bool(
        re.search(
            r"趋势|增长|上涨|曲线|Star|star|破万|暴涨|同比|环比|效率.*%|数据",
            tts,
            re.I,
        )
    )


def _tts_has_compare_narrative(tts: str) -> bool:
    return bool(re.search(r"对比|vs|VS|前后|原来.*现在|提升.*倍", tts))


def _tts_has_single_stat(tts: str) -> bool:
    return bool(re.search(r"\d+[\d.%万千]*", tts))


def _apply_viz(
    s: dict[str, Any],
    viz: str,
    series: list,
    label: str,
    unit: str,
    stat: str,
    *,
    tts: str = "",
) -> None:
    """严格应用 viz：禁止把 none 自动改成 line。"""
    viz = (viz or "none").lower()
    if viz not in _VIZ_TYPES:
        viz = "none"

    nums = []
    for x in series or []:
        try:
            nums.append(float(x))
        except (TypeError, ValueError):
            pass

    if viz == "line":
        if len(nums) < 3 or not _tts_has_trend_narrative(tts):
            viz = "none"
    elif viz == "bar":
        if len(nums) < 2 or not _tts_has_compare_narrative(tts):
            viz = "none"
    elif viz == "stat":
        if not (stat or _tts_has_single_stat(tts)):
            viz = "none"

    s["viz_type"] = viz
    s["show_chart"] = viz in ("line", "bar")
    s["chart_series"] = nums[:8] if viz in ("line", "bar") else []
    s["chart_bars"] = list(s["chart_series"])
    s["chart_label"] = (label or "") if viz in ("line", "bar") else ""
    s["chart_unit"] = (unit or "") if viz in ("line", "bar") else ""
    if viz == "stat":
        s["show_chart"] = False
        s["stat_value"] = (stat or "")[:24]
    else:
        s["stat_value"] = ""


def _enforce_viz_budget(slides: list[dict[str, Any]]) -> None:
    """全片图表预算：超出则降级为 none。"""
    used = {"line": 0, "bar": 0, "stat": 0}
    for s in slides:
        if not (s.get("scene_focus") or str(s.get("type")) == "content_card"):
            continue
        vt = str(s.get("viz_type") or "none")
        if vt not in used:
            continue
        if used[vt] >= _VIZ_BUDGET[vt]:
            s["viz_type"] = "none"
            s["show_chart"] = False
            s["chart_series"] = []
            s["chart_bars"] = []
            s["stat_value"] = ""
        else:
            used[vt] += 1


def direct_slides_script(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    platform: str,
) -> list[dict[str, Any]]:
    plat = (platform or "").strip().lower()
    ai_rows = _llm_direct_script(slides, brief, plat)
    by_i: dict[int, dict[str, Any]] = {}
    if ai_rows:
        for row in ai_rows:
            try:
                by_i[int(row.get("i", -1))] = row
            except (TypeError, ValueError):
                pass

    out: list[dict[str, Any]] = []
    for i, slide in enumerate(slides):
        s = dict(slide)
        row = by_i.get(i)
        st = str(s.get("type") or "")
        tts = str(s.get("tts_text") or "")

        if row:
            if row.get("tts_text"):
                s["tts_text"] = str(row["tts_text"]).strip()
                tts = s["tts_text"]
            if row.get("heading"):
                s["heading"] = str(row["heading"])[:20]

            if st == "title_card":
                beats = [str(x)[:18] for x in (row.get("hook_beats") or []) if str(x).strip()][:4]
                if beats:
                    s["hook_beats"] = beats
                    s["hook_text"] = str(row.get("hook_text") or beats[0])[:18]
                elif row.get("hook_text"):
                    s["hook_text"] = str(row["hook_text"])[:18]

            if st == "content_card" or s.get("scene_focus"):
                lines = [str(x)[:14] for x in (row.get("summary_lines") or []) if str(x).strip()][:3]
                if lines:
                    s["summary_lines"] = lines
                kin = [str(x)[:10] for x in (row.get("kinetic_phrases") or []) if str(x).strip()][:5]
                if kin:
                    s["kinetic_phrases"] = kin
                icon = str(row.get("mid_icon") or "").strip()[:4]
                if icon:
                    s["mid_icon"] = icon
                _apply_viz(
                    s,
                    str(row.get("viz_type") or "none").lower(),
                    list(row.get("chart_series") or row.get("chart_bars") or []),
                    str(row.get("chart_label") or ""),
                    str(row.get("chart_unit") or ""),
                    str(row.get("stat_value") or ""),
                    tts=tts,
                )
                effect = str(row.get("mid_effect") or "auto")
                s["mid_effect"] = effect
                s["show_kinetic_wall"] = effect == "kinetic_wall" and s.get("viz_type") == "none"
                layout = str(row.get("mid_info_layout") or "").lower()
                if layout in ("keywords", "steps", "compare", "none"):
                    s["mid_info_layout"] = layout

        elif st == "title_card":
            s["hook_beats"] = _split_hook_beats(
                str(s.get("hook_text") or brief.get("hook") or ""),
                tts,
            )

        if st == "title_card" and not s.get("hook_beats"):
            s["hook_beats"] = _split_hook_beats(str(s.get("hook_text") or ""), tts)

        if (st == "content_card" or s.get("scene_focus")) and not s.get("viz_type"):
            _apply_viz(s, "none", [], "", "", "", tts=tts)
            s.setdefault("show_kinetic_wall", True)

        s["css_decorations"] = _strip_bottom_chart(list(s.get("css_decorations") or []))
        s["llm_directed"] = bool(row)
        out.append(s)

    _enforce_viz_budget(out)
    _enforce_mid_density(out)
    return out


def _enforce_mid_density(slides: list[dict[str, Any]]) -> None:
    """禁止连续 2 个内容镜缺少 summary_lines。"""
    empty_run = 0
    layouts = ("keywords", "steps", "compare")
    li = 0
    for s in slides:
        if not (s.get("scene_focus") or str(s.get("type")) == "content_card"):
            continue
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if not lines:
            empty_run += 1
            h = str(s.get("heading") or s.get("feature_label") or "核心亮点")[:14]
            s["summary_lines"] = [h, "值得一看"]
            s.setdefault("mid_info_layout", layouts[li % len(layouts)])
            li += 1
        else:
            empty_run = 0
            if not str(s.get("mid_info_layout") or "").strip():
                s["mid_info_layout"] = layouts[li % len(layouts)]
                li += 1
        if empty_run >= 2:
            s["kinetic_phrases"] = s.get("kinetic_phrases") or ["收藏", "开源", "好用"]
            s["show_kinetic_wall"] = True
            empty_run = 0
