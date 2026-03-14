import os
from huggingface_hub import snapshot_download

# 强制切换到国内镜像，绕过所有网络限制
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("🚀 正在拉取 2026 年最稳的 Whisper-Turbo 模型...")

try:
    # 直接下载，不检查登录信息
    snapshot_download(
        repo_id="Systran/faster-whisper-large-v3-turbo",
        local_dir="./my_model",
        token=False,  # 关键：彻底绕过 401 授权错误
        # 忽略那些不必要的说明文档，只下核心文件
        allow_patterns=["*.bin", "*.json", "*.txt"] 
    )
    print("\n✅ 搞定！所有核心碎片已集齐，别管它几年前，能跑就是好大脑。")
except Exception as e:
    print(f"❌ 还是不行？报错是：{e}")