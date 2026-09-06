# Architecture

## Overview

StockAI is a single-host full-stack web application. The backend is a Python FastAPI server; the frontend is a React SPA. They communicate over a local HTTP REST API. A SQLite database stores all state.

```
Browser (React + Vite)
        │  HTTP REST (JSON)
        ▼
FastAPI (uvicorn)  ──►  SQLite (data/portfolio.db)
        │
        ├── APScheduler jobs (price poller, agent runner, indicator calc)
        │
        ├── yfinance (NSE/BSE quotes, OHLCV)
        ├── NSE EQUITY_L.csv (symbol search master)
        ├── screener.in (fundamentals + industry scraping)
        └── Google Gemini API (AI analysis)
```

---

## Backend

### Entry point — `backend/app/main.py`

FastAPI app with a `lifespan` context manager:

1. `Base.metadata.create_all()` — creates all SQLite tables on first run
2. `_ensure_nse_symbols()` — downloads the NSE equity master CSV in a daemon thread
3. `scheduler.start()` — starts APScheduler with IST timezone

CORS is configured via `CORS_ORIGINS` in `.env` (defaults to `localhost:5173,localhost:3000`).

### Configuration — `backend/app/core/config.py`

`pydantic-settings` reads all values from `.env` (and environment variables, case-insensitive). A cached `get_settings()` singleton is used everywhere. Paths are `pathlib.Path` objects — Windows and Unix compatible.

### Database — `backend/app/core/db.py`

SQLAlchemy 2 with a SQLite file engine. `SessionLocal` is the session factory used by all routers via `Depends(get_db)`. No connection pool is needed for SQLite.

### Models — `backend/app/models.py`

| Model | Table | Key constraints |
|---|---|---|
| `Watchlist` | `watchlist` | Unique on `(symbol, exchange)` implied by usage |
| `PriceHistory` | `price_history` | Indexed on `(symbol, timestamp)` |
| `Trade` | `trades` | Plain insert; FIFO logic in `_recalculate_portfolio` |
| `Portfolio` | `portfolio` | `UNIQUE (symbol, exchange)` — enforced in DB |
| `Alert` | `alerts` | FK to `watchlist.id` (nullable, `SET NULL` on delete) |
| `AlertLog` | `alert_log` | FK to `alerts.id` (CASCADE delete) |
| `RiskProfile` | `risk_profile` | Single row (id=1) |
| `AgentAnalysis` | `agent_analysis` | One row per analysis run per symbol |
| `AgentFeedback` | `agent_feedback` | FK to `agent_analysis.id` (CASCADE delete) |
| `CorporateAction` | `corporate_actions` | Plain insert |

### Routers (API endpoints)

| Router | Prefix | Responsibility |
|---|---|---|
| `watchlist.py` | `/watchlist` | CRUD for watched symbols; symbol search |
| `prices.py` | `/prices` | Live quote + OHLCV history via yfinance |
| `trades.py` | `/trades` | Trade CRUD, portfolio view, CSV export, AI portfolio review, bulk import |
| `alerts.py` | `/alerts` | Alert CRUD; triggers immediate evaluation on creation |
| `analysis.py` | `/analysis` | Per-stock AI analysis; fundamentals; indicators |
| `market.py` | `/market` | Industry overview table; AI sector pulse |
| `risk_profile.py` | `/risk-profile` | GET + PUT for the single-row risk profile |
| `corporate_actions.py` | `/corporate-actions` | CRUD for dividends, bonuses, splits |

### Services

**`data_fetch.py`** — all external data fetching:
- `fetch_quote(symbol, exchange)` → yfinance `.NS` / `.BO` ticker
- `fetch_ohlcv(symbol, exchange, days)` → yfinance daily bars
- `search_symbols(query)` → in-memory search of NSE EQUITY_L.csv master
- `fetch_fundamentals(symbol, exchange)` → screener.in scraper (24h in-process cache, keyed `SYMBOL:EXCHANGE`)
- `scrape_industry_overview()` → screener.in sector table
- `fetch_sector_index_data(sector)` → screener.in L2 industry data

**`ai_agent.py`** — Google Gemini calls:
- `run_analysis(symbol, exchange, db)` — per-stock analysis; uses `response_mime_type="application/json"` + `response_schema` for structured output; in-flight dedup via `_analysis_running` set + lock
- `run_sector_analysis(overview_rows)` — sector pulse; 24h cache

**`alert_engine.py`** — `check_alerts(symbol, exchange, ltp, prev_price, db)` — evaluates all active alerts for a symbol; fires notification on trigger; sets `active=False` for non-repeating alerts.

**`notifier.py`** — dispatches to configured channels (ntfy, Telegram, SMTP, Twilio WhatsApp) based on `NOTIFY_CHANNELS`.

**`indicators.py`** — pure Python RSI, SMA, EMA, realized volatility from price history rows.

### Background Jobs (APScheduler)

All jobs run under `BackgroundScheduler(timezone="Asia/Kolkata")`.

| Job | Trigger | Function |
|---|---|---|
| Price poller | Every `PRICE_POLL_INTERVAL_MINUTES` min | `price_poller.run()` — upserts `price_history`, calls `check_alerts` |
| Agent runner | Cron 08:00 IST | `agent_runner.run()` — Gemini analysis for all watchlist symbols |
| Indicator calc | Cron 16:00 IST | `indicator_calc.run()` — refreshes indicators after close |
| Feedback evaluator | Cron 17:00 IST | `feedback_evaluator.run()` — scores old analyses against actual moves |

Price poller silently returns (no-op) outside 09:15–15:30 IST weekdays.

---

## Frontend

### Stack
- React 18 (function components + hooks)
- Vite 5 (build tool + dev server)
- TypeScript 5
- Tailwind CSS 3 (utility-first styling)
- Recharts 2 (portfolio charts)
- react-router-dom 6 (client-side routing)
- lucide-react (icons)

### API client — `src/api/client.ts`

`apiFetch<T>(path, options?, signal?)` is the single fetch helper used by all API modules. It:
- Prepends `VITE_API_URL` (default `http://localhost:8000`)
- Throws `ApiError` (with `.status`) on non-2xx responses
- Passes an optional `AbortSignal` for cancellation

### Routing — `src/App.tsx`

```
/               → Watchlist
/portfolio      → Portfolio
/alerts         → Alerts
/industry       → Industry Dashboard
/risk           → Risk Profile
/stock/:symbol  → Stock Detail (chart, AI analysis, fundamentals, peers)
*               → 404
```

Sidebar footer contains a live `MarketStatusDot` — green when NSE/BSE is open (Mon–Fri 9:15–15:30 IST), grey otherwise. Computed client-side via `Intl.DateTimeFormat` with `Asia/Kolkata` timezone.

### `useSortFilter` hook — `src/hooks/useSortFilter.ts`

Generic sort + filter hook used by Watchlist, Portfolio, Alerts:
- `numericKeys` array — columns that default to descending on first click
- Two flat `setSortKey` / `setSortDir` calls (never nested) to avoid React 18 concurrent mode closure bug

### Pages

| Page | Key features |
|---|---|
| `Watchlist.tsx` | Day range bar, volume, staleness, NSE\|BSE chip, header stat bar, inline delete, ChevronRight affordance |
| `Portfolio.tsx` | P&L tint cards, fuel gauge, colour-coded left border per P&L magnitude, cap-tier tabs with shimmer, analytics panel (4 chart tabs + tier table), collapsible trade history, CSV export button, AI portfolio review |
| `Alerts.tsx` | Collapsible add form, progress bar toward trigger, colour-coded condition pills, paused section, inline delete, Not Monitored banner |
| `StockDetail.tsx` | OHLCV chart with SMA/EMA overlays (memoised), AbortController per symbol, AI analysis card, fundamentals, peers table (sortable), corporate actions |
| `Industry.tsx` | Sticky header, independently collapsible sector sidebar, overview table, AI Sector Pulse (3-tab: BUY / HOLD / AVOID) |
| `RiskProfile.tsx` | Time horizon, loss tolerance, experience level form |

---

## Data Flow: Price Update → Alert → Notification

```
APScheduler tick (every 5 min, market hours)
  └─ price_poller.run()
       ├─ fetch_quote(symbol, exchange)    [yfinance]
       ├─ upsert PriceHistory row          [SQLite]
       └─ check_alerts(symbol, ltp, ...)
            ├─ query Alert rows for symbol
            ├─ evaluate condition_type + threshold
            ├─ if triggered:
            │    ├─ insert AlertLog row
            │    ├─ set active=False (if not repeating)
            │    └─ notifier.send(...)     [ntfy / Telegram / Email / WhatsApp]
            └─ commit
```

## Data Flow: AI Analysis

```
User clicks "Run Analysis" (StockDetail page)
  └─ POST /analysis/{symbol}/run
       ├─ compute_indicators(symbol, exchange, db)   [RSI, SMA, EMA from price_history]
       ├─ fetch_fundamentals(symbol, exchange)        [screener.in, 24h cached]
       ├─ fetch_news(symbol)                          [yfinance news]
       ├─ build prompt with indicators + fundamentals + news + risk profile
       ├─ Gemini API call (response_mime_type=application/json)
       ├─ insert AgentAnalysis row
       └─ return structured_output to frontend
```

---

## Windows Compatibility

The backend uses only cross-platform Python:
- `pathlib.Path` for all file paths
- `pytz` / APScheduler for timezone-aware scheduling (no Unix-only `zoneinfo` dependency issues)
- `threading` (not `multiprocessing`) for all in-process concurrency
- No `uvloop`, no `fork()`, no Unix sockets, no signal handlers

See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for setup instructions and known gotchas.
