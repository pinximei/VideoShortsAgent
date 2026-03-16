"""
TranslateSkill - LLM 翻译技能

将语音识别文本批量翻译为中文，保持时间戳不变。
从 app.py 中的 _correct_transcript_with_llm 函数抽取而来。
"""
import os
import json


class TranslateSkill:
    """LLM 翻译技能（分批处理，保持时间戳不变）"""

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size

    def execute(self, segments: list) -> list:
        """执行翻译

        Args:
            segments: 转录片段列表 [{"start": 0.0, "end": 3.5, "text": "..."}, ...]

        Returns:
            翻译后的片段列表（格式相同，text 替换为中文）
        """
        from python_agent.llm_client import create_llm_client
        from python_agent.config import get_config

        cfg = get_config()
        client = create_llm_client()

        # 加载翻译提示词
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        with open(os.path.join(prompts_dir, "translate.txt"), "r", encoding="utf-8") as f:
            prompt_template = f.read()

        all_corrected = []
        total_batches = (len(segments) + self.batch_size - 1) // self.batch_size
        print(f"[TranslateSkill] LLM 翻译: {len(segments)} 条片段，分 {total_batches} 批处理")

        for batch_idx in range(total_batches):
            batch = segments[batch_idx * self.batch_size: (batch_idx + 1) * self.batch_size]
            full_text = "\n".join(
                f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in batch
            )

            prompt = prompt_template.replace("{segments_text}", full_text)

            try:
                print(f"  批次 {batch_idx + 1}/{total_batches} ({len(batch)} 条)...", end=" ")
                response = client.chat.completions.create(
                    model=cfg.llm_translate_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                result_text = response.choices[0].message.content.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                corrected = json.loads(result_text)
                all_corrected.extend(corrected)
                print(f"✅ {len(corrected)} 条")
            except Exception as e:
                print(f"⚠️ 失败({e})，使用原文")
                all_corrected.extend(batch)

        print(f"[TranslateSkill] 翻译完成，共 {len(all_corrected)} 条字幕")
        return all_corrected
