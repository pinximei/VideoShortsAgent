"""各平台固定发布脚本共用工具。"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from .base import PublishPack


def sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000.0)


def extract_hashtags(text: str) -> list[str]:
    return re.findall(r"#([^\s#]{1,30})", text or "")


def fill_editor_content(
    page: Any,
    locator: Any,
    plain_text: str,
    *,
    html: str | None = None,
) -> None:
    """向 contenteditable 填入分段正文：优先 HTML 粘贴，否则逐段 Enter。"""
    locator.click(force=True, timeout=15_000)
    sleep_ms(250)
    pasted = False
    if html:
        try:
            locator.evaluate(
                """(el, payload) => {
                    el.focus();
                    el.innerHTML = payload.html;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                {"html": html},
            )
            sleep_ms(500)
            pasted = True
        except Exception:
            pasted = False
    if not pasted:
        try:
            locator.fill("")
        except Exception:
            pass
        page.keyboard.press("Control+A")
        sleep_ms(80)
        paragraphs = [ln for ln in (plain_text or "").split("\n")]
        for i, line in enumerate(paragraphs):
            if line.strip():
                page.keyboard.type(line, delay=10)
            if i < len(paragraphs) - 1:
                page.keyboard.press("Enter")
                if not line.strip():
                    page.keyboard.press("Enter")
                sleep_ms(60)


def split_title_body(text: str) -> tuple[str, str]:
    lines = [ln.strip() for ln in (text or "").splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    if not lines:
        return "", ""
    if len(lines) == 1:
        return lines[0][:80], ""
    return lines[0][:80], "\n".join(lines[1:]).strip()


def screenshot_on_fail(page: Any, pack: PublishPack, name: str) -> None:
    if not pack.output_dir:
        return
    out = pack.output_dir / "publish" / name
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out), full_page=True)
    except Exception:
        pass


def wait_spa_content_ready(
    page: Any,
    *,
    loading_markers: tuple[str, ...] = ("加载中", "Loading...", "请稍候"),
    min_body_len: int = 60,
    timeout_ms: int = 120_000,
) -> tuple[bool, str]:
    """等待 SPA 列表/页面脱离纯 loading 状态。"""
    deadline = time.time() + timeout_ms / 1000.0
    last = ""
    while time.time() < deadline:
        try:
            body = page.locator("body").inner_text(timeout=8_000)
            last = body[:80].replace("\n", " ")
            compact = body.replace(" ", "").replace("\n", "")
            if any(m in body for m in loading_markers) and len(compact) < min_body_len:
                sleep_ms(900)
                continue
            if len(compact) >= min_body_len:
                return True, "spa_ready"
        except Exception as e:
            last = str(e)[:60]
        sleep_ms(900)
    return False, f"spa_timeout:{last}"


def click_confirm_dialogs(page: Any) -> None:
    for txt in (
        "确认发布",
        "确定发布",
        "确定",
        "我知道了",
        "知道了",
        "声明原创",
        "同意",
        "继续发布",
        "暂不设置",
        "跳过",
        "使用推荐封面",
        "智能推荐",
    ):
        loc = page.locator(f"button:has-text('{txt}')")
        if loc.count():
            try:
                loc.first.click(timeout=3_000)
                sleep_ms(400)
            except Exception:
                pass


def page_contains_needle(page: Any, needle: str, *, min_len: int = 6) -> bool:
    if not needle or len(needle.strip()) < min_len:
        return False
    n = needle.strip().replace(" ", "")[:24]
    try:
        body = page.locator("body").inner_text(timeout=8_000)
        compact = body.replace(" ", "").replace("\n", "")
        return n in compact
    except Exception:
        return False


def _needles_for_match(needle: str, *, allow_generic: bool = True) -> list[str]:
    """仅使用标题相关 needle；禁止用「AI上下文」等泛词误匹配页面模板文案。"""
    n = (needle or "").strip()
    out: list[str] = []
    pieces = [n, n[:24], n[:16], n[:12]]
    if allow_generic:
        pieces.extend(["Bluedot", "Apple Watch"])
    for piece in pieces:
        p = piece.strip()
        if len(p) >= 8 and p not in out:
            out.append(p)
    return out or ([n[:12]] if len(n) >= 8 else [n])


def _list_item_has_title(page: Any, title: str) -> bool:
    """在列表页用链接/标题节点匹配，避免编辑器残留标题导致 body 误匹配。"""
    t = (title or "").strip()
    if len(t) < 8:
        return False
    for sel in (
        f'a:has-text("{t[:40]}")',
        f'[class*="title"]:has-text("{t[:30]}")',
        f'article:has-text("{t[:30]}")',
    ):
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return True
        except Exception:
            continue
    try:
        loc = page.get_by_text(t[:30], exact=False)
        if loc.count() > 0:
            for i in range(min(loc.count(), 5)):
                if loc.nth(i).is_visible():
                    tag = loc.nth(i).evaluate("el => el.tagName")
                    if tag and tag.lower() in ("a", "h1", "h2", "h3", "article", "li"):
                        return True
    except Exception:
        pass
    return False


def wait_manage_list_has_needle(
    page: Any,
    manage_url: str,
    needle: str,
    *,
    timeout_ms: int = 90_000,
    scroll_times: int = 4,
    tab_labels: tuple[str, ...] = ("", "已发布", "审核中", "草稿", "全部"),
    allow_generic_needles: bool = True,
    require_list_item: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """打开作品管理/列表页，切换 Tab 并滚动查找标题。"""
    ev: dict[str, Any] = {"manage_url": manage_url, "needle": needle[:24]}
    needles = _needles_for_match(needle, allow_generic=allow_generic_needles)
    try:
        page.goto(manage_url, wait_until="domcontentloaded", timeout=90_000)
        sleep_ms(2000)
        ready, spa_detail = wait_spa_content_ready(page, timeout_ms=90_000)
        ev["spa"] = spa_detail
        if not ready:
            try:
                page.reload(wait_until="domcontentloaded", timeout=60_000)
                sleep_ms(2000)
                ready, spa_detail = wait_spa_content_ready(page, timeout_ms=60_000)
                ev["spa_reload"] = spa_detail
            except Exception:
                pass
    except Exception as e:
        ev["detail"] = f"goto_manage_fail:{str(e)[:60]}"
        return False, ev
    deadline = time.time() + timeout_ms / 1000.0
    tab_i = 0
    while time.time() < deadline:
        if tab_labels:
            label = tab_labels[tab_i % len(tab_labels)]
            tab_i += 1
            if label:
                try:
                    t = page.get_by_text(label, exact=True)
                    if t.count():
                        t.first.click(timeout=3_000)
                        sleep_ms(1200)
                except Exception:
                    pass
        if require_list_item and _list_item_has_title(page, needle):
            ev["detail"] = "manage_list_item_match"
            ev["matched"] = needle[:24]
            ev["final_url"] = page.url
            return True, ev
        if not require_list_item:
            for nd in needles:
                if page_contains_needle(page, nd):
                    ev["detail"] = "manage_list_match"
                    ev["matched"] = nd
                    ev["final_url"] = page.url
                    return True, ev
        for _ in range(scroll_times):
            try:
                page.mouse.wheel(0, 700)
                sleep_ms(500)
            except Exception:
                break
        sleep_ms(600)
    ev["detail"] = "manage_list_no_match"
    ev["final_url"] = page.url
    return False, ev


def wait_for_toast_ok(
    page: Any,
    *,
    timeout_ms: int = 90_000,
    ok_patterns: tuple[str, ...] = (
        "发布成功",
        "已发布",
        "发布完成",
        "提交成功",
        "审核中",
    ),
    fail_patterns: tuple[str, ...] = ("发布失败",),
) -> tuple[bool, dict[str, Any]]:
    ev: dict[str, Any] = {}
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        for bad in fail_patterns:
            if page.locator(f"text={bad}").count():
                ev["detail"] = bad
                return False, ev
        for good in ok_patterns:
            if page.locator(f"text={good}").count():
                ev["detail"] = good
                ev["toast"] = good
                return True, ev
        sleep_ms(700)
    ev["detail"] = "no_toast"
    ev["final_url"] = page.url
    return False, ev
