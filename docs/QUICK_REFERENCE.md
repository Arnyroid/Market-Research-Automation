# Quick Reference — StockAI

## 🚀 Start the App

```bash
# 1 — Activate venv & start backend  (from repo root)
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

cd backend
uvicorn app.main:app --reload --port 8000

# 2 — Start frontend  (new terminal, from repo root)
cd frontend
npm run dev
```

- Frontend → http://localhost:5173  
- API docs → http://localhost:8000/docs  
- DB file  → `data/portfolio.db`

---

## ⚙️ Required `.env` Keys

```
# Notification (required for alerts to fire)
NOTIFY_CHANNELS=ntfy
NTFY_TOPIC=stck_alerts

# AI Insight (required for stock analysis)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=models/gemini-flash-latest
GEMINI_MODEL_FALLBACK=models/gemini-flash-lite-latest

# CORS (leave as-is for local dev)
CORS_ORIGINS=http://localhost:5173
```

---

## 📱 Pages & What They Do

| Page | URL | What you can do |
|------|-----|----------------|
| Watchlist | `/` | Add/remove NSE symbols, live LTP via WebSocket, sortable table, click row → Stock Detail |
| Portfolio | `/portfolio` | Log BUY/SELL trades, FIFO holdings with unrealized P&L, realized P&L on SELLs, AI portfolio review |
| Alerts | `/alerts` | Create price/% / portfolio-stop-loss alerts, repeating toggle, ntfy push notifications |
| Stock Detail | `/stock/:symbol` | 300-day chart with SMA-20/EMA-20/DMA-50/DMA-200 overlays, indicator tiles, Gemini AI insight |
| Risk Profile | `/risk` | Set time horizon, loss tolerance, experience level |

---

## 🔔 Alert Condition Types

| `condition_type` | Fires when… | Threshold unit |
|-----------------|-------------|----------------|
| `price_above` | LTP ≥ threshold | ₹ |
| `price_below` | LTP ≤ threshold | ₹ |
| `pct_change_up` | 1-day gain ≥ threshold | % |
| `pct_change_down` | 1-day drop ≥ threshold | % |
| `portfolio_pnl_below` | Unrealized P&L% ≤ threshold (e.g. `-10`) | % |

---

## 🔌 Key API Endpoints

### Watchlist
```
GET    /watchlist
POST   /watchlist              { symbol, exchange, company_name? }
DELETE /watchlist/{id}
GET    /watchlist/search?q=    symbol / company name search (NSE master)
```

### Prices
```
GET    /prices/{symbol}?exchange=NSE          live quote
GET    /prices/{symbol}/history?exchange=NSE&days=300
WS     /prices/ws/prices                      live price feed
```

### Trades & Portfolio
```
GET    /trades                                 all transactions
POST   /trades                                { trade_date, symbol, exchange, trade_type, quantity, price, brokerage? }
DELETE /trades/{id}
GET    /trades/portfolio                       aggregated holdings with P&L
POST   /trades/portfolio/analyse              Gemini portfolio review
```

### Alerts
```
GET    /alerts
POST   /alerts                                { symbol, exchange, condition_type, threshold, repeating?, notes? }
PUT    /alerts/{id}                           { active?, threshold?, repeating?, notes? }
DELETE /alerts/{id}
GET    /alerts/{id}/log                       trigger history
```

### Analysis
```
GET    /analysis/{symbol}?exchange=NSE        latest AI analysis
POST   /analysis/{symbol}/refresh?exchange=NSE  queue new analysis
```

---

## 📊 Background Jobs

| Job | Schedule | What it does |
|-----|----------|--------------|
| `price_poller` | Every 5 min, market hours (IST) | Fetches LTP via yfinance, upserts one row/day, checks alerts |
| `feedback_evaluator` | Daily 17:00 IST | Scores past AI recommendations (risk flag + BUY/HOLD/SELL accuracy) |

> **Alert checking runs inside `price_poller`** — no separate job needed.  
> **AI analysis is on-demand only** — triggered when you open Stock Detail or click "Refresh Insight".

---

## 🗄️ Database — `data/portfolio.db`

```bash
# Open with DB Browser for SQLite  https://sqlitebrowser.org/

# Or query from terminal
sqlite3 data/portfolio.db "SELECT symbol, total_quantity, unrealized_pnl_pct FROM portfolio;"
sqlite3 data/portfolio.db "SELECT * FROM alerts WHERE active=1;"
sqlite3 data/portfolio.db "SELECT * FROM agent_feedback ORDER BY evaluated_at DESC LIMIT 10;"
```

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| Prices never update | Add symbol to Watchlist; poller only fetches watchlist symbols |
| Alert not firing | Check `active=1` in DB; `portfolio_pnl_below` requires a portfolio row |
| AI insight stuck "Generating…" | Check `GEMINI_API_KEY` in `.env`; watch backend log for 503 errors |
| ntfy notification not received | Verify `NTFY_TOPIC` matches your phone subscription |
| `ModuleNotFoundError` | Run `pip install -r backend/requirements.txt` inside activated venv |
| WebSocket disconnects | Reconnects automatically after 5 s; yellow banner shows in Watchlist |
| DMA-50/200 shows `—` | Analysis must be regenerated after adding the symbol; needs 50/200 days of history |
| Realized P&L missing on old SELLs | Trigger a recalculation: delete + re-enter the SELL trade |

---

## 🔑 yfinance Ticker Conventions

| Exchange | Format | Example |
|----------|--------|---------|
| NSE | `{SYMBOL}.NS` | `RELIANCE.NS` |
| BSE | `{SYMBOL}.BO` | `RELIANCE.BO` |

> BSE `.BO` tickers often lack live price feeds. Prefer NSE symbols.

---

## ✅ Production Checklist

- [ ] `.env` created from `.env.example` with real keys
- [ ] `NTFY_TOPIC` subscribed on phone
- [ ] `GEMINI_API_KEY` set and valid
- [ ] Backend starts without errors (`uvicorn app.main:app`)
- [ ] Frontend builds (`npm run build`)
- [ ] At least 3 symbols added to Watchlist
- [ ] At least 1 alert created and confirmed firing
- [ ] At least 1 trade logged in Portfolio

---

**Version**: 2.0 · **Last Updated**: September 2026
