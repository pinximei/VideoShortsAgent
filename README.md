# 🎬 VideoShortsAgent

AI 驱动的短视频自动剪辑工具。输入长视频或 YouTube 链接，Agent 自动完成 **转录 → 金句提取 → 多片段裁剪 → 特效转场 → 拼接输出**。

## ✨ 核心特性

- **ReAct Agent**：Qwen LLM 自主决策，自动选择工具和特效
- **多片段提取**：AI 分析转录文本，提取 3-5 个精彩片段
- **平滑转场**：FFmpeg xfade 支持 16 种转场效果（fade/wipeleft/circleopen 等）
- **自动特效**：Agent 根据视频风格选择字幕动画和背景特效
- **YouTube 下载**：粘贴链接即可，支持 YouTube/Bilibili/TikTok 等 1000+ 平台
- **Gradio Web UI**：可视化操作，支持上传视频或输入 URL

## 🏗️ 架构

```
用户输入（视频/URL + 指令）
     ↓
┌─────────────────────────────┐
│     ReAct Agent (Qwen)      │  LLM 自主决策
│  System Prompt + Tool Loop  │
└──────┬──┬──┬──┬─────────────┘
       │  │  │  │
  download │  │  render ──→ FFmpeg 多段裁剪
       │  │  │              + ASS 字幕烧录
  transcribe │              + xfade 转场拼接
       │  analyze
   Whisper    Qwen
  large-v3   3.5-flash
```

## 📁 项目结构

```
VideoShortsAgent/
├── python_agent/
│   ├── agent.py              # ReAct Agent 主循环
│   ├── tools.py              # 工具注册器
│   ├── config.py             # 配置管理
│   ├── main.py               # CLI 入口
│   ├── app.py                # Gradio Web UI
│   └── skills/
│       ├── download_skill.py  # yt-dlp 视频下载
│       ├── transcribe_skill.py # Whisper 语音转录
│       ├── analysis_skill.py  # Qwen 金句分析
│       └── render_skill.py    # FFmpeg 渲染+转场
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
# 编辑 .env，填入 DASHSCOPE_API_KEY
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
| `transcribe` | 语音转文字 | faster-whisper large-v3 |
| `analyze` | 提取多个精彩片段 | Qwen 3.5-flash |
| `render` | 多段裁剪+字幕+转场拼接 | FFmpeg xfade |

## 🎨 特效系统

Agent 自动选择特效组合，通过 `effects_json` 传入 render：

```json
{
  "caption_style": "spring",
  "transition": "circleopen",
  "transition_duration": 0.8,
  "gradient": true,
  "gradient_colors": ["#FF6B6B", "#4ECDC4"]
}
```

**可用转场**：`fade` / `wipeleft` / `wiperight` / `circleopen` / `circleclose` / `slideup` / `slidedown` / `dissolve` / `pixelize` 等 16 种

## 📋 系统要求

- Python 3.10+
- FFmpeg 4.4+
- Node.js 18+（Remotion 特效可选）
- CUDA GPU（推荐，加速 Whisper 转录）

## 📄 License

MIT