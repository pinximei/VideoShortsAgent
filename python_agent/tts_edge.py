"""
Microsoft Edge 在线 TTS 封装：限流、重试、缓存。

业务背景：edge-tts 走 Bing WSS，无官方 SLA；高并发或短时 burst 易 503/401。
本模块统一入口，避免 DubbingSkill / 验收脚本各自直连导致雪崩。
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import random
import re
import time
from pathlib import Path
from typing import Any

# 全局并发：同时仅 1 路 WebSocket（可通过环境变量放宽）
_WS_SEM: asyncio.Semaphore | None = None
_LAST_REQUEST_AT: float = 0.0


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def tts_max_retries() -> int:
    return max(1, _env_int("TTS_MAX_RETRIES", 6))


def tts_retry_base_sec() -> float:
    return max(0.5, _env_float("TTS_RETRY_BASE_SEC", 1.5))


def tts_max_concurrent() -> int:
    return max(1, _env_int("TTS_MAX_CONCURRENT", 1))


def tts_sentence_delay_sec() -> float:
    return max(0.0, _env_float("TTS_SENTENCE_DELAY_MS", 250) / 1000.0)


def tts_cache_enabled() -> bool:
    return os.getenv("TTS_CACHE", "1").strip().lower() not in ("0", "false", "no")


def _get_ws_sem() -> asyncio.Semaphore:
    global _WS_SEM
    if _WS_SEM is None:
        _WS_SEM = asyncio.Semaphore(tts_max_concurrent())
    return _WS_SEM


def is_retryable_error(exc: BaseException) -> bool:
    """503/502/429 及 handshake 类瞬时错误可重试。"""
    if isinstance(exc, asyncio.TimeoutError):
        return True
    msg = str(exc).lower()
    patterns = (
        "503",
        "502",
        "429",
        "500",
        "invalid response status",
        "server disconnected",
        "connection reset",
        "cannot connect",
        "temporarily unavailable",
        "no audio received",
    )
    if any(p in msg for p in patterns):
        return True
    status = getattr(exc, "status", None)
    if status is None:
        status = getattr(exc, "code", None)
    try:
        if status is not None and int(status) in (401, 403, 429, 500, 502, 503):
            # 401/403 偶发 token 问题，短重试有时可恢复（见 edge-tts #416/#458）
            return True
    except (TypeError, ValueError):
        pass
    return False


def cache_key(text: str, voice: str) -> str:
    raw = f"{voice}\n{(text or '').strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.mp3"


async def _throttle_before_request() -> None:
    """句间最小间隔，降低 Bing 限流概率。"""
    global _LAST_REQUEST_AT
    delay = tts_sentence_delay_sec()
    if delay <= 0:
        return
    now = time.monotonic()
    wait = delay - (now - _LAST_REQUEST_AT)
    if wait > 0:
        await asyncio.sleep(wait)
    _LAST_REQUEST_AT = time.monotonic()


async def synthesize_to_file(
    text: str,
    voice: str,
    output_path: str | Path,
    *,
    cache_dir: str | Path | None = None,
    rate: str = "+0%",
) -> Path:
    """
    合成单句/段文本到 mp3；失败时指数退避重试。

    Raises:
        RuntimeError: 重试耗尽仍失败
    """
    import edge_tts

    text = (text or "").strip()
    if not text:
        raise ValueError("TTS 文本为空")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rate = (rate or "+0%").strip()
    key = cache_key(f"{text}|{rate}", voice)
    shared: Path | None = None
    if cache_dir and tts_cache_enabled():
        shared = cache_path(Path(cache_dir), key)
        if shared.is_file() and shared.stat().st_size > 80:
            if shared.resolve() != out.resolve():
                import shutil
                shutil.copy2(shared, out)
            return out

    last_err: BaseException | None = None
    retries = tts_max_retries()
    base = tts_retry_base_sec()

    for attempt in range(retries):
        try:
            await _throttle_before_request()
            async with _get_ws_sem():
                comm = edge_tts.Communicate(text, voice, rate=rate)
                await comm.save(str(out))
            if out.is_file() and out.stat().st_size > 80:
                if shared is not None:
                    import shutil
                    shutil.copy2(out, shared)
                return out
            raise RuntimeError("edge_tts_empty_output")
        except Exception as exc:
            last_err = exc
            if not is_retryable_error(exc) or attempt >= retries - 1:
                break
            sleep_s = base * (2**attempt) + random.uniform(0, 0.4)
            print(
                f"[TTS] 重试 {attempt + 1}/{retries - 1} "
                f"({type(exc).__name__}: {str(exc)[:80]}) 等待 {sleep_s:.1f}s"
            )
            await asyncio.sleep(sleep_s)
            if out.is_file():
                try:
                    out.unlink()
                except OSError:
                    pass

    hint = (
        "Edge TTS 不可用（503/限流/网络）。建议：检查网络、升级 edge-tts>=7.2.7、"
        "降低 TTS_MAX_CONCURRENT=1、稍后重试；生产可配置备用 TTS。"
    )
    raise RuntimeError(f"{hint} 原文: {type(last_err).__name__}: {last_err}") from last_err


def run_async(coro: Any) -> Any:
    """在同步上下文中运行协程（兼容已有 event loop）。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=600)


async def synthesize_batch_sequential(
    items: list[tuple[str, str]],
    *,
    voice: str,
    cache_dir: str | Path | None = None,
    rate: str = "+0%",
) -> list[Path]:
    """顺序合成多句，避免 asyncio.gather 触发 Bing burst 限流。"""
    paths: list[Path] = []
    for text, path in items:
        paths.append(
            await synthesize_to_file(text, voice, path, cache_dir=cache_dir, rate=rate)
        )
    return paths


def health_check(voice: str | None = None) -> dict[str, Any]:
    """探测 Edge TTS 是否可用（用于运维/启动检查）。"""
    voice = voice or os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")
    tmp = Path(os.getenv("TEMP", ".")) / f"tts_health_{os.getpid()}.mp3"
    t0 = time.monotonic()
    try:
        run_async(synthesize_to_file("语音服务探测", voice, tmp, cache_dir=None))
        ok = tmp.is_file() and tmp.stat().st_size > 80
        return {
            "ok": ok,
            "voice": voice,
            "latency_sec": round(time.monotonic() - t0, 2),
            "bytes": tmp.stat().st_size if ok else 0,
        }
    except Exception as exc:
        return {
            "ok": False,
            "voice": voice,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_sec": round(time.monotonic() - t0, 2),
        }
    finally:
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass
