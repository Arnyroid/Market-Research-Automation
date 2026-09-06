# StockAI — Personal Indian Equities Tracker

A full-stack web application for tracking NSE and BSE equities with real-time prices, AI-powered analysis, portfolio management, and configurable push alerts.

**Stack:** FastAPI 0.115 · SQLAlchemy 2 · SQLite · React 18 · Vite 5 · TypeScript · Tailwind CSS 3 · Recharts 2 · Google Gemini (free tier)

---

## Features

| Area | What it does |
|---|---|
| **Watchlist** | Track any NSE/BSE symbol · live LTP, day range bar, volume · staleness badge · NSE\|BSE toggle · Bell quick-alert |
| **Portfolio** | FIFO cost basis · unrealized & realized P&L · colour-coded holdings · cap-tier analytics (Large/Mid/Small) · fuel gauge · CSV export |
| **Alerts** | Price-above/below, % change triggers · repeating option · ntfy / Telegram / Email / WhatsApp delivery · immediate evaluation on creation |
| **AI Analysis** | Per-stock Gemini analysis: RSI, SMA/EMA, fundamentals, news context · 24h cache · in-flight dedup |
| **AI Portfolio Review** | Full portfolio health check: BUY\_MORE / HOLD / TRIM / EXIT per holding · rebalance & risk notes |
| **Industry Dashboard** | Sector overview scraped from screener.in · AI Sector Pulse (BUY/HOLD/AVOID per L1 sector, 24h cache) |
| **Risk Profile** | Time horizon, loss tolerance, experience level — fed into AI prompts |
| **Corporate Actions** | Record dividends, bonuses, splits, rights issues; portfolio warns when any exist |

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.10 – 3.13** | 3.10.16 used in development; `python3` or `py` launcher |
| Node.js | **18 LTS or 20 LTS** | Needed for the React frontend |
| Git | any | |
| Internet | — | yfinance + NSE CSV + screener.in scraping |

> **Windows users:** see [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md) for a step-by-step guide, known gotchas, and the Windows Task Scheduler service setup.

---

## Quick Setup

### macOS / Linux

```bash
git clone <repo-url>
cd Market-Research-Automation
bash setup.sh          # creates .venv, installs deps, copies .env.example → .env
```

### Windows

```bat
git clone <repo-url>
cd Market-Research-Automation
setup.bat              # creates .venv, installs deps, copies .env.example → .env
```

---

## Configuration

Edit `.env` (created from `.env.example` by the setup script):

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | **Yes** (for AI) | Free at [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `NTFY_TOPIC` | For alerts | Unique topic name from the [ntfy app](https://ntfy.sh) |
| `GEMINI_MODEL` | No | Default: `models/gemini-flash-latest` |
| `GEMINI_MODEL_FALLBACK` | No | Default: `models/gemini-flash-lite-latest` |
| `PRICE_POLL_INTERVAL_MINUTES` | No | Default: `5` (during market hours 9:15–15:30 IST) |
| `NOTIFY_CHANNELS` | No | Default: `ntfy` — can be `ntfy,telegram,email,whatsapp` |
| `CORS_ORIGINS` | No | Default: `http://localhost:5173,http://localhost:3000` |

For Telegram, Email (SMTP), and WhatsApp (Twilio) configuration see the comments in `.env.example`.

---

## Starting the App

### macOS / Linux

```bash
# Terminal 1 — backend
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

### Windows

```bat
start.bat       ← opens both backend and frontend in separate windows
```

Or manually:

```bat
REM Terminal 1 — backend
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

REM Terminal 2 — frontend
cd frontend
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |

---

## Project Structure

```
Market-Research-Automation/
│
├── README.md
├── .env.example            ← copy to .env, fill in API keys
├── setup.sh / setup.bat    ← one-click setup
├── start.bat               ← Windows one-click start
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py         ← FastAPI entry point + lifespan (DB init, scheduler)
│       ├── models.py       ← SQLAlchemy ORM models
│       ├── core/
│       │   ├── config.py   ← pydantic-settings (reads .env)
│       │   └── db.py       ← SQLite engine + SessionLocal
│       ├── routers/        ← API endpoints
│       │   ├── watchlist.py
│       │   ├── prices.py
│       │   ├── trades.py         ← portfolio + CSV export
│       │   ├── alerts.py
│       │   ├── analysis.py
│       │   ├── market.py         ← industry overview + sector analysis
│       │   ├── risk_profile.py
│       │   └── corporate_actions.py
│       ├── services/
│       │   ├── data_fetch.py     ← yfinance quotes, NSE master CSV, screener.in scraping
│       │   ├── ai_agent.py       ← Gemini per-stock analysis + sector analysis
│       │   ├── alert_engine.py   ← alert evaluation logic
│       │   ├── notifier.py       ← ntfy / Telegram / Email / WhatsApp dispatch
│       │   └── indicators.py     ← RSI, SMA, EMA, volatility calculations
│       └── jobs/
│           ├── scheduler.py      ← APScheduler setup (IST timezone)
│           ├── price_poller.py   ← runs every N min during market hours
│           ├── agent_runner.py   ← daily 08:00 IST bulk AI analysis
│           └── indicator_calc.py ← end-of-day 16:00 IST indicator refresh
│
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.tsx               ← sidebar nav + routes + market status dot
│       ├── api/                  ← typed API client modules
│       │   ├── client.ts         ← ApiError class, apiFetch helper
│       │   ├── watchlist.ts
│       │   ├── trades.ts
│       │   ├── prices.ts
│       │   ├── analysis.ts
│       │   ├── fundamentals.ts
│       │   ├── market.ts
│       │   └── corporateActions.ts
│       ├── hooks/
│       │   └── useSortFilter.ts  ← generic sort + filter hook with numericKeys
│       └── pages/
│           ├── Watchlist.tsx
│           ├── Portfolio.tsx
│           ├── Alerts.tsx
│           ├── StockDetail.tsx
│           ├── Industry.tsx
│           └── RiskProfile.tsx
│
├── data/
│   └── portfolio.db        ← SQLite database (auto-created on first run)
├── logs/                   ← loguru rotating logs
└── docs/                   ← detailed guides
```

---

## Database

SQLite at `data/portfolio.db`. Tables auto-created on first backend start — no migrations needed for a fresh install.

| Table | Description |
|---|---|
| `watchlist` | Symbols being tracked |
| `price_history` | Intraday OHLCV written by the price poller (one row per symbol per trading day, upserted) |
| `trades` | All BUY/SELL transactions |
| `portfolio` | Aggregated holdings — unique on `(symbol, exchange)` |
| `alerts` | Active alert rules |
| `alert_log` | Every time an alert fired |
| `risk_profile` | Single-row user risk preferences |
| `agent_analysis` | LLM analysis results per symbol |
| `agent_feedback` | Outcome data written N days post-analysis |
| `corporate_actions` | Dividends, bonuses, splits, rights |

---

## API Overview

All endpoints are documented interactively at **http://localhost:8000/docs**.

| Prefix | Notable endpoints |
|---|---|
| `GET /watchlist` | List watchlist; `POST` to add; `DELETE /{id}` to remove |
| `GET /prices/{symbol}` | Live quote; `GET /prices/{symbol}/history` for OHLCV |
| `GET /trades/portfolio` | Current holdings with P&L and cap tier |
| `GET /trades/export` | Download all trades as CSV (`?symbol=` to filter) |
| `POST /trades/portfolio/analyse` | Trigger AI portfolio review |
| `POST /trades/import` | Bulk import trades from CSV/XLSX |
| `GET /analysis/{symbol}/latest` | Latest AI analysis |
| `POST /analysis/{symbol}/run` | Trigger new AI analysis |
| `GET /analysis/{symbol}/fundamentals` | Scraped fundamentals (24h cached) |
| `GET /market/overview` | Industry overview table |
| `GET /market/sector-analysis` | AI Sector Pulse (24h cached) |
| `GET /alerts` | List alerts; `POST` to create; `DELETE /{id}` to remove |
| `GET /risk-profile` | User risk profile; `PUT` to update |
| `GET /health` | `{"status": "ok"}` |

---

## Validating the Frontend Build

```bash
cd frontend && ./node_modules/.bin/vite build
# Must produce: ✓ built — zero errors
```

On Windows:
```bat
cd frontend && node_modules\.bin\vite build
```

---

## Notifications Setup

### ntfy (recommended — zero signup)
1. Install the ntfy app: [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) · [iOS](https://apps.apple.com/app/ntfy/id1625396347)
2. Subscribe to a **private** topic name (treat it like a password)
3. Set `NTFY_TOPIC=your-topic-name` in `.env`

### Telegram
1. Message [@BotFather](https://t.me/botfather) → `/newbot` → copy token
2. Message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your chat ID
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
4. Add `telegram` to `NOTIFY_CHANNELS=ntfy,telegram`

### Email (Gmail / Outlook)
Gmail: Account → Security → 2-Step Verification → App Passwords → generate one.  
Set `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TO` in `.env`, add `email` to `NOTIFY_CHANNELS`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| **Backend won't start** | Activate venv first: `source .venv/bin/activate` (Mac/Linux) or `.venv\Scripts\activate` (Windows) |
| **`ModuleNotFoundError: backend`** | Run uvicorn from the **repo root**, not from inside `backend/`: `uvicorn backend.app.main:app …` |
| **Frontend can't reach backend** | Check `CORS_ORIGINS` in `.env` includes `http://localhost:5173`; ensure backend is running on port 8000 |
| **No prices loading** | yfinance needs internet; check firewall; try `python -c "import yfinance; print(yfinance.__version__)"` |
| **NSE symbol search empty** | NSE CSV download failed at startup — check logs; retry by restarting the backend |
| **AI features return "no API key"** | Set `GEMINI_API_KEY` in `.env` and restart the backend |
| **Alerts not firing** | Price poller only runs 9:15–15:30 IST Mon–Fri; alert is evaluated immediately on creation so it fires if condition is already met |
| **`lxml` install fails on Windows** | Use a pre-built wheel: `pip install lxml --prefer-binary` |
| **`ModuleNotFoundError: No module named '_lzma'`** | Windows Python from Microsoft Store lacks some stdlib modules; use the official python.org installer |

---

## Documentation

| File | Contents |
|---|---|
| [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md) | Step-by-step Windows guide, gotchas, Task Scheduler service setup |
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | Detailed cross-platform setup |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, data flow, component map |
| [docs/QUICK_START.md](docs/QUICK_START.md) | Fastest path from clone to running |
| [docs/ALERT_SYSTEM_GUIDE.md](docs/ALERT_SYSTEM_GUIDE.md) | Alert conditions, notification channels, repeating alerts |
| [docs/PORTFOLIO_USAGE_GUIDE.md](docs/PORTFOLIO_USAGE_GUIDE.md) | Portfolio tracking, FIFO P&L, CSV export |
| [docs/CORPORATE_ACTIONS_GUIDE.md](docs/CORPORATE_ACTIONS_GUIDE.md) | Recording dividends, bonuses, splits |

---

## Disclaimer

This tool is for personal research and educational purposes only. It is not financial advice. Always verify data accuracy and consult a SEBI-registered advisor before making investment decisions.
