"""
template_loader - 模板加载器

从 templates/ 目录加载场景、视觉风格和 BGM 配置。
用户可直接编辑 templates/ 下的 JSON 文件来定制视频生成行为。

目录结构:
    templates/
    ├── scenes/      场景模板（含内联 prompt）
    ├── styles/      视觉风格配置
    └── bgm/         BGM 配置
"""
import os
import json

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATES_DIR = os.path.join(_PROJECT_ROOT, "templates")


def _load_dir(subdir: str) -> dict:
    """加载指定子目录下的所有 JSON 文件，key = 文件名（无扩展名）"""
    result = {}
    target = os.path.join(TEMPLATES_DIR, subdir)
    if not os.path.isdir(target):
        print(f"[TemplateLoader] ⚠️ 目录不存在: {target}")
        return result
    for fname in sorted(os.listdir(target)):
        if not fname.endswith(".json"):
            continue
        key = fname[:-5]  # 去掉 .json
        path = os.path.join(target, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                result[key] = json.load(f)
        except Exception as e:
            print(f"[TemplateLoader] ⚠️ 加载失败 {fname}: {e}")
    return result


def load_scenes() -> dict:
    """加载所有场景模板"""
    return _load_dir("scenes")


def load_styles() -> dict:
    """加载所有视觉风格"""
    d = _load_dir("styles")
    
    # 强制注入 "Agent 决策" 极客选项 (让 Agent 全权代理视觉特效)
    d["auto"] = {
        "name": "✨ 自动匹配 (Agent 决策)",
        "colors": [],
        "text_color": "#ffffff",
        "accent_color": "#ffdd57",
        "caption_style": "spring"
    }
    
    return d


def load_bgm() -> dict:
    """加载所有 BGM 配置"""
    return _load_dir("bgm")


def load_all() -> dict:
    """一次性加载所有模板，返回兼容旧格式的 dict"""
    scenes = load_scenes()
    styles = load_styles()
    bgm = load_bgm()
    return {
        "scene_templates": scenes,
        "visual_styles": styles,
        "bgm_library": bgm
    }


def get_scene(scene_key: str) -> dict:
    """获取指定场景模板，不存在则返回 general"""
    scenes = load_scenes()
    if scene_key in scenes:
        return scenes[scene_key]
    if "general" in scenes:
        print(f"[TemplateLoader] 未知场景 '{scene_key}'，使用通用模板")
        return scenes["general"]
    raise ValueError(f"场景模板 '{scene_key}' 不存在且无 general 回退")


def get_style(style_key: str) -> dict:
    """获取指定视觉风格"""
    styles = load_styles()
    if style_key in styles:
        return styles[style_key]
    # 回退到第一个可用风格
    if styles:
        fallback = next(iter(styles))
        print(f"[TemplateLoader] 未知风格 '{style_key}'，回退到 '{fallback}'")
        return styles[fallback]
    # 硬编码兜底
    return {"name": "默认", "colors": ["#0f0c29", "#302b63"],
            "text_color": "#ffffff", "accent_color": "#00d2ff",
            "caption_style": "spring"}


def get_bgm_path(bgm_key: str) -> str:
    """获取 BGM 文件路径，返回绝对路径或 None"""
    bgm_configs = load_bgm()
    config = bgm_configs.get(bgm_key, {})
    rel_path = config.get("path")
    if not rel_path:
        return None
    abs_path = os.path.join(_PROJECT_ROOT, rel_path)
    return abs_path if os.path.exists(abs_path) else None
