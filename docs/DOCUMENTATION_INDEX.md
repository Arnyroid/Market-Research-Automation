# Documentation Index — StockAI

## Start Here

| I want to… | Read |
|-----------|------|
| Start the app right now | **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — startup commands, API cheatsheet, troubleshooting |
| Understand the full system | **[ARCHITECTURE.md](ARCHITECTURE.md)** — data flows, schema, design decisions |
| See everything that was built | **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** — feature checklist, file reference, dependencies |
| Set up from scratch | **[SETUP_GUIDE.md](SETUP_GUIDE.md)** — step-by-step environment setup |

---

## Project Structure

```
Market-Research-Automation/
├── .env                        ← secrets (gitignored — copy from .env.example)
├── .env.example                ← config template with all supported keys
├── setup.bat / setup.sh        ← one-click setup (Windows / macOS)
├── start.bat                   ← one-click start (Windows)
│
├── backend/                    ← Python FastAPI backend
│   ├── app/
│   │   ├── main.py             ← FastAPI lifespan, router registration, CORS
│   │   ├── core/               ← config.py (pydantic-settings v2), db.py
│   │   ├── models.py           ← 9 SQLAlchemy ORM models
│   │   ├── routers/            ← watchlist, prices, alerts, trades, analysis, risk_profile
│   │   ├── services/           ← data_fetch, indicators, ai_agent, alert_engine, notifier
│   │   └── jobs/               ← price_poller, feedback_evaluator, scheduler
│   └── requirements.txt        ← Python deps (yfinance, google-genai, fastapi, …)
│
├── frontend/                   ← React + Vite + TypeScript frontend
│   └── src/
│       ├── pages/              ← Watchlist, Portfolio, Alerts, StockDetail, RiskProfile
│       ├── hooks/              ← usePriceSocket, useSortFilter
│       ├── api/                ← client, watchlist, prices, alerts, trades, analysis
│       ├── App.tsx             ← router
│       └── index.css           ← Tailwind + utility classes
│
├── data/
│   └── portfolio.db            ← SQLite runtime database
│
├── docs/                       ← all documentation (you are here)
│   ├── DOCUMENTATION_INDEX.md
│   ├── QUICK_REFERENCE.md
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── SETUP_GUIDE.md
│
└── src/                        ← legacy standalone Python module
    └── config.py
```

---

## Feature Map

### Pages
| Page | Route | Key Features |
|------|-------|-------------|
| Watchlist | `/` | Add NSE/BSE symbols, live WebSocket prices, WifiOff / stale-price indicators, sortable table |
| Portfolio | `/portfolio` | BUY/SELL trades, FIFO P&L, realized P&L on SELLs, clickable holdings → Stock Detail, AI review |
| Alerts | `/alerts` | 5 condition types incl. portfolio stop-loss, repeating alerts, ntfy push, trigger history |
| Stock Detail | `/stock/:symbol` | 300-day chart, SMA-20/EMA-20/DMA-50/DMA-200 toggles, indicator tiles, Gemini AI insight |
| Risk Profile | `/risk` | Time horizon, loss tolerance, experience level |

### Alert Conditions
| Type | Description |
|------|-------------|
| `price_above` | LTP crosses above threshold (₹) |
| `price_below` | LTP crosses below threshold (₹) |
| `pct_change_up` | 1-day gain exceeds threshold (%) |
| `pct_change_down` | 1-day drop exceeds threshold (%) |
| `portfolio_pnl_below` | Holding unrealized P&L% drops below threshold (%) — portfolio stop-loss |

### Background Jobs
| Job | Schedule | Purpose |
|-----|----------|---------|
| `price_poller` | Every 5 min, market hours (IST) | Fetch LTP, upsert price_history, evaluate alerts |
| `feedback_evaluator` | Daily 17:00 IST | Score past AI recommendations: `was_flag_useful` + `was_rec_accurate` |

---

## Common Questions

**Q: Prices aren't updating**  
Add the symbol to your Watchlist — the poller only fetches symbols that are in `watchlist` table. Wait up to 5 minutes during market hours (09:15–15:30 IST).

**Q: AI insight is stuck on "Generating…"**  
Check `GEMINI_API_KEY` in `.env`. Watch the backend log — a `503` means Gemini is overloaded; it auto-retries with the Flash Lite model.

**Q: ntfy notification didn't arrive**  
Verify `NTFY_TOPIC` in `.env` matches the topic you subscribed to on your phone. ntfy e2e was confirmed working at topic `stck_alerts`.

**Q: DMA-50 / DMA-200 shows `—`**  
These require 50 / 200 trading days of price history. Regenerate the analysis after the symbol has enough history.

**Q: Realized P&L is missing on old SELL trades**  
The `realized_pnl` column was added later. Delete and re-enter those SELL trades to trigger the FIFO recalculation.

**Q: BSE prices aren't live**  
Use NSE symbols (e.g. `RELIANCE`, `HDFCBANK`). BSE `.BO` tickers on yfinance often lack real-time feeds.

**Q: What API docs are available?**  
Interactive Swagger UI at http://localhost:8000/docs while the backend is running.

---

## Version

**Version**: 2.0  
**Last Updated**: September 2026  
**Status**: ✅ Production-ready (personal use)
