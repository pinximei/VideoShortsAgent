---
name: analyze
description: 从转录文本中分析内容并提取关键主题段落
parameters:
  - name: transcript_path
    description: transcript.json 文件路径
    required: true
---

## 功能

从视频转录文本（transcript.json）中，利用 LLM 分析内容并提取若干完整描述主题的关键段落。

## 输入

- `transcript_path`：transcript.json 文件路径，内容为带时间戳的转录片段数组

## 输出

JSON 对象，包含以下字段：
- `start`：金句片段的开始时间（秒）
- `end`：金句片段的结束时间（秒）
- `hook_text`：精简后的金句文案（用于字幕显示）

## 示例

输出示例：
```json
{"start": 12.0, "end": 30.0, "hook_text": "自动识别圆形轮廓，精准测量结果实时显示！"}
```
