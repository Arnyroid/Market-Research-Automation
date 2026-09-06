# Implementation Summary — StockAI

**Status:** ✅ Production-ready personal-use app  
**Last Updated:** September 2026  
**Stack:** FastAPI + SQLite + React + Vite + Gemini AI + ntfy.sh

---

## What Was Built

### Backend (Python / FastAPI)

| Component | File(s) | Notes |
|-----------|---------|-------|
| App entry point | `backend/app/main.py` | Lifespan startup (NSE symbol preload), CORS, router registration |
| Config | `backend/app/core/config.py` | pydantic-settings v2, CSV list parsing via `@property` |
| Database | `backend/app/core/db.py` | SQLite, SQLAlchemy 2, `create_all` on startup |
| Models | `backend/app/models.py` | 9 ORM models (see schema below) |
| Watchlist router | `backend/app/routers/watchlist.py` | CRUD + NSE symbol search + company_name backfill |
| Prices router | `backend/app/routers/prices.py` | Live quote, OHLCV history (up to 400 days), WebSocket feed |
| Alerts router | `backend/app/routers/alerts.py` | 5 condition types, repeating flag, trigger log |
| Trades router | `backend/app/routers/trades.py` | BUY/SELL entry, FIFO P&L, realized P&L on SELLs, Gemini portfolio review |
| Analysis router | `backend/app/routers/analysis.py` | On-demand Gemini analysis + latest/history endpoints |
| Risk profile router | `backend/app/routers/risk_profile.py` | Single-row CRUD |
| Data fetch service | `backend/app/services/data_fetch.py` | yfinance quotes + OHLCV, NSE equity master CSV (2,570 symbols, cached), news |
| Indicators service | `backend/app/services/indicators.py` | RSI-14, SMA-20/50/200, EMA-20, volatility, % changes, signal_context |
| AI agent service | `backend/app/services/ai_agent.py` | Gemini Flash, fallback to Flash Lite, JSON fence stripping, structured output |
| Notifier service | `backend/app/services/notifier.py` | ntfy.sh (confirmed ✅), Telegram, email |
| Alert engine | `backend/app/services/alert_engine.py` | 5 condition types, repeating behaviour, portfolio P&L lookup |
| Price poller job | `backend/app/jobs/price_poller.py` | Every 5 min market hours, IST-aware, upsert by date, calls check_alerts() |
| Feedback evaluator | `backend/app/jobs/feedback_evaluator.py` | Daily 17:00 IST, scores `risk_flag` + `recommendation` accuracy |
| Scheduler | `backend/app/jobs/scheduler.py` | APScheduler, 2 active jobs |

### Frontend (React / Vite / TypeScript)

| File | What it does |
|------|-------------|
| `pages/Watchlist.tsx` | NSE symbol search, sortable table, WebSocket live prices, WifiOff banner, stale price clock icon |
| `pages/Portfolio.tsx` | Holdings (clickable → Stock Detail), FIFO P&L, realized P&L column, Add Transaction modal, AI portfolio review card |
| `pages/Alerts.tsx` | 5 condition types, pre-fill via `?symbol=`, trigger history, repeating toggle |
| `pages/StockDetail.tsx` | 300-day chart, 4 overlay toggles, 7 indicator tiles, quick-action buttons (Add Alert / Add Trade), Gemini AI insight panel |
| `pages/RiskProfile.tsx` | Risk preference form |
| `hooks/usePriceSocket.ts` | WebSocket with `{ prices, connected }`, `lastUpdated` per price, auto-reconnect |
| `hooks/useSortFilter.ts` | Generic sort + text-filter hook used across all tables |
| `api/watchlist.ts` | Watchlist CRUD + symbol search |
| `api/prices.ts` | Live quote + history |
| `api/alerts.ts` | Alerts CRUD + logs |
| `api/trades.ts` | Trade CRUD + `realized_pnl` |
| `api/analysis.ts` | Gemini analysis fetch + refresh |

### Database Tables

| Table | Key columns | Notes |
|-------|------------|-------|
| `watchlist` | symbol, exchange, company_name | NSE/BSE equity list |
| `price_history` | symbol, exchange, timestamp, OHLCV | One row per trading day (upsert) |
| `trades` | trade_type, quantity, price, realized_pnl | BUY/SELL; FIFO realized P&L on SELLs |
| `portfolio` | total_quantity, avg_buy_price, unrealized_pnl(_pct) | Rebuilt on every trade add/delete |
| `alerts` | condition_type, threshold, active, repeating | 5 condition types |
| `alert_log` | triggered_at, price_at_trigger, notified | History per alert |
| `risk_profile` | time_horizon, loss_tolerance, experience_level | Single row |
| `agent_analysis` | indicators_snapshot, structured_output, risk_flag | On-demand Gemini results |
| `agent_feedback` | was_flag_useful, was_rec_accurate | Auto-scored after 7 days |

---

## Feature Checklist

### Data
- ✅ Live LTP via yfinance (NSE `.NS` / BSE `.BO`)
- ✅ 300-day OHLCV history for charts and DMA-200
- ✅ NSE equity master (2,570 symbols, downloaded on startup, cached in memory)
- ✅ One price row per trading day — no duplicate intraday rows
- ✅ Market hours gate: IST-aware via `pytz`

### Alerts
- ✅ `price_above`, `price_below`
- ✅ `pct_change_up`, `pct_change_down` (1-day)
- ✅ `portfolio_pnl_below` — stop-loss on a holding's unrealized P&L%
- ✅ Repeating alerts (fire on every poll tick while condition holds)
- ✅ ntfy.sh push notifications (e2e confirmed ✅)
- ✅ Trigger history per alert

### Portfolio
- ✅ BUY/SELL trade entry with live price pre-fill
- ✅ FIFO cost basis calculation
- ✅ Unrealized P&L (live price × qty − invested)
- ✅ Realized P&L on SELL trades (written on every recalculation)
- ✅ Holdings table clickable → Stock Detail page
- ✅ Gemini AI portfolio review (BUY_MORE / HOLD / TRIM / EXIT per position)
- ✅ Add Transaction modal pre-fillable via `?addTrade=SYMBOL` URL param

### Stock Detail
- ✅ 300-day price chart (Recharts)
- ✅ SMA-20 (amber dashed), EMA-20 (violet dotted) overlays with toggle pills
- ✅ DMA-50 (orange solid), DMA-200 (red solid) overlays with toggle pills
- ✅ 7 indicator tiles: RSI-14, SMA-20, DMA-50, DMA-200, EMA-20, 5d%, volatility
- ✅ Golden/Death cross status on DMA-50 tile
- ✅ Gemini AI insight: auto-generates if stale (previous day), poll loop, 45 s timeout
- ✅ Recommendation badge (BUY/HOLD/SELL/AVOID) + rationale block
- ✅ Quick-action "Add Alert" and "Add Trade" buttons → pre-fill respective pages

### Watchlist
- ✅ NSE symbol search dropdown (company name primary, ticker subtitle)
- ✅ WebSocket live price feed with auto-reconnect
- ✅ `connected` indicator: green dot (live) / WifiOff (reconnecting) in footer
- ✅ Yellow banner when WebSocket drops
- ✅ Clock icon on LTP when price not updated > 10 minutes
- ✅ Sortable / filterable table

### AI & Feedback
- ✅ Gemini Flash with Flash Lite fallback (503 handling)
- ✅ Signal context: deterministic Python signals passed as structured text
- ✅ Feedback evaluator: scores `was_flag_useful` and `was_rec_accurate` after 7 days
- ✅ BUY accurate if +3%+, SELL/AVOID accurate if −3%+, HOLD accurate if ±5%

---

## Dependencies

### Backend (`backend/requirements.txt`)
```
fastapi, uvicorn[standard]    — web framework
sqlalchemy                    — ORM
pydantic-settings             — config (v2)
apscheduler                   — background jobs
yfinance                      — market data (replaces nsepython/bsedata)
google-genai                  — Gemini AI (replaces anthropic)
python-multipart              — FastAPI file uploads
httpx                         — ntfy / Telegram HTTP calls
pandas                        — indicator calculations
pytz                          — IST timezone
loguru                        — structured logging
```

### Frontend (`frontend/package.json`)
```
react 18, react-dom           — UI framework
react-router-dom 6            — routing
recharts 2                    — price charts
lucide-react                  — icons
tailwindcss 3                 — styling
vite 5                        — build tool
typescript                    — type safety
```

---

## Known Limitations

| Limitation | Detail |
|-----------|--------|
| BSE live prices | `.BO` tickers on yfinance often lack real-time feeds; use NSE symbols |
| Gemini 503 | Free tier overloads during peak hours; Flash Lite fallback handles most cases |
| DMA-200 tile | Requires ≥ 200 trading days of history; shows `—` for newer symbols |
| Realized P&L on old SELLs | Historical SELL trades logged before this feature won't have `realized_pnl` until re-entered |
| Single-user only | No auth; CORS locked to localhost in dev |
| SQLite | Suitable for personal use; migrate to PostgreSQL for multi-user |

---

## File Reference

```
backend/app/
├── main.py                    FastAPI lifespan, router registration, CORS
├── core/
│   ├── config.py              pydantic-settings v2 (CSV @property accessors)
│   └── db.py                  SQLite engine, SessionLocal, Base
├── models.py                  9 SQLAlchemy ORM models
├── routers/
│   ├── watchlist.py           CRUD + search + backfill
│   ├── prices.py              quote + history (400-day cap) + WebSocket
│   ├── alerts.py              CRUD + 5 condition types + log endpoint
│   ├── trades.py              CRUD + FIFO recalc + portfolio review
│   ├── analysis.py            Gemini on-demand + latest/history
│   └── risk_profile.py        single-row CRUD
├── services/
│   ├── data_fetch.py          yfinance, NSE CSV (2570 symbols), news
│   ├── indicators.py          RSI/SMA/EMA/vol + signal_context
│   ├── ai_agent.py            Gemini client, prompt builder, JSON parser
│   ├── alert_engine.py        5 condition evaluators, Portfolio lookup
│   └── notifier.py            ntfy / Telegram / email
└── jobs/
    ├── scheduler.py           APScheduler config
    ├── price_poller.py        every 5 min, IST-aware, upsert, check_alerts
    ├── feedback_evaluator.py  daily, was_flag_useful + was_rec_accurate
    └── agent_runner.py        kept but no longer scheduled (on-demand only)

frontend/src/
├── App.tsx                    routes: / /portfolio /alerts /stock/:s /risk
├── index.css                  Tailwind + .card .th .td .btn-primary utilities
├── pages/
│   ├── Watchlist.tsx
│   ├── Portfolio.tsx
│   ├── Alerts.tsx
│   ├── StockDetail.tsx
│   └── RiskProfile.tsx
├── hooks/
│   ├── usePriceSocket.ts      { prices, connected }, lastUpdated per price
│   └── useSortFilter.ts       generic sort + text filter
└── api/
    ├── client.ts              apiFetch wrapper, WS_URL
    ├── watchlist.ts
    ├── prices.ts
    ├── alerts.ts              includes portfolio_pnl_below condition type
    ├── trades.ts              includes realized_pnl field
    └── analysis.ts

docs/                          all documentation (this file + others)
data/portfolio.db              SQLite runtime database
.env                           secrets (gitignored — see .env.example)
```
