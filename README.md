# 🎬 VideoShortsAgent

AI 驱动的视频短片生成工具。**两大核心功能**：

1. **🎬 AI 精彩片段提取**：输入长视频 → AI 自动挑出精彩片段 → 加配音+字幕特效+转场 → 生成 60 秒短视频
2. **🗣️ 全片中文翻译配音**：英文视频 → 语音识别 → AI 翻译 → 中文配音 → 字幕烧录

> 📺 适合做科普、技术分享、学习笔记、内容二创

---

## ✨ 功能亮点

| 特性 | 说明 |
|------|------|
| 🤖 AI Agent 自主决策 | Qwen LLM 自动选择精彩片段、特效、转场 |
| 🎵 中文 TTS 配音 | Edge TTS，语速自动适配原始节奏 |
| 🎨 Remotion 字幕特效 | spring 弹出 / fade 淡入 / typewriter 打字机 |
| 🔀 16 种转场效果 | fade / wipeleft / circleopen / dissolve 等 |
| 🌐 支持 1000+ 平台 | YouTube / B站 / TikTok 等链接直接输入 |
| 🔒 本地运行 | 完全免费，数据不上传 |
| 🖥️ Web UI | Gradio 双 Tab 操作，无需命令行 |

---

## 📋 前置条件

在使用之前，请确保你的电脑安装了以下软件：

### 1. Python 3.10+

- **下载地址**：https://www.python.org/downloads/
- 安装时 **务必勾选** `Add Python to PATH`
- 验证安装：
  ```bash
  python --version
  # 输出应为 Python 3.10.x 或更高
  ```

### 2. FFmpeg 4.4+

FFmpeg 是视频处理的核心工具，**必须安装**。

**Windows 安装方法**：
1. 下载：https://github.com/BtbN/FFmpeg-Builds/releases
   - 选择 `ffmpeg-master-latest-win64-gpl.zip`
2. 解压到 `C:\ffmpeg`
3. 添加环境变量：
   - 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
   - 在 `Path` 中添加 `C:\ffmpeg\bin`
4. 验证安装：
   ```bash
   ffmpeg -version
   # 输出应显示 ffmpeg version 4.x 或更高
   ```

**Mac 安装方法**：
```bash
brew install ffmpeg
```

### 3. Node.js 18+（Remotion 特效可选）

如果你想使用 **字幕动画特效**（spring/fade/typewriter），需要安装 Node.js。不安装也能正常使用（会自动降级为 ASS 静态字幕）。

- **下载地址**：https://nodejs.org/ （选 LTS 版本）
- 验证安装：
  ```bash
  node --version
  # 输出应为 v18.x 或更高
  ```

### 4. API Key

你需要至少一个 LLM API Key：

| API Key | 用途 | 必需？ | 获取地址 |
|---------|------|--------|----------|
| `DASHSCOPE_API_KEY` | 通义千问 LLM (翻译+分析) | ✅ 必需 | https://dashscope.console.aliyun.com/ |
| `GROQ_API_KEY` | Groq Whisper (极速转录) | ⭐ 推荐 | https://console.groq.com/ |

> **DASHSCOPE_API_KEY 获取步骤**：
> 1. 注册/登录阿里云
> 2. 打开 [DashScope 控制台](https://dashscope.console.aliyun.com/)
> 3. 点击"API-KEY 管理" → 创建 API Key
> 4. 复制保存

> **GROQ_API_KEY 获取步骤**（推荐，转录速度快 10 倍）：
> 1. 注册 https://console.groq.com/
> 2. 左侧菜单 API Keys → Create API Key
> 3. 复制保存

---

## 🚀 安装步骤

### 方式一：一键安装（推荐）

```bash
git clone https://github.com/pinximei/VideoShortsAgent.git
cd VideoShortsAgent
```

| 系统 | 命令 |
|------|------|
| **Windows** | 双击 `install.bat` |
| **macOS / Linux** | `chmod +x install.sh && ./install.sh` |

脚本会自动完成：检测环境 → 安装 Python 依赖 → 配置 Remotion（如有 Node.js）→ 创建 `.env`

安装完成后，编辑 `.env` 填入你的 API Key，然后双击 `start.bat`（Windows）或运行 `python -m python_agent.app` 启动。

### 方式二：手动安装

<details>
<summary>点击展开手动安装步骤</summary>

```bash
# 1. 克隆项目
git clone https://github.com/pinximei/VideoShortsAgent.git
cd VideoShortsAgent

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 配置 API Key（复制 .env.example 并填入密钥）
cp .env.example .env

# 4.（可选）安装 Remotion 字幕特效
cd remotion_effects && npm install && cd ..
```

</details>

### 本地 Whisper 模型（可选）

如果你想使用**本地语音转录**（不依赖 Groq 云端），需要下载 faster-whisper 模型：

| 模型 | 大小 | 下载链接 |
|------|------|----------|
| faster-whisper-large-v3 | ~3 GB | [🤗 Hugging Face](https://huggingface.co/Systran/faster-whisper-large-v3) · [🪞 国内镜像](https://hf-mirror.com/Systran/faster-whisper-large-v3) |

下载后将模型文件夹放在项目根目录，命名为 `faster-whisper-large-v3`。

> 💡 **推荐**：配置 `GROQ_API_KEY` 使用云端转录，速度快 10 倍且无需下载模型

### 启动

| 系统 | 方式 |
|------|------|
| **Windows** | 双击 `start.bat` |
| **macOS / Linux** | `chmod +x start.sh && ./start.sh` |

---

## 📖 使用指南

### 模式一：🎬 AI Agent 精彩片段提取

适合：从长视频中提取精彩片段，生成短视频

1. 打开 Web UI，切换到 **🎬 AI Agent** Tab
2. 上传视频或粘贴视频链接（YouTube/B站等）
3. 在指令框输入想要的效果，例如：
   ```
   从这个视频中提取 3 个最精彩的片段，生成 60 秒短视频
   ```
4. 点击 **开始处理**
5. 等待 Agent 自动完成：转录 → 分析 → 配音 → 特效 → 拼接
6. 下载生成的短视频

**AI 会自动为你做**：
- ✅ 从长视频中挑出最有价值的片段
- ✅ 为每段生成中文 TTS 配音
- ✅ 添加字幕动画特效（spring/fade/typewriter）
- ✅ 添加转场效果（fade/wipeleft/circleopen 等）
- ✅ 拼接成完整短视频

### 模式二：🗣️ 全片中文翻译配音

适合：把完整的英文视频翻译成中文配音版本

1. 切换到 **📝 中文字幕** Tab
2. 三种输入方式任选其一：
   - 📁 上传本地视频文件
   - 🔗 粘贴视频链接（YouTube/B站等）
   - 📂 输入已有任务目录（跳过转录，适合重复处理）
3. 点击 **开始处理**
4. 等待五步流水线完成：
   ```
   ① 语音识别 → ② AI 翻译 → ③ TTS 配音 → ④ 音轨合成 → ⑤ 字幕烧录
   ```
5. 下载带中文配音和字幕的视频

---

## 🔧 技术架构

```
┌──────────────────────────────────────────────┐
│  🎬 AI Agent 模式                              │
│  ReAct Agent (Qwen) 自主决策                    │
│  download → transcribe → analyze → dub → render │
│  多片段裁剪 + Remotion特效 + 转场拼接            │
├──────────────────────────────────────────────┤
│  🗣️ 中文字幕模式（固定流水线）                    │
│  transcribe → LLM翻译 → TTS配音                 │
│  → concat音轨合成 → FFmpeg字幕烧录               │
└──────────────────────────────────────────────┘
```

### Agent 工具链

| 工具 | 功能 | 技术栈 |
|------|------|--------|
| `download` | 从 URL 下载视频 | yt-dlp |
| `transcribe` | 语音转文字 | Groq Whisper / faster-whisper |
| `analyze` | 提取精彩片段 + 规划特效 | Qwen LLM |
| `dubbing` | 中文 TTS 配音 | Edge TTS（句级精确同步）|
| `render` | 多段裁剪 + 字幕 + 转场拼接 | FFmpeg + Remotion |

### 特效系统

**字幕动画**（Remotion）：

| 动画 | 效果 |
|------|------|
| `spring` | 弹性弹出（默认） |
| `fade` | 淡入淡出 |
| `typewriter` | 打字机逐字显示 |

**转场效果**（FFmpeg xfade）：
`fade` / `wipeleft` / `wiperight` / `circleopen` / `circleclose` / `slideup` / `slidedown` / `dissolve` / `pixelize` 等 16 种

---

## 📁 项目结构

```
VideoShortsAgent/
├── python_agent/
│   ├── app.py                # Gradio Web UI（双 Tab）
│   ├── agent.py              # ReAct Agent 主循环
│   ├── tools.py              # 工具注册器
│   ├── config.py             # 配置管理
│   └── skills/
│       ├── download_skill.py   # yt-dlp 视频下载
│       ├── transcribe_skill.py # Whisper 语音转录
│       ├── analysis_skill.py   # Qwen 金句分析
│       ├── dubbing_skill.py    # Edge TTS 配音
│       └── render_skill.py     # FFmpeg + Remotion 渲染
├── remotion_effects/           # Remotion 特效组件（可选）
├── .env                        # API Key 配置
├── requirements.txt
└── start.bat                   # Windows 一键启动
```

---

## ❓ 常见问题

### Q: 没有 GPU 可以用吗？
A: 可以。推荐配置 `GROQ_API_KEY` 使用云端 Whisper 转录（速度快 10 倍）。没有 GPU 也可以用本地 Whisper，只是速度慢一些。

### Q: FFmpeg 报错 "不是内部或外部命令"
A: FFmpeg 没有添加到系统 PATH。请按照上面的安装步骤，将 FFmpeg 的 bin 目录添加到环境变量。

### Q: Remotion 渲染失败或黑屏
A: 确保 Node.js 已安装且版本 ≥ 18。在 `remotion_effects` 目录下运行 `npm install`。渲染失败时会自动降级为 ASS 静态字幕。

### Q: 支持 Mac/Linux 吗？
A: 支持。安装 Python + FFmpeg + Node.js 后，运行 `python -m python_agent.app` 即可。

### Q: API Key 收费吗？
A: 通义千问（qwen-turbo）有免费额度，足够日常使用。Groq 有免费 tier，速率限制内免费。

---

## 🔮 未来规划

- 🎨 **AI 视频美化**：接入 Seedance / 可灵，画质增强+风格迁移
- 🌍 **多语言字幕**：支持日语、韩语等更多语言
- 📱 **竖版适配**：自动裁切为 9:16 短视频格式
- 🧠 **智能剪辑建议**：AI 分析最佳剪辑方案

---

## ⭐ Star History

如果觉得有用，请给个 Star 支持一下！🙏

## 📄 License

MIT