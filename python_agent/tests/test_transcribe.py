"""
TranscribeSkill 手动测试脚本

使用方法：
    1. 先安装依赖：pip install -r requirements.txt
    2. 准备一个测试视频/音频文件
    3. 运行：python -m python_agent.tests.test_transcribe

如果没有测试文件，脚本会用 FFmpeg 自动生成一段带语音的测试音频。
"""
import os
import sys
import json
import subprocess

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def generate_test_audio(output_path: str) -> str:
    """用 FFmpeg 生成一段测试音频（5秒静音 + 叠加文字转语音）

    这里用最简单的方式：生成一段 5 秒的正弦波音频作为占位。
    真实测试时你可以替换为任何包含人声的 mp4/mp3/wav 文件。
    """
    print("[测试] 未找到测试文件，正在用 FFmpeg 生成测试音频...")
    cmd = [
        "ffmpeg", "-y",                     # 覆盖已有文件
        "-f", "lavfi",                       # 使用 lavfi 虚拟输入
        "-i", "sine=frequency=440:duration=5",  # 生成 5 秒 440Hz 正弦波
        "-ar", "16000",                      # 采样率 16kHz（Whisper 推荐）
        "-ac", "1",                          # 单声道
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[测试] 测试音频已生成: {output_path}")
    return output_path


def main():
    # 1. 确定测试文件路径
    test_file = os.path.join(ROOT_DIR, "test_video.mp4")

    # 如果没有用户提供的测试文件，自动生成一个
    if not os.path.exists(test_file):
        test_file = os.path.join(ROOT_DIR, "test_audio.wav")
        if not os.path.exists(test_file):
            generate_test_audio(test_file)

    # 2. 准备输出目录
    output_dir = os.path.join(ROOT_DIR, "output", "test_transcribe")

    # 3. 运行 TranscribeSkill
    print("=" * 50)
    print("  TranscribeSkill 测试")
    print("=" * 50)

    from python_agent.skills.transcribe_skill import TranscribeSkill

    skill = TranscribeSkill(model_size="tiny")  # 用 tiny 模型加速首次测试
    result_path = skill.execute(test_file, output_dir)

    # 4. 打印结果
    print("\n" + "=" * 50)
    print("  转录结果")
    print("=" * 50)

    with open(result_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    if not transcript:
        print("（无转录内容 — 测试音频是正弦波，没有人声，这是正常的）")
        print("提示：把一个包含人声的 .mp4 文件放到项目根目录并命名为 test_video.mp4 再试")
    else:
        for item in transcript:
            print(f"  [{item['start']:.2f}s - {item['end']:.2f}s] {item['text']}")

    print(f"\n完整结果已保存到: {result_path}")


if __name__ == "__main__":
    main()
