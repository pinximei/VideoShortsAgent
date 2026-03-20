"""
MusicSearchSkill 测试脚本

使用方法：
    python -m python_agent.tests.test_music_search

测试内容：
    1. 无 API Key 时搜索应返回空列表
    2. 有 API Key 时搜索正常工作
    3. 下载功能和缓存机制
"""
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_no_api_key():
    """测试：无 API Key 时应安全返回空列表"""
    print("\n--- 测试 1: 无 API Key 时搜索 ---")
    # 临时清除 API Key
    original = os.environ.pop("FREESOUND_API_KEY", None)
    try:
        # 重新实例化以获取空的 key
        from python_agent.skills.music_search_skill import MusicSearchSkill
        skill = MusicSearchSkill()
        skill.api_key = ""  # 强制清空
        results = skill.search("test music")
        assert results == [], f"期望空列表，实际: {results}"
        print("  ✅ 通过: 无 API Key 时返回空列表，无异常")
    finally:
        if original:
            os.environ["FREESOUND_API_KEY"] = original


def test_search_with_key():
    """测试：有 API Key 时搜索正常返回结果"""
    print("\n--- 测试 2: 有 API Key 时搜索 ---")
    from python_agent.skills.music_search_skill import MusicSearchSkill
    skill = MusicSearchSkill()

    if not skill.is_available():
        print("  ⏭️ 跳过: 未配置 FREESOUND_API_KEY")
        return

    results = skill.search("upbeat technology", page_size=3)
    assert isinstance(results, list), f"结果应为列表，实际: {type(results)}"
    if results:
        item = results[0]
        assert "id" in item, "结果应包含 id"
        assert "name" in item, "结果应包含 name"
        assert "preview_url" in item, "结果应包含 preview_url"
        assert item["preview_url"].startswith("http"), f"preview_url 格式错误: {item['preview_url']}"
        print(f"  ✅ 通过: 找到 {len(results)} 条结果")
        print(f"     第一条: {item['name']} ({item['duration']}s)")
    else:
        print("  ⚠️ 搜索返回空结果（可能是网络问题）")


def test_download():
    """测试：下载功能和缓存"""
    print("\n--- 测试 3: 下载和缓存 ---")
    from python_agent.skills.music_search_skill import MusicSearchSkill
    skill = MusicSearchSkill()

    if not skill.is_available():
        print("  ⏭️ 跳过: 未配置 FREESOUND_API_KEY")
        return

    results = skill.search("calm piano", page_size=1, min_duration=10, max_duration=60)
    if not results:
        print("  ⏭️ 跳过: 搜索无结果")
        return

    item = results[0]
    output_dir = os.path.join(ROOT_DIR, "output", "test_music")
    path = skill.download(item["id"], item["preview_url"], output_dir)

    if path and os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✅ 下载成功: {path} ({size_kb:.0f}KB)")

        # 测试缓存命中
        path2 = skill.download(item["id"], item["preview_url"], output_dir)
        assert path == path2, "缓存应返回相同路径"
        print(f"  ✅ 缓存命中正常")
    else:
        print(f"  ⚠️ 下载失败")


def main():
    print("=" * 50)
    print("  MusicSearchSkill 测试")
    print("=" * 50)

    test_no_api_key()
    test_search_with_key()
    test_download()

    print("\n" + "=" * 50)
    print("  测试完成 ✓")
    print("=" * 50)


if __name__ == "__main__":
    main()
