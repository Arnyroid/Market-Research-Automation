# Quick Start

Get StockAI running in under 5 minutes.

---

## 1. Clone and set up

**macOS / Linux:**
```bash
git clone <repo-url>
cd Market-Research-Automation
bash setup.sh
```

**Windows:**
```bat
git clone <repo-url>
cd Market-Research-Automation
setup.bat
```

The setup script creates `.venv/`, installs all Python and Node dependencies, and copies `.env.example` to `.env`.

---

## 2. Add your API key

Open `.env` and set:
```
GEMINI_API_KEY=your-key-here
```

Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — no billing required.

For push notifications, also set:
```
NTFY_TOPIC=my-private-topic-name
```

---

## 3. Start

**macOS / Linux — two terminals:**
```bash
# Terminal 1
source .venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

**Windows:**
```bat
start.bat
```

---

## 4. Open the app

- **Frontend:** http://localhost:5173
- **API docs:** http://localhost:8000/docs

---

## First steps

1. **Watchlist** — search for any NSE symbol (e.g. `RELIANCE`) and click Add
2. **Portfolio** → Add Transaction — enter a BUY trade; P&L updates after the next price poll
3. **Alerts** — set a price-above or price-below threshold; the alert fires immediately if the condition is already met
4. **Stock Detail** — click any symbol in Watchlist or Portfolio to see the chart, AI analysis, and fundamentals
5. **Industry** — browse sectors and trigger the AI Sector Pulse

---

## What runs in the background

| Job | Schedule | What it does |
|---|---|---|
| Price poller | Every 5 min (9:15–15:30 IST Mon–Fri) | Fetches LTP for all watchlist symbols; evaluates alerts |
| Agent runner | 08:00 IST daily | Runs Gemini analysis for all watchlist symbols |
| Indicator calculator | 16:00 IST daily | Refreshes RSI, SMA, EMA after market close |
| Feedback evaluator | 17:00 IST daily | Scores previous AI recommendations against actual price moves |

All jobs are IST-aware (pytz `Asia/Kolkata`). Nothing runs outside market hours.

---

## Detailed guides

| Topic | Guide |
|---|---|
| Windows setup | [docs/WINDOWS_SETUP.md](WINDOWS_SETUP.md) |
| Full setup | [docs/SETUP_GUIDE.md](SETUP_GUIDE.md) |
| Architecture | [docs/ARCHITECTURE.md](ARCHITECTURE.md) |
| Alerts | [docs/ALERT_SYSTEM_GUIDE.md](ALERT_SYSTEM_GUIDE.md) |
| Portfolio & P&L | [docs/PORTFOLIO_USAGE_GUIDE.md](PORTFOLIO_USAGE_GUIDE.md) |
| Corporate actions | [docs/CORPORATE_ACTIONS_GUIDE.md](CORPORATE_ACTIONS_GUIDE.md) |
