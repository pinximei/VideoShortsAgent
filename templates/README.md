## 目录结构

```
templates/
├── scenes/                  # 场景模板（用户可编辑/新增）
│   ├── recruitment.json
│   ├── company_intro.json
│   ├── product.json
│   ├── project_release.json
│   ├── knowledge.json
│   └── general.json
├── styles/                  # 视觉风格（用户可编辑/新增）
│   ├── tech_blue.json
│   ├── vibrant_orange.json
│   └── ...
└── bgm/                     # BGM 配置（用户可编辑/新增）
    ├── none.json
    ├── upbeat_tech.json
    └── ...
```

## 模板格式

### 场景模板 (scenes/*.json)

每个文件是一个完整的场景配置，包含内联 prompt：

```json
{
  "name": "🧑‍💻 招聘 JD",
  "description": "适用于招聘岗位发布的短视频",
  "default_style": "tech_blue",
  "default_voice": "zh-CN-YunjianNeural",
  "default_bgm": "upbeat_tech",
  "slide_structure": ["title_card", "content_card", "content_card", "cta_card"],
  "prompt": "你是一个专业的短视频内容编排专家。\n\n将以下招聘信息编排为..."
}
```

### 视觉风格 (styles/*.json)

```json
{
  "name": "🌊 科技蓝",
  "colors": ["#0f0c29", "#302b63", "#24243e"],
  "text_color": "#ffffff",
  "accent_color": "#00d2ff",
  "caption_style": "spring"
}
```

### BGM 配置 (bgm/*.json)

```json
{
  "name": "🎵 轻快科技",
  "path": "assets/bgm/upbeat_tech.mp3"
}
```
