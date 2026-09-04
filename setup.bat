@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Stock Watchlist & AI Trading Assistant — Windows setup script
REM  Run once: setup.bat
REM  Then to start: start.bat
REM ─────────────────────────────────────────────────────────────────

echo.
echo [1/4] Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 (echo ERROR: python not found. Install from python.org && pause && exit /b 1)

echo.
echo [2/4] Installing backend dependencies...
call .venv\Scripts\activate.bat
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
