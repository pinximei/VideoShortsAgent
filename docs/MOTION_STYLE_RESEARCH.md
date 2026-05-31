# 短视频 Remotion 动效调研（替代「配色表」）

> 完整口播语法与管线说明见 **[DOUYIN_MOTION_REFERENCE.md](./DOUYIN_MOTION_REFERENCE.md)**。  
> 说明：无法直接爬取抖音 CDN 视频做逐帧拆解，本调研基于 **Remotion 官方 TikTok 模板**、**remotion-bits / remocn 开源组件**、以及技术口播类爆款（GitHub 日更、快闪测评、产品演示）的**可复现动效结构**。模板按「动效编排」命名，不按商务蓝/活力橙命名。

## 别人好看、我们像 AI 的常见差距

| 问题 | AI 感来源 | 应对 |
|------|-----------|------|
| 背景发糊 | 大面积 `blur()` + 半透明光斑叠 3 层 | 纯色/锐网格/代码雨，禁止全屏模糊粒子 |
| 字一起弹出 | 整段 `opacity` 淡入 | **按词/按字** spring，参考 TikTok caption |
| 节奏平 | 每镜同一套 spring | 每套 `motion_profile` 独立节奏参数 |
| 装饰堆砌 | 粒子+暗角+扫光全开 | 钩子镜可 glitch，正文镜干净可读 |
| 配色随机 | 霓虹紫绿乱搭 | GitHub 类固定 `#0d1117` + `#58a6ff` / `#3fb950` |

## 已对齐的参考来源

1. **Remotion 官方 TikTok 模板** — `createTikTokStyleCaptions()`，按词高亮、页内组合（1200ms 一页 vs 逐词）
2. **Remotion 文档** — `spring()` 弹射、`interpolate()` 限速，禁止 CSS transition 防 flicker
3. **remotion-bits** — `AnimatedText` split: word/character + stagger
4. **lacymorrow/marketing-videos** — 产品名 spring 入场 + 玻璃卡片 stagger（非模糊光晕）
5. **技术口播/GitHub 日更（结构归纳）** — 角标「今日第 N 个」、标题词弹射、要点右轨滑入、CTA 脉冲按钮

## 模板目录 v2 原则

- 文件：`templates/motion_templates/catalog.json`
- 每条模板 = **`motion_profile`（动效档案 ID）** + **`motion_params`（节奏数字）** + `reference`（参考风格文字）
- **禁止**仅用 `colors[]` 区分模板
- 目标 100 条 = 20 种动效档案 × 5 组节奏参数（stagger、spring、词分页间隔）

## 动效档案一览（实现于 `remotion_effects/src/motion/profiles/`）

| profile | 参考像什么 | 核心动画 |
|---------|------------|----------|
| `github_daily_hook` | 每天一个 GitHub 开场 | 角标 + 按词 spring 砸字 |
| `github_daily_bullets` | 同账号正文 | 要点右滑轨 + 行线 |
| `tiktok_word_pop` | 抖音口播字幕 | 当前词放大高亮 |
| `kinetic_slam_tight` | 快闪测评 | 极短 stagger 字词弹射 |
| `typewriter_terminal` | 终端风 | 等宽 + 光标 |
| `episode_counter` | 日更序号 | 大数字再出标题 |
| `glitch_hook_clean` | 钩子 glitch 正文稳 | 前 18 帧 glitch 后静止 |
| `bullet_rail_right` | 信息列表 | 条目标签从右入 |
| `minimal_headline` | 极简科技 | 单行 scale 呼吸 |
| `cta_pulse_arrow` | 结尾引导 | 按钮光圈 + 箭头 |

生成命令：`py -3 scripts/generate_motion_style_catalog.py`
