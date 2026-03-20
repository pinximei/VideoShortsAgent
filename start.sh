#!/bin/bash
# VideoShortsAgent launcher (macOS / Linux / Git-Bash on Windows)
# Aligned with start.bat: PYTHONPATH, UTF-8 I/O, pip-based Python, py -3 on Windows embed issues.

echo ""
echo "=========================================="
echo "  VideoShortsAgent Launcher"
echo "=========================================="

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
# Help some Linux terminals use UTF-8 for prints with symbols
export LANG="${LANG:-en_US.UTF-8}"

is_windows=false
case "${OSTYPE:-}" in
    msys*|cygwin*|win32*) is_windows=true ;;
esac
UNAME_S="$(uname -s 2>/dev/null || true)"
case "$UNAME_S" in
    MINGW*|MSYS*|CYGWIN*|*Windows*) is_windows=true ;;
esac

# ── Free port 7860 ──
echo "[1/3] Free port 7860 if in use..."
if command -v lsof &>/dev/null; then
    OLD_PID=$(lsof -ti:7860 2>/dev/null || true)
    if [ -n "$OLD_PID" ]; then
        echo "  kill PID $OLD_PID"
        kill -9 $OLD_PID 2>/dev/null || true
        sleep 1
    fi
elif command -v fuser &>/dev/null; then
    fuser -k 7860/tcp 2>/dev/null || true
    sleep 1
fi

# ── Select Python (need pip) ──
echo "[0/3] Select Python (need pip)..."
PY=""
PY_ARGS=""

if command -v python3 &>/dev/null && python3 -m pip --version &>/dev/null; then
    PY="python3"
    PY_ARGS=""
    echo "  Using: python3"
elif command -v python &>/dev/null && python -m pip --version &>/dev/null; then
    PY="python"
    PY_ARGS=""
    echo "  Using: python"
elif $is_windows && command -v py &>/dev/null && py -3 -m pip --version &>/dev/null; then
    PY="py"
    PY_ARGS="-3"
    echo "  Using: py -3"
else
    echo "ERROR: No Python with working pip. Run ./install.sh or install.bat first."
    exit 1
fi

# ── Dependencies ──
echo "[2/3] Check edge-tts / groq..."
$PY $PY_ARGS -c "import edge_tts" 2>/dev/null || $PY $PY_ARGS -m pip install edge-tts -q
$PY $PY_ARGS -c "import groq" 2>/dev/null || $PY $PY_ARGS -m pip install groq -q

echo "[3/3] Start Gradio..."
echo ""
exec $PY $PY_ARGS -u -m python_agent.app
