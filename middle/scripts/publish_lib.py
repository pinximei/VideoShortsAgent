"""多平台固定发布 — 共用步骤（供 publish_channel.py 调用）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.platform_presets import get_platform_preset, is_video_platform
from publisher.scripts.registry import BROWSER_CHANNELS

# 爱资讯默认账号（config.yaml channel_accounts）
DEFAULT_ACCOUNTS: dict[str, str] = {
    "douyin": "acc_ai_news_douyin",
    "xhs": "acc_ai_news_xhs",
    "toutiao": "acc_ai_news_toutiao",
    "douban": "acc_ai_news_douban",
}

CHANNEL_LABELS: dict[str, str] = {
    "douyin": "抖音",
    "xhs": "小红书",
    "toutiao": "今日头条",
    "douban": "豆瓣",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_brief(task_dir: Path) -> dict[str, Any]:
    p = task_dir / "brief.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_account_id(cfg, channel_id: str, account_id: str) -> str:
    aid = (account_id or "").strip() or DEFAULT_ACCOUNTS.get(channel_id, "")
    if not aid:
        raise RuntimeError(f"未指定 --account-id，且渠道 {channel_id} 无默认账号")
    acc = next((a for a in cfg.channel_accounts if a.id == aid), None)
    if not acc:
        raise RuntimeError(f"账号不存在: {aid}")
    if acc.channel_id != channel_id:
        raise RuntimeError(f"账号 {aid} 属于 {acc.channel_id}，不能用于 {channel_id}")
    return aid


def step_prepare(cfg, article_id: int, channel_id: str) -> dict[str, Any]:
    from pipeline.db import JobStore
    from pipeline.models import content_key_for_article
    from pipeline.publish_guard import build_publish_bindings, refresh_job_bindings

    task_dir = cfg.output_root / str(article_id)
    brief = load_brief(task_dir)
    if not brief:
        raise RuntimeError(f"缺少 brief.json: {task_dir}")

    theme_id = str(brief.get("theme_id") or "").strip()
    if not theme_id:
        raise RuntimeError("brief.json 缺少 theme_id")

    bindings = build_publish_bindings(cfg, theme_id)
    brief = refresh_job_bindings(cfg, theme_id, brief)
    (task_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    store = JobStore(cfg.db_path)
    ck = content_key_for_article(article_id)
    job = store.get_job(ck)
    if not job:
        store.upsert_discovered(
            content_key=ck,
            article_id=article_id,
            snapshot={"id": article_id, "title": brief.get("title", "")},
            theme_id=theme_id,
        )
    store.update_job(
        ck,
        status="ready_to_publish",
        brief_json=brief,
        theme_id=theme_id,
    )
    ch_bind = (bindings.get("channels") or {}).get(channel_id) or {}
    return {
        "ok": True,
        "theme_id": theme_id,
        "batch_id": bindings.get("batch_id"),
        "account_id": ch_bind.get("account_id"),
    }


def step_preflight(cfg, article_id: int, channel_id: str, account_id: str) -> dict[str, Any]:
    from pipeline.models import content_key_for_article
    from pipeline.pipeline_gates import PipelineGateError, assert_channel_publishable
    from publisher.runner import check_login

    if channel_id not in BROWSER_CHANNELS:
        raise RuntimeError(f"未知渠道: {channel_id}")

    aid = resolve_account_id(cfg, channel_id, account_id)
    acc = next(a for a in cfg.channel_accounts if a.id == aid)
    batch_id = (acc.batch_id or "").strip()
    if not batch_id:
        batch = cfg.publisher.batch_for_site(acc.site_code)
        batch_id = batch.batch_id if batch else ""
    if not batch_id:
        raise RuntimeError("账号未配置 batch_id")

    login = check_login(cfg, batch_id, acc)
    if not login.get("logged_in"):
        label = CHANNEL_LABELS.get(channel_id, channel_id)
        raise RuntimeError(
            f"{label}未登录 account={aid}，请先运行:\n"
            f"  py -3.12 scripts/open_platform_login.py --account-id {aid}"
        )

    from pipeline.db import JobStore

    store = JobStore(cfg.db_path)
    ck = content_key_for_article(article_id)
    job = store.get_job(ck)
    if not job:
        raise RuntimeError(f"任务不存在: article_id={article_id}，请加 --prepare")

    try:
        asset = assert_channel_publishable(cfg, article_id, channel_id, job=job)
    except PipelineGateError as e:
        raise RuntimeError(f"发布门禁未通过: {e.code}: {e.message}") from e

    task_dir = cfg.output_root / str(article_id)
    preset = get_platform_preset(channel_id)
    if is_video_platform(channel_id):
        if not (task_dir / "publish" / f"{channel_id}_title.txt").is_file():
            raise RuntimeError(f"缺少 publish/{channel_id}_title.txt")
    else:
        if not asset.is_file() or not asset.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"缺少或为空: publish/{preset.publish_file}")

    return {
        "ok": True,
        "account_id": aid,
        "batch_id": batch_id,
        "logged_in": True,
        "asset": str(asset),
        "kind": preset.content_kind,
    }


def step_dry_run(cfg, article_id: int, channel_id: str, account_id: str) -> dict[str, Any]:
    from publisher.runner import PublishRequest, publish_content

    aid = resolve_account_id(cfg, channel_id, account_id)
    result = publish_content(
        cfg,
        PublishRequest(
            article_id=article_id,
            channel_id=channel_id,
            account_id=aid,
            dry_run=True,
        ),
    )
    out = {
        "ok": result.ok,
        "batch_id": result.batch_id,
        "account_id": result.account_id,
        "steps": result.steps,
        "script": result.script,
    }
    if not result.ok:
        raise RuntimeError(f"dry-run 失败: {out}")
    return out


def _strict_publish_confirmed(cfg, out: dict) -> bool:
    if not getattr(cfg.publisher, "strict_publish", True):
        return True
    if not out.get("publish_confirmed") and not out.get("ok"):
        return False
    ev = out.get("evidence") or {}
    detail = str(ev.get("detail") or "")
    final_url = str(ev.get("final_url") or "")
    steps = out.get("steps") or []
    last = steps[-1] if steps else {}
    last_detail = str(last.get("detail") or detail)
    toast_txt = str(ev.get("toast") or "")
    if "toast" in last_detail or last_detail == "toast_ok":
        return True
    if "发布成功" in last_detail or "已发布" in last_detail:
        return True
    if "发布成功" in toast_txt or "已发布" in toast_txt:
        return True
    if "body_text_success" in last_detail:
        return True
    if "/publish/success" in final_url:
        return True
    if out.get("channel_id") == "douyin":
        if "manage_list" in detail or "manage_page_match" in detail:
            return True
        if "content/post/video" in final_url or "content/upload" in final_url:
            return False
        if detail in ("发布成功", "已发布") and "manage" not in final_url:
            return False
        return False
    if out.get("channel_id") == "toutiao" and "manage_list" in detail:
        return True
    if out.get("channel_id") == "douban" and (
        "note_url" in detail or "notes_list_item_match" in detail
    ):
        return True
    if out.get("channel_id") == "douban" and "/note/" in final_url and "create" not in final_url:
        return True
    return False


def _close_browser_pool(cfg) -> None:
    try:
        from publisher.browser_pool import get_pool

        get_pool(cfg.publisher).close_all()
    except Exception:
        pass


def step_publish(
    cfg, article_id: int, channel_id: str, account_id: str, *, retries: int = 2
) -> dict[str, Any]:
    from publisher.runner import PublishRequest, publish_content

    aid = resolve_account_id(cfg, channel_id, account_id)
    if channel_id in (cfg.publisher.headed_channels or []):
        _close_browser_pool(cfg)
    last_err: Exception | None = None
    for attempt in range(1, retries + 2):
        result = publish_content(
            cfg,
            PublishRequest(
                article_id=article_id,
                channel_id=channel_id,
                account_id=aid,
                dry_run=False,
            ),
        )
        out = {
            "ok": result.ok,
            "channel_id": channel_id,
            "batch_id": result.batch_id,
            "account_id": result.account_id,
            "steps": result.steps,
            "script": result.script,
            "publish_confirmed": result.ok,
            "evidence": result.evidence or {},
            "attempt": attempt,
        }
        report_side = (
            cfg.output_root
            / str(article_id)
            / "publish"
            / f"{channel_id}_publish_steps.json"
        )
        write_report(report_side, out)
        if result.ok and _strict_publish_confirmed(cfg, out):
            return out
        if result.ok and not _strict_publish_confirmed(cfg, out):
            out["ok"] = False
            out["publish_confirmed"] = False
            out["strict_reject"] = "weak_publish_confirm_not_allowed"
            write_report(report_side, out)
            last_err = RuntimeError(
                f"严格模式：未检测到 toast/成功页，视为未发布 evidence={out.get('evidence')}"
            )
            if attempt <= retries:
                import time

                time.sleep(3)
                continue
            raise last_err
        failed = [s for s in result.steps if not s.get("ok")]
        last_err = RuntimeError(f"发布失败 steps={failed}")
        if attempt <= retries:
            import time

            time.sleep(3)
            continue
    raise last_err or RuntimeError("发布失败")


def step_verify(
    cfg, article_id: int, channel_id: str, account_id: str, *, retries: int = 1
) -> dict[str, Any]:
    from publisher.verify import VerifyRequest, verify_published

    aid = resolve_account_id(cfg, channel_id, account_id)
    last_err: Exception | None = None
    for attempt in range(1, retries + 2):
        result = verify_published(
            cfg,
            VerifyRequest(
                article_id=article_id,
                channel_id=channel_id,
                account_id=aid,
            ),
        )
        out = {
            "ok": result.ok,
            "verified": result.verified,
            "batch_id": result.batch_id,
            "account_id": result.account_id,
            "steps": result.steps,
            "script": result.script,
            "evidence": result.evidence,
            "title_needle": result.title_needle,
            "attempt": attempt,
        }
        report_path = (
            cfg.output_root
            / str(article_id)
            / "publish"
            / f"{channel_id}_publish_verify.json"
        )
        write_report(report_path, out)
        if result.ok:
            return out
        last_err = RuntimeError(
            f"发布后验收失败 needle={result.title_needle!r} evidence={result.evidence}"
        )
        if attempt <= retries:
            import time

            time.sleep(5)
            continue
    raise last_err or RuntimeError("发布后验收失败")


def step_mark(cfg, article_id: int, channel_id: str, note: str) -> dict[str, Any]:
    from pipeline.db import JobStore
    from pipeline.models import content_key_for_article
    from pipeline.pipeline_gates import PipelineGateError, assert_channel_publishable

    store = JobStore(cfg.db_path)
    ck = content_key_for_article(article_id)
    job = store.get_job(ck)
    if not job:
        raise RuntimeError("无任务，无法 mark")
    try:
        assert_channel_publishable(cfg, article_id, channel_id, job=job)
    except PipelineGateError as e:
        raise RuntimeError(f"mark 门禁: {e.code}: {e.message}") from e
    verify_path = cfg.output_root / str(article_id) / "publish" / f"{channel_id}_publish_verify.json"
    if verify_path.is_file():
        try:
            vdoc = json.loads(verify_path.read_text(encoding="utf-8"))
            if not vdoc.get("ok"):
                raise RuntimeError(
                    f"发布验收未通过，禁止 mark：见 {verify_path.name}"
                )
        except json.JSONDecodeError:
            pass

    created = store.mark_published(ck, channel_id, note or "publish_channel.py")
    return {"ok": True, "created": created, "content_key": ck}
