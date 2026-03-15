# 🎬 VideoShortsAgent

AI 驱动的短视频自动剪辑工具。输入长视频或 YouTube 链接，Agent 自动完成 **转录 → 金句提取 → 多片段裁剪 → 特效转场 → 拼接输出**。

## ✨ 核心特性

- **ReAct Agent**：Qwen LLM 自主决策，自动选择工具和特效
- **多片段提取**：AI 分析转录文本，提取 3-5 个精彩片段
- **平滑转场**：FFmpeg xfade 支持 16 种转场效果（fade/wipeleft/circleopen 等）
- **Remotion 动态特效**：每段独立字幕动画（spring/fade/typewriter）
- **中文字幕+配音**：固定流水线，翻译纠错 + edge-tts 配音 + 字幕烧录
- **YouTube 下载**：粘贴链接即可，支持 YouTube/Bilibili/TikTok 等 1000+ 平台
- **Gradio Web UI**：双 Tab 操作（Agent 模式 + 中文字幕模式）

## 🏗️ 架构

```
用户输入（视频/URL + 指令）
     ↓
┌─────────────────────────────────────────────┐
│  Tab 1: ReAct Agent (Qwen)                  │
│  transcribe → analyze → dubbing → render    │
│  LLM 自主决策，多片段裁剪+特效+转场          │
├─────────────────────────────────────────────┤
│  Tab 2: 中文字幕（固定流水线）                │
│  transcribe → LLM翻译纠错 → TTS配音          │
│  → ASS字幕 → FFmpeg烧录+替换音频             │
└─────────────────────────────────────────────┘
```

## 📁 项目结构

```
VideoShortsAgent/
├── python_agent/
│   ├── agent.py              # ReAct Agent 主循环
│   ├── tools.py              # 工具注册器
│   ├── config.py             # 配置管理
│   ├── main.py               # CLI 入口
│   ├── app.py                # Gradio Web UI（双 Tab）
│   └── skills/
│       ├── download_skill.py  # yt-dlp 视频下载
│       ├── transcribe_skill.py # Whisper 语音转录（Groq/本地）
│       ├── analysis_skill.py  # Qwen 金句分析+片段规划
│       ├── dubbing_skill.py   # edge-tts 中文配音（句级同步）
│       └── render_skill.py    # FFmpeg 渲染+转场+Remotion
├── remotion_effects/          # Remotion 特效（可选）
│   └── src/compositions/
│       ├── CaptionOverlay.tsx  # 字幕弹出动画
│       └── GradientBackground.tsx # 渐变背景
├── .env                       # API Key 配置
├── requirements.txt
└── start.bat                  # Windows 一键启动
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# Whisper 模型（首次需下载）
python download_model.py
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入：
# DASHSCOPE_API_KEY=sk-xxx     （必须，Qwen LLM）
# GROQ_API_KEY=gsk_xxx         （推荐，极速转录）
```

### 3. 启动

**方式一：Web UI**
```bash
# Windows 双击 start.bat
# 或命令行：
python -m python_agent.app
# 打开 http://localhost:7860
```

**方式二：命令行**
```bash
python -m python_agent.main --input video/test.mp4 --model ./faster-whisper-large-v3
```

## 🔧 Agent 工具链

| 工具 | 功能 | 技术栈 |
|------|------|--------|
| `download` | 从 URL 下载视频 | yt-dlp + Chrome cookies |
| `transcribe` | 语音转文字 | faster-whisper / Groq API |
| `analyze` | 提取精彩片段+规划特效 | Qwen 3.5-flash |
| `dubbing` | 中文 TTS 配音 | edge-tts（句级精确同步）|
| `render` | 多段裁剪+字幕+转场拼接 | FFmpeg + Remotion |

## 🎨 特效系统

Agent 为每段视频独立选择字幕动画和转场效果：

| 字幕动画 | 效果 |
|----------|------|
| `spring` | 弹性弹出 |
| `fade` | 淡入淡出 |
| `typewriter` | 打字机效果 |
| `slide` | 滑入 |
| `bounce` | 弹跳 |

**转场效果**：`fade` / `wipeleft` / `circleopen` / `circleclose` / `slideup` / `dissolve` / `pixelize` 等 16 种

## 📝 中文字幕模式

固定流水线，不走 Agent，速度快：

1. **转录** → Groq Whisper（极速）或本地 faster-whisper
2. **翻译纠错** → qwen-turbo（分批 50 条/批，自动翻译英文/纠正中文）
3. **TTS 配音** → edge-tts（逐段生成中文语音）
4. **合成音轨** → FFmpeg（按时间戳对齐所有语音段）
5. **烧录输出** → FFmpeg（字幕烧录 + 原声替换为中文配音）

支持三种输入：上传视频 / URL 下载 / 已有任务目录（跳过转录）

## 🔮 未来规划

- **AI 视频美化**：接入 Seedance / 可灵等视频生成模型，对剪辑片段进行风格化美化（画质增强、风格迁移、运动增强）
- **AI 视频生成**：输入文字脚本，Seedance 生成视频片段 → 配音 → 字幕 → 拼接为完整短视频
- **多语言字幕**：支持日语、韩语等更多目标语言
- **智能剪辑建议**：AI 分析视频内容，自动推荐最佳剪辑方案

## 📋 系统要求

- Python 3.10+
- FFmpeg 4.4+
- Node.js 18+（Remotion 特效可选）
- CUDA GPU（推荐，加速 Whisper 转录）

## 📄 License

MIT