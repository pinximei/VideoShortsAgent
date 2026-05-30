"""
统一 TTS 入口：Edge（免费）+ Key 后端（Dashscope / Azure / OpenAI）。

环境变量：
  TTS_PROVIDER=auto|edge|dashscope|azure|openai
  TTS_FALLBACK=dashscope,azure,openai   # auto 模式下 Edge 失败后的顺序
  DASHSCOPE_API_KEY / AZURE_SPEECH_KEY / OPENAI_API_KEY
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from python_agent.tts_edge import (
    cache_key,
    cache_path,
    run_async,
    synthesize_batch_sequential as edge_batch,
    synthesize_to_file as edge_synthesize,
    tts_cache_enabled,
)
from python_agent.tts_key import (
    available_key_providers,
    synthesize_azure,
    synthesize_dashscope,
    synthesize_openai,
)


def tts_provider_mode() -> str:
    return (os.getenv("TTS_PROVIDER", "auto") or "auto").strip().lower()


def fallback_order() -> list[str]:
    raw = os.getenv("TTS_FALLBACK", "dashscope,azure,openai")
    names = [x.strip().lower() for x in raw.split(",") if x.strip()]
    allowed = set(available_key_providers())
    return [n for n in names if n in allowed]


def resolve_provider_chain() -> list[str]:
    mode = tts_provider_mode()
    if mode == "edge":
        return ["edge"]
    if mode in ("dashscope", "azure", "openai"):
        if mode not in available_key_providers():
            raise RuntimeError(
                f"TTS_PROVIDER={mode} 但未配置对应 API Key"
            )
        return [mode]
    if mode == "auto":
        chain = ["edge"] + fallback_order()
        return chain
    raise ValueError(f"未知 TTS_PROVIDER={mode}")


def _read_cache(text: str, voice: str, out: Path, cache_dir: Path | None) -> Path | None:
    if not cache_dir or not tts_cache_enabled():
        return None
    shared = cache_path(cache_dir, cache_key(text, voice))
    if shared.is_file() and shared.stat().st_size > 80:
        if shared.resolve() != out.resolve():
            import shutil
            shutil.copy2(shared, out)
        return out
    return None


def _write_cache(text: str, voice: str, out: Path, cache_dir: Path | None) -> None:
    if not cache_dir or not tts_cache_enabled():
        return
    shared = cache_path(cache_dir, cache_key(text, voice))
    import shutil
    shutil.copy2(out, shared)


def _synthesize_one_provider(
    provider: str,
    text: str,
    voice: str,
    out: Path,
) -> Path:
    if provider == "edge":
        return Path(
            run_async(edge_synthesize(text, voice, out, cache_dir=None))
        )
    if provider == "dashscope":
        return synthesize_dashscope(text, voice, out)
    if provider == "azure":
        return synthesize_azure(text, voice, out)
    if provider == "openai":
        return synthesize_openai(text, voice, out)
    raise ValueError(f"未知 TTS provider: {provider}")


async def synthesize_to_file(
    text: str,
    voice: str,
    output_path: str | Path,
    *,
    cache_dir: str | Path | None = None,
) -> Path:
    text = (text or "").strip()
    if not text:
        raise ValueError("TTS 文本为空")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cdir = Path(cache_dir) if cache_dir else None
    hit = _read_cache(text, voice, out, cdir)
    if hit:
        return hit

    chain = resolve_provider_chain()
    errors: list[str] = []
    for provider in chain:
        try:
            result = _synthesize_one_provider(provider, text, voice, out)
            _write_cache(text, voice, result, cdir)
            if provider != "edge":
                print(f"[TTS] 使用 Key 后端: {provider}")
            return result
        except Exception as exc:
            msg = f"{provider}: {type(exc).__name__}: {exc}"
            errors.append(msg)
            if provider == "edge":
                print(f"[TTS] Edge 失败，尝试 Key 备用… ({str(exc)[:100]})")
            else:
                print(f"[TTS] {provider} 失败: {str(exc)[:120]}")

    hint = (
        "所有 TTS 渠道均失败。可配置: DASHSCOPE_API_KEY（推荐）、"
        "AZURE_SPEECH_KEY+AZURE_SPEECH_REGION、OPENAI_API_KEY；"
        "或检查 Edge 网络/TTS_MAX_CONCURRENT=1。"
    )
    raise RuntimeError(f"{hint}\n" + "\n".join(errors[-4:]))


async def synthesize_batch_sequential(
    items: list[tuple[str, str]],
    *,
    voice: str,
    cache_dir: str | Path | None = None,
) -> list[Path]:
    paths: list[Path] = []
    for text, path in items:
        paths.append(
            await synthesize_to_file(text, voice, path, cache_dir=cache_dir)
        )
    return paths


def health_check(voice: str | None = None) -> dict[str, Any]:
    """探测当前配置下可用的 TTS 渠道。"""
    import time

    voice = voice or os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")
    mode = tts_provider_mode()
    chain = resolve_provider_chain() if mode != "edge" else ["edge"]
    if mode == "auto":
        chain = ["edge"] + fallback_order()

    results: dict[str, Any] = {
        "mode": mode,
        "chain": chain,
        "key_providers_configured": available_key_providers(),
        "providers": {},
    }
    tmp_dir = Path(os.getenv("TEMP", "."))
    for provider in chain:
        if provider != "edge" and provider not in available_key_providers():
            results["providers"][provider] = {"ok": False, "skipped": "no_api_key"}
            continue
        tmp = tmp_dir / f"tts_health_{provider}_{os.getpid()}.mp3"
        t0 = time.monotonic()
        try:
            if provider == "edge":
                run_async(edge_synthesize("语音服务探测", voice, tmp, cache_dir=None))
            else:
                _synthesize_one_provider(provider, "语音服务探测", voice, tmp)
            ok = tmp.is_file() and tmp.stat().st_size > 80
            results["providers"][provider] = {
                "ok": ok,
                "latency_sec": round(time.monotonic() - t0, 2),
                "bytes": tmp.stat().st_size if ok else 0,
            }
        except Exception as exc:
            results["providers"][provider] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "latency_sec": round(time.monotonic() - t0, 2),
            }
        finally:
            if tmp.is_file():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    results["ok"] = any(
        (p.get("ok") for p in results["providers"].values() if isinstance(p, dict))
    )
    return results
