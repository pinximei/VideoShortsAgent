"""
TranscribeSkill - 语音转文字技能

使用 faster-whisper（基于 CTranslate2 的 Whisper 实现）将视频/音频转为
带时间戳的文字记录，输出为 JSON 文件。

核心概念：
- WhisperModel: 语音识别模型，支持多种大小（tiny/base/small/medium/large）
- segments: 模型输出的片段列表，每个片段包含 start、end、text
- transcript.json: 最终输出的结构化文件

使用示例：
    skill = TranscribeSkill()
    result_path = skill.execute("input.mp4", "./output")
    # result_path -> "./output/transcript.json"
"""
import os
import json
from faster_whisper import WhisperModel


class TranscribeSkill:
    """语音转文字技能

    将音频/视频文件中的语音内容转录为带时间戳的 JSON 文件。

    Attributes:
        model: WhisperModel 实例
            - "base" 模型：平衡速度和精度，约 150MB
            - device="cpu": 不依赖 GPU
            - compute_type="int8": 量化推理，减少内存占用
    """

    def __init__(self, model_size: str = "base"):
        """初始化转录模型

        Args:
            model_size: Whisper 模型大小，可选 tiny/base/small/medium/large
                        模型越大越准，但越慢。入门用 base 即可。
        """
        print(f"[TranscribeSkill] 正在加载 Whisper {model_size} 模型...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print(f"[TranscribeSkill] 模型加载完成 ✓")

    def execute(self, video_path: str, output_dir: str) -> str:
        """执行转录

        Args:
            video_path: 输入的视频/音频文件路径
            output_dir: 输出目录（transcript.json 将保存在此处）

        Returns:
            transcript.json 的完整路径
        """
        # 1. 检查输入文件是否存在
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"输入文件不存在: {video_path}")

        # 2. 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 3. 调用 Whisper 进行转录
        print(f"[TranscribeSkill] 正在转录: {video_path}")
        segments, info = self.model.transcribe(video_path)

        # info 包含检测到的语言等元信息
        print(f"[TranscribeSkill] 检测到语言: {info.language} (置信度: {info.language_probability:.2f})")

        # 4. 将 segments 转为 list（segments 是个生成器，需要遍历消费）
        transcript = []
        for segment in segments:
            transcript.append({
                "start": round(segment.start, 2),   # 开始时间（秒）
                "end": round(segment.end, 2),        # 结束时间（秒）
                "text": segment.text.strip()          # 文字内容
            })

        print(f"[TranscribeSkill] 转录完成，共 {len(transcript)} 个片段")

        # 5. 写入 JSON 文件
        output_path = os.path.join(output_dir, "transcript.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

        print(f"[TranscribeSkill] 已保存: {output_path}")
        return output_path
