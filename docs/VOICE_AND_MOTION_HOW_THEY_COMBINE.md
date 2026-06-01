# 画面模板 vs 口播模板 — 怎么组合、别混

## 两套模板各管什么

| 维度 | 目录 | ID | 控制什么 | **不**控制什么 |
|------|------|-----|----------|----------------|
| **画面 / 视频风格** | `templates/github_daily_20/` + `motion_templates/` | **G01–G20** | 角标、弹幕、切镜动效、配色装饰、Remotion 组件 | 音色、音调、语速、文案钩子 |
| **声音 / 口播风格** | `templates/voice_content_20/` | **V01–V20** | `tts_voice` 音色、`edge_tts_rate` 语速、`edge_tts_pitch` 音调、`sentence_pause_sec` 句间停顿、总字数/钩子/语气（给 LLM） | 画面动画、转场、字幕样式 |

一句话：**G = 看起来像什么；V = 听起来像什么、文案怎么写。**

## 怎么组合（唯一规则）

1. `slides_render` 先按 brief 选 **V** → 写入 `brief.tts_rate` / `tts_voice` / `tts_pitch` / `sentence_pause_sec`。
2. 再按 brief 选 **G** → 写入每镜 `github_daily_style_id`、动效 plan。
3. 可选配对：V 里 `reference_motion: "G01"` 表示「推荐与 G01 一起用」；**不是**强制绑定，哈希选型仍可拆开。

任务目录落盘：

- `llm/voice_content_style.json` — 本次 **V**
- `llm/github_daily_style.json` — 本次 **G**

## 男声 vs 女声（你反馈的现象）

| 渠道 | 默认音色 | 听感 | 本次调整 |
|------|----------|------|----------|
| **抖音（男）** | 原 `Yunxi` 偏沉 | 易显慢、空 | 默认 **`Yunyang`**，`rate +14%`、`pitch +8Hz` |
| **小红书（女）** | `Xiaoxiao` | 你说语速还行 | **`Xiaoxiao`**，`+6%` / `+4Hz` |

**重要（已修）**：此前 slides 模式只渲抖音再把 mp4 **复制**到小红书，导致小红书也是男声。现已改为**文案共用、分平台各渲一条**（各用各的 TTS）。

「字少」与音色无关：Compose 曾写「字数越少越狠」导致屏上字少；口播 `tts_text` 也偏短。已改为**屏上标题可短、口播必须写满**，并加全片字数下限校验。

## 你听的「慢」通常来自哪

| 原因 | 层 | 处理 |
|------|-----|------|
| 语速 | V → `edge_tts_rate` | 对标 ASR 中位 ~369 字/分；GitHub 日更基线 **+12%**，爆款快钩子 **+16%~+18%** |
| 音色偏沉 | V → `tts_voice` | 默认 Yunxi 偏稳；日更基线改为 **Yunyang**（更利落） |
| 音调偏低 | V → `edge_tts_pitch` | Edge 支持 `+6Hz`~`+10Hz`，已接入 `DubbingSkill` |
| 句间空太长 | V → `sentence_pause_sec` | 快口播 0.12–0.16s，慢讲 0.22–0.28s |
| 文案太长 | V → `total_chars` / Compose | 字多必然拖时长，与 rate 无关 |

**注意**：仅有抖音 phash（字幕切换间隔）实测的 V 槽位**不能**证明语速，只用基线 rate，禁止再用 +5% 当「学完的爆款语速」。

## 复现检查

成片日志应出现：

```text
[SlidesRender] scene=... voice=V03_top10_listing
[DubbingSkill] 语音: zh-CN-YunyangNeural rate=+14% pitch=+8Hz OK
```

若仍是 `rate=+0%` 或 `Yunxi` 且无 `voice=` 行，说明没走 `slides_render` 或未命中 GitHub 日更 brief。
