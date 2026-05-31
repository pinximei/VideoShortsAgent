# 别人怎么做 vs 我们怎么做（对照表）

> 目的：先**把片做漂亮再发**。下面每一行都可追溯到「参考源 / 源码 / 实测 / 我们代码路径」。  
> **抖音爆款成片**：尚未入库（搜索页未加载），表中「口播爆款」一行来自 **Remotion 官方 TikTok 模板 + 剪映教程实测 + 口播剪辑规律**，不是猜的。

---

## 一、预研证据（证明做过，不是嘴上说）

| 证据 | 路径 / 链接 | 得到什么 |
|------|-------------|----------|
| Remotion 官方 TikTok 模板源码 | [template-tiktok/Page.tsx](https://github.com/remotion-dev/template-tiktok/blob/main/src/CaptionedVideo/Page.tsx) | 字幕距底 350px、字号上限 120、高亮 `#39E508`、分页 1200ms |
| 分页算法 | [create-tiktok-style-captions.ts](https://github.com/remotion-dev/remotion/blob/main/packages/captions/src/create-tiktok-style-captions.ts) | 按词时间戳 + 空格切页 |
| 剪映教程样本帧差 | `research/motion/reports/subtitle_motion_20260531_131929.json` | 教程 UI 区切换 **≈800ms** |
| 文字动效教程样本 | 同上，`text_fx_BV1Uo2gYqEeY_p1.mp4` | 卡点段落切换 **≈2000ms** |
| 口播剪辑规律 | [B站专栏 cv38441883](https://www.bilibili.com/read/cv38441883/) | 每 **≥5 秒** 要有一个视觉变化；重点词单独加动画 |
| 竖屏知识节奏 | [AI 批量剪映工作流](https://aistacknav.com/short-video-batch-production-ai-workflow-chatgpt-kling-capcut/) | **2–4 秒** 一个信息点；字幕 **10–16 字/行** |
| 抖音搜索采样 | `research/motion/douyin_snapshots/search_20260531_131729.png` | **失败**：灰屏未出结果，**尚无真实抖音 AI 资讯成片** |
| 剪映教程画面抽帧 | `research/motion/proof/reference_jianying_text_fx.png` | 黄字黑描边、分栏构图（教程演示，非抖音成片） |
| 我们 Remotion 预览（改后） | `research/motion/ours/preview_title_tiktok.mp4` + `preview_title_frame.png` | 黑底 + 绿字高亮字幕 + 官方分页逻辑 |
| 我们成片抽帧 | 任务重渲后补 `research/motion/ours/task_*.png` | 与参考逐帧对比 |

---

## 二、总览：为什么我们的片「一眼 AI」

| 维度 | 别人（口播爆款 / 官方 TikTok 模板） | 我们当前实现 | 差距 |
|------|-------------------------------------|--------------|------|
| 定位 | **先好看再发**；模板是剪辑语言 | 先跑通管线；100 条目录多半是参数网格 | 本末倒置 |
| 背景 | 纯色 / 实拍 B-roll / 极轻暗角 | 仍有渐变扫光 + 历史 `mesh-aurora` 路径 | 脏、糊、像 PPT |
| 字幕 | 跟 TTS **词级**高亮，大字号，安全区 | 手写 `TikTokActiveCaption`，距底 200、字号 52 | 偏小、偏上、不像抖音 |
| 标题 | 1 句钩子，**3–4 词一页** 或逐词弹 | 整段 spring / GitHub 角标 / neon 导演 | 系列感错、堆砌特效 |
| 节奏 | 2–4 秒信息点；字幕切 0.2–1.2s | 参数有，**组件未按证据调** | 数字在 JSON，画面不像 |
| 预研 | 对标视频 → 抽帧 → 填参数 | 曾写「100 套完成」 | 无抖音成片 = 未完成 |

---

## 三、分镜对照（逐条）

### 3.1 片头 / 钩子（0–3s）

| 项目 | 别人怎么做 | 我们怎么做 | 证据 |
|------|------------|------------|------|
| 文案 | 「别划走 / 刚刚 / 很多人不知道」≤14 字 | `ai_news` 场景已改；旧版 `daily_github` 仍像「今天第 N 个 GitHub」 | `templates/scenes/ai_news.json` |
| 画面 | 人脸或纯色 + **大字砸入**（按词 2–3 帧间隔） | `AnimatedHeading` 按词 spring；资讯仍可能抽到 `github_daily_hook` 角标 | `AnimatedHeading.tsx` L49–68 角标 |
| 背景 | 黑 / 实拍，无紫绿光斑 | `ProfileBackground` 仍有 `accent` 渐变层 | `ProfileBackground.tsx` L32–38 |
| 动效 | 快闪 `flash_hook_smash` 或 Remotion 页 spring(damping:200) | `flash_hook_smash` 与 `kinetic` 共用一套字弹逻辑 | 档案名不同、动画未分叉 |
| 证据链 | 剪映：入场「弹入/放大」+ 对齐重音 | LLM 视觉导演曾要求 neon/matrix（slides 模式已关） | `compose_skill.py` Pass2 |

### 3.2 口播字幕（全程，最关键）

| 项目 | 别人怎么做（Remotion 官方 = TikTok 口播事实标准） | 我们怎么做 | 证据 |
|------|---------------------------------------------------|------------|------|
| 位置 | `bottom: 350`（1080×1920 下 **≈18%** 自底） | `bottom: 200`（**≈10%**） | 官方 Page.tsx vs `TikTokActiveCaption.tsx` L42 |
| 字号 | `DESIRED_FONT_SIZE = 120` + fitText | 激活 52 / 非激活 38 | 同上 |
| 高亮色 | `#39E508`（绿） | 青 `#25f4ee` + 粉光晕 | 官方 vs `THEMES.tiktok` |
| 分页 | `createTikTokStyleCaptions`，默认 **1200ms**；注释 **200ms** 逐词 | 手写过滤，默认 `wordsPerPageMs=1000` | 未装 `@remotion/captions` |
| 当前词 | `token.fromMs <= t < token.toMs` 变色 | 用 `sentences` 近似，时间轴常对不齐 TTS 词 | `render_slides_skill` → TTS sentences |
| 描边 | 粗体 + 暗底可读（Shorts 安全区） | 轻 `textShadow`，无黑底条 | 官方示例带 padding/背景 |
| 实测节奏 | 教程区 **800ms**；卡点 **2000ms** | catalog 已写 200/800/1200/2500，**组件未跟** | `catalog.json` research_status |

### 3.3 正文要点（10–40s）

| 项目 | 别人怎么做 | 我们怎么做 | 证据 |
|------|------------|------------|------|
| 结构 | 画中画 / 素材插入；**每 5s 有变化** | 多 slide 切换；变化靠 xfade | 专栏 cv38441883 |
| 文字 | 一行 10–16 字；**重点词**换色放大 | `AnimatedBullets` 右轨/上浮；无关键词检测 | 工作流文档 |
| 卡片 | 剪映玻璃条 / 细边框 | `glass_card_stack` 有实现 | `AnimatedBullets.tsx` |
| B-roll | 实拍暗色 Ken Burns | `ensure_broll` 已改深色（pipeline 模式） | slides 模式常无 B-roll |

### 3.4 结尾 CTA（最后 3s）

| 项目 | 别人怎么做 | 我们怎么做 |
|------|------------|------------|
| 文案 | 「关注 / 评论区」短句 | `cta_card` + `cta_pulse_arrow` |
| 按钮 | 实心绿钮 + 脉冲，无霓虹 | 绿渐变钮（尚可），外圈脉冲 |

---

## 四、技术栈对照

| 层 | 别人 | 我们 |
|----|------|------|
| 剪辑 | 剪映：识别字幕 → 动画(弹入/KTV/循环) → 重点词样式 | Remotion 幻灯片 + 可选 FFmpeg ASS |
| 字幕 API | `@remotion/captions` + Whisper 词轴 | 自研 `TikTokActiveCaption`（近似） |
| 模板含义 | 一种 **剪辑语法**（字怎么动） | 曾混用 **配色表** `generate_motion_templates.py`（已禁用） |
| 选型 | 人眼选对标 → 套剪映预设 | `motion_templates.py` 按 seed 选 profile |
| 发布门槛 | 自己先看 3 遍 | `verify_ok` 偏技术，不评美感 |

---

## 五、参数对照（预研数字 → 代码是否落地）

| 参数 | 参考值 | catalog 里 | Remotion 组件里 |
|------|--------|------------|-----------------|
| `combineTokensWithinMilliseconds` | 200 / 800 / 1200 / 2500 | ✅ `wordsPerPageMs` | ❌ 未接官方 API |
| 字幕 `bottom` | 350px @1920 | — | ❌ 200 |
| 高亮色 | `#39E508` | — | ❌ 青粉霓虹 |
| 页入场 spring | damping 200, 5 帧 | 部分 profile | ❌ 字幕无页级 spring |
| 信息点间隔 | 2–4s | 2500ms 档 | ⚠️ 依赖 slide 时长，非强制 |

---

## 六、接下来怎么做才算「有意义」（顺序）

1. **对齐 Remotion 官方字幕**（`@remotion/captions` + bottom 350 + 120 号字 + `#39E508`）— 今天改代码  
2. **重渲一条样片** → 抽帧到 `research/motion/ours/`，和 `refs/` 并排放  
3. **你提供 2–3 条抖音 AI 资讯对标链接** → 下载分析 → 把表中「口播爆款」从「官方代理」换成「实测爆款」  
4. **美感门禁**：发布前人工看 0s / 5s / 15s 静帧，不通过不发布  

---

## 七、文件索引

| 文档 | 内容 |
|------|------|
| [MOTION_PRESEARCH_REPORT.md](./MOTION_PRESEARCH_REPORT.md) | 实测数字、未完成项 |
| [DOUYIN_MOTION_REFERENCE.md](./DOUYIN_MOTION_REFERENCE.md) | 动效语法草案 |
| `research/motion/reports/*.json` | 帧差分析原始数据 |
| `templates/motion_templates/catalog.json` | 100 条档案（4/5 节奏有文献依据） |

*更新：2026-05-31*
