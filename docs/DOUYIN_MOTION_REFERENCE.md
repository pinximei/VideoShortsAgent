# 抖音口播 / 资讯类 Remotion 动效参考（草案）

> **实证进展见 [MOTION_PRESEARCH_REPORT.md](./MOTION_PRESEARCH_REPORT.md)**。  
> 目标：复刻**别人视频里的动画语法**，而不是「商务蓝 / 活力橙」换皮。  
> `catalog.json` 的 100 条 = 20 档案 × 5 组节奏；其中 **4/5 组节奏有文献或样本依据**，**整目录尚未经 3 条抖音爆款成片逐条验收**。

## 一、爆款口播里常见的 6 种「动画语法」

| 语法 | 剪映/抖音里叫什么 | 画面行为 | 本仓库 `motion_profile` |
|------|------------------|----------|-------------------------|
| 当前词高亮 | 卡拉OK / 逐词放大 | 跟 TTS 时间轴，**仅当前词**放大+双色 | `tiktok_word_pop` |
| 短语分页 | 一句一页 / 字幕分页 | 3~4 词一组，切页时再 spring | `tiktok_phrase_pages` |
| 钩子砸字 | 弹跳字幕 / 强调 | 标题按词/按字短间隔 spring 砸入 | `kinetic_slam_tight` / `flash_hook_smash` |
| 要点轨 | 列表滑入 |  bullet 右轨或自下 stagger | `bullet_rail_right` / `bullet_stagger_up` |
| 玻璃卡片 | 卡片堆叠 | 半透明底+细边框，**不全屏 blur** | `glass_card_stack` |
| 极简标题 | 纯字呼吸 | 单行 scale 微呼吸，无粒子 | `minimal_headline` |

**不要做的（一眼 AI）：** 全屏紫绿渐变 + 三层光斑 blur、整段淡入、每镜同一 spring、PH 蓝球铺满 0s。

## 二、Remotion 官方可对齐的实现

1. **TikTok 模板** — `createTikTokStyleCaptions()`：按词时间戳高亮（我们：`TikTokActiveCaption.tsx`）
2. **spring / interpolate** — 用帧驱动，不用 CSS transition（防 flicker）
3. **remotion-bits** — word/character stagger（我们：`AnimatedHeading` 按词/字）

## 三、100 套模板 ≠ 100 种颜色

每条模板字段：

- `motion_profile`：动效档案（上表）
- `motion_params`：`staggerFrames` / `springDamping` / `springStiffness` / `wordsPerPageMs` — **改节奏不改色相**
- `reference`：人类可读参考（如「抖音口播·当前词高亮」）

生成：`py -3 scripts/generate_motion_style_catalog.py`

## 四、管线怎么选模板

| 泳道 | 场景 | 模板池偏向 |
|------|------|------------|
| `feed_kind=news` | `ai_news` | `tiktok_*` / `kinetic_*` / `glass_card_stack` |
| GitHub 日更 | `daily_github` | `github_daily_*` / `episode_counter` |

代码：`python_agent/motion_templates.py` → `middle/pipeline/slides_render.py` 在 Compose 之后 `apply_template_plan_to_slides`。

**已关闭：** `ComposeSkill` 在 `motion_directed=True` 时不再跑「视觉导演 Pass2」（neon/matrix/glow 堆砌）。

## 五、和「去抖音扒视频」的关系

抖音 CDN 无法在本仓库内自动逐帧扒片，调研方式：

1. 人工看 3~5 条同赛道爆款（科技资讯 / GitHub 日更），记录：**几秒一镜、字怎么进、字幕跟读还是整句**  
2. 对照上表映射到 `motion_profile`  
3. 用 `motion_params` 微调节奏，直到和参考片接近  

验收：看 `llm/motion_template_plan.json` + 成片 0s/3s 静帧，不应再出现商务渐变球体片头。

## 六、本地重渲

```powershell
cd D:\VideoShortsAgent\middle
py -3 scripts\demo_render_one.py --render-only --task-dir data\output\885
```

确认 `config.yaml`：`render.mode: slides`，`render.scene: ai_news`，`render.visual_style: github_dark`。
