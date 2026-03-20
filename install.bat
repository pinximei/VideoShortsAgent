@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   VideoShortsAgent - Windows install (ASCII-safe)
echo ============================================================
echo.

cd /d "%~dp0"

echo [0/5] Selecting Python
set "PY=python"
set "PY_ARGS="
"%PY%" %PY_ARGS% -m pip --version >nul 2>&1
if errorlevel 1 (
    py -3 -m pip --version >nul 2>&1
    if not errorlevel 1 (
        set "PY=py"
        set "PY_ARGS=-3"
        echo   Using: py -3
    ) else (
        echo ERROR: python and py -3 both failed.
        echo Trying winget to install Python 3.12 - needs network, may ask UAC.
        call :try_winget_python
        if errorlevel 1 (
            echo.
            echo Manual fix:
            echo   1. winget install -e --id Python.Python.3.12
            echo   2. https://www.python.org/downloads/ - enable Add Python to PATH
            echo   3. Settings - Apps - App execution aliases: OFF python.exe and python3.exe
            pause
            exit /b 1
        )
    )
) else (
    echo   Using: python
)

rem --- Step 1: verify Python ---
echo [1/5] Check Python...
"%PY%" %PY_ARGS% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: selected Python does not run. Resolving from disk...
    call :resolve_python_exe
    if errorlevel 1 (
        echo Fix py -3 or reinstall Python, then run install.bat again.
        pause
        exit /b 1
    )
)
for /f "tokens=2 delims= " %%v in ('"%PY%" %PY_ARGS% --version 2^>^&1') do (
    echo   OK Python %%v
)

rem --- Step 2: FFmpeg (try winget if missing) ---
echo [2/5] Check FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo   ffmpeg not in PATH. Trying winget: Gyan.FFmpeg ...
    call :try_winget_ffmpeg
    ffmpeg -version >nul 2>&1
    if errorlevel 1 (
        echo   WARN: ffmpeg still not found. Pip will still run.
        echo   Open a NEW CMD window and run install.bat again ^(PATH refresh^)
        echo   Or: winget install -e --id Gyan.FFmpeg
        echo   Or: https://www.gyan.dev/ffmpeg/builds/
        echo.
    ) else (
        for /f "tokens=3 delims= " %%v in ('ffmpeg -version 2^>^&1 ^| findstr /B "ffmpeg version"') do (
            echo   OK FFmpeg %%v
        )
    )
) else (
    for /f "tokens=3 delims= " %%v in ('ffmpeg -version 2^>^&1 ^| findstr /B "ffmpeg version"') do (
        echo   OK FFmpeg %%v
    )
)

rem --- Step 3: pip dependencies ---
echo [3/5] pip install -r requirements.txt
"%PY%" %PY_ARGS% -m pip install --upgrade pip >nul 2>&1
"%PY%" %PY_ARGS% -m pip install -r requirements.txt
if errorlevel 1 (
    echo FAIL: pip install. Try verbose:
    echo   "%PY%" %PY_ARGS% -m pip install -r requirements.txt -v
    echo Or mirror:
    echo   "%PY%" %PY_ARGS% -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
    pause
    exit /b 1
)
echo   OK Python packages installed.

rem --- Step 4: Node (optional) ---
echo [4/5] Check Node.js - Remotion optional
node --version >nul 2>&1
if errorlevel 1 (
    echo   WARN: Node.js not found. Skipping Remotion. Subtitles use FFmpeg ASS.
    echo   Optional: https://nodejs.org/
) else (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do (
        echo   OK Node.js %%v
    )
    if exist "remotion_effects\package.json" (
        echo   npm install in remotion_effects
        pushd remotion_effects
        call npm install >nul 2>&1
        if errorlevel 1 (
            echo   WARN: Remotion npm install failed; ASS fallback.
        ) else (
            echo   OK Remotion deps.
        )
        popd
    )
)

rem --- Step 5: .env ---
echo [5/5] Check .env
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   Created .env from .env.example
        echo   Edit .env: set DASHSCOPE_API_KEY and optional GROQ_API_KEY
    ) else (
        echo   WARN: no .env - create one with your API keys
    )
) else (
    echo   OK .env exists
)

echo.
echo ============================================================
echo   Done.
echo ============================================================
echo.
echo   Edit .env for DASHSCOPE_API_KEY. Whisper model: see README.
echo   Start:
echo     "%PY%" %PY_ARGS% -m python_agent.app
echo   Or double-click start.bat
echo.
pause
exit /b 0

:try_winget_python
where winget >nul 2>&1
if errorlevel 1 exit /b 1
echo   winget install Python.Python.3.12
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
call :resolve_python_exe
if errorlevel 1 exit /b 1
echo   OK: Python found after winget.
exit /b 0

:resolve_python_exe
set "PY="
call :rp_one "%LocalAppData%\Programs\Python\Python313\python.exe"
if defined PY goto :rp_ok
call :rp_one "%LocalAppData%\Programs\Python\Python312\python.exe"
if defined PY goto :rp_ok
call :rp_one "%LocalAppData%\Programs\Python\Python311\python.exe"
if defined PY goto :rp_ok
call :rp_one "%LocalAppData%\Programs\Python\Python310\python.exe"
if defined PY goto :rp_ok
call :rp_one "%ProgramFiles%\Python312\python.exe"
if defined PY goto :rp_ok
call :rp_one "%ProgramFiles%\Python311\python.exe"
if defined PY goto :rp_ok
exit /b 1
:rp_ok
echo   Using: %PY%
exit /b 0

:rp_one
if not exist "%~1" exit /b 1
"%~1" -m pip --version >nul 2>&1
if errorlevel 1 exit /b 1
set "PY=%~1"
set "PY_ARGS="
exit /b 0

:try_winget_ffmpeg
where winget >nul 2>&1
if errorlevel 1 exit /b 1
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements --silent
call :refresh_path_from_os
call :prepend_ffmpeg_dirs
exit /b 0

:refresh_path_from_os
for /f "delims=" %%P in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine')+';'+[Environment]::GetEnvironmentVariable('Path','User')"') do set "PATH=%PATH%;%%P"
exit /b 0

:prepend_ffmpeg_dirs
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
if exist "%ProgramFiles%\ffmpeg\bin\ffmpeg.exe" set "PATH=%ProgramFiles%\ffmpeg\bin;%PATH%"
if exist "%ProgramFiles%\Gyan\FFmpeg\bin\ffmpeg.exe" set "PATH=%ProgramFiles%\Gyan\FFmpeg\bin;%PATH%"
if exist "C:\ffmpeg\bin\ffmpeg.exe" set "PATH=C:\ffmpeg\bin;%PATH%"
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*") do (
    for /f "delims=" %%F in ('dir /s /b "%%D\ffmpeg.exe" 2^>nul') do (
        set "PATH=%%~dpF;%PATH%"
        goto :ffmpeg_path_done
    )
)
:ffmpeg_path_done
exit /b 0
