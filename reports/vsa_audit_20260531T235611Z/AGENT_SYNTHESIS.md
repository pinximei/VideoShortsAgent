# VSA 多 Agent 审查综合报告

> 审计时间 UTC: 2026-05-31（与 `00_meta.json` 一致）  
> 20 轮机器检查目录: 本文件夹 `round_XX_*.json` + `SUMMARY.json`  
> 4 路并行 Agent 审查（只基于读文件/跑测试，无虚构）

## 执行证明

| 动作 | 证据 |
|------|------|
| 20 轮自动检查 | `py -3 scripts/vsa_comprehensive_audit.py` → `SUMMARY.json`（首轮 17/20 PASS） |
| Agent-1 TTS/音色 | 见下文「音色与 TTS」 |
| Agent-2 测试与门禁 | 见下文「测试缺口」 |
| Agent-3 并发/配置 | 见下文「配置与并发」 |
| Agent-4 入口矩阵 | 见下文「入口矩阵」 |
| 本轮代码修复 | `git log -1` 见 `POST_AUDIT_FIXES.json`（审计后提交） |

复现：

```powershell
cd D:\VideoShortsAgent
py -3 scripts/vsa_comprehensive_audit.py
type reports\vsa_audit_*\SUMMARY.json
```

---

## 首轮 20 轮结果摘要

| 结果 | 项 |
|------|-----|
| ❌ FAIL | `pytest_test_vsa`（conftest 需从 `middle/` 目录跑；脚本已修） |
| ❌ FAIL | `legacy_dubbing_without_rate`（`app.py` Gradio 仍部分未接 rate） |
| ❌ FAIL | `pytest_capabilities_registry`（环境/路径，非 VSA 核心） |
| ✅ 其余 17 项 | 见 `REPORT.md` |

---

## Agent-1：音色与 TTS 路径

**HIGH**

- `vsa.py` 曾传 `voice=preset.voice`，可覆盖 task 内 `tts_voice` → **已移除该参数**
- `vsa_render` voice 优先级已改为：brief → resolve → 调用方兜底
- `agent.py` `_tool_dubbing` 曾 `DubbingSkill()` 默认 +0% → **已改为 `resolve_tts_for_platform`**
- `app.py` Text2Video / Gradio 仍 `DubbingSkill(voice=voice)` 无 rate（**待修**）
- `vsa_cli` 仍带 Yunxi 默认（**待修**）

**MED**

- `slides_render` 未合并 `llm/voice_content_style.json` → **已加 `load_tts_from_task_dir`**
- `pipeline_render.py` 在 `save_video_clips_plan(..., effects=effects)` 时 `effects` 未定义 → **已前移定义**

---

## Agent-2：测试与门禁

- `middle/tests/test_vsa.py` 仅覆盖 `task_pack.load_video_clips`，**未测** `render_from_llm_plan` / `vsa_adapter`
- `pipeline_gates` 大量分支无单测；fixture 与 `plan_too_few_clips` 不一致导致 2 个 gate 测试失败（Agent 实测）
- `render.verify_required` 配置在 VSA 路径被忽略（`vsa.py` 始终 verify）

**建议新增测试**

1. mock `render_from_plan` 的 `render_from_llm_plan` 单测  
2. `resolve_tts` + `DubbingSkill` 参数断言  
3. 修 gate fixture（`feed_kind` + ≥3 clips）

---

## Agent-3：配置与并发

- `render.parallel` + `render.max_concurrent` 可叠加，实际并发可能 > 配置预期  
- slides 模式下 `parallel: true` **不生效**（只渲 primary 再 copy）  
- 多平台并行时共享 Remotion 目录，存在竞态风险  
- `render.min_duration_sec` 配置**未被代码读取**（死配置）

---

## Agent-4：入口矩阵（生产默认）

| 生产默认 `render.mode: slides` | 函数链 | TTS |
|-------------------------------|--------|-----|
| orchestrator → `render_task_slides_videos` | Compose → DubbingSkill(resolve) → RenderSlidesSkill | ✅ 完整 |

| `render.mode: pipeline` | `render_from_llm_plan` → `vsa_render` | ✅ 完整（修 voice 覆盖后） |

| 废弃/并行 | Gradio `app.py`、ReAct `agent` 初始化 | ⚠️ 部分 |

---

## 审计后已落地修复（代码）

1. `pipeline_render.py` — `effects` 未定义即使用（真实 bug）  
2. `middle/pipeline/vsa.py` — 不再传入 `voice=preset.voice`  
3. `vsa_render.py` — TTS voice 优先级  
4. `slides_render.py` — 合并 task 内 voice style JSON  
5. `agent.py` — dubbing 工具走 `resolve_tts_for_platform`  
6. `scripts/vsa_comprehensive_audit.py` — 可复现 20 轮 + 报告目录  

---

## 待办（未声称已完成）

- [ ] `app.py` Gradio 全面接 `resolve_tts_for_platform`  
- [ ] `vsa_cli.py` 去掉 Yunxi 硬编码  
- [ ] 扩展 `test_vsa.py` 覆盖 render 路径  
- [ ] 修 `test_pipeline_gates` fixture  
- [ ] `render.verify_required` 与 `vsa.py` 行为对齐  
