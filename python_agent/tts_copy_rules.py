"""口播文案规则：禁套话、校验与清洗（mock / LLM / 门禁共用）。"""
from __future__ import annotations

import re

TTS_BANNED_PATTERNS: tuple[str, ...] = (
    r"这是第\s*\d+\s*个重点",
    r"建议收藏",
    r"真的值得你现在就试",
    r"你绝对不知道",
    r"一夜破万",
    r"平台对比验证",
    r"上手门槛不高",
    r"适合想提效",
)

# 元信息套话：协议/地址/评论区领资料，非项目价值
TTS_META_FILLER_PATTERNS: tuple[str, ...] = (
    r"开源\s*MIT",
    r"MIT\s*协议",
    r"Apache\s*2\.0",
    r"GPL\s*协议",
    r"评论区",
    r"部署表",
    r"仓库链接",
    r"发你链接",
    r"README\s*里",
    r"一键安装命令",
    r"Star\s*曲线",
    r"个人学习和小团队都能用",
    r"开源许可友好",
    r"部署步骤",
    r"照抄配置",
)

TTS_BANNED_COMPILED = [re.compile(p, re.I) for p in TTS_BANNED_PATTERNS]
TTS_META_COMPILED = [re.compile(p, re.I) for p in TTS_META_FILLER_PATTERNS]


def tts_has_banned_phrase(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return False
    return any(p.search(s) for p in TTS_BANNED_COMPILED)


def tts_has_meta_filler(text: str) -> bool:
    s = (text or "").strip()
    return bool(s) and any(p.search(s) for p in TTS_META_COMPILED)


def strip_meta_filler_clauses(text: str) -> str:
    """去掉协议/部署/评论区等从句，保留产品能力描述。"""
    s = (text or "").strip()
    if not s:
        return s
    parts = re.split(r"(?<=[。！？；])", s)
    kept: list[str] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        if tts_has_meta_filler(chunk):
            continue
        kept.append(chunk)
    out = "".join(kept).strip()
    return out or s


def sanitize_tts_text(text: str) -> str:
    s = strip_meta_filler_clauses(text)
    for p in TTS_BANNED_COMPILED:
        s = p.sub("", s)
    for p in TTS_META_COMPILED:
        s = p.sub("", s)
    s = re.sub(r"[，,]{2,}", "，", s)
    s = re.sub(r"\s+", " ", s).strip("，,。！？ ")
    return s


def validate_slides_tts_copy(slides: list) -> list[str]:
    issues: list[str] = []
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        tts = str(slide.get("tts_text") or "")
        if tts_has_banned_phrase(tts):
            issues.append(f"slide_{i}_banned_tts_phrase")
        if tts_has_meta_filler(tts):
            issues.append(f"slide_{i}_meta_filler_tts")
    return issues
