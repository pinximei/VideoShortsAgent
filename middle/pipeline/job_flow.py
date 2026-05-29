"""任务状态与步骤（中间层编排）。"""
from __future__ import annotations

# 粗粒度状态
STATUS_DISCOVERED = "discovered"
STATUS_PROCESSING = "processing"
STATUS_READY = "ready_to_publish"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

TERMINAL_STATUSES = (STATUS_SKIPPED, STATUS_FAILED, STATUS_COMPLETED)
PUBLISH_CHANNELS = ("douyin", "xhs", "toutiao", "douban")

# 细粒度步骤（展示用）
STEP_DISCOVER = "discover"
STEP_FETCH = "fetch_article"
STEP_FILTER = "filter"
STEP_BRIEF = "build_brief"
STEP_LLM = "llm_platform_copy"
STEP_PACK = "write_publish_pack"
STEP_VSA = "vsa_render"
STEP_READY = "await_manual_publish"
STEP_DONE = "all_channels_published"

STEP_LABELS: dict[str, str] = {
    STEP_DISCOVER: "已发现",
    STEP_FETCH: "拉取文章",
    STEP_FILTER: "筛选",
    STEP_BRIEF: "生成 Brief",
    STEP_LLM: "大模型改写各平台",
    STEP_PACK: "写入发布包",
    STEP_VSA: "VSA 裁剪视频",
    STEP_READY: "待人工发布",
    STEP_DONE: "全渠道已标记发布",
}
