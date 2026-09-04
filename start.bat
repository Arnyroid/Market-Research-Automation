@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Start backend + frontend in two separate windows
REM ─────────────────────────────────────────────────────────────────

REM Detect venv folder (.venv preferred, venv legacy fallback)
if exist .venv\Scripts\activate.bat (
    set VENV_DIR=.venv
) else if exist venv\Scripts\activate.bat (
    set VENV_DIR=venv
) else (
    echo ERROR: No virtual environment found. Run setup.bat first.
    pause && exit /b 1
)
call %VENV_DIR%\Scripts\activate.bat

echo Starting backend on http://0.0.0.0:8000 ...
start "StockAI Backend" cmd /k "call %VENV_DIR%\Scripts\activate.bat && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting frontend on http://localhost:5173 ...
start "StockAI Frontend" cmd /k "cd frontend && npm run dev -- --host 0.0.0.0"

echo.
echo ================================================================
echo  Backend  : http://localhost:8000
echo  API Docs : http://localhost:8000/docs
echo  Frontend : http://localhost:5173
echo ================================================================
echo.
echo Both windows opened. Close them to stop the servers.
pause
