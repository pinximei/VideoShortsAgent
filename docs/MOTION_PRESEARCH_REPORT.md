# 动效预研报告（实证版，非凭感觉）

> 状态：**进行中**。上一版 `catalog.json` 的 100 条 = 20 档案 × 5 节奏，**大部分尚未经对标视频逐帧验证**；本报告只收录**已跑工具 / 已读源码 / 已下载样本**的结论。

## 1. 我承认的问题

| 问题 | 事实 |
|------|------|
| 「100 套做完了」 | **不成立**。目录是脚本生成的参数网格，不是 100 个经抖音样本验证的独立编排。 |
| 「去抖音分析了」 | **此前没有**。抖音 CDN 不能匿名扒片；需登录采样 + 本地下载 + 帧分析流水线。 |
| `generate_motion_templates.py` | 生成的是 **Web3 配色×背景变体**（正是你反对的「商务蓝换皮」），**不应**与 `generate_motion_style_catalog.py` 混用。 |

## 2. 已完成的预研动作（可复现）

### 2.1 Remotion 官方 TikTok 模板（源码级）

来源：[remotion-dev/template-tiktok](https://github.com/remotion-dev/template-tiktok)

| 参数 | 值 | 文件 |
|------|-----|------|
| `SWITCH_CAPTIONS_EVERY_MS` | **1200** | `CaptionedVideo/index.tsx` |
| 注释建议逐词 | **200** | 同文件注释 |
| 高亮色 | `#39E508` | `CaptionedVideo/Page.tsx` |
| 目标字号 | 120（`fitText` 上限） | `Page.tsx` |
| 字幕距底 | `bottom: 350` | `Page.tsx` |
| 页入场 spring | `damping: 200`, `durationInFrames: 5` | `SubtitlePage.tsx` |

分页算法源码：[create-tiktok-style-captions.ts](https://github.com/remotion-dev/remotion/blob/main/packages/captions/src/create-tiktok-style-captions.ts) — 按**词间空格 + 时间间隔**切页。

**差距**：我们 `remotion_effects` **未安装** `@remotion/captions`，`TikTokActiveCaption.tsx` 是手写近似，未与官方 API 对齐。

### 2.2 剪映教程样本（帧差测量）

| 项 | 值 |
|----|-----|
| 样本 | [BV196xNzDEU9](https://www.bilibili.com/video/BV196xNzDEU9/) 前 45s → `research/motion/refs/BV196xNzDEU9_p1.mp4` |
| 工具 | `scripts/motion_research/analyze_subtitle_motion.py` |
| 分析区 | 画面下方 38% |
| 测得切换间隔 | **≈800ms**（中位数） |
| 建议 `combineTokensWithinMilliseconds` | **800**（教程类 UI 演示，非抖音成片） |

报告：`research/motion/reports/subtitle_motion_*.json`（最新见 `research/motion/index.json`）

| 样本 | 测得切换间隔 | 说明 |
|------|-------------|------|
| BV196xNzDEU9 剪映教程 45s | **800ms** | UI/字幕演示区 |
| BV1Uo2gYqEeY 文字动效教程 35s | **2000ms** | 含「文字卡点」段落，切换更慢 |

### 2.3 口播剪辑规律（文献）

来源：[B站专栏·口播五招](https://www.bilibili.com/read/cv38441883/)

- 识别字幕后，**重点词**单独改样式/动画，不要全片统一格式。
- **至少每 5 秒**一个变换（缩放/转场/画中画/文字），否则完播差。

来源：[AI 批量剪映工作流](https://aistacknav.com/short-video-batch-production-ai-workflow-chatgpt-kling-capcut/)

- 竖屏知识类：**2–4 秒一个信息点**。
- 屏幕字幕：**每句 ≤18 字**，一行 10–16 字。

### 2.4 抖音 Web 采样（首次尝试）

脚本：`scripts/motion_research/snapshot_douyin_search.py`  
截图：`research/motion/douyin_snapshots/search_20260531_131729.png`

**结果**：页面未加载出搜索结果（灰屏 loading），**0 条视频链接**。  
下一步：延长等待 / 改创作者后台检索 / 你提供 2–3 条对标链接直接下载。

## 3. 参数校准建议（仅基于上述证据）

| 场景 | `wordsPerPageMs` / 分页 | 依据 |
|------|-------------------------|------|
| 抖音口播·跟读高亮 | 200–500 | Remotion 注释「逐词」 |
| 口播·短语一页 | **800–1200** | 教程实测 800 + 官方默认 1200 |
| 资讯要点条 | 2000–4000 | 2–4 秒/info（工作流文档） |

**尚未验证**：`springDamping/stiffness` 与抖音爆款是否一致（需对真实抖音成片做光流/帧差标定）。

## 4. 工具链（已入库）

```powershell
# 1) 下载参考 mp4 到 research/motion/refs/
# 2) 帧分析
py -3 scripts/motion_research/analyze_subtitle_motion.py research/motion/refs/*.mp4

# 3) 汇总
py -3 scripts/motion_research/run_presearch.py

# 4) 抖音搜索截图（需已登录 profile）
py -3 scripts/motion_research/snapshot_douyin_search.py --query "AI资讯"
```

配置索引：`scripts/motion_research/references.yaml`

## 5. 未完成清单（这才是「预研做完」的标准）

- [ ] 抖音：**3 条**同赛道爆款（AI 资讯口播）下载 + 逐条 `analyze_subtitle_motion` + 人工记 3 种动效（钩子/正文/字幕）
- [ ] Remotion：安装 `@remotion/captions`，按官方 `Page.tsx` 重写字幕组件
- [ ] 用实测间隔**重生成** `catalog.json` 的 5 组 `wordsPerPageMs`，并给每条加 `research_status: validated|hypothesis`
- [ ] 废弃或隔离 `scripts/generate_motion_templates.py`（配色表生成器）

## 6. 请你协助的一点（可选）

发 **2–3 条**你认为好看的抖音 AI 资讯视频链接（或创作者主页）。我会：

1. 尝试 `yt-dlp` / 录屏样本入库  
2. 跑帧分析写进本报告  
3. 只把**对得上的**动效档案标为 `validated`，其余从目录里降级为 `hypothesis`

---

*最后更新：2026-05-31（UTC），随 `research/motion/reports/` 新报告追加。*
