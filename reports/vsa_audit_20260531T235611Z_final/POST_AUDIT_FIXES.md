# 审计后代码修复清单

| 文件 | 问题 | 修复 |
|------|------|------|
| `python_agent/pipeline_render.py` | `effects` 在赋值前传入 `save_video_clips_plan` | 将 `effects = dict(preset.effects)` 前移 |
| `middle/pipeline/vsa.py` | `voice=preset.voice` 覆盖 task TTS | 移除 `voice` 参数，由 `vsa_render` 解析 |
| `python_agent/vsa_render.py` | voice 优先级错误 | brief/resolve 优先于调用方 voice |
| `middle/pipeline/slides_render.py` | 未读 `voice_content_style.json` | `load_tts_from_task_dir` 合并 brief |
| `python_agent/agent.py` | DubbingSkill 默认 +0% | init 与 `_tool_dubbing` 使用 `resolve_tts_for_platform` |
| `python_agent/app.py` | Text2Video 无 rate/pitch | 同 resolve + DubbingSkill 全参数 |
| `python_agent/vsa_cli.py` | 硬编码 Yunxi | 移除 PLATFORM_DEFAULTS 中的 voice |
| `scripts/vsa_comprehensive_audit.py` | 可复现 20 轮审查 | 新增 |
