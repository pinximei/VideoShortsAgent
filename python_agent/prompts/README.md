# 提示词模板目录

此目录存放所有 AI 提示词模板文件，供代码运行时动态加载。  
**直接编辑这些文件即可调整 AI 行为，无需修改代码。**

## 文件说明

| 文件 | 用途 | 占位符 |
|------|------|--------|
| `agent_system.txt` | Agent 模式的系统提示词 | `{effects_section}` `{presets_section}` — 由代码自动注入特效配置 |
| `analysis.txt` | 视频内容分析 & 精彩片段提取 | `{transcript}` — 转录文本 |
| `analysis_en_addon.txt` | 英文视频的额外翻译指令 | 无 |
| `translate.txt` | 字幕模式的逐句翻译 | `{segments_text}` — 带时间戳的原文 |

## 自定义指南

1. **修改分析策略**：编辑 `analysis.txt` 中的"要求"列表，如调整片段数量、字数限制等
2. **修改 Agent 行为**：编辑 `agent_system.txt`，如调整可用步骤、语音角色列表等
3. **修改翻译风格**：编辑 `translate.txt` 中的翻译要求

> ⚠️ 请勿删除 `{占位符}`，代码运行时需要用实际数据替换它们。
