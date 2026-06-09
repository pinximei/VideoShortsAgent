"""基于 API Key 的 TTS 后端（HTTP，无强制 SDK）。"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx

# Edge 神经语音 → 各云厂商音色（可按 .env 覆盖）
EDGE_TO_DASHSCOPE_VOICE: dict[str, str] = {
    "zh-CN-YunxiNeural": "Ethan",
    "zh-CN-XiaoxiaoNeural": "Cherry",
    "zh-CN-YunyangNeural": "Ethan",
}
EDGE_TO_OPENAI_VOICE: dict[str, str] = {
    "zh-CN-YunxiNeural": "onyx",
    "zh-CN-XiaoxiaoNeural": "nova",
}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def dashscope_api_key() -> str:
    return _env("DASHSCOPE_API_KEY") or _env("TTS_DASHSCOPE_API_KEY")


def azure_speech_key() -> str:
    return _env("AZURE_SPEECH_KEY") or _env("TTS_AZURE_SPEECH_KEY")


def azure_speech_region() -> str:
    return _env("AZURE_SPEECH_REGION", "eastasia") or "eastasia"


def openai_tts_api_key() -> str:
    return _env("OPENAI_TTS_API_KEY") or _env("OPENAI_API_KEY")


def openai_tts_base_url() -> str:
    base = _env("OPENAI_TTS_BASE_URL", "https://api.openai.com/v1")
    return base.rstrip("/")


def resolve_dashscope_voice(edge_voice: str) -> str:
    custom = _env("DASHSCOPE_TTS_VOICE")
    if custom:
        return custom
    return EDGE_TO_DASHSCOPE_VOICE.get(edge_voice, "Cherry")


def resolve_azure_voice(edge_voice: str) -> str:
    custom = _env("AZURE_TTS_VOICE")
    if custom:
        return custom
    return edge_voice if edge_voice else "zh-CN-YunxiNeural"


def resolve_openai_voice(edge_voice: str) -> str:
    custom = _env("OPENAI_TTS_VOICE")
    if custom:
        return custom
    return EDGE_TO_OPENAI_VOICE.get(edge_voice, "nova")


def _ensure_mp3(src: Path, dest: Path) -> Path:
    """将 wav/ogg 转为 mp3（pipeline 统一用 mp3）。"""
    if src.suffix.lower() == ".mp3":
        if src.resolve() != dest.resolve():
            import shutil
            shutil.copy2(src, dest)
        return dest
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-c:a", "libmp3lame", "-b:a", "128k", str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not dest.is_file():
        raise RuntimeError(f"音频转 mp3 失败: {(r.stderr or '')[-200:]}")
    return dest


def synthesize_dashscope(text: str, edge_voice: str, output_path: Path) -> Path:
    key = dashscope_api_key()
    if not key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")
    model = _env("DASHSCOPE_TTS_MODEL", "qwen3-tts-flash")
    voice = resolve_dashscope_voice(edge_voice)
    base = _env("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    url = f"{base}/services/aigc/multimodal-generation/generation"
    payload = {
        "model": model,
        "input": {
            "text": text,
            "voice": voice,
            "language_type": _env("DASHSCOPE_TTS_LANGUAGE", "Chinese"),
        },
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Dashscope TTS HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    if data.get("code"):
        raise RuntimeError(f"Dashscope TTS: {data.get('code')} {data.get('message', '')[:200]}")
    out = data.get("output") or {}
    audio = out.get("audio") or {}
    audio_url = (audio.get("url") or "").strip()
    b64 = audio.get("data") or audio.get("base64")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if audio_url:
        with httpx.Client(timeout=90.0, follow_redirects=True) as client:
            r = client.get(audio_url)
            r.raise_for_status()
            raw = r.content
    elif b64:
        import base64
        raw = base64.b64decode(b64)
    else:
        raise RuntimeError("Dashscope TTS 响应无 audio.url / audio.data")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if raw[:3] == b"ID3" or raw[:2] == b"\xff\xfb":
        output_path.write_bytes(raw)
    else:
        tmp = output_path.with_suffix(".tmp.audio")
        tmp.write_bytes(raw)
        _ensure_mp3(tmp, output_path)
        if tmp.is_file() and tmp != output_path:
            tmp.unlink(missing_ok=True)
    if output_path.stat().st_size < 80:
        raise RuntimeError("Dashscope TTS 输出过小")
    return output_path


def _edge_rate_to_prosody(rate: str) -> str:
    r = (rate or "+0%").strip()
    if r.endswith("%"):
        return r if r.startswith(("+", "-")) else f"+{r}"
    return "+0%"


def _edge_pitch_to_prosody(pitch: str) -> str:
    p = (pitch or "+0Hz").strip().lower()
    if p.endswith("hz"):
        num = p.replace("hz", "").strip()
        if num.startswith(("+", "-")):
            return f"{num}Hz"
        return f"+{num}Hz"
    return "+0Hz"


def synthesize_azure(
    text: str,
    edge_voice: str,
    output_path: Path,
    *,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    key = azure_speech_key()
    if not key:
        raise RuntimeError("未配置 AZURE_SPEECH_KEY")
    region = azure_speech_region()
    voice = resolve_azure_voice(edge_voice)
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    prosody_rate = _edge_rate_to_prosody(rate)
    prosody_pitch = _edge_pitch_to_prosody(pitch)
    inner = _xml_escape(text)
    ssml = (
        f"<speak version='1.0' xml:lang='zh-CN'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='{prosody_rate}' pitch='{prosody_pitch}'>{inner}</prosody>"
        f"</voice></speak>"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
    }
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(url, content=ssml.encode("utf-8"), headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Azure TTS HTTP {resp.status_code}: {resp.text[:200]}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(resp.content)
    if output_path.stat().st_size < 80:
        raise RuntimeError("Azure TTS 输出过小")
    return output_path


def synthesize_openai(text: str, edge_voice: str, output_path: Path) -> Path:
    key = openai_tts_api_key()
    if not key:
        raise RuntimeError("未配置 OPENAI_TTS_API_KEY / OPENAI_API_KEY")
    model = _env("OPENAI_TTS_MODEL", "tts-1")
    voice = resolve_openai_voice(edge_voice)
    url = f"{openai_tts_base_url()}/audio/speech"
    payload = {"model": model, "input": text, "voice": voice, "response_format": "mp3"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI TTS HTTP {resp.status_code}: {resp.text[:200]}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(resp.content)
    if output_path.stat().st_size < 80:
        raise RuntimeError("OpenAI TTS 输出过小")
    return output_path


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def available_key_providers() -> list[str]:
    out: list[str] = []
    if dashscope_api_key():
        out.append("dashscope")
    if azure_speech_key():
        out.append("azure")
    if openai_tts_api_key():
        out.append("openai")
    return out
