# 「每天一个 GitHub」20 套动效模板（我方执行规范）

> 依据 [GITHUB_DAILY_REFERENCE_ANALYSIS.md](./GITHUB_DAILY_REFERENCE_ANALYSIS.md) 中 **20 条对标抽帧** 归纳。  
> 机器可读目录：`templates/github_daily_20/catalog.json`  
> **以后 GitHub 日更成片只从这 20 套里选，禁止再用 100 配色变体。**

---

## 0. 你怎么验收

| 材料 | 路径 | 用途 |
|------|------|------|
| 别人 20 条 × 6 关键帧 | `research/motion/github_daily/captures/<id>/keyframes/` | 对照「别人怎么做」 |
| 别人逐条拆解 | [GITHUB_DAILY_REFERENCE_ANALYSIS.md](./GITHUB_DAILY_REFERENCE_ANALYSIS.md) | 每条 URL + 风格 + 图片路径 |
| 我方样片抽帧 | `research/motion/github_daily/ours/keyframes/key_*.png` | 对照「我们现在长什么样」 |
| 我方样片 MP4 | `research/motion/github_daily/ours/preview_title_tiktok.mp4` | 3s TitleCard 预览 |

重新生成我方抽帧：

```powershell
cd D:\VideoShortsAgent
py -3 scripts/motion_research/capture_ours_preview.py
```

---

## 1. 对标归纳 → 4 母版（S01–S04）

| 母版 | 代表视频 ID | 画面特征 | 技术栈 |
|------|-------------|----------|--------|
| **S01 赛博数据** | `7618932620755291433` | 紫蓝网格隧道、黄字黑描边、白卡片+折线、Star 数强调 | Remotion `ProfileBackground` + CSS grid 动画 + chart div |
| **S02 徽章幻灯** | `7641485803578789172` | 浅灰底、顶栏 Logo/URL、橙词强调、底部 pill 徽章 | Remotion spring 标题 + flex badge 行 |
| **S03 极简系列** | `7642198364225948962` | 米白全屏、两行居中黑标题、少装饰 | `minimal_headline` + 纯色底 |
| **S04 黑底榜单** | `7642633512055475313` 等 | 纯黑、`DAILY VIDEO` 角标、Top10 大字、底口播字幕 | `episode_counter` + `TikTokActiveCaption` |

B站 12 条样本用于凑满 20 条抽帧；部分为教程/混剪，**以抖音 8 条为真对标**，B 站仅作节奏/字幕参考。

---

## 2. 二十套模板一览（G01–G20）

每套固定 **镜序**：`title_card` → `content_card` × N → `cta_card`（见 catalog `slides`）。

| ID | 名称 | 母版 | title_profile | content_profile | 背景/CSS |
|----|------|------|---------------|-----------------|----------|
| G01 | 赛博网格钩子·黄字描边 | S01 | kinetic_slam_tight | glass_card_stack | `#0d1117` + grid-tunnel + text-stroke-yellow |
| G02 | 白卡片折线图+Star | S01 | minimal_headline | github_daily_bullets | chart-line-rise + stat-pill |
| G03 | 米白极简系列标题 | S03 | minimal_headline | bullet_rail_right | plain-white `#f5f5f0` |
| G04 | 浅灰徽章行+Logo头 | S02 | split_mask_reveal | bullet_stagger_up | pill-badge + accent-orange |
| G05 | 黑底 Top10 榜单 | S04 | episode_counter | tiktok_word_pop | daily-video-tag + rank-number |
| G06 | 黑底绿字跟读 | S04 | tiktok_word_pop | tiktok_word_pop | caption-bottom-safe |
| G07 | Glitch 钩子+GitHub 角标 | — | glitch_hook_clean | github_daily_bullets | github-badge |
| G08 | 终端 README 打字 | — | typewriter_terminal | mono_code_rain | cursor-blink |
| G09 | 左文右仓库截图 | — | product_split_frame | bullet_rail_right | image-right-panel |
| G10 | 玻璃卡片三点 | — | github_daily_hook | glass_card_stack | glass-card |
| G11 | 快闪按字砸入 | — | flash_hook_smash | kinetic_slam_loose | 纯黑 |
| G12 | 短语分页字幕 | — | tiktok_phrase_pages | tiktok_phrase_pages | wordsPerPageMs 1000 |
| G13 | 顶栏 Topic 跑马 | — | marquee_ticker | github_daily_bullets | marquee-top |
| G14 | 关键词微震 | — | shake_emphasis | bullet_stagger_up | 纯黑 |
| G15 | Star 数字滚动 | — | minimal_headline | github_daily_bullets | odometer-stars |
| G16 | 柔和紫渐变 | — | github_daily_hook | bullet_rail_right | soft-purple（**非商务蓝**） |
| G17 | 代码雨+单行标题 | — | mono_code_rain | minimal_headline | `#0a0f0a` |
| G18 | Star 脉冲 CTA | — | github_daily_hook | cta_pulse_arrow | pulse-button |
| G19 | 日更集数+大序号 | S04 | episode_counter | github_daily_bullets | 纯黑 |
| G20 | 极简+橙词+徽章 | S02 | minimal_headline | glass_card_stack | `#f0f0f0` + pill |

---

## 3. Remotion / CSS 组件映射

| 能力 | 组件/文件 | 用于模板 |
|------|-----------|----------|
| 纯黑底（无渐变） | `ProfileBackground.tsx` theme=tiktok | G05,G06,G11,G14,G19 |
| 绿字跟读字幕 | `TikTokActiveCaption.tsx` + `createTikTokPages.ts` | G06,G12 |
| 按词 spring | `AnimatedHeading` / kinetic profiles | G01,G11 |
| 玻璃要点卡 | content `glass_card_stack` | G02,G04,G10,G20 |
| 集数/榜单角标 | `episode_counter` profile | G05,G19 |
| 网格隧道 | CSS `@keyframes gridMove`（待加 `remotion_effects/src/styles/github-daily.css`） | G01 |
| Pill 徽章 | flex + `border-radius: 999px` | G04,G20 |
| 折线图 | div 高度动画或 SVG path | G02 |

**禁止**：neon/matrix 粒子、`use_web3_background`、商务蓝全屏渐变（`compose_skill` 在 `motion_directed` 时已跳过）。

---

## 4. 管线如何选型（已接线）

1. `brief.feed_kind` = `github` / `github_daily`，或系列含 `github` / `每天`  
2. `is_github_daily_brief()` → `build_github_daily_slide_plan()` 从 catalog 哈希选 **一套 Gxx**（整片统一）  
3. 每镜映射 `title_profile` / `content_profile` + `bg` + `css[]`  
4. `slides_render` 写入 `llm/github_daily_style.json` + `motion_template_plan.json`  
5. Remotion 接收 `backgroundColor`、`cssDecorations`

代码入口：`python_agent/motion_templates.py`  
验证报告：`docs/GITHUB_DAILY_VERIFICATION_REPORT.md`（由 `verify_github_daily_all.py` 生成）

---

## 5. 我方 vs 别人 — 当前差距（请看图确认）

| 维度 | 别人（见对标 keyframes） | 我方（`ours/keyframes`） |
|------|--------------------------|---------------------------|
| 钩子背景 | 紫网格 / 米白 / 浅灰 | 目前多为 **纯黑** |
| 标题字 | 黄字描边 / 橙强调 / 榜单大字 | **绿字跟读**（TikTok 风） |
| 数据层 | Star 数、折线、徽章 pill | **缺** chart/badge |
| 结构 | 3–5 镜明确切换 | 样片仅 TitleCard 3s |

**下一步实现优先级**（按 S01→S04）：

1. G01/G02：网格 CSS + 黄字描边 + stat pill  
2. G04/G20：浅灰底 + 徽章行  
3. G03：米白极简标题镜  
4. G05/G19：Top10 + DAILY 角标（保留 G06 绿字幕为子风格）

---

## 6. 重新采集对标抽帧

```powershell
cd D:\VideoShortsAgent
py -3 scripts/motion_research/capture_douyin_frames.py --frames 20
py -3 scripts/motion_research/capture_bilibili_frames.py
py -3 scripts/motion_research/build_reference_doc.py
```

---

## 7. 相关文档

- [GITHUB_DAILY_REFERENCE_ANALYSIS.md](./GITHUB_DAILY_REFERENCE_ANALYSIS.md) — 20 条逐条 + 图片路径  
- [STYLE_COMPARE_OTHERS_VS_OURS.md](./STYLE_COMPARE_OTHERS_VS_OURS.md) — 总对照  
- [DOUYIN_MOTION_REFERENCE.md](./DOUYIN_MOTION_REFERENCE.md) — 动效语法
