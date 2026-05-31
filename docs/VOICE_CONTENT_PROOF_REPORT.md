# 口播预研可证伪报告

> 2026-05-31T23:34:31.551540+00:00

## 实测摘要（机器输出，可复现）

| 指标 | 数值 | 证据文件 |
|------|------|----------|
| B站音轨下载成功 | **12/12** | `download_manifest.json` |
| DashScope ASR 可算字/分钟 | **11/12** | `asr_analysis.json` |
| 抖音底栏 phash 字幕切换（可靠） | **6/8** | `phash_analysis.json` + `captures_v3/`（回退 v2） |
| 旧版抽帧差分「可靠」 | **0/20** | `analysis_report.json`（已弃用主证据） |
| 旧版登录弹窗遮挡 | **0/20** | v1 captures；v2 已用 video seek 修复 |
| catalog validated 样式 | **17/20** | `templates/voice_content_20/catalog.json` |

## B站 ASR 字/分钟（DashScope Paraformer，前 120s 或全片）

| BV | 分析时长(s) | 字数 | 字/分钟 | 预览 |
|----|------------|------|---------|------|
| BV1iF411k7cu | 120 | 377 | **188** | Hello, 大家好，我是你们的小胖。今天来教大家如何将get thub这个全是… |
| BV1YQ3nztEuL | 65.92 | 367 | **334** | 每天认识一款高质量开源项目第十三期今天要认识的是皮狗是世界上最快的网站构建框架，… |
| BV1DFvKzgEDE | 120 | 581 | **290** | 大家好，我是林小晨，本期视频带你快速上手get up。有这么一个网站叫做。那gt… |
| BV1hS4y1S7wL | 120 | 641 | **320** | 从前有个不会用gthu的小白。看到群友分享了一个好玩的开源项目，接下来该怎么办呢… |
| BV1XNVS6FEJG | 22.15 | 140 | **379** | 太炸裂了cloud open 4.8GPT5.5免费体验所有配额一键接入任意应用… |
| BV1b9VS64E1s | 120 | 757 | **378** | 本周Githu热门项目汇总understand nothing把代码变成可视化网… |
| BV1ySLc6QEcB | 120 | 746 | **373** | G与Githu已经成为了AI时代必学必会的基本功之一了，很多aa agent的核… |
| BV1aGVQ6AE3s | 60.33 | 340 | **361** | 顶集本期推荐一款运行在电脑端的开源免费离线文字识别工具，名字叫做2，在gtop上… |
| BV1R8Vn6JEWH | 70.03 | 428 | **369** | 用WiFi信号就能感知人体，完全不需要摄像头，这是真的成了。第一个2U6把家用路… |
| BV1aJQGBSEit | 120 | 739 | **369** | 这五款Githu开源软件你可千万别错过了，知道我为啥这么久没更新gup合集系列吗… |
| BV14qh8ztEhv | 120 | 805 | **403** | 第二是这个星球上最强大的免费资源网站。它可不是程序员的专属，而是普通人获取信息差… |

逐条转写：`research/voice_content/media/BV*/asr_dashscope.json`

## 抖音字幕切换（phash 底栏，captures_v3）

| 视频 ID | 切换间隔(ms) | phash 跳变 | reliable |
|---------|-------------|-----------|----------|
| 7618932620755291433 | 750 | 13 | True |
| 7641485803578789172 | 500 | 17 | True |
| 7642198364225948962 | 500 | 18 | True |
| 7642633512055475313 | 500 | 20 | True |
| 7641791711051647030 | — | — | None |
| 7643092805896032739 | 500 | 2 | False |
| 7643043013397623478 | 1500 | 5 | True |
| 7641861418416901414 | 500 | 16 | True |

## 我方 TTS rate 实测（同文案 38 字，ffprobe）

| rate | 字数 | 秒数 | 字/分钟 |
|------|------|------|---------|
| +0% | 38 | 5.88 | 387 |
| +10% | 38 | 5.352 | 426 |
| +18% | 38 | 4.992 | 456 |

MP3：`research/voice_content/ours_tts/sample_*.mp3`

## 复现命令

```powershell
cd D:\VideoShortsAgent
pip install imagehash dashscope
py -3 scripts/motion_research/download_bilibili_batch.py
py -3 scripts/motion_research/capture_douyin_frames.py --force --out-subdir captures_v2
py -3 scripts/motion_research/analyze_subtitle_phash.py
py -3 scripts/motion_research/batch_asr_dashscope.py
py -3 scripts/motion_research/build_validated_catalog.py
py -3 scripts/motion_research/build_honest_voice_docs.py
```

## 对旧版文档的说明

此前无 ASR 支撑的「240~290 字/分钟」已作废。
当前 B站 ASR 中位约 **290~380 字/分钟**（见 asr_analysis.json，中文按字计）。
无 ASR 的抖音条目仅能用 phash 证明**字幕切换节奏**，不能直接标语速。
