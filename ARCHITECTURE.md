# VideoShortsAgent + Soul 中间层（同仓）

## 结构

```text
VideoShortsAgent/
  middle/                      # Soul 编排中间层（原 aisoul-pipeline）
  python_agent/
    capabilities/registry.py   # 统一特效/样式/转场能力目录
    vsa_render.py              # 裁剪函数（消费 LLM 分镜 JSON）
    vsa_cli.py                 # 可选 CLI / EXE 入口
    skills/                    # FFmpeg / TTS / Remotion（能力不删减）
  remotion_effects/            # 特效配置 effects_config.json
  apps/studio/                 # 可选桌面 UI
```

## 主链路

Soul 文章 → `middle` LLM（读 capabilities 目录）→ `llm/video_clips_*.json` → `vsa_render.render_from_plan()` → 发布标记

能力查询：`GET /api/v1/capabilities`（middle 控制台）

详见 `middle/README.md`。

