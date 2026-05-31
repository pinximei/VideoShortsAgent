# GitHub 日更 G01–G20 产物验证报告

> 生成时间（UTC）：2026-05-31T15:12:51.226731+00:00

## 摘要

| 指标 | 值 |
|------|-----|
| 模板总数 | 20 |
| 渲染+抽帧通过 | **20/20** |
| 输出目录 | `research/motion/github_daily/verify_g20/` |

## 逐项结果（请打开 keyframe 列图片验收）

| ID | 名称 | 渲染 | 关键帧 | title_profile | CSS 装饰 | 问题 |
|----|------|------|--------|---------------|----------|------|
| G01_cyber_hook_yellow | 赛博网格钩子·黄字描边 | ✅ | `research/motion/github_daily/verify_g20/G01_cyber_hook_yellow/keyframe_50pct.png` | `kinetic_slam_tight` | grid-tunnel-bg, text-stroke-yellow, float-icon | — |
| G02_chart_card_stat | 白卡片折线图+Star数 | ✅ | `research/motion/github_daily/verify_g20/G02_chart_card_stat/keyframe_50pct.png` | `minimal_headline` | chart-line-rise, stat-pill-row | — |
| G03_minimal_white_series | 米白极简系列标题 | ✅ | `research/motion/github_daily/verify_g20/G03_minimal_white_series/keyframe_50pct.png` | `minimal_headline` | plain-white-bg | — |
| G04_badge_pills_intro | 浅灰底·徽章行+Logo头 | ✅ | `research/motion/github_daily/verify_g20/G04_badge_pills_intro/keyframe_50pct.png` | `split_mask_reveal` | repo-header, pill-badge, accent-orange-word | — |
| G05_dark_top10_rank | 黑底Top10榜单 | ✅ | `research/motion/github_daily/verify_g20/G05_dark_top10_rank/keyframe_50pct.png` | `episode_counter` | daily-video-tag, rank-number | — |
| G06_tiktok_follow_caption | 黑底绿字跟读口播 | ✅ | `research/motion/github_daily/verify_g20/G06_tiktok_follow_caption/keyframe_50pct.png` | `tiktok_word_pop` | caption-bottom-safe | — |
| G07_hook_glitch_github | Glitch钩子+GitHub角标 | ✅ | `research/motion/github_daily/verify_g20/G07_hook_glitch_github/keyframe_50pct.png` | `glitch_hook_clean` | github-badge | — |
| G08_terminal_readme | 终端风README打字 | ✅ | `research/motion/github_daily/verify_g20/G08_terminal_readme/keyframe_50pct.png` | `typewriter_terminal` | cursor-blink | — |
| G09_split_repo_screenshot | 左文右仓库截图 | ✅ | `research/motion/github_daily/verify_g20/G09_split_repo_screenshot/keyframe_50pct.png` | `product_split_frame` | image-right-panel | — |
| G10_glass_three_points | 玻璃卡片三点 | ✅ | `research/motion/github_daily/verify_g20/G10_glass_three_points/keyframe_50pct.png` | `github_daily_hook` | glass-card | — |
| G11_kinetic_word_slam | 快闪按字砸入 | ✅ | `research/motion/github_daily/verify_g20/G11_kinetic_word_slam/keyframe_50pct.png` | `flash_hook_smash` | — | — |
| G12_phrase_pages_caption | 短语分页字幕 | ✅ | `research/motion/github_daily/verify_g20/G12_phrase_pages_caption/keyframe_50pct.png` | `tiktok_phrase_pages` | — | — |
| G13_marquee_topics | 顶栏Topic跑马 | ✅ | `research/motion/github_daily/verify_g20/G13_marquee_topics/keyframe_50pct.png` | `marquee_ticker` | marquee-top | — |
| G14_shake_keyword | 关键词微震强调 | ✅ | `research/motion/github_daily/verify_g20/G14_shake_keyword/keyframe_50pct.png` | `shake_emphasis` | — | — |
| G15_star_counter_roll | Star数字滚动 | ✅ | `research/motion/github_daily/verify_g20/G15_star_counter_roll/keyframe_50pct.png` | `minimal_headline` | odometer-stars | — |
| G16_purple_gradient_soft | 柔和紫渐变（非商务蓝） | ✅ | `research/motion/github_daily/verify_g20/G16_purple_gradient_soft/keyframe_50pct.png` | `github_daily_hook` | soft-purple-gradient | — |
| G17_code_rain_minimal | 代码雨+单行标题 | ✅ | `research/motion/github_daily/verify_g20/G17_code_rain_minimal/keyframe_50pct.png` | `mono_code_rain` | — | — |
| G18_cta_star_pulse | Star脉冲CTA | ✅ | `research/motion/github_daily/verify_g20/G18_cta_star_pulse/keyframe_50pct.png` | `github_daily_hook` | pulse-button | — |
| G19_rank_episode_daily | 日更集数+大序号 | ✅ | `research/motion/github_daily/verify_g20/G19_rank_episode_daily/keyframe_50pct.png` | `episode_counter` | — | — |
| G20_clean_badge_orange | 极简+橙词+徽章（大光风） | ✅ | `research/motion/github_daily/verify_g20/G20_clean_badge_orange/keyframe_50pct.png` | `minimal_headline` | pill-badge, accent-orange-word | — |

## 管线接线验证

| 项 | 状态 |
|----|------|
| `is_github_daily_brief` → `build_github_daily_slide_plan` | ✅ `motion_templates.py` |
| `slides_render` 写入 `llm/github_daily_style.json` | ✅ |
| Remotion `backgroundColor` + `cssDecorations` props | ✅ TitleCard/Content/CTA |
| `GithubDailyDecorations` 装饰层 | ✅ `remotion_effects/src/motion/decorations/` |

## 对标抽帧（20 条别人视频）

仍见 [GITHUB_DAILY_REFERENCE_ANALYSIS.md](./GITHUB_DAILY_REFERENCE_ANALYSIS.md)

## 复现命令

```powershell
cd D:\VideoShortsAgent
py -3 scripts/motion_research/verify_github_daily_all.py
```
