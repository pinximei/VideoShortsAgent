#!/bin/bash
# VideoShortsAgent install (macOS / Linux / Git-Bash on Windows)
# Aligned with install.bat: pip-based Python pick, auto FFmpeg when possible, continue if FFmpeg still missing.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}OK $1${NC}"; }
warn() { echo -e "  ${YELLOW}WARN $1${NC}"; }
fail() { echo -e "  ${RED}FAIL $1${NC}"; }

echo ""
echo "============================================================"
echo "  VideoShortsAgent install"
echo "============================================================"
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

is_windows=false
case "${OSTYPE:-}" in
    msys*|cygwin*|win32*) is_windows=true ;;
esac
UNAME_S="$(uname -s 2>/dev/null || true)"
case "$UNAME_S" in
    MINGW*|MSYS*|CYGWIN*|*Windows*) is_windows=true ;;
esac

# ─────────────────────────────────────────────────
# 1. Select Python (must have pip, same idea as install.bat)
# ─────────────────────────────────────────────────
echo "[1/5] Select Python (need pip)..."

PY=""
PY_ARGS=""

_pick_python() {
    if command -v python3 &>/dev/null && python3 -m pip --version &>/dev/null; then
        PY="python3"
        PY_ARGS=""
        return 0
    fi
    if command -v python &>/dev/null && python -m pip --version &>/dev/null; then
        PY="python"
        PY_ARGS=""
        return 0
    fi
    if $is_windows && command -v py &>/dev/null && py -3 -m pip --version &>/dev/null; then
        PY="py"
        PY_ARGS="-3"
        return 0
    fi
    return 1
}

if ! _pick_python; then
    fail "No Python with working pip found."
    if $is_windows; then
        echo "  On Windows (Git Bash): install Python 3.10+, enable PATH, or use py -3."
        echo "  Or run install.bat which can use winget for Python."
        echo "  Disable App execution aliases for python.exe / python3.exe if needed."
    elif [[ "$OSTYPE" == darwin* ]]; then
        echo "  Try: brew install python"
    else
        echo "  Try: sudo apt install python3 python3-pip   (Debian/Ubuntu)"
        echo "  Or:  sudo dnf install python3 python3-pip   (Fedora)"
    fi
    exit 1
fi

PY_VER=$($PY $PY_ARGS --version 2>&1)
ok "$PY_VER (using: $PY $PY_ARGS)"

# ─────────────────────────────────────────────────
# 2. FFmpeg (auto-install when possible; warn and continue if still missing)
# ─────────────────────────────────────────────────
echo "[2/5] Check FFmpeg..."

_try_install_ffmpeg_windows() {
    command -v winget &>/dev/null || return 1
    echo "  Trying: winget install Gyan.FFmpeg ..."
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements --silent || true
    # Common locations after winget / manual (Git Bash paths)
    local extra=""
    [ -x "/c/Program Files/ffmpeg/bin/ffmpeg.exe" ] && extra="/c/Program Files/ffmpeg/bin:$extra"
    [ -x "/c/ffmpeg/bin/ffmpeg.exe" ] && extra="/c/ffmpeg/bin:$extra"
    [ -n "${LOCALAPPDATA:-}" ] && [ -x "${LOCALAPPDATA}/Microsoft/WinGet/Links/ffmpeg.exe" ] && extra="${LOCALAPPDATA}/Microsoft/WinGet/Links:$extra"
    if [ -n "$extra" ]; then
        export PATH="$extra$PATH"
    fi
    return 0
}

_try_install_ffmpeg_linux() {
    if command -v apt-get &>/dev/null; then
        echo "  Trying: sudo apt-get install ffmpeg (may ask password)..."
        sudo apt-get update -qq && sudo apt-get install -y ffmpeg
        return $?
    fi
    if command -v dnf &>/dev/null; then
        echo "  Trying: sudo dnf install -y ffmpeg ..."
        sudo dnf install -y ffmpeg
        return $?
    fi
    if command -v yum &>/dev/null; then
        echo "  Trying: sudo yum install -y ffmpeg ..."
        sudo yum install -y ffmpeg
        return $?
    fi
    if command -v pacman &>/dev/null; then
        echo "  Trying: sudo pacman -Sy --noconfirm ffmpeg ..."
        sudo pacman -Sy --noconfirm ffmpeg
        return $?
    fi
    if command -v apk &>/dev/null; then
        echo "  Trying: sudo apk add ffmpeg ..."
        sudo apk add ffmpeg
        return $?
    fi
    return 1
}

if command -v ffmpeg &>/dev/null; then
    FF_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    ok "FFmpeg $FF_VER"
else
    if [[ "$OSTYPE" == darwin* ]]; then
        if command -v brew &>/dev/null; then
            echo "  Trying: brew install ffmpeg ..."
            brew install ffmpeg && ok "FFmpeg installed via brew" || warn "brew install ffmpeg failed"
        else
            warn "No brew; install Homebrew or ffmpeg manually."
        fi
    elif $is_windows; then
        _try_install_ffmpeg_windows || warn "winget not available or install failed"
    else
        _try_install_ffmpeg_linux || warn "Could not auto-install ffmpeg (no apt/dnf/yum/pacman/apk or sudo failed)"
    fi

    if command -v ffmpeg &>/dev/null; then
        FF_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
        ok "FFmpeg $FF_VER"
    else
        warn "ffmpeg still not in PATH. Video steps will fail until you install it."
        echo "  macOS: brew install ffmpeg"
        echo "  Linux: sudo apt install ffmpeg   or   sudo dnf install ffmpeg"
        echo "  Windows: winget install -e --id Gyan.FFmpeg"
    fi
fi

# ─────────────────────────────────────────────────
# 3. Python dependencies
# ─────────────────────────────────────────────────
echo "[3/5] pip install -r requirements.txt ..."
if ! $PY $PY_ARGS -m pip install --upgrade pip -q; then
    fail "pip upgrade failed"
    exit 1
fi
if ! $PY $PY_ARGS -m pip install -r requirements.txt; then
    fail "pip install failed. Try mirror, e.g.:"
    echo "  $PY $PY_ARGS -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt"
    exit 1
fi
ok "Python packages installed"

# ─────────────────────────────────────────────────
# 4. Node + Remotion (optional)
# ─────────────────────────────────────────────────
echo "[4/5] Node.js (Remotion, optional)..."
if command -v node &>/dev/null; then
    ok "Node.js $(node --version)"
    if [ -f "remotion_effects/package.json" ]; then
        echo "  npm install in remotion_effects ..."
        (cd remotion_effects && npm install --silent 2>/dev/null && ok "Remotion deps" ) || warn "Remotion npm failed; ASS fallback"
    fi
else
    warn "Node.js not found; skipping Remotion."
    echo "  Optional: https://nodejs.org/  or  brew install node"
fi

# ─────────────────────────────────────────────────
# 5. .env
# ─────────────────────────────────────────────────
echo "[5/5] Check .env ..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
        warn "Edit .env: DASHSCOPE_API_KEY and optional GROQ_API_KEY"
    else
        warn "No .env; create one with your API keys"
    fi
else
    ok ".env exists"
fi

echo ""
echo "============================================================"
echo "  Done."
echo "============================================================"
echo ""
echo "  Start:"
echo "    $PY $PY_ARGS -m python_agent.app"
echo "  Or:   ./start.sh"
echo ""
