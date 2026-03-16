#!/bin/bash
# ══════════════════════════════════════════════════
#   🎬 VideoShortsAgent 启动脚本 (macOS / Linux)
# ══════════════════════════════════════════════════

echo ""
echo "=========================================="
echo "  VideoShortsAgent Launcher"
echo "=========================================="

cd "$(dirname "$0")"

# 检测 Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "❌ 未检测到 Python，请先运行 install.sh"
    exit 1
fi

# 杀掉占用 7860 端口的旧进程
echo "[1/2] 清理旧进程..."
if command -v lsof &>/dev/null; then
    OLD_PID=$(lsof -ti:7860 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        echo "  Killing PID $OLD_PID"
        kill -9 $OLD_PID 2>/dev/null
        sleep 1
    fi
fi

# 检查依赖
echo "[2/2] 检查依赖..."
$PY -c "import edge_tts" 2>/dev/null || $PY -m pip install edge-tts -q
$PY -c "import groq" 2>/dev/null || $PY -m pip install groq -q

echo ""
echo "🚀 启动 Gradio..."
echo ""
$PY -u -m python_agent.app
