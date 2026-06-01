"""开篇钩子：视频前几秒 + 图文前几行统一吸引注意力。"""
from __future__ import annotations

import re
from typing import Any

OPENING_HOOK_RULES = """
### 开篇钩子（前 3～8 秒 / 前 2 行，必须遵守）
1. **第 1 段 clip** 专职开场：`start` 必须从 0 开始；`hook_text` ≤18 字，用疑问/反差/数字/利益点（例：「Watch 一按就进 Claude？」「月费 15 刀值吗？」）。
2. **第 1 段 `tts_text`** 前一句 ≤20 字、口语、有悬念；禁止以「大家好」「今天介绍」开头。
3. 第 1 段 `caption_style` 用 **spring**（抖音/小红书均可）；`transition_to_next` 用 **circleopen** 或 **slideup**（更有冲击）。
4. `effects.intro_card`：抖音、小红书均为 **true**（片头 TitleCard 展示 hook）。
5. 图文：`douyin.title` / `xhs.title` / `toutiao.body` / `douban.body` **第一行必须是钩子句**（可与 brief.hook 一致或更强），再写正文。
""".strip()

_HOOK_PATTERNS = (
    re.compile(r"[？?]"),
    re.compile(r"\d"),
    re.compile(r"居然|竟然|别再|为什么|怎么|值不值|刚刚|首发|免费|暴涨|暴跌|secret|vs", re.I),
)


def scroll_stopping_hook(*, title: str, hook: str, feed_kind: str = "news") -> str:
    """生成 ≤28 字、适合前 3 秒口播/屏显的钩子。"""
    h = re.sub(r"\s+", " ", (hook or "").strip())
    t = re.sub(r"\s+", " ", (title or "").strip())
    if h and len(h) <= 28 and any(p.search(h) for p in _HOOK_PATTERNS):
        return h[:28]
    if h and len(h) <= 28:
        return h[:28]
    # 标题「产品：利益点」→ 用利益点造问句（避免 [:n] 截断英文单词）
    if "：" in t or ":" in t:
        parts = re.split(r"[：:]", t, maxsplit=1)
        if len(parts) == 2:
            benefit = parts[1].strip()
            if "，" in benefit:
                tail = benefit.split("，", 1)[-1].strip()
                if 6 <= len(tail) <= 26:
                    return (tail.rstrip("。") + "？")[:28]
            if 6 <= len(benefit) <= 26:
                return (benefit.rstrip("。") + "？")[:28]
            if len(benefit) > 26:
                short = benefit[:24].rstrip("，,。 ")
                if short.endswith(("Claud", "Clau", "Cla")) and len(benefit) > len(short):
                    short = benefit.split("，")[0][:24].rstrip("，,。 ")
                return (short + "？")[:28]
    # 从标题提炼
    for chunk in re.split(r"[：:，,。！？?!]", t):
        chunk = chunk.strip()
        if 8 <= len(chunk) <= 28:
            if not chunk.endswith(("？", "?", "！")):
                chunk = chunk.rstrip("。") + "？"
            return chunk[:28]
    if t:
        short = t[:22].rstrip("，,。 ")
        return (short + "？")[:28] if len(short) >= 6 else short[:28]
    return (h or "这条资讯你可能漏了")[:28]


def _screen_hook_text(hook: str, *, max_len: int = 18) -> str:
    """屏显短字幕：按字符截断，避免切断英文单词尾部。"""
    s = re.sub(r"\s+", " ", (hook or "").strip())
    if len(s) <= max_len:
        return s
    cut = s[:max_len]
    if cut and cut[-1].isascii() and len(s) > max_len and s[max_len : max_len + 1].isalnum():
        cut = s[: max_len - 1].rstrip()
    return cut.rstrip("，,。 ") or s[:max_len]


def _opening_tts_line(hook: str, tts: str) -> str:
    """口播第一句：钩子 + 原稿，避免废话开场。"""
    h = (hook or "").strip()
    t = (tts or "").strip()
    if not t:
        return h
    bad_starts = ("大家好", "今天", "本期", "我们来", "这篇文章", "分享一下")
    if any(t.startswith(s) for s in bad_starts):
        t = re.sub(r"^[^。！？?]+[。！？?]\s*", "", t).strip() or t
    first, _, rest = t.partition("。")
    if len(first) <= 22 and any(p.search(first) for p in _HOOK_PATTERNS):
        return t
    if h and not t.startswith(h[:12]):
        lead = h if h.endswith(("？", "?", "！")) else h.rstrip("。") + "。"
        return f"{lead}{t}" if t else lead
    return t


def _lead_paragraph(hook: str, body: str, *, max_hook_line: int = 36) -> str:
    body = (body or "").strip()
    h = (hook or "").strip()[:max_hook_line]
    if not h:
        return body
    if body.startswith(h) or body.startswith(f"【{h}】"):
        return body
    return f"{h}\n\n{body}" if body else h


def enforce_opening_hook_on_copy(
    copy: dict[str, Any],
    *,
    brief_hook: str,
    title: str,
    feed_kind: str = "news",
    talking_points: list[Any] | None = None,
) -> dict[str, Any]:
    """LLM 产出后强制开篇结构（视频 clips + 图文首行）。"""
    hook = scroll_stopping_hook(title=title, hook=brief_hook, feed_kind=feed_kind)
    out = dict(copy)

    for platform in ("douyin", "xhs"):
        block = out.get(platform)
        if not isinstance(block, dict):
            continue
        effects = dict(block.get("effects") or {})
        effects["intro_card"] = True
        effects["outro_card"] = True
        block["effects"] = effects

        clips = block.get("clips")
        if not isinstance(clips, list) or not clips:
            continue
        c0 = dict(clips[0]) if isinstance(clips[0], dict) else {}
        try:
            c0["start"] = 0.0
            end = float(c0.get("end") or 8.0)
            if end - float(c0["start"]) > 12.0:
                end = 8.0
            c0["end"] = end
        except (TypeError, ValueError):
            c0["start"], c0["end"] = 0.0, 8.0
        screen_hook = scroll_stopping_hook(
            title=title,
            hook=str(c0.get("hook_text") or hook),
            feed_kind=feed_kind,
        )
        c0["hook_text"] = _screen_hook_text(screen_hook, max_len=18)
        c0["tts_text"] = _opening_tts_line(hook, str(c0.get("tts_text") or hook))
        c0["caption_style"] = "spring"
        # 段间 xfade：news 仅用 fade，避免 circleopen 叠 testsrc 类 B-roll 出现色条残影
        seg_tr = "fade" if (feed_kind or "news").strip().lower() == "news" else (
            "circleopen" if platform == "douyin" else "slideup"
        )
        c0["transition_to_next"] = seg_tr
        clips[0] = c0
        block["clips"] = clips

        if platform == "douyin":
            t = str(block.get("title") or "").strip()
            block["title"] = f"{hook}｜{t}"[:55] if t and not t.startswith(hook[:8]) else (hook[:55])
        else:
            t = str(block.get("title") or "").strip()
            block["title"] = hook[:40] if not t.startswith(hook[:8]) else t[:40]
            body = str(block.get("body") or "")
            block["body"] = _lead_paragraph(hook, body)

    tt = out.get("toutiao")
    if isinstance(tt, dict):
        tt = dict(tt)
        tt["body"] = _lead_paragraph(hook, str(tt.get("body") or ""))
        out["toutiao"] = tt
    db = out.get("douban")
    if isinstance(db, dict):
        db = dict(db)
        db["body"] = _lead_paragraph(hook, str(db.get("body") or ""))
        out["douban"] = db

    for platform in ("douyin", "xhs"):
        block = out.get(platform)
        if isinstance(block, dict) and isinstance(block.get("clips"), list):
            block["clips"] = ensure_min_clips(
                block["clips"],
                brief={
                    "hook": hook,
                    "talking_points": talking_points or [],
                    "title": title,
                },
                feed_kind=feed_kind,
            )
            out[platform] = block

    return out


def ensure_min_clips(
    clips: list[Any],
    *,
    brief: dict[str, Any],
    feed_kind: str = "news",
    min_clips: int | None = None,
) -> list[dict[str, Any]]:
    """资讯至少 3 段正文；不足时从 talking_points 补段。"""
    fk = (feed_kind or "news").strip().lower()
    target = min_clips if min_clips is not None else (3 if fk == "news" else 2)
    out: list[dict[str, Any]] = [dict(c) for c in clips if isinstance(c, dict)]
    hook = scroll_stopping_hook(
        title=str(brief.get("title") or ""),
        hook=str(brief.get("hook") or ""),
        feed_kind=fk,
    )
    used = " ".join(str(c.get("tts_text") or "") for c in out)
    points = list(brief.get("talking_points") or [])
    pi = 0
    while len(out) < target and pi < len(points):
        pt = str(points[pi]).strip()
        pi += 1
        if not pt or pt[:30] in used:
            continue
        used += pt
        out.append(
            {
                "start": 0.0,
                "end": 12.0,
                "hook_text": pt[:24],
                "tts_text": pt[:200],
                "caption_style": "fade",
                "transition_to_next": "fade",
            }
        )
    if not out:
        out.append(
            {
                "start": 0.0,
                "end": 8.0,
                "hook_text": _screen_hook_text(hook, max_len=18),
                "tts_text": hook,
                "caption_style": "spring",
                "transition_to_next": "circleopen",
            }
        )
    if out:
        out[0]["start"] = 0.0
        try:
            if float(out[0].get("end") or 0) > 10.0:
                out[0]["end"] = 8.0
        except (TypeError, ValueError):
            out[0]["end"] = 8.0
        out[0]["caption_style"] = "spring"
        fk_local = (feed_kind or "news").strip().lower()
        out[0]["transition_to_next"] = "fade" if fk_local == "news" else (
            out[0].get("transition_to_next") or "fade"
        )
    seg_durs = [8.0]
    for i in range(1, len(out)):
        seg_durs.append(14.0)
    t = 0.0
    fk_local = (feed_kind or "news").strip().lower()
    for i, clip in enumerate(out):
        dur = seg_durs[i] if i < len(seg_durs) else 12.0
        clip["start"] = round(t, 1)
        clip["end"] = round(t + dur, 1)
        t = clip["end"]
        if fk_local == "news" or i == len(out) - 1:
            clip["transition_to_next"] = "fade"
    return out[:4]


def enforce_opening_hook_on_slides_script(
    script: dict[str, Any],
    *,
    brief: dict[str, Any],
    platform: str = "",
) -> dict[str, Any]:
    """slides 管线：强化第 1 镜（title_card）前 3 秒钩子屏显 + 口播起手。"""
    slides = [dict(s) for s in (script.get("slides") or [])]
    if not slides:
        return script
    s0 = slides[0]
    if str(s0.get("type") or "") != "title_card":
        return script

    fk = str(brief.get("feed_kind") or "github_daily")
    title = str(brief.get("title") or s0.get("heading") or "")
    hook = scroll_stopping_hook(
        title=title,
        hook=str(brief.get("hook") or s0.get("hook_text") or ""),
        feed_kind=fk,
    )
    screen = _screen_hook_text(hook, max_len=18)
    s0["hook_text"] = screen
    beats = s0.get("hook_beats")
    if isinstance(beats, list) and len(beats) >= 2:
        s0["hook_beats"] = [str(x)[:18] for x in beats if str(x).strip()][:4]
    else:
        parts = re.split(r"(?<=[。！？?!，,])", hook)
        s0["hook_beats"] = [
            _screen_hook_text(p.strip("，,。！？?! "), max_len=16)
            for p in parts
            if 4 <= len(p.strip()) <= 18
        ][:4]
        if not s0["hook_beats"]:
            s0["hook_beats"] = [screen, hook[:14] if len(hook) > 14 else hook]
    s0["opening_burst"] = True

    tts = str(s0.get("tts_text") or "").strip()
    hook_sent = hook.rstrip("。！？?!") + "！"
    first_clause = tts.split("。", 1)[0] if tts else ""
    hook_key = hook[:8] if len(hook) >= 4 else hook
    already_hooked = (
        tts.startswith(hook_sent[: min(8, len(hook_sent))])
        or (hook_key and hook_key in first_clause)
        or (screen[:8] and screen[:8] in first_clause)
    )
    if already_hooked and hook_key and tts.count(hook_key) > 1:
        rest = tts.split(hook_key, 1)[-1].lstrip("！。，, ")
        tts = f"{hook_sent}{rest}" if rest else hook_sent
        already_hooked = True
    if already_hooked:
        s0["tts_text"] = tts
    else:
        cleaned = tts
        for bad in ("大家好", "今天", "本期", "我们来"):
            if cleaned.startswith(bad):
                cleaned = re.sub(r"^[^。！？?]+[。！？?]\s*", "", cleaned).strip() or cleaned
        s0["tts_text"] = f"{hook_sent}{cleaned}" if cleaned else hook_sent

    plat = (platform or str(brief.get("platform") or "")).strip().lower()
    if plat == "douyin":
        mp = dict(s0.get("motion_params") or {})
        mp["staggerFrames"] = 2
        mp["springStiffness"] = 220
        mp["springDamping"] = 9
        mp["wordsPerPageMs"] = 380
        s0["motion_params"] = mp
        s0["caption_mode"] = s0.get("caption_mode") or "tiktok"

    slides[0] = s0
    out = dict(script)
    out["slides"] = slides
    return out
