@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Stock Watchlist & AI Trading Assistant — Windows setup script
REM  Run once: setup.bat
REM  Then to start: start.bat
REM ─────────────────────────────────────────────────────────────────

echo.
echo [1/4] Python virtual environment...

REM ── Locate a Python 3.10+ interpreter ────────────────────────────
REM   Strategy: ask whichever command is available to print its version,
REM   then parse major.minor from "Python X.Y.Z" output.
set PY_CMD=
set PY_VER=

REM Try the py launcher (ships with official Python installs on Windows)
py --version >nul 2>&1
if not errorlevel 1 (
    set PY_CMD=py
    for /f "tokens=2" %%V in ('py --version 2^>^&1') do set PY_VER=%%V
)

REM Fall back to bare "python" if py launcher is not available
if not defined PY_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set PY_CMD=python
        for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PY_VER=%%V
    )
)

if not defined PY_CMD (
    echo ERROR: No Python interpreter found.
    echo        Install Python 3.13 from https://python.org and re-run.
    pause && exit /b 1
)

REM ── Verify it is 3.10 or newer ────────────────────────────────────
for /f "tokens=1,2 delims=." %%A in ("%PY_VER%") do (
    set PY_MAJOR=%%A
    set PY_MINOR=%%B
)
if %PY_MAJOR% LSS 3 (
    echo ERROR: Python %PY_VER% is too old. Install Python 3.13+.
    pause && exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo ERROR: Python %PY_VER% is too old. Install Python 3.13+.
    pause && exit /b 1
)
echo      Using interpreter: %PY_CMD% ^(%PY_VER%^)

REM ── Check if an existing venv is already Python 3.10+ ─────────────
set VENV_DIR=
set REGEN=0

for %%d in (.venv venv) do (
    if not defined VENV_DIR (
        if exist %%d\Scripts\activate.bat (
            REM Read the pyvenv.cfg to check Python version
            findstr /i "version_info = 3.9" %%d\pyvenv.cfg >nul 2>&1
            if not errorlevel 1 (
                echo      Found %%d but it is Python 3.9 — will recreate with %PY_CMD%
                set VENV_DIR=%%d
                set REGEN=1
            ) else (
                echo      Found existing %%d ^(Python 3.10+^) — skipping creation
                set VENV_DIR=%%d
            )
        )
    )
)

REM ── Create or recreate venv ───────────────────────────────────────
if not defined VENV_DIR (
    echo      No existing venv found — creating .venv with %PY_CMD% ...
    set VENV_DIR=.venv
    set REGEN=1
)
if "%REGEN%"=="1" (
    if exist %VENV_DIR% (
        echo      Removing old venv at %VENV_DIR% ...
        rmdir /s /q %VENV_DIR%
    )
    %PY_CMD% -m venv %VENV_DIR%
    if errorlevel 1 (echo ERROR: failed to create venv && pause && exit /b 1)
    echo      Created %VENV_DIR% with %PY_CMD%
)

echo.
echo [2/4] Installing backend dependencies...
call %VENV_DIR%\Scripts\activate.bat
pip install -r backend\requirements.txt
if errorlevel 1 (echo ERROR: pip install failed && pause && exit /b 1)

echo.
echo [3/4] Installing frontend dependencies...
cd frontend
npm install
if errorlevel 1 (echo ERROR: npm not found. Install Node.js from nodejs.org && pause && exit /b 1)
cd ..

echo.
echo [4/4] Copying .env.example to .env ...
if not exist .env (
    copy .env.example .env
    echo      .env created — open it and fill in NTFY_TOPIC and CLAUDE_API_KEY
) else (
    echo      .env already exists — skipping
)

echo.
echo ================================================================
echo  Setup complete!
echo  Next step: edit .env, then run start.bat
echo ================================================================
pause
