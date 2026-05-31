# 口播/文案 20 套模板（V01–V20）

> **⚠️ 未验证占位**：`catalog.json` 中 `validated: false`；WPM/rate 不是从 20 条爆款实测得出。  
> 请看 **`docs/VOICE_CONTENT_PROOF_REPORT.md`** 了解目前已证明什么。

> 机器目录：`templates/voice_content_20/catalog.json`

## 与画面模板关系

**必读**：`docs/VOICE_AND_MOTION_HOW_THEY_COMBINE.md`（G=画面，V=声音，组合规则）。

每套 Vxx 可通过 `reference_motion` 与 Gxx **推荐配对**；也可独立哈希选型。  
TTS 三维：`tts_voice`（音色）、`edge_tts_rate`（语速）、`edge_tts_pitch`（音调）、`sentence_pause_sec`（句停顿）。

| ID | 名称 | TTS rate | 句停顿 | 目标 WPM | 钩子 |
|----|------|----------|--------|----------|------|
| V01_burst_hook_fast | 爆款快钩子 | +18% | 0.12s | 280 | 别划走|你绝对不知道|刚刚 |
| V02_tiktok_follow_punch | 跟读短句连击 | +10% | 0.15s | 240 | 今天这个|一分钟|讲清 |
| V03_top10_listing | 榜单枚举口播 | +14% | 0.18s | 260 | Top10|前十|本周 |
| V04_minimal_calm | 极简慢讲系列感 | +5% | 0.28s | 200 | 每天一个|优质项目 |
| V05_badge_authority | 数据徽章权威感 | +8% | 0.22s | 220 | Star|MIT|开源 |
| V06_chart_story | 数据故事弧线 | +12% | 0.2s | 250 | 暴涨|增长|破万 |
| V07_glitch_tease | 悬念炸裂预告 | +16% | 0.14s | 270 | 又炸了|离谱|绝了 |
| V08_terminal_dev | 程序员终端口吻 | +6% | 0.25s | 210 | clone|README|一行命令 |
| V09_split_demo | 边讲边演示 | +10% | 0.2s | 230 | 看这个界面|左边|右边 |
| V10_glass_three_points | 三点结构化 | +9% | 0.24s | 215 | 第一|第二|第三 |
| V11_word_slam_energy | 高能量砸字口播 | +20% | 0.1s | 290 | 快|狠|准 |
| V12_phrase_pages | 短语分页口播 | +8% | 0.3s | 205 | 分三步|听我说 |
| V13_marquee_news | 资讯快报体 | +15% | 0.16s | 265 | 刚刚|突发|更新 |
| V14_shake_keyword | 关键词重复强调 | +13% | 0.18s | 255 | 重点来了|记住 |
| V15_star_odometer | Star数滚动叙事 | +11% | 0.2s | 245 | Star|星标|万人 |
| V16_soft_purple_story | 柔和叙事种草 | +7% | 0.26s | 215 | 为什么火|适合谁 |
| V17_code_rain_hook | 极客冷开场 | +5% | 0.28s | 200 | 开发者|仓库 |
| V18_cta_star_push | 强引导Star | +12% | 0.2s | 240 | 点个Star|评论区 |
| V19_daily_episode | 日更集数口播 | +10% | 0.22s | 230 | 第\d+期|日更 |
| V20_clean_badge_friend | 朋友推荐口吻 | +6% | 0.25s | 210 | 安利|自用|真心 |

## VSA 接线

- `platform_llm` / `ComposeSkill` 注入 `voice_style_prompt_block`
- `slides_render` 写入 `llm/voice_content_style.json`
- `DubbingSkill(tts_rate=..., sentence_pause=...)`

复现分析：`py -3 scripts/motion_research/analyze_voice_from_captures.py`
