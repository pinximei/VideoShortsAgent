---
name: video_orchestrate
description: 多 Skill 编排 slides 成片（Compose→LLM导演→拆镜→TTS→Remotion），遵循 remotion-dev/skills
parameters:
  - name: task_dir
    description: 任务目录（含 brief.json）
    required: true
  - name: platforms
    description: 平台列表，逗号分隔，默认 douyin,xhs
    required: false
---

## 功能

调用 `python_agent.video_skills_orchestrator.run_full_orchestration`，串联：

1. **remotion-dev/skills**（官方，`.agents/skills/remotion-best-practices`）
2. **compose_skill** — LLM 分镜剧本
3. **slides_llm_director** — 口播、hook_beats、中部归纳、viz_type
4. **slides_scene_expander** — 多场景与转场
5. **slides_ai_enricher** — 视觉兜底
6. **platform_gv_motion** — G20+V20
7. **dubbing_skill** + **render_slides_skill** — TTS 与 Remotion 渲染

## 安装官方 Remotion Skill（首次）

```bash
npx skills add remotion-dev/skills
```

## 参数

- `task_dir`: 任务根目录
- `platforms`: 可选，`douyin,xhs`

## 输出

在 `task_dir` 上级目录生成 `ORCHESTRATION_REPORT_*.json` 与 `.md`。
