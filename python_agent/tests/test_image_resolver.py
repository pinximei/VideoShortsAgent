"""
ImageResolverSkill 测试脚本（Pexels 搜索）

使用方法：
    python -m python_agent.tests.test_image_resolver

测试内容：
    1. 无 Pexels API Key 时搜索应安全跳过
    2. 有 API Key 时搜索并下载图片
"""
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_no_api_key():
    """测试：无 Pexels API Key 时 _search_pexels 应返回空字符串"""
    print("\n--- 测试 1: 无 API Key 时搜索 ---")
    original = os.environ.pop("PEXELS_API_KEY", None)
    try:
        from python_agent.skills.image_resolver_skill import ImageResolverSkill
        skill = ImageResolverSkill()
        result = skill._search_pexels("technology office", "/tmp", 0)
        assert result == "", f"期望空字符串，实际: {result}"
        print("  ✅ 通过: 无 API Key 时安全返回空字符串")
    finally:
        if original:
            os.environ["PEXELS_API_KEY"] = original


def test_pexels_search():
    """测试：Pexels 搜索并下载图片"""
    print("\n--- 测试 2: Pexels 搜索 ---")
    from python_agent.config import get_config
    config = get_config()
    if not config.pexels_api_key:
        print("  ⏭️ 跳过: 未配置 PEXELS_API_KEY")
        return

    from python_agent.skills.image_resolver_skill import ImageResolverSkill
    skill = ImageResolverSkill()

    output_dir = os.path.join(ROOT_DIR, "output", "test_pexels")
    os.makedirs(output_dir, exist_ok=True)

    result = skill._search_pexels("technology office modern", output_dir, 0)
    if result and os.path.exists(result):
        size_kb = os.path.getsize(result) / 1024
        print(f"  ✅ 下载成功: {result} ({size_kb:.0f}KB)")
    else:
        print("  ⚠️ Pexels 搜索/下载失败")


def test_execute_with_pexels():
    """测试：execute() 方法使用 Pexels 配图"""
    print("\n--- 测试 3: execute() 集成测试 ---")
    from python_agent.config import get_config
    config = get_config()
    if not config.pexels_api_key:
        print("  ⏭️ 跳过: 未配置 PEXELS_API_KEY")
        return

    from python_agent.skills.image_resolver_skill import ImageResolverSkill
    skill = ImageResolverSkill()

    output_dir = os.path.join(ROOT_DIR, "output", "test_pexels_exec")
    os.makedirs(output_dir, exist_ok=True)

    slides = [
        {
            "type": "title_card",
            "heading": "AI 技术",
            "image_keywords": "artificial intelligence technology",
            "image_prompt": "现代科技感的AI服务器机房",
            "needs_image": True,
        },
        {
            "type": "content_card",
            "heading": "团队协作",
            "needs_image": False,
        },
    ]

    result = skill.execute(slides, enable_ai_image=True, output_dir=output_dir)
    has_image = sum(1 for s in result if s.get("image_path"))
    print(f"  结果: {has_image}/{len(result)} 个 slides 有图片")
    if has_image > 0:
        print(f"  ✅ Pexels 配图集成正常")
    else:
        print(f"  ⚠️ 无图片（可能 Pexels 无匹配结果）")


def main():
    print("=" * 50)
    print("  ImageResolverSkill (Pexels) 测试")
    print("=" * 50)

    test_no_api_key()
    test_pexels_search()
    test_execute_with_pexels()

    print("\n" + "=" * 50)
    print("  测试完成 ✓")
    print("=" * 50)


if __name__ == "__main__":
    main()
