# Remotion 动效风格目录 v2

**不是配色变体表。** 每条模板绑定一个 `motion_profile`（动效档案）+ `motion_params`（节奏参数）。

## 生成

```bash
py -3 scripts/generate_motion_style_catalog.py
```

默认产出 **100 套** = 20 种动效档案 × 5 组节奏（stagger / spring / 分页间隔）。

## 调研说明

见 [docs/MOTION_STYLE_RESEARCH.md](../../docs/MOTION_STYLE_RESEARCH.md)

## 选型

`python_agent/motion_templates.py` → `llm/motion_template_plan.json`  
按 `article_id` + `slide.type`（title_card / content_card / cta_card）稳定选型。

## 实现位置

- 动效代码：`remotion_effects/src/motion/`
- 卡片接入：`TitleCard` / `ContentCard` 在传入 `motionProfile` 时走新引擎
