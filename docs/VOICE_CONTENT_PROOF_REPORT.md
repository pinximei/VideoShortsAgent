# 口播预研可证伪报告

> 2026-05-31T23:01:38.678597+00:00

## 实测摘要（机器输出，可复现）

| 指标 | 数值 | 证据文件 |
|------|------|----------|
| 抽帧字幕差分「可靠」条数 | **1/20** | `analysis_report.json` |
| 抽帧被登录弹窗遮挡 | **7/20** | `login_blocked:true` |
| yt-dlp 成功下载音轨 | **1/20** | `download_manifest.json` |
| VAD 有声占比（仅下载成功样本） | 见 vad_analysis | BV1dU4y1e7N9 speech_ratio≈0.987 |

## 我方 TTS rate 实测（同文案 38 字，ffprobe）

| rate | 字数 | 秒数 | 字/分钟 |
|------|------|------|---------|
| +0% | 38 | 5.88 | 387 |
| +10% | 38 | 5.352 | 426 |
| +18% | 38 | 4.992 | 456 |

MP3：`research/voice_content/ours_tts/sample_*.mp3`

## 画面文案审计（非语速，需你打开 PNG 核对）

见 `research/voice_content/visual_keyframe_audit.json`（4 条已写证据路径）

## 复现

```powershell
cd D:\VideoShortsAgent
py -3 scripts/motion_research/analyze_voice_from_captures.py
py -3 scripts/motion_research/audit_visual_from_keyframes.py
py -3 scripts/motion_research/download_reference_media.py
py -3 scripts/motion_research/analyze_audio_vad.py
```

## 对旧版文档的说明

此前 `VOICE_CONTENT_*` 中「240~290 字/分钟」等数字**无足够实测支撑**，已作废。
`templates/voice_content_20/catalog.json` 全部 `validated:false`，不得当已学完爆款。
