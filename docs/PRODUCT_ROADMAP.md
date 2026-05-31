# VideoShorts Studio — 单 EXE 产品规划

> 定位：**本地视频工作站**（一个安装包卖断）。API Key **仅用户在本机填写**，开发者不代付、不托管模型。

## 产品名建议

对外：**VideoShorts Studio（短视频工坊）**  
EXE：`VideoShortsStudio.exe`（与开源仓库 VideoShortsAgent 可并存）

## 商业模式（双轨）

详见 **[BUSINESS_MODEL.md](BUSINESS_MODEL.md)**：

- **A. 买断 + BYOK**：软件 ¥5–10 终身，用户自购通义/Groq Key，你几乎零 API 成本。  
- **B. 买断 + 平台 Token**：用户向你充值，按次扣点，你用批发 API 赚差价（需后端，建议第二版）。

第一版只做 **A**；本地/抖音/电商场景 **不扣 Token**。

---

## 架构：可扩展「场景模块」

```
VideoShortsStudio.exe
├── 壳层：pywebview + Gradio UI
├── 核心引擎：FFmpeg 渲染 / 任务队列 / 导出
├── 用户配置：%APPDATA%\VideoShortsAgent\user.env（API Key 仅此处）
├── 授权：专业版激活码（本地校验）
└── 场景 plugins（python_agent/scenarios/）
      ├── local_clip      ✅ 已实现
      ├── douyin_pack     ✅ 预设（9:16 / 时长）
      ├── ai_highlights   ✅ 已有 Agent
      ├── subtitle_cn     ✅ 已有流水线
      ├── ecommerce       🔜 商品讲解切片
      ├── live_replay     🔜 直播回放切片
      ├── batch_queue     🔜 批量任务
      └── template_store  🔜 字幕/转场模板市场
```

新增场景 = 新增一个模块 + 在 `registry.py` 注册，**不必改 EXE 壳**（小版本可用自动更新配置/插件目录）。

---

## 功能分期（覆盖抖音 / 电商 / 通用）

### Phase 1 — 可售卖 MVP（当前冲刺）

| 场景 | 用户 | 是否需要 API | 说明 |
|------|------|--------------|------|
| **本地裁剪** | 所有人 | 否 | 时间段裁剪、拼接、9:16 |
| **抖音发布包** | 达人 | 否 | 9:16 + 时长建议 + 导出命名规范 |
| **AI 智能切片** | 有通义/Groq 的用户 | 是（用户自填） | 长视频→多段短片 |
| **翻译配音** | 跨境/教程 | 是 | 英文→中文配音字幕 |
| **授权 / 设置** | 所有人 | — | 激活码；Key 仅本机 |

**收费建议**：只卖一个 **专业版 EXE 买断**（¥68–128），免费版保留水印 + AI 月限额。

### Phase 2 — 抖音 / 短视频增强（1–2 月）

- 批量导入文件夹，队列导出
- 竖屏安全区（标题/字幕避开通用遮挡区）
- 片头片尾模板（品牌/logo）
- 一键「60 秒内 / 3 段钩子」规则（仍可用本地裁剪，不强制 AI）
- 导出目录按日期/账号归档

### Phase 3 — 电商场景（2–3 月）

- **商品讲解切片**：按静音/段落切（可先规则，后可选 AI）
- **主图视频**：固定 3:4 / 1:1 裁切 + 时长 ≤15s
- **混剪素材库**：用户本地 B-roll 文件夹随机插入
- 字幕样式：价格/卖点关键词高亮（ASS 模板）

### Phase 4 — 平台与自动化（可选）

- 抖音/快手：**仅导出符合规范的成片**（不代发布，避免合规风险）
- 脚本/API 导出到剪映草稿（若可行再调研）
- 团队版：多机授权码

---

## API Key 策略（你不掏钱）

| 项 | 策略 |
|----|------|
| 存储位置 | `%APPDATA%\VideoShortsAgent\user.env` |
| 谁填写 | 用户在「设置」页输入；可选首次引导 |
| 开发者 | **永不**写入安装包或服务器 |
| 免费功能 | 本地裁剪、抖音预设 → **0 Key** |
| AI 功能 | 通义（文案/翻译）+ Groq（转录，可选）由用户申请 |

---

## 单 EXE 打包要点

1. **PyInstaller** 打 `VideoShortsStudio.exe`（windowed）
2. **内置 FFmpeg**（`resources/ffmpeg/bin`）→ 用户无需单独装
3. **不内置**任何 API Key、不包含 `.env` 样例密钥
4. 首次启动创建 `user.env` 模板（空 Key + 说明链接）
5. 输出/缓存：`%APPDATA%\VideoShortsAgent\output`（可选，避免写安装目录）

---

## 竞品差异（话术）

- 不是云端 SaaS，**不上传视频到开发者服务器**
- 不是又一个「AI 生成大片」，而是 **切片 + 发布规范 + 可选 AI**
- 电商/抖音用 **场景预设**，降低学习成本

---

## 你下一步只做三件事

1. 用 `build_pc.bat` 打出 EXE，自己剪 3 条片当演示视频  
2. 闲鱼/小红书卖 **买断 + 激活码**（`tools/generate_license.py`）  
3. 按 Phase 2 用户需求加 **批量队列**（回报最高）

技术实现索引见仓库 `python_agent/scenarios/registry.py`。
