"""共享测试配置：发布绑定需要渠道账号。"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.channel_registry import ChannelAccount
from pipeline.config import PipelineConfig
from pipeline.job_flow import PUBLISH_CHANNELS


def add_test_channel_accounts(cfg: PipelineConfig) -> None:
    site_code = "ai-trends-apps"
    batch_id = "batch_a"
    for ch in PUBLISH_CHANNELS:
        cfg.channel_accounts.append(
            ChannelAccount(
                id=f"acc_test_{ch}",
                site_code=site_code,
                channel_id=ch,
                batch_id=batch_id,
                label=f"测试 {ch}",
                enabled=True,
                is_primary=True,
            )
        )


@pytest.fixture()
def pipeline_cfg(tmp_path: Path) -> PipelineConfig:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        feed_kinds=["apps"],
        llm_enabled=False,
        render_enabled=False,
        pipeline_fail_closed=True,
    )
    add_test_channel_accounts(cfg)
    return cfg
