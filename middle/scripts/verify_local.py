#!/usr/bin/env python3
"""本地端到端验证：Soul 拉取 → Brief → 文案包 → 去重 → 发布台账。"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import PipelineConfig, load_config
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.orchestrator import run_pipeline


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    raise SystemExit(1)


def main() -> int:
    base_cfg = load_config(ROOT / "config.yaml")
    tmp = Path(tempfile.mkdtemp(prefix="aisoul-pipeline-verify-"))
    data_dir = tmp / "data"
    print(f"验证目录: {tmp}\n")

    cfg = PipelineConfig(
        soul_base_url=base_cfg.soul_base_url,
        soul_feed=base_cfg.soul_feed,
        soul_replication_high_value=base_cfg.soul_replication_high_value,
        soul_published_within_days=base_cfg.soul_published_within_days,
        soul_page_size=base_cfg.soul_page_size,
        min_worth_score=base_cfg.min_worth_score,
        feed_kinds=base_cfg.feed_kinds,
        data_dir=data_dir,
        vsa_root=base_cfg.vsa_root,
        public_base_url=base_cfg.public_base_url,
        render_enabled=False,
    )

    print("1) 首轮 pipeline（发现 + 打包）")
    s1 = run_pipeline(cfg)
    print(
        f"     discovered={s1.discovered} packed={s1.packed} skipped={s1.skipped} failed={s1.failed}"
    )
    if s1.failed > 0:
        for e in s1.errors:
            print(f"     {e}")
        _fail("首轮存在 failed")
    if s1.packed < 1 and s1.discovered < 1:
        _fail("未从 Soul 拉到任何候选（检查网络或 API）")
    _ok(f"首轮完成 packed={s1.packed}")

    store = JobStore(cfg.db_path)
    packed = [j for j in store.list_jobs() if j["status"] == "packed"]
    if not packed:
        _fail("无 packed 任务")
    sample = packed[0]
    aid = int(sample["article_id"])
    out_dir = Path(sample["output_dir"])
    if not out_dir.is_dir():
        out_dir = data_dir / "output" / str(aid)
    required = [
        out_dir / "brief.json",
        out_dir / "script.txt",
        out_dir / "publish" / "douyin_title.txt",
        out_dir / "publish" / "xhs_title.txt",
    ]
    for p in required:
        if not p.is_file():
            _fail(f"缺少产出: {p}")
    _ok(f"产出文件齐全 article_id={aid}")

    brief = json.loads((out_dir / "brief.json").read_text(encoding="utf-8"))
    if not brief.get("hook") or not brief.get("talking_points"):
        _fail("brief.json 缺少 hook/talking_points")
    _ok("brief 结构正常")

    print("\n2) 第二轮 pipeline（去重）")
    s2 = run_pipeline(cfg)
    print(f"     deduped={s2.deduped} packed={s2.packed}")
    if s2.packed > 0:
        _fail("第二轮不应再 packed（应去重）")
    if s2.deduped < 1 and s1.packed > 0:
        _fail("第二轮应 deduped >= 1")
    _ok("去重正常")

    print("\n3) 发布台账")
    ck = content_key_for_article(aid)
    if not store.mark_published(ck, "douyin", note="verify"):
        _fail("首次 mark_published 应成功")
    if store.mark_published(ck, "douyin"):
        _fail("重复 mark 应被拒绝")
    pending = store.pending_publish("douyin")
    if any(int(j["article_id"]) == aid for j in pending):
        _fail("已标记发布后仍出现在 pending douyin")
    _ok("发布台账正常")

    print("\n4) VSA 路径（仅检查存在，render 默认关闭）")
    if cfg.vsa_root and cfg.vsa_root.is_dir():
        _ok(f"vsa_root 存在: {cfg.vsa_root}")
    else:
        print(f"  [WARN] vsa_root 未配置或不存在，出片步骤跳过")

    print("\n=== 本地流程验证通过 ===")
    print(f"样例产出: {out_dir}")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
