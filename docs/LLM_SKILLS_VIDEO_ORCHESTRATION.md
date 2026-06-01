# LLM 多 Skill 视频编排方案（开源 Remotion Skills）

## 目标

让 **LLM 负责视频编排**（口播、中部屏显、动效类型），渲染层遵循 **Remotion 官方开源 Agent Skills**，避免自造 Remotion 轮子。

## 开源 Skill 来源

| 来源 | 安装 | 作用 |
|------|------|------|
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | `npx skills add remotion-dev/skills` | 动画用 `useCurrentFrame`+`spring`/`interpolate`；禁止 CSS animation；转场用 `@remotion/transitions`；字幕/音频规范 |
| [@remotion/mcp](https://www.remotion.dev/docs/ai/mcp) | Cursor MCP: `npx @remotion/mcp@latest` | 开发时检索 Remotion 文档 |
| [mquhuy/remotion-skill](https://github.com/mquhuy/remotion-skill) | `npx remotion-skill init --ai cursor --deep` | 社区封装（可选，与官方 skills 二选一即可） |

本项目已将官方 skill 安装到：

```text
.agents/skills/remotion-best-practices/
```

编排器会从该目录读取 `SKILL.md` 与 `rules/timing.md` 等片段，注入 Compose / LLM 导演 prompt。

## 项目内多 Skill 协作链

```mermaid
flowchart TB
  subgraph open [开源]
    R[remotion-dev/skills]
    M[@remotion/mcp 可选]
  end
  subgraph ours [VideoShortsAgent]
    C[compose_skill]
    D[slides_llm_director]
    E[slides_scene_expander]
    V[slides_ai_enricher]
    G[platform G+V templates]
    T[dubbing_skill]
    P[render_slides_skill]
  end
  Brief[brief.json] --> C
  R -.->|约束注入| C
  R -.->|约束注入| D
  C --> D --> E --> V --> G --> T --> P
  P --> MP4[douyin.mp4 / xhs.mp4]
```

### 各 Skill 职责

1. **compose_skill** — LLM 生成 `slides_script`（title/content/cta + 口播草案）
2. **slides_llm_director** — LLM 改写口播、`hook_beats`（开场多句）、`summary_lines`、`viz_type`（none/line/bar/stat）
3. **slides_scene_expander** — 内容卡拆多镜 + xfade 转场名
4. **slides_ai_enricher** — 未覆盖字段规则兜底；**禁止**向 `css_decorations` 添加 `chart-line-rise`（避免与中部图表重复）
5. **platform G+V** — 抖音暖色榜单 / 小红书冷色 editorial
6. **dubbing_skill** — Edge TTS，句级时间轴
7. **render_slides_skill** — Remotion `ContentCard`/`TitleCard` + FFmpeg xfade

通用 Skill 注册表：`python_agent/skill_registry.py` + `skills/*/SKILL.md`。

新增编排 Skill：`skills/video_orchestrate/`。

## 运行方式

```bash
# 1. 安装官方 Remotion skills（仓库内已执行可跳过）
npx skills add remotion-dev/skills

# 2. 多 Skill 编排 + 双平台成片 + 报告
py -3 scripts/run_open_skills_video.py
```

报告输出：

- `reports/skills_orchestration/<timestamp>/ORCHESTRATION_REPORT_*.md`
- `reports/skills_orchestration/<timestamp>/ORCHESTRATION_REPORT_*.json`
- 成片：`.../task/videos/douyin.mp4`、`xhs.mp4`

## 与「自造轮子」的边界

| 保留自研 | 改用开源/官方 |
|----------|----------------|
| 抖音/小红书 brief、G20/V20 模板、TTS 管线 | Remotion 动画/转场/字幕规范 → **remotion-dev/skills** |
| 业务拆镜、平台 preset | 图表参考 `rules/assets/charts-bar-chart.tsx`（单通道中部） |
| `slides_llm_director` 业务 prompt | 不再每镜硬塞 `chart-line-rise` CSS 装饰 |

后续可演进：用 `@remotion/transitions` 的 `TransitionSeries` 替代 FFmpeg xfade（见 [REMOTION_OFFICIAL_RESOURCES.md](./REMOTION_OFFICIAL_RESOURCES.md)）。

编排 prompt 已改为 `python_agent/remotion_resources.orchestration_prompt_block()`，自动拉取官方 skills rules（timing / captions / transitions 等）。

## Cursor 配置建议

`.cursor/mcp.json`（可选）：

```json
{
  "mcpServers": {
    "remotion-documentation": {
      "command": "npx",
      "args": ["@remotion/mcp@latest"]
    }
  }
}
```

规则：`.cursor/rules/remotion-open-skills.mdc`（引用官方 skill 目录）。
