"""
配置管理模块

统一配置入口，从 .env 文件读取环境变量并提供合理的默认值。
所有可配置项集中于此，其他模块通过 Config 单例访问。
"""
import os
from dotenv import load_dotenv

# 向上查找 .env 文件（从 python_agent/ 找到项目根目录的 .env）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))


class Config:
    """全局配置（从 .env 读取，提供默认值）"""

    # ── LLM 配置 ──
    @property
    def llm_api_key(self) -> str:
        """LLM API Key（必需）"""
        key = os.getenv("DASHSCOPE_API_KEY", "")
        if not key:
            raise ValueError("请在 .env 文件中设置 DASHSCOPE_API_KEY")
        return key

    @property
    def llm_base_url(self) -> str:
        return os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "qwen3.5-flash")

    @property
    def llm_analysis_model(self) -> str:
        """分析专用模型，默认与主模型相同"""
        return os.getenv("LLM_ANALYSIS_MODEL", self.llm_model)

    @property
    def llm_translate_model(self) -> str:
        """翻译专用模型"""
        return os.getenv("LLM_TRANSLATE_MODEL", "qwen-turbo")

    # ── 转录配置 ──
    @property
    def groq_api_key(self) -> str:
        return os.getenv("GROQ_API_KEY", "")

    @property
    def transcribe_mode(self) -> str:
        """默认转录模式：有 Groq Key 则用 groq，否则 local"""
        default = "groq" if self.groq_api_key else "local"
        return os.getenv("TRANSCRIBE_MODE", default)

    # ── TTS 配置 ──
    @property
    def tts_voice(self) -> str:
        return os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")

    # ── 外部 API 配置 ──
    @property
    def freesound_api_key(self) -> str:
        """Freesound API Key（在线 BGM 搜索）"""
        return os.getenv("FREESOUND_API_KEY", "")

    @property
    def pexels_api_key(self) -> str:
        """Pexels API Key（在线图片搜索）"""
        return os.getenv("PEXELS_API_KEY", "")

    # ── Agent 配置 ──
    @property
    def max_iterations(self) -> int:
        return int(os.getenv("MAX_ITERATIONS", "10"))

    @property
    def max_video_duration(self) -> float:
        """输出视频最大时长（秒）"""
        return float(os.getenv("MAX_VIDEO_DURATION", "65"))

    # ── 服务器配置 ──
    @property
    def server_port(self) -> int:
        return int(os.getenv("SERVER_PORT", "7860"))

    # ── 路径配置 ──
    @property
    def project_root(self) -> str:
        return _PROJECT_ROOT

    @property
    def whisper_model_path(self) -> str:
        return os.getenv("WHISPER_MODEL_PATH", os.path.join(_PROJECT_ROOT, "faster-whisper-large-v3"))


# ── 全局单例 ──
_config = None


def get_config() -> Config:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


# ── 向下兼容旧接口 ──
def get_dashscope_api_key() -> str:
    return get_config().llm_api_key


def get_groq_api_key() -> str:
    return get_config().groq_api_key


def save_to_env(updates: dict) -> str:
    """将配置更新写入 .env 文件，并同步更新当前进程的环境变量

    Args:
        updates: {环境变量名: 值} 字典，如 {"LLM_MODEL": "qwen-turbo"}

    Returns:
        保存结果消息
    """
    env_path = os.path.join(_PROJECT_ROOT, ".env")

    # 1. 读取现有 .env 内容
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    # 2. 更新或追加每个配置项
    remaining = dict(updates)  # 未处理的更新项
    new_lines = []
    for line in existing_lines:
        stripped = line.strip()
        # 跳过空行和注释
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        # 解析 KEY=VALUE
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                # 用新值替换
                new_lines.append(f"{key}={remaining.pop(key)}\n")
                continue
        new_lines.append(line)

    # 3. 追加尚未写入的新配置项
    if remaining:
        new_lines.append("\n")
        for key, value in remaining.items():
            new_lines.append(f"{key}={value}\n")

    # 4. 写回文件
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 5. 同步更新当前进程的环境变量（使配置立即生效）
    for key, value in updates.items():
        os.environ[key] = str(value)

    count = len(updates)
    print(f"[Config] ✅ 已保存 {count} 项配置到 {env_path}")
    return f"✅ 已保存 {count} 项配置到 .env 文件（部分设置需重启后生效）"
