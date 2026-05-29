# Soul 中间层 + VSA 同仓

编排、大模型、任务状态、发布台账、Web 控制台。VSA 裁剪函数在 `python_agent/vsa_render.py`。

## 启动

```powershell
cd D:\VideoShortsAgent\middle
copy config.example.yaml config.yaml
py -3.12 -m pip install -r requirements.txt
py -3.12 scripts\start_server.py
```

## 能力目录 API

`GET http://127.0.0.1:8780/api/v1/capabilities` — 全部字幕样式、转场、Remotion 预设，LLM 生成时必须引用。

## 内容赛道（多账号）

一平台账号只维护一种内容类型。在 `config.yaml` 的 `themes` 中配置赛道（如 AI 变现 / AI 资讯），每赛道绑定各平台账号名称；任务按 Soul `feed_kind` 自动归类。

- `GET /api/v1/themes` — 赛道与账号配置
- 待发布列表支持 `?theme=ai_news` 按赛道筛选
- 任务详情可手动调整赛道

## 渠道账号（站点 code × 发布渠道）

`config.yaml` 中 `sites` 绑定 Soul 站点 code 与赛道；`channel_accounts` 为账号卡片列表。

- 控制台 **⚙️ 渠道账号**（`/settings/channels`）：选站点 code → 选渠道 → 编辑账号卡片 → 保存写回 `config.yaml`
- `GET /api/v1/channel-config` — 站点、渠道目录、账号矩阵
- `PUT /api/v1/channel-config/accounts` — 保存某站点+渠道下的全部卡片

## 发布批次（双无头浏览器 + 固定脚本）

`publisher` 模块：**不使用大模型操作网页**，全部由 Playwright 固定脚本点击。

- 固定 **2 个槽位** ↔ **2 个批次 ID**（`batch_a` / `batch_b`）↔ 两个主体
- 每账号 Profile：`data/browser/{batch_id}/{account_id}/`（复用目录保留登录）
- 控制台 **🖥️ 发布批次**（`/settings/publisher`）
- `POST /api/v1/publisher/publish` — 固定脚本发布（`dry_run: true` 只跑路由）
- `POST /api/v1/publisher/login-check` — 固定脚本检查登录

首次登录需在本机对某账号执行登录（扫码）；之后同一 Profile 目录自动带登录态。

安装：`pip install playwright && playwright install chromium`

## 配置

- `paths.vsa_root` 默认同仓库根，一般无需改
- `llm.enabled: true` + `DASHSCOPE_API_KEY`
