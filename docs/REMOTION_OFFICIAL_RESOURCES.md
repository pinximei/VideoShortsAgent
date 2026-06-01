# Remotion 官方资源优化指南

> 对照 [Remotion Resources](https://www.remotion.dev/docs/resources) 与已安装的 `remotion-dev/skills`。

## 已接入本项目

| 官方资源 | 文档 | 项目落点 |
|----------|------|----------|
| **Agent Skills** | [docs/ai/skills](https://www.remotion.dev/docs/ai/skills) | `vendor/remotion-best-practices/`（`py -3 scripts/sync_remotion_official_skills.py`） |
| **MCP** | [docs/ai/mcp](https://www.remotion.dev/docs/ai/mcp) | `.cursor/mcp.json` → `remotion-documentation` |
| **Transitions** | [docs/transitions](https://www.remotion.dev/docs/transitions) | `remotion_effects` 依赖 `@remotion/transitions`；Python `map_transition_to_official()` |
| **Google Fonts** | [docs/google-fonts](https://www.remotion.dev/docs/google-fonts) | 图表组件 `AnimatedBarChart` / `AnimatedLineChart` |
| **Timing / spring** | [docs/animation](https://www.remotion.dev/docs/animation) | 柱图 stagger `damping:18 stiffness:80`（与官方 assets 一致） |
| **Captions** | skills `display-captions.md` | `SlideCaptionLayer` / TikTok 底栏 |
| **Voiceover** | skills `voiceover.md` | 外部 `dubbing_skill`（Edge TTS）+ 句级 `sentences` |

代码入口：`python_agent/remotion_resources.py`（`load_skill_rules` / `orchestration_prompt_block`）。

## 推荐安装（本机一次）

```bash
# 官方 Agent Skills（已安装可跳过）
npx skills add remotion-dev/skills

# Remotion 官方包（在 remotion_effects 目录）
cd remotion_effects
npm install @remotion/google-fonts @remotion/transitions @remotion/media
npx remotion add @remotion/transitions

# Cursor MCP（可选，开发期查文档）
# 见 .cursor/mcp.json
```

## 动画与图表（不要双通道）

1. **禁止** CSS `animation` / Tailwind 动画类（skills 明确要求）。
2. **中部图表** 仅用 `ContentRichStage` + `viz_type`（`line` / `bar` / `stat` / `none`）。
3. **禁止** 同时启用 `chart-line-rise` 底栏装饰 + 中部图表（已在校验链剔除）。
4. 柱图实现参考官方 skill 资产：`rules/assets/charts-bar-chart.tsx`（spring 逐柱延迟）。
5. **LLM 编排**：全片最多 2 个折线图镜、1 个柱状对比镜；其余镜 `viz_type=none`，中部大字居中（见 `slides_llm_director._enforce_viz_budget`）。

## 转场演进路线

| 阶段 | 方案 |
|------|------|
| 当前 | FFmpeg `xfade`（`render_slides_skill`） |
| 目标 | `@remotion/transitions` 的 `TransitionSeries`（单 Composition 多 Sequence） |

Python 侧 `transition_to_next` 仍可用 `wipeleft` 等；映射到官方类型见 `remotion_resources.map_transition_to_official()`。

## 可选增强（Resources 页常见扩展）

- **@remotion/light-leaks** — 切镜 Overlay，不缩短时间轴
- **@remotion/layout-utils** — 文字测量、fitText
- **calculateMetadata** — 按 TTS 时长动态 `durationInFrames`（替代固定 9000 帧上限）

## 编排链路

见 [LLM_SKILLS_VIDEO_ORCHESTRATION.md](./LLM_SKILLS_VIDEO_ORCHESTRATION.md)；Compose/导演 prompt 通过 `remotion_resources.orchestration_prompt_block()` 拉取官方 rules。

## 验证

```bash
py -3 scripts/run_open_skills_video.py
# 报告含 remotion-dev/skills 与各 Skill 步骤
```
