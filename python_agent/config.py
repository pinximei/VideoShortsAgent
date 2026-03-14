"""
配置加载模块

从 .env 文件读取环境变量，提供统一的配置访问入口。
"""
import os
from dotenv import load_dotenv

# 向上查找 .env 文件（从 python_agent/ 找到项目根目录的 .env）
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_dashscope_api_key() -> str:
    """获取 DashScope API Key（用于 Qwen-Max）"""
    key = os.getenv("DASHSCOPE_API_KEY", "")
    if not key:
        raise ValueError("请在 .env 文件中设置 DASHSCOPE_API_KEY")
    return key
