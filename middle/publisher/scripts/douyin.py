"""抖音创作者中心 — 固定步骤脚本（非 LLM）。"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from .base import PlatformPublishScript, PublishPack, ScriptStepResult
from .common import (
    click_confirm_dialogs,
    extract_hashtags,
    page_contains_needle,
    screenshot_on_fail,
    sleep_ms,
    wait_for_toast_ok,
    wait_manage_list_has_needle,
    wait_spa_content_ready,
)
from .format_copy import format_douyin_title_desc

CREATOR_UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"
CREATOR_PUBLISH_URL = (
    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page"
)
MANAGE_URL = "https://creator.douyin.com/creator-micro/content/manage"
SEL_LOGIN = "text=扫码登录"
SEL_FILE_INPUT = 'input[type="file"]'
SEL_TITLE = (
    'input[placeholder*="作品标题"], input[placeholder*="标题"], '
    'textarea[placeholder*="标题"], div[data-placeholder*="标题"]'
)
SEL_DESC = (
    'div[contenteditable="true"][placeholder*="作品简介"], '
    'div[contenteditable="true"], '
    'textarea[placeholder*="简介"], textarea[placeholder*="描述"], '
    'div[placeholder*="添加作品简介"], div[contenteditable][data-placeholder*="简介"]'
)
TITLE_MAX = 30
UPLOAD_READY_TIMEOUT_MS = 600_000


class DouyinPublishScript(PlatformPublishScript):
    channel_id = "douyin"
    creator_url = CREATOR_UPLOAD_URL
    fixed_steps = (
        "open_creator_upload",
        "assert_logged_in",
        "upload_video_file",
        "wait_video_ready",
        "fill_title_and_desc",
        "fill_declaration",
        "click_publish",
        "wait_publish_result",
    )

    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        results: list[ScriptStepResult] = []
        evidence: dict[str, Any] = {}

        short_title, desc = self._load_douyin_copy(pack)
        publish_dir = (pack.output_dir or Path(".")) / "publish"

        try:
            page.goto(CREATOR_UPLOAD_URL, wait_until="domcontentloaded", timeout=90_000)
            sleep_ms(2000)
            self._snap(page, publish_dir, "douyin_step_upload_open.png")
            self.step_log(results, "open_creator_upload", True, page.url)
        except Exception as e:
            self.step_log(results, "open_creator_upload", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        if page.locator(SEL_LOGIN).count() > 0:
            self.step_log(results, "assert_logged_in", False, "需要扫码登录")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self.step_log(results, "assert_logged_in", True)

        if not pack.video_path or not pack.video_path.is_file():
            self.step_log(results, "upload_video_file", False, "视频不存在")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        try:
            inp = page.locator(SEL_FILE_INPUT).first
            inp.wait_for(state="attached", timeout=30_000)
            inp.set_input_files(str(pack.video_path.resolve()))
            self.step_log(results, "upload_video_file", True, pack.video_path.name)
        except Exception as e:
            self.step_log(results, "upload_video_file", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ready, detail = self._wait_upload_and_publish_ready(page)
        self.step_log(results, "wait_video_ready", ready, detail)
        if not ready:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self._snap(page, publish_dir, "douyin_step_upload_ready.png")

        self._ensure_cover_if_required(page)
        decl_ok = self._fill_self_declaration(page)
        if not decl_ok:
            self.step_log(results, "fill_declaration", False, "required")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self.step_log(results, "fill_declaration", True, "ok")

        try:
            tloc = page.locator(SEL_TITLE)
            if tloc.count():
                tloc.first.click()
                sleep_ms(200)
                tloc.first.fill("")
                tloc.first.fill(short_title[:TITLE_MAX])
            if desc:
                filled = self._fill_description(page, desc)
                if not filled:
                    self.step_log(results, "fill_title_and_desc", False, "desc_not_applied")
                    return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
            tags = extract_hashtags(desc or pack.body or "")
            if tags:
                topic = page.locator('input[placeholder*="话题"], input[placeholder*="添加话题"]')
                if topic.count():
                    topic.first.fill(" ".join(f"#{t}" for t in tags[:5]))
            title_ok = self._title_applied(page, short_title)
            self.step_log(
                results,
                "fill_title_and_desc",
                title_ok,
                f"title={short_title[:20]} desc_len={len(desc)} title_ok={title_ok}",
            )
            if not title_ok:
                return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        except Exception as e:
            self.step_log(results, "fill_title_and_desc", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self._snap(page, publish_dir, "douyin_step_filled.png")

        clicked = False
        click_detail = ""
        for attempt in range(5):
            btn, detail = self._find_publish_button(page)
            click_detail = detail
            if not btn:
                sleep_ms(1500)
                continue
            try:
                btn.scroll_into_view_if_needed()
                btn.click(timeout=15_000)
                sleep_ms(1200)
                click_confirm_dialogs(page)
                sleep_ms(1200)
                for txt in ("确认发布", "立即发布", "发布", "完成"):
                    loc = page.get_by_role("button", name=txt)
                    if loc.count():
                        try:
                            loc.first.click(timeout=5_000)
                            sleep_ms(800)
                        except Exception:
                            pass
                click_confirm_dialogs(page)
                sleep_ms(2000)
                err = self._publish_blocking_error(page)
                if err:
                    self.step_log(results, "click_publish", False, err)
                    sleep_ms(1000)
                    continue
                self._snap(page, publish_dir, f"douyin_step_after_click_{attempt + 1}.png")
                clicked = True
                self.step_log(results, "click_publish", True, f"{detail}:try{attempt + 1}")
                break
            except Exception as e:
                self.step_log(results, "click_publish", False, str(e)[:120])
        if not clicked:
            self.step_log(results, "click_publish", False, click_detail or "no_button")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        confirmed, ev = self._wait_publish_success(page, short_title)
        self._snap(page, publish_dir, "douyin_step_final.png")
        evidence.update(ev)
        self.step_log(results, "wait_publish_result", confirmed, ev.get("detail", ""))
        return self._out(results, ok=confirmed, evidence=evidence, pack=pack, page=page)

    def _load_douyin_copy(self, pack: PublishPack) -> tuple[str, str]:
        publish_dir = (pack.output_dir or Path(".")) / "publish"
        title_path = publish_dir / "douyin_title.txt"
        full_title = (
            title_path.read_text(encoding="utf-8").strip()
            if title_path.is_file()
            else (pack.title or "").strip()
        )
        desc_path = publish_dir / "douyin_desc.txt"
        desc = desc_path.read_text(encoding="utf-8").strip() if desc_path.is_file() else ""
        if not desc and (pack.body or "").strip():
            desc = pack.body.strip()
        short, formatted = format_douyin_title_desc(full_title, desc)
        return short, formatted

    def _upload_still_processing(self, page: Any) -> bool:
        markers = (
            "上传中",
            "转码中",
            "处理中",
            "正在上传",
            "视频上传中",
            "文件解析",
            "请稍等",
            "解析中",
            "封面生成中",
        )
        try:
            body = page.locator("body").inner_text(timeout=5_000)
            if "上传失败" in body:
                return True
            if "重新上传" in body:
                if re.search(r"(?<![\d])100%(?!\d)", body):
                    return False
                if not re.search(r"\d{1,2}%", body):
                    return False
            if re.search(r"\d{1,2}%", body) and "100%" not in body:
                return True
            return any(m in body for m in markers)
        except Exception:
            return False

    def _fill_self_declaration(self, page: Any) -> bool:
        """自主声明弹窗：选「内容由AI生成」并点确定。"""
        body = self._body_text(page)
        if "自主声明" not in body and "对作品内容添加声明" not in body:
            return True
        if "请选择自主声明" not in body and "对作品内容添加声明" not in body:
            return True
        try:
            if page.get_by_text("请选择自主声明").count():
                page.get_by_text("请选择自主声明").first.click(timeout=5_000)
                sleep_ms(800)
            for opt in (
                "内容由AI生成",
                "内容为个人观点或见解",
                "无需添加自主声明",
                "内容取材网络",
            ):
                radio = page.locator(f'label.semi-radio:has-text("{opt}")')
                if radio.count():
                    radio.first.click(force=True, timeout=4_000)
                    sleep_ms(400)
                    break
                loc = page.get_by_text(opt, exact=True)
                if loc.count():
                    loc.first.click(force=True, timeout=4_000)
                    sleep_ms(400)
                    break
            confirm = page.get_by_role("button", name="确定")
            if confirm.count():
                try:
                    if not confirm.first.is_disabled():
                        confirm.first.click(timeout=5_000)
                        sleep_ms(600)
                except Exception:
                    confirm.first.click(force=True, timeout=5_000)
                    sleep_ms(600)
            click_confirm_dialogs(page)
        except Exception:
            pass
        body_after = self._body_text(page)
        return "请选择自主声明" not in body_after and "对作品内容添加声明" not in body_after

    def _wait_upload_and_publish_ready(self, page: Any) -> tuple[bool, str]:
        deadline = time.time() + UPLOAD_READY_TIMEOUT_MS / 1000.0
        last = ""
        stable_ready = 0
        while time.time() < deadline:
            if self._upload_still_processing(page):
                last = "upload_processing"
                stable_ready = 0
                sleep_ms(1500)
                continue
            btn, detail = self._find_publish_button(page)
            last = detail
            if btn is not None:
                stable_ready += 1
                if stable_ready >= 2:
                    return True, detail
            else:
                stable_ready = 0
            sleep_ms(1000)
        return False, f"timeout:{last}"

    def _body_text(self, page: Any) -> str:
        try:
            return page.locator("body").inner_text(timeout=5_000)
        except Exception:
            return ""

    def _title_applied(self, page: Any, short_title: str) -> bool:
        needle = short_title[:6].replace("？", "").replace("?", "")
        for sel in (SEL_TITLE, 'input[placeholder*="作品标题"]'):
            loc = page.locator(sel)
            if loc.count():
                try:
                    val = loc.first.input_value(timeout=3_000)
                    if needle and needle in val.replace("？", "").replace("?", ""):
                        return True
                except Exception:
                    pass
        body = self._body_text(page).replace(" ", "")
        return bool(needle and needle in body.replace("？", "").replace("?", ""))

    def _fill_description(self, page: Any, desc: str) -> bool:
        """抖音描述多为 contenteditable，需点击后键盘输入。"""
        selectors = (
            SEL_DESC,
            'div[contenteditable="true"]',
            'div.notranslate[contenteditable="true"]',
            'div[class*="editor"] [contenteditable="true"]',
        )
        for sel in selectors:
            loc = page.locator(sel)
            if not loc.count():
                continue
            box = loc.first
            try:
                box.click(timeout=5_000)
                sleep_ms(300)
                page.keyboard.press("Control+A")
                sleep_ms(100)
                page.keyboard.press("Backspace")
                sleep_ms(100)
                page.keyboard.type(desc[:1000], delay=10)
                sleep_ms(500)
                body = self._body_text(page)
                if "0/30" in body and len(desc) > 5:
                    continue
                if desc[:6].replace(" ", "") in body.replace(" ", ""):
                    return True
            except Exception:
                continue
        dloc = page.locator(SEL_DESC)
        if dloc.count():
            try:
                dloc.first.fill(desc)
                sleep_ms(400)
                return desc[:6] in self._body_text(page)
            except Exception:
                pass
        return False

    def _publish_blocking_error(self, page: Any) -> str:
        for bad in (
            "请设置封面",
            "请选择封面",
            "请填写作品",
            "作品描述不能为空",
            "上传未完成",
            "请等待上传",
            "请选择自主声明",
            "发布失败",
        ):
            if page.locator(f"text={bad}").count():
                return bad
        return ""

    def _still_on_publish_editor(self, page: Any) -> bool:
        url = page.url or ""
        if any(p in url for p in ("content/upload", "content/publish", "content/post/video")):
            body = self._body_text(page)
            if "0/30" in body or "高清发布" in body and "作品描述" in body:
                return True
        return False

    def _ensure_cover_if_required(self, page: Any) -> None:
        body = self._body_text(page)
        if "封面生成中" in body or "智能推荐封面生成" in body:
            deadline = time.time() + 90
            while time.time() < deadline and (
                "封面生成中" in self._body_text(page) or "智能推荐封面生成" in self._body_text(page)
            ):
                sleep_ms(1500)
        for sel in (
            'div[class*="cover"] img',
            'div[class*="Cover"] img',
            '[class*="coverPick"] img',
            '[class*="coverCard"] img',
            'img[class*="cover"]',
        ):
            loc = page.locator(sel)
            if loc.count():
                try:
                    loc.first.click(timeout=5_000)
                    sleep_ms(600)
                    click_confirm_dialogs(page)
                    return
                except Exception:
                    pass
        if any(k in body for k in ("请设置封面", "选择封面", "设置封面")):
            try:
                page.get_by_text("设置封面", exact=False).first.click(timeout=4_000)
                sleep_ms(800)
                thumbs = page.locator('[class*="cover"] img, [class*="Cover"] img')
                if thumbs.count():
                    thumbs.first.click(timeout=4_000)
                    sleep_ms(400)
                click_confirm_dialogs(page)
            except Exception:
                pass

    def _find_publish_button(self, page: Any) -> tuple[Any | None, str]:
        skip_words = ("草稿", "定时", "预览", "取消")
        candidates: list[tuple[Any, str]] = []

        def _ok(btn: Any) -> bool:
            try:
                if not btn.is_visible() or btn.is_disabled():
                    return False
                txt = (btn.inner_text(timeout=1_000) or "").strip()
                if any(w in txt for w in skip_words):
                    return False
                return "发布" in txt
            except Exception:
                return False

        for sel in (
            'div[class*="submit"] button:has-text("发布")',
            'div[class*="footer"] button:has-text("发布")',
            'button[class*="primary"]:has-text("发布")',
        ):
            loc = page.locator(sel)
            for i in range(loc.count() - 1, -1, -1):
                btn = loc.nth(i)
                if _ok(btn):
                    candidates.append((btn, sel))

        try:
            buttons = page.get_by_role("button", name="发布")
            for i in range(buttons.count() - 1, -1, -1):
                btn = buttons.nth(i)
                if _ok(btn):
                    candidates.append((btn, "role=发布"))
        except Exception:
            pass

        if candidates:
            return candidates[0]
        return None, "publish_button_not_found"

    def _wait_publish_success(self, page: Any, title: str) -> tuple[bool, dict[str, Any]]:
        """必须离开发布编辑页，且在作品管理列表匹配标题（toast  alone 不算）。"""
        sleep_ms(2000)
        deadline = time.time() + 120
        while time.time() < deadline:
            url = page.url or ""
            if self._still_on_publish_editor(page):
                sleep_ms(800)
                continue
            if "content/manage" in url:
                ready, _ = wait_spa_content_ready(page, timeout_ms=15_000)
                if ready and page_contains_needle(page, title):
                    return True, {"detail": "manage_page_match", "final_url": url}
            ok, ev = wait_for_toast_ok(
                page,
                timeout_ms=2_000,
                ok_patterns=("发布成功", "已发布", "作品发布成功", "提交成功"),
            )
            if ok and not self._still_on_publish_editor(page):
                ev["final_url"] = url
                if "content/manage" in url or page_contains_needle(page, title):
                    return True, ev
            sleep_ms(800)

        ok, ev = wait_manage_list_has_needle(
            page,
            MANAGE_URL,
            title,
            timeout_ms=120_000,
            tab_labels=("已发布", "全部", "审核中", "草稿", ""),
        )
        if ok:
            return True, ev
        try:
            page.screenshot(path=str(Path.cwd() / "douyin_manage_fail.png"), full_page=True)
        except Exception:
            pass
        return False, {
            "detail": "manage_list_no_match",
            "final_url": page.url,
        }

    def _out(
        self,
        results: list[ScriptStepResult],
        *,
        ok: bool,
        evidence: dict[str, Any],
        pack: PublishPack | None = None,
        page: Any | None = None,
    ) -> dict[str, Any]:
        if not ok and page is not None and pack is not None:
            screenshot_on_fail(page, pack, "douyin_last.png")
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "publish_confirmed": ok,
            "evidence": evidence,
            "steps": [r.__dict__ for r in results],
            "script": "douyin_fixed_v5",
        }

    def _snap(self, page: Any, publish_dir: Path, name: str) -> None:
        try:
            publish_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(publish_dir / name), full_page=True)
        except Exception:
            pass


class DouyinLoginScript:
    creator_url = CREATOR_UPLOAD_URL

    def check(self, page: Any) -> dict[str, Any]:
        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=90_000)
        sleep_ms(4000)
        url = (page.url or "").lower()
        has_upload = page.locator(SEL_FILE_INPUT).count() > 0
        on_creator = "creator.douyin.com" in url
        login_url = "/login" in url or "passport" in url
        login_gate = page.locator(SEL_LOGIN).count() > 0 and not has_upload
        logged_in = has_upload or (on_creator and not login_url and not login_gate)
        return {
            "channel_id": "douyin",
            "logged_in": logged_in,
            "need_login": not logged_in,
            "script": "douyin_login_check_v2",
            "detail": url[:100],
        }
