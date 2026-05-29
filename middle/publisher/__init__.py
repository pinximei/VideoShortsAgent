"""固定脚本发布：双无头浏览器槽位 × 批次主体 × 持久化 Profile。不使用大模型操作网页。"""

from .batches import PublisherBatch, PublisherSlot, parse_publisher_config
from .runner import PublishRequest, PublishResult, publish_content

__all__ = [
    "PublisherBatch",
    "PublisherSlot",
    "parse_publisher_config",
    "PublishRequest",
    "PublishResult",
    "publish_content",
]
