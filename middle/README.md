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

## 配置

- `paths.vsa_root` 默认同仓库根，一般无需改
- `llm.enabled: true` + `DASHSCOPE_API_KEY`
