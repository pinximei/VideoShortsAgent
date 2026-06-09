"""各平台验收共用逻辑。"""
from __future__ import annotations

import json
from typing import Any

from publisher.scripts.common import sleep_ms

from ..pack import VerifyPack


def try_evidence_url(page: Any, pack: VerifyPack) -> tuple[bool, dict[str, Any]]:
    """若发布阶段留下 final_url，优先打开该页校验。"""
    ev = dict(pack.publish_evidence or {})
    url = str(ev.get("final_url") or ev.get("note_url") or "").strip()
    if not url or url.startswith("about:"):
        return False, {"detail": "no_publish_url"}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        sleep_ms(2000)
        if "content/post/video" in url or "content/upload" in url:
            try:
                body = page.locator("body").inner_text(timeout=8_000)
                if "0/30" in body and "作品描述" in body:
                    return False, {"detail": "still_on_publish_editor", "url": url}
            except Exception:
                pass
        html = page.content()
        needle = pack.title_needle
        if needle and needle in html.replace(" ", ""):
            return True, {"detail": "publish_url_match", "url": url}
        if pack.title and pack.title[:12] in html:
            return True, {"detail": "publish_url_title_match", "url": url}
    except Exception as e:
        return False, {"detail": f"publish_url_error:{str(e)[:80]}"}
    return False, {"detail": "publish_url_no_match", "url": url}


def find_needle_on_page(page: Any, pack: VerifyPack, *, scroll_times: int = 3) -> tuple[bool, str]:
    needles: list[str] = []
    if pack.title_needle:
        needles.append(pack.title_needle)
        if len(pack.title_needle) > 8:
            needles.append(pack.title_needle[:8])
    if pack.title and pack.title not in needles:
        needles.append(pack.title.replace(" ", "")[:18])
        if len(pack.title) >= 6:
            needles.append(pack.title[:6])
    if not needles:
        return False, "empty_needle"
    for _ in range(scroll_times + 1):
        for needle in needles:
            try:
                body = page.locator("body").inner_text(timeout=5_000)
                compact = body.replace(" ", "").replace("\n", "")
                if needle in compact:
                    return True, f"body_text:{needle[:8]}"
            except Exception:
                pass
            try:
                loc = page.get_by_text(needle, exact=False)
                if loc.count() > 0:
                    return True, f"locator:{needle[:8]}"
            except Exception:
                pass
        try:
            page.mouse.wheel(0, 600)
            sleep_ms(500)
        except Exception:
            break
    return False, "needle_not_found"


def assert_logged_in_generic(page: Any, *, login_markers: tuple[str, ...]) -> tuple[bool, str]:
    url = page.url or ""
    for m in login_markers:
        if m in url:
            return False, f"login_redirect:{url[:80]}"
    return True, url[:80]


def check_publish_steps_fallback(
    pack: VerifyPack, *, strict: bool = True
) -> tuple[bool, str]:
    """列表未及时索引时的备用验收。strict 时仅认 toast/明确成功文案，避免误报已发布。"""
    p = pack.output_dir / "publish" / f"{pack.channel_id}_publish_steps.json"
    if not p.is_file():
        return False, "no_steps_file"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False, "bad_steps_file"
    if not (doc.get("publish_confirmed") or doc.get("ok")):
        return False, "publish_not_confirmed"
    steps = doc.get("steps") or []
    last = steps[-1] if steps else {}
    detail = str(last.get("detail") or "")
    if last.get("step") != "wait_publish_result" or not last.get("ok"):
        return False, "publish_steps_weak"
    ev = doc.get("evidence") or {}
    final_url = str(ev.get("final_url") or "")
    if strict:
        if "toast" in detail or detail in ("发布成功", "toast_ok", "已发布"):
            return True, f"publish_steps:{detail}"
        if "已发布" in str(ev.get("toast") or ""):
            return True, "publish_steps:已发布"
        if "/publish/success" in final_url or "note-manager" in final_url:
            return True, f"publish_steps:url:{final_url[:60]}"
        if "manage_list_match" in detail or "manage_page_match" in detail:
            return True, f"publish_steps:{detail}"
        if "topic_url" in detail or "notes_list" in detail:
            return True, f"publish_steps:{detail}"
        return False, f"publish_steps_not_strict:{detail}"
    weak_ok = ("toast", "发布成功", "success", "manage")
    if any(k in detail for k in weak_ok):
        return True, f"publish_steps:{detail or 'ok'}"
    return False, "publish_steps_weak"
