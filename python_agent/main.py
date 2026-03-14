"""
VideoShortsAgent CLI 入口

使用方法：
    python -m python_agent.main --input video.mp4
    python -m python_agent.main --input video.mp4 --model tiny
"""
import argparse
import sys
import os

# 确保项目根目录在 Python 路径中
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="VideoShortsAgent - AI 视频自动再加工"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="输入视频文件路径"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="输出目录（默认: output）"
    )
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper 模型大小（默认: base）"
    )
    args = parser.parse_args()

    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        sys.exit(1)

    # 创建并运行 Agent
    from python_agent.agent import VideoShortsAgent

    agent = VideoShortsAgent(whisper_model=args.model)
    result = agent.run(args.input, args.output)

    # 打印最终结果
    if result["status"] == "success":
        print("\n🎉 处理完成！")
    else:
        print(f"\n💥 处理失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
