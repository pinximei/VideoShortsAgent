# VideoShorts Studio — 方案 A + 全平台愿景（Rust 核心）

> **当前承诺：只卖软件（¥5–30 终身），AI 全部 BYOK。**  
> 本文回答：AI 短剧能不能做、能不能做「视频大全」、图片/海报、开源借鉴、**如何用 Rust 逐步实现**。

---

## 1. 方案 A（现在就做）

| 项 | 决定 |
|----|------|
| 收入 | 仅软件买断 + 可选专业版激活码 |
| API | 用户自填通义/Groq，**你不卖 Token、不代调** |
| 交付 | 一个（或一系列）Windows EXE |
| 第一版卖点 | **剪片 + 抖音规范 + 电商切段**（无 Key 也能用） |

详见 [BUSINESS_MODEL.md](BUSINESS_MODEL.md)。

---

## 2. AI 短剧能做吗？

**能做，但不是第一版，也不是「点一下就完」那种。**

短剧链路通常是：

```
剧本（LLM，用户 Key）→ 分镜/镜头表 → 画面（图 or 视频片段）
    → 配音（TTS，Edge 免费 or 通义）→ 字幕 → 合成（FFmpeg）
```

| 档次 | 做法 | 难度 | 是否适合 ¥10 软件 |
|------|------|------|-------------------|
| **轻量** | 用户上传若干图片/短视频 + 文案 → 自动配音字幕 + Ken Burns 幻灯片 | 中 | ✅ Phase「短剧-lite」 |
| **中等** | 剧本 JSON + 每镜用 **用户本地 ComfyUI/SD** 出图 → 合成 | 高 | ✅ 专业版模块 |
| **重量** | 文生视频（可灵/Sora API）、一致角色 | 很高 | ❌ 不适合低价买断 |

**建议产品名模块：** `短剧工坊（Beta）` — 先做 **轻量**（图+旁白+BGM），再对接本地 ComfyUI（开源）。

---

## 3. 「所有视频业务 + 图片海报」——能做「大集合」，但要分模块卖

不要一个 EXE 第一版塞满所有功能；用 **同一壳 + 场景插件** 逐年扩展。

### 3.1 视频域（核心盘）

| 模块 | 用户 | API | 开源参考 | 阶段 |
|------|------|-----|----------|------|
| 本地裁剪/拼接 | 所有人 | 无 | LosslessCut, auto-editor, FFmpeg | ✅ 已有 |
| 抖音/竖屏包 | 达人 | 无 | 平台规范文档 | ✅ 已有 |
| 电商讲解切 | 小店 | 无/可选 | PySceneDetect 静音检测 | Phase 2–3 |
| AI 精彩片段 | 创作者 | BYOK | MoneyPrinterTurbo 思路（不抄代码） | ✅ 已有 |
| 翻译配音 | 跨境 | BYOK | whisper + TTS 流水线 | ✅ 已有 |
| 批量队列 | 机构 | 无 | 自研任务队列 | Phase 2 |
| **短剧-lite** | 剧情号 | BYOK+可选本地 SD | 幻灯片+TTS 模板 | Phase 3 |
| 直播切片 | 主播 | 可选 BYOK | 回放+静音切 | Phase 3 |
| 去水印/压制 | 通用 | 无 | FFmpeg 滤镜 | Phase 2 |

### 3.2 图片 / 海报（扩展盘，同一品牌）

| 模块 | API | 开源参考 | 阶段 |
|------|-----|----------|------|
| 封面/缩略图 | 无/可选 BYOK | Pillow, 模板 JSON | Phase 3 |
| 电商主图批量 | 无 | 裁剪+描边+文字 | Phase 3 |
| AI 海报 | BYOK 或本地 SD | **ComfyUI** / fooocus 工作流文件 | Phase 4 |
| 抠图 | 无 | rembg, RMBG-2 | Phase 4 |

**关键：** 图片生成尽量 **调用用户本机 ComfyUI/SD WebUI**（开源、你不托管 GPU），你只卖「模板 + 一键发任务」。

---

## 4. 开源借鉴清单（合规：学架构，不直接抄 GPL 整包卖）

| 领域 | 项目 | 借鉴什么 |
|------|------|----------|
| 短视频流水线 | MoneyPrinterTurbo, NarratoAI | 任务步骤、配置项 |
| 剪辑 | LosslessCut, auto-editor, shotcut-cli | 时间段 UX、检测静音 |
| 转录 | faster-whisper, whisper.cpp | Rust 可绑 whisper.cpp |
| 字幕 | Remotion, ASS 模板 | 字幕样式 JSON |
| 下载 | yt-dlp | 外链下载（注意 ToS） |
| 短剧/幻灯片 | moviepy 思路 | 用 FFmpeg 滤镜替代 |
| 图像 | ComfyUI, InvokeAI | 工作流 JSON、本地 API |
| 桌面壳 | Tauri, pywebview | 单 EXE 方案 |

许可证注意：AGPL 项目（如部分 Comfy 节点）**不要静态链接进闭源 EXE**；用 **进程外调用** 或用户自行安装。

---

## 5. 为什么用 Rust？怎么和现有 Python 共存？

| 层级 | 技术 | 职责 |
|------|------|------|
| **vsa-core（Rust）** | ffmpeg 封装、裁剪、拼接、Probe、队列、授权校验 | 性能、单 EXE、少依赖 |
| **vsa-ui** | Tauri 2（Rust）或 暂留 Python+pywebview | 界面、场景 Tab |
| **vsa-ai（可选 Python 或 Rust HTTP）** | 调用户 Key 的 OpenAI 兼容 API | 先保留 Python 最快 |

### 推荐迁移路线（别一口吃成胖子）

```
阶段 0（现在）  Python + FFmpeg + Gradio/pywebview → 验证买断与场景
阶段 1          Rust DLL/CLI：vsa-cli clip / concat / probe
阶段 2          Python UI 改调 vsa-cli（子进程），核心迁 Rust
阶段 3          Tauri 壳 + Rust 核心；Python 仅留 AI 胶水
阶段 4          短剧/海报模块加进 vsa-core
```

已在仓库预留：`rust/vsa-core/README.md`（占位与 crate 规划）。

---

## 6. 第一版 EXE 功能边界（方案 A 可卖）

**标准版 ¥9.9**

- 本地裁剪、抖音发布包、电商基础切片  
- AI / 翻译：**仅 BYOK**（设置里填 Key）  
- 免费版：AI 次数限制 + 水印（可选）

**专业版 ¥29（后续）**

- 去水印、批量队列、更多导出模板  

**明确不做（第一版）**

- 不卖 Token、不托管 API  
- 不做文生视频、不做云端 GPU  
- 不做短剧完整版（只写路线图）  

---

## 7. 你问的「大集合」品牌建议

对外可叫：**VideoShorts Studio（短视频工坊）**  
副标题：**剪片 · 抖音 · 电商 ·（将支持）短剧与海报**

一个安装包，左侧 **场景树**（未来 Tauri）：

```
视频
  ├─ 本地裁剪 ✅
  ├─ 抖音发布包 ✅
  ├─ 电商切片 ✅
  ├─ AI 智能切片 ✅ BYOK
  ├─ 翻译配音 ✅ BYOK
  ├─ 批量任务 🔜
  └─ 短剧 lite 🔜
图片
  ├─ 封面模板 🔜
  └─ 本地 Comfy 海报 🔜
设置 / 授权
```

---

## 8. 下一步（只方案 A）

1. 冻结 **v1 功能**：三件套无 Key + AI BYOK + 激活码 + `VideoShortsStudio.exe`  
2. 立项 **rust/vsa-core**：先实现 `clip` / `concat` / `probe` 三个子命令  
3. 短剧、海报写进路线图，**不写入 v1 承诺**  
4. 售卖话术：「终身本地工具，AI 用自己 Key，比 SaaS 便宜」

相关：[PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) · [BUSINESS_MODEL.md](BUSINESS_MODEL.md)
