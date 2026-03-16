#!/bin/bash
# ══════════════════════════════════════════════════
#   🎬 VideoShortsAgent 一键安装脚本 (macOS / Linux)
# ══════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }

echo ""
echo "══════════════════════════════════════════════════"
echo "  🎬 VideoShortsAgent 一键安装脚本"
echo "══════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")"

# ─────────────────────────────────────────────────
# 1. 检测 Python
# ─────────────────────────────────────────────────
echo "[1/5] 检测 Python..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    fail "未检测到 Python！"
    echo "  请先安装 Python 3.10+："
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "    brew install python"
    else
        echo "    sudo apt install python3 python3-pip  (Ubuntu/Debian)"
        echo "    sudo dnf install python3 python3-pip  (Fedora)"
    fi
    exit 1
fi
PY_VER=$($PY --version 2>&1)
ok "$PY_VER"

# ─────────────────────────────────────────────────
# 2. 检测 FFmpeg
# ─────────────────────────────────────────────────
echo "[2/5] 检测 FFmpeg..."
if command -v ffmpeg &>/dev/null; then
    FF_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    ok "FFmpeg $FF_VER"
else
    fail "未检测到 FFmpeg！"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  尝试通过 Homebrew 自动安装..."
        if command -v brew &>/dev/null; then
            brew install ffmpeg
            ok "FFmpeg 安装完成"
        else
            fail "未检测到 Homebrew，请先安装: https://brew.sh"
            exit 1
        fi
    else
        echo "  请手动安装："
        echo "    sudo apt install ffmpeg  (Ubuntu/Debian)"
        echo "    sudo dnf install ffmpeg  (Fedora)"
        exit 1
    fi
fi

# ─────────────────────────────────────────────────
# 3. 安装 Python 依赖
# ─────────────────────────────────────────────────
echo "[3/5] 安装 Python 依赖..."
$PY -m pip install --upgrade pip -q
$PY -m pip install -r requirements.txt
ok "Python 依赖安装完成"

# ─────────────────────────────────────────────────
# 4. Node.js + Remotion（可选）
# ─────────────────────────────────────────────────
echo "[4/5] 检测 Node.js（字幕动画特效，可选）..."
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    ok "Node.js $NODE_VER"
    if [ -f "remotion_effects/package.json" ]; then
        echo "  安装 Remotion 特效依赖..."
        cd remotion_effects
        npm install --silent 2>/dev/null && ok "Remotion 特效就绪" || warn "Remotion 安装失败，将使用 ASS 字幕降级"
        cd ..
    fi
else
    warn "未检测到 Node.js，跳过 Remotion 安装"
    echo "  → 字幕将使用 FFmpeg ASS 静态样式（功能不受影响）"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  → 如需动画特效: brew install node"
    else
        echo "  → 如需动画特效: https://nodejs.org/"
    fi
fi

# ─────────────────────────────────────────────────
# 5. 配置 .env
# ─────────────────────────────────────────────────
echo "[5/5] 检查配置文件..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  📝 已从 .env.example 创建 .env"
        warn "请编辑 .env 文件，填入你的 API Key："
        echo "     DASHSCOPE_API_KEY=sk-你的阿里云密钥"
        echo "     GROQ_API_KEY=gsk_你的Groq密钥（推荐）"
    else
        warn "未找到 .env 文件，请手动创建并填入 API Key"
    fi
else
    ok ".env 配置文件已存在"
fi

# ─────────────────────────────────────────────────
# 完成
# ─────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✅ 安装完成！"
echo "══════════════════════════════════════════════════"
echo ""
echo "  📌 使用前请确认："
echo "    1. .env 中已填入 DASHSCOPE_API_KEY"
echo "    2. 如需本地转录，请下载 Whisper 模型（见 README）"
echo ""
echo "  🚀 启动方式："
echo "     $PY -m python_agent.app"
echo ""
