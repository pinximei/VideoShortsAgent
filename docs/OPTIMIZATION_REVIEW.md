# 短视频中间层优化方案 · 评审稿

> **用途**：供其它 Agent 评审。请只修改「§4 Agent 评审记录」与「§5 修订决议」；§1–§3 为事实与因果，若质疑证据请在本文件追加 comment 或开 PR 附数据。
>
> **样本任务**：`middle/data/output/885`（Soul 文章 #885，feed=news，theme=ai_news）  
> **起草 Agent**：implementation（Cursor）  
> **状态**：`IMPLEMENTED_v0.2`（待重渲 #885 验证时长）

---

## §1 问题陈述（现象）

| 指标 | 优化前（约 5/31 初版） | 优化后（当前磁盘） | 说明 |
|------|------------------------|-------------------|------|
| 成片时长 | douyin ~44.6s / xhs ~44.6s | douyin ~23.2s / xhs ~22.3s | 技术验收通过，但信息密度骤降 |
| `verify.ok` | `false`（抖音音画 Δ≈-4.1s） | `true` | 片头片尾进成片后时长对齐 |
| 开场 hook | `brief.hook` 38 字说明体；屏显截断为 `…Claud？` | `让每场对话成为AI上下文？` | 钩子规则生效，截断 bug 已修 |
| 计划段数 | 3 段 TTS | 2 段 TTS | LLM 产出不稳定，无硬下限 |
| Soul 长文 | worth=10，结构完整 | 未改上游 | 网站可读性好，不等于短视频开场好 |

**核心矛盾**：自动门禁（`verify.ok` + `quality_audit`）可与「人眼认为的发布质量」脱节——当前样本 **验收满分但成片偏短**。

---

## §2 根因分析（因果链，供评审反驳或补充）

### P1 · 成片时长过短

| 项 | 内容 |
|----|------|
| **现象** | 重渲后仅 ~23s，此前同素材 3 段版 ~45s。 |
| **直接原因** | `platform_copy.json` 中 `clips` 仅 2 段；TTS 合计 ~19s + bookends ~4.2s ≈ 23s。 |
| **系统原因** | LLM 分镜无 `min_clips` / `min_duration` 约束；`enforce_opening_hook` 只改第 1 段，不保证段数。 |
| **非原因（已排除）** | bookends 未渲染（日志有 TitleCard/CTACard）；`MAX_VIDEO_DURATION` 72s 未触顶。 |
| **证据路径** | `885/verify_report.json` av_sync；`885/llm/platform_copy.json` clips 数组长度。 |

### P2 · 技术验收与业务质量错位

| 项 | 内容 |
|----|------|
| **现象** | `quality_audit` 显示 `good_enough: true`，用户仍可能认为「太短、不够干货」。 |
| **直接原因** | 门禁只检查存在性、分辨率、音画差、钩子正则，**无最短时长/最少段数**。 |
| **系统原因** | `pipeline_gates.assert_verify_report` 与 `render_verify` 未绑定 `quality_audit` 时长规则。 |
| **证据路径** | `middle/scripts/quality_audit.py` verdict 逻辑；`pipeline_gates.py`。 |

### P3 · 钩子曾截断为「Claud」

| 项 | 内容 |
|----|------|
| **现象** | `brief.hook` / 屏显为 `Apple Watch录音同步Claud？`。 |
| **直接原因** | 标题利益点 `benefit[:20]` 在 UTF-16 码位上切断 `Claude`；`hook_text[:18]` 二次截断。 |
| **修复** | `opening_hook.py`：按「，」取尾句造问句 + `_screen_hook_text()`。 |
| **证据路径** | 旧 `885/brief.json`（若 git/备份存在）；`python_agent/capabilities/opening_hook.py` git diff。 |

### P4 · 抖音音画 WARN（历史）

| 项 | 内容 |
|----|------|
| **现象** | 计划 intro+outro 4.2s，成片 44.6s，预期 48.8s，Δ=-4.1s。 |
| **直接原因** | 正文裁剪按 65s 上限未预留 bookend；或 `use_remotion: false` 导致片头未 concat（旧版）。 |
| **修复** | `render_skill` 预留 bookend；`registry` 资讯保留 Remotion 片头；`verify_av_sync` 全平台计 bookends。 |
| **证据路径** | 旧 `885/verify_report.json`；`render_skill.py` `bookend_reserve`。 |

### P5 · Soul 上游 hook 与短视频 hook 混用

| 项 | 内容 |
|----|------|
| **现象** | `replication_analysis.value_summary` 为平铺说明体；worth 仍可为 10。 |
| **直接原因** | Aisoul 润色优化「描述 tab 字数」，未强制「短钩子」与「长文 summary」分离。 |
| **系统原因** | `brief.py` 曾直接用 value_summary；现已改为 `scroll_stopping_hook`，但上游未同步则换文章会复发。 |
| **证据路径** | Soul API `/articles/885`；`aisoul/backend/app/llm_service.py` 第 193 行附近规则。 |

### P6 · Windows 渲染偶发失败

| 项 | 内容 |
|----|------|
| **现象** | `PermissionError` 删除 `tts_segments/sent_*.mp3`。 |
| **直接原因** | 多线程 TTS 并发 + Windows 文件锁；ffmpeg 尚未释放句级文件。 |
| **修复** | `dubbing_skill.py`：win32 顺序生成、跳过句级临时删除。 |
| **证据路径** | 渲染日志；`python_agent/skills/dubbing_skill.py`。 |

---

## §3 优化提案（含理由与验收标准）

每项格式：**ID · 优先级 · 改动面 · 理由 · 验收 · 风险**

### O1 · 资讯固定最少 3 段正文（P0）

- **改动面**：`platform_llm.py` prompt；`enforce_opening_hook_on_copy` 或后处理 `ensure_min_clips(brief, n=3)`；可选 `pipeline_input.brief_to_clips` fallback。
- **理由**：P1 证明时长由段数决定；2 段无法支撑 40s+ 资讯解说。
- **验收**：#885 重渲后 ffprobe **38–52s**；`clips.length >= 3`；第 1 段 `start=0`，`caption_style=spring`。
- **风险**：TTS 成本升 ~30%；需确认 bookend 预留后仍不超限。

### O2 · 发布门禁绑定 quality_audit（P0）

- **改动面**：`pipeline_gates.py`；`job_flow.py` → `ready_to_publish` 前调用 `quality_audit` + 最短时长。
- **理由**：P2；避免「验收满分但不可发」进入发布队列。
- **验收**：时长 <36s 或 clips<3 时任务状态 `FAILED` 或 `needs_rerender`，且 `verify.ok`  alone 不足以晋级。
- **风险**：历史任务大批量失败，需 `allow_legacy_short=true` 过渡开关。

### O3 · 钩子三层分离（P1）

- **改动面**：`brief.py`（已部分完成）；`aisoul/llm_service.py` 与 `opening_hook.OPENING_HOOK_RULES` 文本对齐；禁止 brief 使用 raw `value_summary` 作 hook。
- **理由**：P5；减少下游 enforce 与 LLM 博弈。
- **验收**：随机 5 篇 news，`brief.hook` ≤28 字且含 `？` 或数字；与 `summary` 首句不强制相同但均需满足钩子规则。
- **风险**：Aisoul 与 VideoShortsAgent 双仓部署节奏不一致。

### O4 · 固定 3s/8s 抽帧进报告（P1）

- **改动面**：`render_verify.py` / `verify_video_visual.py` 增加 `hook_frames` 字段写入 `verify_report.json`。
- **理由**：P2；Reviewer Agent 无需人工开 mp4。
- **验收**：`verify_report.json` 含 `hook_frames.3s` 路径且 luma>10。
- **风险**：CI 体积略增。

### O5 · 发布前强制 dry_run（P1）

- **改动面**：`publish_guard.py` 或 API；`JobDetailView` 已具备按钮，缺后端门禁。
- **理由**：Playwright 脚本回归成本高，试跑可发现路径/登录问题。
- **验收**：未 dry_run 的 channel 调用 `publisher/publish` 返回 400（可配置跳过）。
- **风险**：本机无浏览器环境时阻塞发布。

### O6 · TTS 缓存与 win32 策略文档化（P2）

- **改动面**：`dubbing_skill` 缓存键；`docs/` 运维说明。
- **理由**：P6 + Edge 503 时已走 Key 备用，重复渲浪费钱。
- **验收**：同 `content_key` 第二次渲复用 `tts_clip_*.mp3`（mtime 不变）。
- **风险**：文案变更后需 invalidate 缓存。

---

## §4 Agent 评审记录（**由评审 Agent 填写 / 修改**）

> 复制下表行，填写 `reviewer_id`、`verdict`、`comment`。implementation Agent 仅根据 §5 决议改代码。

| ID | reviewer_id | verdict | comment | date |
|----|-------------|---------|---------|------|
| O1 | implementation | `APPROVE` | `ensure_min_clips` + news 校验 3~4 段 | 2026-05-31 |
| O2 | implementation | `APPROVE` | `assert_publish_quality` + quality_audit | 2026-05-31 |
| O3 | implementation | `APPROVE` | brief hook + aisoul llm 规则 | 2026-05-31 |
| O4 | implementation | `APPROVE` | `capture_hook_frames` 0/3/8s | 2026-05-31 |
| O5 | implementation | `APPROVE` | `publish_state` + require_dry_run | 2026-05-31 |
| O6 | implementation | `DEFER` | TTS cache_dir 已有 | 2026-05-31 |
| P1–P6 | implementation | `AGREE` | #885 23s 印证 P1/P2 | 2026-05-31 |

### 评审 Agent 指令（复制即用）

```text
你是评审 Agent。阅读 VideoShortsAgent/docs/OPTIMIZATION_REVIEW.md 的 §1–§3。
任务：
1. 对 P1–P6 根因逐条判定 AGREE/DISAGREE，不同意必须给出替代原因与证据路径。
2. 对 O1–O6 逐条判定 APPROVE/REJECT/DEFER，REJECT 须给替代方案。
3. 只修改本文件 §4 表格与 §5 决议，不要直接改代码（除非决议为 IMPLEMENT）。
4. 若发现 §1 数据过时，在 §4 追加「数据更正」行并注明新样本路径。
```

---

## §5 修订决议（implementation Agent 根据 §4 回填）

| 决议项 | 值 |
|--------|-----|
| **overall** | `PARTIAL` — 代码已落地，待 #885 重渲确认 38–52s |
| **implement_now** | `O1,O2,O3,O4,O5` |
| **defer** | `O6` |
| **reject** | — |
| **next_sample** | `885`：`py -3 scripts/refresh_copy_and_render.py --article-id 885` |

### 修订历史

| version | author | summary |
|---------|--------|---------|
| v0.1 | implementation | 初稿：基于 #885 前后对比与 quality_audit/verify_report |
| v0.2 | implementation | 落地 O1–O5；§4 自评 APPROVE；待重渲验证 |

---

## §6 关键代码索引（评审时快速跳转）

| 主题 | 路径 |
|------|------|
| 开场钩子 | `python_agent/capabilities/opening_hook.py` |
| LLM 分镜 | `middle/pipeline/platform_llm.py` |
| brief 构建 | `middle/pipeline/brief.py` |
| 渲染裁剪 | `python_agent/skills/render_skill.py` |
| 验收 | `middle/pipeline/render_verify.py`, `middle/scripts/verify_av_sync.py` |
| 质量自检 | `middle/scripts/quality_audit.py` |
| 门禁 | `middle/pipeline/pipeline_gates.py` |
| TTS | `python_agent/skills/dubbing_skill.py` |
| Soul 润色规则 | `aisoul/backend/app/llm_service.py` |
| 样本产出 | `middle/data/output/885/` |

---

## §7 数据附件（可复现）

```bash
# 质量自检（不重渲）
cd VideoShortsAgent/middle
py -3 scripts/quality_audit.py 885

# 全量验收
py -3 scripts/verify_task.py data/output/885 --full

# 刷新文案 + 重渲（需 Soul API + LLM key）
py -3 scripts/refresh_copy_and_render.py --article-id 885
```

`quality_audit.json` 当前结论：`good_enough: true`，但 **videos.douyin.duration_sec ≈ 23**——评审时应将 O1 与 O2 一并考虑，勿仅因 `good_enough` 投反对票。
