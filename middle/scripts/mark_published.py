#!/usr/bin/env python3
"""标记某条任务已在某渠道发布（发布去重）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import load_config
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.pipeline_gates import PipelineGateError, assert_channel_publishable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--article-id", type=int, required=True)
    parser.add_argument("--channel", required=True, help="douyin|xhs|toutiao|douban")
    parser.add_argument("-c", "--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    cfg = load_config(args.config)
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(args.article_id)
    job = store.get_job(ck)
    if not job:
        print(f"job not found: {ck}", file=sys.stderr)
        return 1
    try:
        assert_channel_publishable(cfg, args.article_id, args.channel, job=job)
    except PipelineGateError as e:
        print(f"gate blocked: {e.code}: {e.message}", file=sys.stderr)
        return 2
    if store.mark_published(ck, args.channel, args.note):
        print(f"marked {ck} @ {args.channel}")
        return 0
    print(f"already published: {ck} @ {args.channel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
