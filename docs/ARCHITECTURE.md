# System Architecture — StockAI

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Frontend                             │
│   Watchlist | Portfolio | Alerts | Stock Detail | Risk Profile   │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP/REST + WebSocket
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend  (port 8000)                │
├──────────────────────────────────────────────────────────────────┤
│ Routers:                                                          │
│  ├─ /watchlist   — add, remove, search, list symbols             │
│  ├─ /alerts      — create, update, delete, log, fire             │
│  ├─ /prices      — live quote, OHLCV history, WebSocket feed     │
│  ├─ /trades      — BUY/SELL entry, FIFO P&L, AI portfolio review │
│  ├─ /analysis    — Gemini AI insight per symbol, on demand       │
│  └─ /risk-profile— user risk preferences                         │
└───┬──────────────┬──────────────┬──────────────┬─────────────────┘
    │              │              │              │
┌───▼───┐    ┌─────▼──┐    ┌─────▼──┐    ┌──────▼──┐
│data_  │    │indica- │    │ai_     │    │notifier │
│fetch  │    │tors    │    │agent   │    │         │
│       │    │        │    │        │    │ntfy.sh  │
│yfinance    │RSI-14  │    │Gemini  │    │(push)   │
│NSE CSV│    │SMA-20  │    │Flash   │    │         │
│search │    │SMA-50  │    │        │    │telegram │
│       │    │SMA-200 │    │struct. │    │email    │
│       │    │EMA-20  │    │JSON    │    │         │
│       │    │Vol-30d │    │output  │    │         │
└───┬───┘    └────────┘    └────────┘    └─────────┘
    │
┌───▼─────────────────────────────────────────────┐
│              APScheduler Background Jobs         │
│  Every 5 min (market hours):  price_poller       │
│    └─ fetches LTP → upserts price_history        │
│    └─ calls check_alerts() for each symbol       │
│  Daily 17:00 IST:             feedback_evaluator │
│    └─ scores past AI recommendations             │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        ▼                      ▼
  ┌───────────┐        ┌──────────────┐
  │  SQLite   │        │ Notifications│
  │ portfolio │        │              │
  │   .db     │        │  ntfy.sh ✅  │
  │           │        │  Telegram    │
  │ watchlist │        │  Email       │
  │ trades    │        └──────────────┘
  │ portfolio │
  │ alerts    │
  │ alert_log │
  │ agent_    │
  │  analysis │
  │ agent_    │
  │  feedback │
  └───────────┘
```

---

## Data Flow: Live Price & Alert Pipeline

```
Market open (09:15 IST)
         ▼
price_poller fires every 5 minutes
         │
         ├─ For each symbol in watchlist:
         │    1. fetch_quote(symbol, exchange)  →  yfinance
         │    2. Upsert price_history (one row per trading day)
         │    3. check_alerts(symbol, price, prev_price, db)
         │         ├─ price_above / price_below   → compare LTP to threshold
         │         ├─ pct_change_up / down         → compare to yesterday's close
         │         └─ portfolio_pnl_below          → compare P&L% vs avg_buy_price
         │              If triggered:
         │                ├─ Write AlertLog row
         │                ├─ Send ntfy push notification
         │                └─ Deactivate alert (unless repeating=True)
         │
         └─ db.commit()

Market hours gate: skips entirely outside 09:15–15:30 IST
IST clock: pytz.timezone("Asia/Kolkata")  — server timezone-independent
```

---

## Data Flow: AI Analysis (On-Demand)

```
User opens /stock/:symbol  OR  clicks "Refresh Insight"
         ▼
POST /analysis/{symbol}/refresh
         │
         ├─ compute_indicators(symbol, exchange, db)
         │    ├─ DB has < 200 bars? → fetch 300-day OHLCV from yfinance
         │    ├─ RSI-14  (Wilder smoothing)
         │    ├─ SMA-20, SMA-50, SMA-200
         │    ├─ EMA-20
         │    ├─ Realized volatility (30-day annualised)
         │    ├─ % change 1d / 5d / 30d
         │    └─ _build_signal_context()  →  plain-English deterministic signals
         │         e.g. "DMA-50 > DMA-200 — GOLDEN CROSS: long-term bullish"
         │
         ├─ fetch_news(symbol)  →  yfinance headlines (nested content.title)
         │
         ├─ Build structured prompt for Gemini:
         │    - Indicator snapshot
         │    - Signal context
         │    - News headlines
         │    - User risk profile
         │
         ├─ Call Gemini Flash (→ fallback Flash Lite on 503)
         │    Returns JSON: { summary, recommendation, rationale,
         │                    risk_flag, caveats, disclaimer }
         │
         ├─ Strip markdown fences, parse JSON
         ├─ Store in agent_analysis
         └─ Set target_review_date = today + 7 days

Frontend polls GET /analysis/{symbol} every 3 s (45 s timeout)
until generated_at is newer than the previous value.
```

---

## Data Flow: Feedback Loop

```
Day 0 — Analysis generated
  agent_analysis row written:
    recommendation = "BUY"
    risk_flag = "low"
    target_review_date = Day 7

Day 7 — 17:00 IST — feedback_evaluator fires
  ├─ Find analyses where target_review_date ≤ today AND no feedback yet
  ├─ price_at  = price_history row closest to generated_at
  ├─ price_now = most recent price_history row
  ├─ pct = (price_now − price_at) / price_at × 100
  │
  ├─ was_flag_useful:
  │    high risk + price fell > 3%  → True
  │    low  risk + price rose > 3%  → True
  │    otherwise                    → False
  │
  └─ was_rec_accurate:
       BUY   + pct > +3%  → True
       SELL/AVOID + pct < −3% → True
       HOLD  + |pct| ≤ 5% → True
       otherwise           → False

agent_feedback row written with both scores.
```

---

## Database Schema

```
watchlist
  id, symbol, exchange, company_name, sector, added_at

price_history                        ← one row per (symbol, exchange, date)
  id, symbol, exchange, timestamp, open, high, low, close, volume

trades
  id, trade_date, symbol, exchange, company_name
  trade_type (BUY|SELL), quantity, price, brokerage
  realized_pnl        ← FIFO gain/loss, populated on SELL by _recalculate_portfolio
  notes, created_at

portfolio                            ← aggregated holdings, rebuilt on every trade change
  id, symbol, exchange, company_name
  total_quantity, avg_buy_price, total_invested
  current_price, current_value
  unrealized_pnl, unrealized_pnl_pct
  last_updated

alerts
  id, watchlist_id (nullable FK), symbol, exchange
  condition_type  (price_above | price_below | pct_change_up |
                   pct_change_down | portfolio_pnl_below)
  threshold, active, repeating, notes, created_at

alert_log
  id, alert_id (FK), triggered_at, price_at_trigger, notified

risk_profile                         ← single row
  id, time_horizon, loss_tolerance, experience_level, updated_at

agent_analysis
  id, symbol, exchange, generated_at
  indicators_snapshot (JSON), news_context (JSON)
  llm_output, risk_flag, structured_output (JSON)
  target_review_date

agent_feedback
  id, analysis_id (FK), outcome_price, outcome_pct_change
  evaluated_at, was_flag_useful, was_rec_accurate
```

---

## Frontend Architecture

```
App.tsx  (React Router v6)
  ├── /                 → Watchlist.tsx
  │     usePriceSocket() → WebSocket live feed
  │     useSortFilter()  → client-side sort + text filter
  │     WifiOff banner when disconnected
  │     Clock icon on prices not updated > 10 min
  │
  ├── /portfolio        → Portfolio.tsx
  │     Holdings table  (clickable rows → /stock/:symbol)
  │     FIFO P&L with unrealized + realized P&L columns
  │     Add Transaction modal (pre-fillable via ?addTrade=SYMBOL)
  │     PortfolioReviewCard  (Gemini AI portfolio analysis)
  │
  ├── /alerts           → Alerts.tsx
  │     New Alert form  (pre-fillable via ?symbol=SYMBOL)
  │     5 condition types including portfolio_pnl_below
  │     Trigger history collapsible per alert
  │
  ├── /stock/:symbol    → StockDetail.tsx
  │     300-day Recharts line chart
  │     4 overlay toggles: SMA-20, EMA-20, DMA-50, DMA-200
  │     8 indicator tiles: RSI, SMA-20, DMA-50, DMA-200,
  │                        EMA-20, 5d change, volatility
  │     Quick-action buttons: Add Alert, Add Trade → pre-fill
  │     Gemini AI insight (auto-generate if stale, poll loop)
  │
  └── /risk             → RiskProfile.tsx

hooks/
  usePriceSocket.ts   → { prices: Map, connected: boolean }
  useSortFilter.ts    → generic sort + text filter

api/
  client.ts, watchlist.ts, prices.ts,
  alerts.ts, trades.ts, analysis.ts
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + Vite | 18 / 5 |
| Frontend charts | Recharts | 2 |
| Frontend routing | React Router | 6 |
| Frontend icons | Lucide React | latest |
| Styling | Tailwind CSS | 3 |
| Backend | FastAPI + Uvicorn | 0.115 / 0.30 |
| ORM | SQLAlchemy | 2 |
| Config | pydantic-settings | 2 |
| Scheduler | APScheduler | 3 |
| Market data | yfinance | ≥0.2.40 |
| AI | google-genai SDK | ≥1.0.0 |
| Notifications | httpx (ntfy REST) | ≥0.27 |
| Data processing | pandas | 2 |
| Timezone | pytz | ≥2024.1 |
| Logging | loguru | 0.7 |
| Database | SQLite | built-in |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| yfinance only (no nsepython/bsedata) | NSE website blocks server-side HTTP (403); yfinance is reliable |
| One price row per trading day (upsert) | Prevents chart going flat from duplicate intraday rows |
| AI on-demand, not scheduled | Gemini free tier has quota limits; user-triggered is more useful |
| `signal_context` in Python, not LLM | Deterministic indicator rules should never be delegated to an LLM |
| `portfolio_pnl_below` checks live P&L | Looks up `avg_buy_price` from portfolio table at trigger time |
| `realized_pnl` written on SELL recalculation | FIFO cost basis is already computed; store it per trade for display |
| `was_rec_accurate` separate from `was_flag_useful` | Flag (risk level) and recommendation (BUY/HOLD/SELL) measure different things |
| URL params for pre-fill (`?symbol=`, `?addTrade=`) | No shared state needed; deep-linkable from any page |
| `pytz.timezone("Asia/Kolkata")` for market hours | Server may run on UTC; system clock can't be assumed to be IST |
