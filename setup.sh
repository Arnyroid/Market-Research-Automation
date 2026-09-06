#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  StockAI — macOS / Linux setup script
#  Run once:       bash setup.sh
#  Then to start:  source .venv/bin/activate
#                  cd backend && uvicorn app.main:app --reload --port 8000
#                  cd frontend && npm run dev
# ─────────────────────────────────────────────────────────────────

set -e  # exit on any error

echo ""
echo "[1/4] Python virtual environment..."

# Locate a Python 3.10+ interpreter
PY_CMD=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PY_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PY_CMD" ]; then
    echo "ERROR: No Python 3.10+ interpreter found."
    echo "       Install Python 3.13 from https://python.org and re-run."
    exit 1
fi
echo "     Using: $PY_CMD ($($PY_CMD --version))"

# Create venv at .venv if it doesn't already exist with 3.10+
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    echo "     Found existing $VENV_DIR — skipping creation"
else
    echo "     Creating $VENV_DIR ..."
    "$PY_CMD" -m venv "$VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

echo ""
echo "[2/4] Installing backend dependencies..."
pip install --upgrade pip -q
pip install -r backend/requirements.txt

echo ""
echo "[3/4] Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "[4/4] Copying .env.example to .env ..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "     .env created — open it and fill in NTFY_TOPIC and GEMINI_API_KEY"
else
    echo "     .env already exists — skipping"
fi

echo ""
echo "================================================================"
echo " Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Edit .env — set NTFY_TOPIC and GEMINI_API_KEY"
echo "   2. Start backend:"
echo "        source .venv/bin/activate"
echo "        cd backend"
echo "        uvicorn app.main:app --reload --port 8000"
echo "   3. Start frontend (new terminal):"
echo "        cd frontend && npm run dev"
echo ""
echo "   Frontend : http://localhost:5173"
echo "   API docs : http://localhost:8000/docs"
echo "================================================================"
