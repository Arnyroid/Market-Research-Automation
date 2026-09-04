@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Start backend + frontend in two separate windows
REM ─────────────────────────────────────────────────────────────────

REM Activate venv
call .venv\Scripts\activate.bat 2>nul || (
    echo Virtual environment not found. Run setup.bat first.
    pause && exit /b 1
)

echo Starting backend on http://0.0.0.0:8000 ...
start "StockAI Backend" cmd /k "call .venv\Scripts\activate.bat && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

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
