"""
VideoShortsAgent CLI 入口

使用方法：
    python -m python_agent.main --input video.mp4
    python -m python_agent.main --input video.mp4 --model tiny
    python -m python_agent.main --input video.mp4 --prompt "挑一段最搞笑的片段"
"""
import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        description="VideoShortsAgent - AI 驱动的短视频自动加工"
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
        default="./faster-whisper-large-v3",
        help="Whisper 模型路径或名称（默认: ./faster-whisper-large-v3）"
    )
    parser.add_argument(
        "--llm",
        default="qwen3-flash",
        help="Qwen 模型名称，如 qwen3-flash / qwen-max / qwen-plus（默认: qwen3-flash）"
    )
    parser.add_argument(
        "--prompt", "-p",
        default="帮我把这个视频中最有爆款潜力的片段做成短视频",
        help="给 Agent 的指令（可自定义）"
    )
    args = parser.parse_args()

    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        sys.exit(1)

    # 创建并运行 Agent
    from python_agent.agent import VideoShortsAgent
    from python_agent.config import get_dashscope_api_key

    api_key = get_dashscope_api_key()
    agent = VideoShortsAgent(api_key=api_key, llm_model=args.llm, whisper_model=args.model)

    # 用户的指令交给 Agent 自主决策
    result = agent.run(
        user_message=args.prompt,
        video_path=args.input,
        output_base=args.output
    )

    # 打印结果
    if result["status"] == "success":
        print(f"\n🎉 完成！共 {len(result['steps'])} 步")
    else:
        print(f"\n⚠️ 状态: {result['status']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
