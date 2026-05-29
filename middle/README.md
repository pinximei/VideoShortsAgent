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

## 配置

- `paths.vsa_root` 默认同仓库根，一般无需改
- `llm.enabled: true` + `DASHSCOPE_API_KEY`
