# 「每天一个 GitHub」对标视频抽帧分析（20 条）

> 生成：2026-05-31T14:13:48.741022+00:00
> **请你直接打开下面每条里的图片路径检查**（仓库内相对路径）。

## 0. 样本说明

| 来源 | 数量 | 目录 |
|------|------|------|
| 抖音 | 8 | `research/motion/github_daily/captures/<video_id>/` |
| B站（补足同赛道剪辑参考） | 12 | 同上，ID 为 BV 号 |

每条视频抽取 **6 张关键帧**：0% / 15% / 35% / 55% / 75% / 100% 进度。
原始序列帧在 `captures/<id>/f_*.png`（各 20 张）。

采集命令：
```powershell
py -3 scripts/motion_research/capture_douyin_frames.py --harvest-search --frames 20
py -3 scripts/motion_research/capture_bilibili_frames.py
```

## 1. 别人怎么做 — 共性（Remotion + CSS）

| 层级 | 别人做法 | 技术实现 |
|------|----------|----------|
| 背景 | 深色纯黑 / 浅灰米白 / 紫蓝网格隧道 | CSS `linear-gradient` + `@keyframes` 移动网格线 |
| 标题 | 大字居中，黄字黑描边 或 黑字橙强调 | Remotion `spring` 按词砸入 |
| 数据 | Star 数、MIT 徽章、语言标签 | Flex row + 圆角 pill（纯 CSS） |
| 图表 | 折线上涨、卡片浮层 | SVG/Canvas 或 div+CSS 动画高度 |
| 口播字幕 | 底部白字 或 绿字跟读 | `TikTokActiveCaption` / ASS |
| 结构 | 钩子(0-3s)→项目名→3要点→引导 | 3~5 个 Sequence 镜 |

## 2. 逐条视频（抽帧 + 制作拆解）

### 1. 每天一个GitHub热门产品

- **平台**：douyin
- **ID**：`7618932620755291433`
- **URL**：https://www.douyin.com/video/7618932620755291433
- **归纳风格**：`S01` — 深紫网格隧道背景(CSS动画) + 居中黄字黑描边 + 可选吉祥物；中段白卡片+折线图
- **Remotion/CSS**：ProfileBackground网格 + AnimatedHeading + CSS chart

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7618932620755291433/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7618932620755291433/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7618932620755291433/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7618932620755291433/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7618932620755291433/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7618932620755291433/keyframes/key_05_100pct.png`

---

### 2. Github项目推荐

- **平台**：douyin
- **ID**：`7641485803578789172`
- **URL**：https://www.douyin.com/video/7641485803578789172
- **归纳风格**：`S02` — 浅灰底幻灯片；顶栏 Logo+仓库URL；标题黑字关键词橙色；底部 pill 徽章(Star/MIT/TS)
- **Remotion/CSS**：glass_card + flex badges + spring 入场

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7641485803578789172/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7641485803578789172/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7641485803578789172/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7641485803578789172/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7641485803578789172/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7641485803578789172/keyframes/key_05_100pct.png`

---

### 3. github今日最快增长

- **平台**：douyin
- **ID**：`7642198364225948962`
- **URL**：https://www.douyin.com/video/7642198364225948962
- **归纳风格**：`S03` — 极简米白底；两行居中黑标题；系列感「每天一个优质项目」
- **Remotion/CSS**：minimal_headline + 无装饰

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7642198364225948962/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7642198364225948962/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7642198364225948962/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7642198364225948962/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7642198364225948962/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7642198364225948962/keyframes/key_05_100pct.png`

---

### 4. 本周github skill前十

- **平台**：douyin
- **ID**：`7642633512055475313`
- **URL**：https://www.douyin.com/video/7642633512055475313
- **归纳风格**：`S04` — 纯黑底；DAILY VIDEO 小标签；Top10 榜单标题；口播字幕在底部
- **Remotion/CSS**：dark bg + episode_counter + TikTokCaption

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7642633512055475313/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7642633512055475313/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7642633512055475313/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7642633512055475313/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7642633512055475313/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7642633512055475313/keyframes/key_05_100pct.png`

---

### 5. github每日热榜

- **平台**：douyin
- **ID**：`7641791711051647030`
- **URL**：https://www.douyin.com/video/7641791711051647030
- **归纳风格**：`S04` — 同热榜/榜单口播系列（黑底白字）
- **Remotion/CSS**：同 S04

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7641791711051647030/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7641791711051647030/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7641791711051647030/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7641791711051647030/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7641791711051647030/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7641791711051647030/keyframes/key_05_100pct.png`

---

### 6. github本周star前十

- **平台**：douyin
- **ID**：`7643092805896032739`
- **URL**：https://www.douyin.com/video/7643092805896032739
- **归纳风格**：`S04` — 榜单类 Star 排名
- **Remotion/CSS**：同 S04

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7643092805896032739/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7643092805896032739/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7643092805896032739/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7643092805896032739/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7643092805896032739/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7643092805896032739/keyframes/key_05_100pct.png`

---

### 7. 本周AI GitHub Top10

- **平台**：douyin
- **ID**：`7643043013397623478`
- **URL**：https://www.douyin.com/video/7643043013397623478
- **归纳风格**：`S04` — AI GitHub Top10
- **Remotion/CSS**：同 S04

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7643043013397623478/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7643043013397623478/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7643043013397623478/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7643043013397623478/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7643043013397623478/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7643043013397623478/keyframes/key_05_100pct.png`

---

### 8. 每周精选GitHub热门

- **平台**：douyin
- **ID**：`7641861418416901414`
- **URL**：https://www.douyin.com/video/7641861418416901414
- **归纳风格**：`S03` — 每周精选，偏浅色标题卡
- **Remotion/CSS**：minimal_headline

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/7641861418416901414/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/7641861418416901414/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/7641861418416901414/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/7641861418416901414/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/7641861418416901414/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/7641861418416901414/keyframes/key_05_100pct.png`

---

### 9. B站-BVHgB7ZnPbcI

- **平台**：bilibili
- **ID**：`BVHgB7ZnPbcI`
- **URL**：https://www.bilibili.com/video/BVHgB7ZnPbcI
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BVHgB7ZnPbcI/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BVHgB7ZnPbcI/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BVHgB7ZnPbcI/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BVHgB7ZnPbcI/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BVHgB7ZnPbcI/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BVHgB7ZnPbcI/keyframes/key_05_100pct.png`

---

### 10. B站-BVHgBvVc9bBR

- **平台**：bilibili
- **ID**：`BVHgBvVc9bBR`
- **URL**：https://www.bilibili.com/video/BVHgBvVc9bBR
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BVHgBvVc9bBR/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BVHgBvVc9bBR/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BVHgBvVc9bBR/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BVHgBvVc9bBR/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BVHgBvVc9bBR/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BVHgBvVc9bBR/keyframes/key_05_100pct.png`

---

### 11. B站-BVHgB7VtdbBx

- **平台**：bilibili
- **ID**：`BVHgB7VtdbBx`
- **URL**：https://www.bilibili.com/video/BVHgB7VtdbBx
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BVHgB7VtdbBx/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BVHgB7VtdbBx/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BVHgB7VtdbBx/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BVHgB7VtdbBx/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BVHgB7VtdbBx/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BVHgB7VtdbBx/keyframes/key_05_100pct.png`

---

### 12. B站-BV9xiti9rNYq

- **平台**：bilibili
- **ID**：`BV9xiti9rNYq`
- **URL**：https://www.bilibili.com/video/BV9xiti9rNYq
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV9xiti9rNYq/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV9xiti9rNYq/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV9xiti9rNYq/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV9xiti9rNYq/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV9xiti9rNYq/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV9xiti9rNYq/keyframes/key_05_100pct.png`

---

### 13. B站-BV1dU4y1e7N9

- **平台**：bilibili
- **ID**：`BV1dU4y1e7N9`
- **URL**：https://www.bilibili.com/video/BV1dU4y1e7N9
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1dU4y1e7N9/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1dU4y1e7N9/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1dU4y1e7N9/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1dU4y1e7N9/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1dU4y1e7N9/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1dU4y1e7N9/keyframes/key_05_100pct.png`

---

### 14. B站-BV1o7411U7j6

- **平台**：bilibili
- **ID**：`BV1o7411U7j6`
- **URL**：https://www.bilibili.com/video/BV1o7411U7j6
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1o7411U7j6/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1o7411U7j6/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1o7411U7j6/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1o7411U7j6/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1o7411U7j6/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1o7411U7j6/keyframes/key_05_100pct.png`

---

### 15. B站-BV1UEVM6uEMA

- **平台**：bilibili
- **ID**：`BV1UEVM6uEMA`
- **URL**：https://www.bilibili.com/video/BV1UEVM6uEMA
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1UEVM6uEMA/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1UEVM6uEMA/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1UEVM6uEMA/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1UEVM6uEMA/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1UEVM6uEMA/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1UEVM6uEMA/keyframes/key_05_100pct.png`

---

### 16. B站-BV1YQ3nztEuL

- **平台**：bilibili
- **ID**：`BV1YQ3nztEuL`
- **URL**：https://www.bilibili.com/video/BV1YQ3nztEuL
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1YQ3nztEuL/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1YQ3nztEuL/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1YQ3nztEuL/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1YQ3nztEuL/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1YQ3nztEuL/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1YQ3nztEuL/keyframes/key_05_100pct.png`

---

### 17. B站-BV1R8Vn6JEWH

- **平台**：bilibili
- **ID**：`BV1R8Vn6JEWH`
- **URL**：https://www.bilibili.com/video/BV1R8Vn6JEWH
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1R8Vn6JEWH/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1R8Vn6JEWH/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1R8Vn6JEWH/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1R8Vn6JEWH/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1R8Vn6JEWH/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1R8Vn6JEWH/keyframes/key_05_100pct.png`

---

### 18. B站-BV1TN41167Ep

- **平台**：bilibili
- **ID**：`BV1TN41167Ep`
- **URL**：https://www.bilibili.com/video/BV1TN41167Ep
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1TN41167Ep/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1TN41167Ep/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1TN41167Ep/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1TN41167Ep/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1TN41167Ep/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1TN41167Ep/keyframes/key_05_100pct.png`

---

### 19. B站-BV1VK411h7Zb

- **平台**：bilibili
- **ID**：`BV1VK411h7Zb`
- **URL**：https://www.bilibili.com/video/BV1VK411h7Zb
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV1VK411h7Zb/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV1VK411h7Zb/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV1VK411h7Zb/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV1VK411h7Zb/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV1VK411h7Zb/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV1VK411h7Zb/keyframes/key_05_100pct.png`

---

### 20. B站-BV15zV46BE6w

- **平台**：bilibili
- **ID**：`BV15zV46BE6w`
- **URL**：https://www.bilibili.com/video/BV15zV46BE6w
- **归纳风格**：`S00` — （请打开下方关键帧人工确认；B站样本可能为教程/混剪，非纯 GitHub 日更）
- **Remotion/CSS**：待标注

**关键帧（请逐张打开）：**

- 0% 开头: `research/motion/github_daily/captures/BV15zV46BE6w/keyframes/key_00_000pct.png`
- 15%: `research/motion/github_daily/captures/BV15zV46BE6w/keyframes/key_01_015pct.png`
- 35%: `research/motion/github_daily/captures/BV15zV46BE6w/keyframes/key_02_035pct.png`
- 55%: `research/motion/github_daily/captures/BV15zV46BE6w/keyframes/key_03_055pct.png`
- 75%: `research/motion/github_daily/captures/BV15zV46BE6w/keyframes/key_04_075pct.png`
- 100% 末尾: `research/motion/github_daily/captures/BV15zV46BE6w/keyframes/key_05_100pct.png`

---

## 3. 风格聚类（→ 20 套模板）

见 [GITHUB_DAILY_20_TEMPLATES.md](./GITHUB_DAILY_20_TEMPLATES.md)

## 4. 我方当前样片抽帧（对照用）

目录：`research/motion/github_daily/ours/`

- 成片：`research/motion/github_daily/ours/preview_title_tiktok.mp4`
- 关键帧：`research/motion/github_daily/ours/keyframes/key_*.png`

对比重点：我们是否已是 **纯黑底 + 绿字跟读**，是否缺 **黄字描边/徽章/网格背景**。
