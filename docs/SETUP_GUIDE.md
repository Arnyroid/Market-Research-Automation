# Setup Guide

Detailed cross-platform setup instructions for StockAI.

> **Windows users:** also read [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for Windows-specific gotchas.

---

## Prerequisites

| Requirement | Minimum version | How to check |
|---|---|---|
| Python | 3.10 | `python --version` or `py --version` |
| Node.js | 18 LTS | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

> **Windows:** Install Python from [python.org](https://python.org) — **not** the Microsoft Store. Check "Add Python to PATH" during installation.

---

## Step 1: Clone

```bash
git clone <repo-url>
cd Market-Research-Automation
```

---

## Step 2: Create a virtual environment and install Python deps

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Windows

```bat
py -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r backend\requirements.txt
```

If `lxml` fails to install on Windows:
```bat
pip install lxml --prefer-binary
```

---

## Step 3: Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Step 4: Configure `.env`

```bash
cp .env.example .env      # macOS / Linux
copy .env.example .env    # Windows
```

Open `.env` in any editor. Required keys:

| Key | Description |
|---|---|
| `GEMINI_API_KEY` | Free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `NTFY_TOPIC` | (Optional) Push notification topic — see ntfy setup below |

Everything else has sensible defaults. Full reference is in `.env.example`.

### ntfy push notifications (recommended)

1. Install the ntfy app on your phone: [ntfy.sh](https://ntfy.sh)
2. Subscribe to a **unique, private** topic name (e.g. `stockai-xyz123abc`) — anyone who knows the name can message you, so make it unguessable
3. Set `NTFY_TOPIC=your-topic-name` in `.env`

Alerts will appear as push notifications on your phone with no signup, no account, no API key.

---

## Step 5: Start the backend

Run **from the repo root** (not from inside `backend/`):

```bash
# macOS / Linux
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000

# Windows
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The first start:
- Creates all SQLite tables in `data/portfolio.db`
- Downloads the NSE equity master CSV (~20k symbols) in the background
- Starts APScheduler (price poller, AI runner, indicator calculator)

Verify: open http://localhost:8000/health — should return `{"status":"ok"}`.

---

## Step 6: Start the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## One-click alternatives

### macOS / Linux

```bash
bash setup.sh     # setup only (run once)
```

Then start manually (two terminals) as in Steps 5–6.

### Windows

```bat
setup.bat         # setup only (run once)
start.bat         # starts both backend + frontend in separate windows
```

---

## Verifying the frontend build

After any frontend change, confirm it compiles with zero errors:

```bash
# macOS / Linux
cd frontend && ./node_modules/.bin/vite build

# Windows
cd frontend && node_modules\.bin\vite build
```

Expected: `✓ built` with no TypeScript or build errors.

---

## Environment variables reference

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | (empty) | Google Gemini API key |
| `GEMINI_MODEL` | `models/gemini-flash-latest` | Primary Gemini model |
| `GEMINI_MODEL_FALLBACK` | `models/gemini-flash-lite-latest` | Fallback on 503 |
| `PRICE_POLL_INTERVAL_MINUTES` | `5` | Minutes between price polls during market hours |
| `NOTIFY_CHANNELS` | `ntfy` | Comma-separated: `ntfy`, `telegram`, `email`, `whatsapp` |
| `NTFY_TOPIC` | (empty) | ntfy topic name |
| `NTFY_SERVER` | `https://ntfy.sh` | ntfy server URL |
| `NTFY_PRIORITY` | `high` | Alert priority: `min`, `low`, `default`, `high`, `urgent` |
| `TELEGRAM_BOT_TOKEN` | (empty) | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | (empty) | Your Telegram chat ID |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port (587 = STARTTLS) |
| `SMTP_USER` | (empty) | SMTP username / email |
| `SMTP_PASSWORD` | (empty) | SMTP password or app password |
| `SMTP_TO` | (empty) | Recipient email address |
| `TWILIO_ACCOUNT_SID` | (empty) | Twilio account SID (WhatsApp) |
| `TWILIO_AUTH_TOKEN` | (empty) | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | (empty) | `whatsapp:+14155238886` (sandbox) |
| `TWILIO_WHATSAPP_TO` | (empty) | `whatsapp:+91XXXXXXXXXX` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |
| `AGENT_FEEDBACK_DAYS` | `7` | Days after analysis to evaluate outcome |

---

## Database

SQLite database at `data/portfolio.db`. Auto-created on first backend start. No migration tool is needed unless you need to add columns to an existing database — in that case, use the SQLite table-rename pattern:

```sql
-- Example: add a column to an existing table
BEGIN;
ALTER TABLE my_table RENAME TO my_table_old;
CREATE TABLE my_table (...);
INSERT INTO my_table SELECT ..., NULL AS new_col FROM my_table_old;
DROP TABLE my_table_old;
COMMIT;
```

---

## Logs

Loguru writes rotating logs to `logs/`. Level is controlled by `LOG_LEVEL` in `.env` (default: `INFO`).

```bash
tail -f logs/*.log
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'backend'` | Run `uvicorn backend.app.main:app …` from the **repo root**, not from `backend/` |
| `Address already in use :8000` | Kill the existing process: `lsof -ti:8000 \| xargs kill` (Mac/Linux) or `netstat -ano \| findstr :8000` then `taskkill /PID <n> /F` (Windows) |
| `CORS error` in browser | Add `http://localhost:5173` to `CORS_ORIGINS` in `.env`; restart backend |
| `No prices` loading | Check internet; try `python -c "import yfinance as yf; print(yf.Ticker('RELIANCE.NS').fast_info)"` |
| `NSE search empty` | NSE CSV download failed at startup (rate limited or no internet); restart backend to retry |
| `AI returns "no API key"` | Set `GEMINI_API_KEY` in `.env` and restart backend |
| `lxml` fails on Windows | `pip install lxml --prefer-binary` |
