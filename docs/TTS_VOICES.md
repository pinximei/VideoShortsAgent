# VSA 口播音色说明

## 为什么听起来忽快忽慢？

1. **以前**：抖音默认 `Yunyang +32%`，和资讯模板里的 V 口播（+14%～+18%）混用，镜与镜不一致。
2. **画面最短 4.2s**：口播只有 2～3 秒时，后面长时间只有画面无声音，像「突然变慢」。
3. **Edge 免费音**：表现力弱于 Azure / 通义 Key；可在 `.env` 配置 `TTS_PROVIDER=azure` 或 `dashscope` 增强情感。

## 爱资讯推荐预设（`middle/config.yaml` → `render.tts_voice_preset`）

| 预设 ID | 音色 | 特点 |
|---------|------|------|
| `news_anchor_female`（默认） | 晓晓 Xiaoxiao | 女声，亲切播报 |
| `news_anchor_male` | 云健 Yunjian | 男声，新闻解说 |
| `news_anchor_tv` | 云扬 Yunyang | 男声，电视快讯略快 |

也可用环境变量：`TTS_VOICE_PRESET=news_anchor_male`

## Edge 其它中文神经音（自行改预设 JSON / 代码）

见 `python_agent/tts_voice_presets.py` 内 `EDGE_ZH_VOICES_DOC`。

## 换 Key 后端（更有「演讲感」）

```env
TTS_PROVIDER=auto
TTS_FALLBACK=dashscope,azure
DASHSCOPE_API_KEY=...
# 或
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastasia
```

Azure 路径会使用 SSML `prosody` 传递语速/音高。
