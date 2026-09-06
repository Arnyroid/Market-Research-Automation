# Windows Setup Guide

This guide covers everything specific to running StockAI on Windows 10 / 11.

---

## 1. Prerequisites

### Python
Install from **[python.org](https://www.python.org/downloads/)** — do **not** use the Microsoft Store version.

> **Why not Microsoft Store Python?**  
> The Store version runs in a sandboxed environment, lacks some stdlib modules (`_lzma`, `_sqlite3`), and the `py` launcher may not work correctly with virtualenvs.

During installation, check:
- ✅ **Add Python to PATH**
- ✅ **Install for all users** (recommended)

Verify in a new Command Prompt:
```bat
python --version
py --version
```

You need Python **3.10 or newer**. The project was developed on 3.10.16.

### Node.js
Install the **LTS** release from [nodejs.org](https://nodejs.org/en/download). The installer adds `node` and `npm` to PATH automatically.

Verify:
```bat
node --version
npm --version
```

### Git
Install from [git-scm.com](https://git-scm.com/download/win). Accept the defaults.

---

## 2. One-Click Setup

Open **Command Prompt** (or Windows Terminal) as a normal user (admin is not needed):

```bat
git clone <repo-url>
cd Market-Research-Automation
setup.bat
```

`setup.bat` will:
1. Detect `py` or `python`, verify it is 3.10+
2. Create `.venv\` in the repo root
3. Install all Python dependencies from `backend\requirements.txt`
4. Run `npm install` in `frontend\`
5. Copy `.env.example` → `.env`

If `setup.bat` fails see [Troubleshooting](#troubleshooting) below.

---

## 3. Configure `.env`

Open `.env` in Notepad (or any editor):

```
GEMINI_API_KEY=your-key-here
NTFY_TOPIC=your-private-topic-name
```

Minimum required:
- `GEMINI_API_KEY` — free at [aistudio.google.com](https://aistudio.google.com/app/apikey)
- `NTFY_TOPIC` — only needed if you want push alert notifications

---

## 4. Starting the App

### Option A — One-click (recommended)

```bat
start.bat
```

This opens two separate Command Prompt windows:
- **StockAI Backend** — uvicorn on port 8000
- **StockAI Frontend** — Vite dev server on port 5173

Open **http://localhost:5173** in your browser.

### Option B — Manual (two terminals)

**Terminal 1 — backend:**
```bat
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — frontend:**
```bat
cd frontend
npm run dev
```

> **Important:** `uvicorn` must be run from the **repo root**, not from inside `backend\`.  
> The correct module path is `backend.app.main:app`.

---

## 5. Validating the Build

To confirm the frontend compiles with zero errors:

```bat
cd frontend
node_modules\.bin\vite build
```

Expected output ends with `✓ built`.

---

## 6. Running as a Windows Service (auto-start on login)

Use **Windows Task Scheduler** to keep the backend running in the background.

### Step-by-step

1. Open **Task Scheduler** (search in Start Menu)
2. Click **Create Task** (not "Create Basic Task")
3. **General tab:**
   - Name: `StockAI Backend`
   - Run only when user is logged on
4. **Triggers tab** → New → Begin the task: **At log on**
5. **Actions tab** → New:
   - Program/script: `cmd.exe`
   - Add arguments:
     ```
     /k "C:\path\to\Market-Research-Automation\.venv\Scripts\activate && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
     ```
   - Start in: `C:\path\to\Market-Research-Automation`
6. **Conditions tab:** uncheck "Start only if the computer is on AC power" (for laptops)
7. Click OK

Repeat for the frontend if you want it auto-started:
- Arguments: `cmd.exe /k "cd frontend && npm run dev"`
- Start in: `C:\path\to\Market-Research-Automation\frontend`

---

## 7. Firewall

Windows Firewall may prompt when uvicorn first binds to `0.0.0.0`. Click **Allow** to permit local connections. You only need `Private networks` — uncheck `Public networks`.

---

## 8. Troubleshooting

### `lxml` installation fails

`lxml` ships with C extension binaries. If pip can't find a pre-built wheel, run:
```bat
pip install lxml --prefer-binary
```

If that still fails, install the Visual C++ Build Tools:
- Download from [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Select **Desktop development with C++** workload

### `ModuleNotFoundError: No module named '_lzma'`

This is the Microsoft Store Python issue. Install the python.org version instead and re-run `setup.bat`.

### `ModuleNotFoundError: No module named 'backend'`

You are running `uvicorn` from inside the `backend\` folder. Always run it from the **repo root**:
```bat
cd C:\path\to\Market-Research-Automation
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --port 8000
```

### `pip` installs but packages are not found when running

The wrong Python environment is active. Check:
```bat
where python
where uvicorn
```
Both should point to paths inside `.venv\Scripts\`. If not, run `.venv\Scripts\activate` first.

### `npm` not found

Node.js is not on PATH. Re-run the Node.js installer and choose "Add to PATH", or add `C:\Program Files\nodejs\` manually to your System Environment Variables.

### Port 8000 or 5173 already in use

Find and kill the process using the port:
```bat
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### `data\portfolio.db` locked

Another process (e.g. DB Browser for SQLite) has the file open. Close it, then restart the backend.

### Antivirus blocking yfinance / requests

Some antivirus software intercepts HTTPS connections. Add an exception for:
- `query1.finance.yahoo.com`
- `archives.nseindia.com`
- `screener.in`
- `ntfy.sh` (if using alerts)

---

## 9. Known Limitations on Windows

All core features work on Windows. There are no Unix-only dependencies in this codebase:
- No `uvloop` (Windows-incompatible async event loop)
- No `fork()`
- No Unix sockets or signals
- Paths use `pathlib.Path` throughout — forward and backward slashes both work

The only Windows-specific difference: `uvicorn` uses the `asyncio` ProactorEventLoop by default on Windows (Python 3.8+), which is fully compatible with FastAPI and SQLAlchemy.
