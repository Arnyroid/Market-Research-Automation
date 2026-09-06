# Personal Stock Watchlist & AI Trading Assistant — Architecture Spec

## 1. Overview

A personal-use web application to track Indian equities (NSE + BSE) via a
watchlist, trigger custom price/percentage alerts, and generate AI-assisted
trend analysis with risk-aware flags. Single user, no multi-tenancy, equities
only (no F&O/derivatives).

## 2. Scope

**In scope**
- Equity watchlist (NSE + BSE)
- Custom price/% alerts with notifications
- AI agent: hybrid deterministic-indicator + LLM interpretation layer
- Adaptive feedback loop so agent guidance improves with observed outcomes

**Explicitly out of scope for now**
- F&O / derivatives
- Multi-user auth or multi-tenancy
- Real broker order execution
- Mobile app
- Custom-trained/fine-tuned models

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React | Requested, good ecosystem for charts |
| Backend | FastAPI (Python) | Requested, async-friendly, pairs well with the data/AI layer being Python too |
| Database | SQLite | Single user, zero ops overhead, easy to inspect directly |
| Scheduler | APScheduler | Lightweight, no Redis/Celery needed at this scale |
| Market data | `bsedata` (BSE), `nsepython` (NSE) | Free, unofficial scrapers — fine for personal, low-frequency polling |
| Alerts | Telegram Bot API (fallback: SMTP email) | Free, push-like, trivial to set up |
| AI | Hosted LLM API (Claude) | Personal-scale query volume makes API cost negligible; reasoning quality matters more than self-hosting savings here |

Upgrade path if outgrown: swap `bsedata`/`nsepython` for Upstox or Angel One's
free official APIs without changing anything downstream of the data-fetch
layer.

## 4. System Flow

```
                     ┌─────────────────────┐
                     │   APScheduler jobs    │
                     └──────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
 price_poller           indicator_calculator      agent_runner
 (every N min,           (runs after poll,         (daily / on-demand)
  market hours)           computes RSI/SMA/vol)
        │                       │                       │
        ▼                       ▼                       ▼
   price_history table    indicators cached      agent_analysis table
        │                                               │
        ▼                                               │
  alert_checker ──► alert_log ──► notifier              │
  (compares latest price          (Telegram/email)      │
   to active alert rules)                                │
                                                          ▼
                                                  agent_feedback table
                                                  (populated N days later,
                                                   closes the loop)

                     ┌─────────────────────┐
Frontend (React) ◄──►│   FastAPI REST API   │
                     └─────────────────────┘
```

## 5. Database Schema (outline)

```
watchlist
  id, symbol, exchange (NSE|BSE), added_at

price_history
  id, symbol, exchange, timestamp, open, high, low, close, volume

alerts
  id, symbol, exchange, condition_type (price_above|price_below|pct_change),
  threshold, active, created_at

alert_log
  id, alert_id, triggered_at, price_at_trigger, notified (bool)

risk_profile
  id, time_horizon, loss_tolerance, experience_level, updated_at
  -- single row table (one user)

agent_analysis
  id, symbol, exchange, generated_at,
  indicators_snapshot (json),   -- RSI, SMA/EMA, volatility, % change
  news_context (json, nullable),
  llm_output (text),
  risk_flag (low|medium|high),
  target_review_date            -- when feedback should be evaluated

agent_feedback
  id, analysis_id (fk),
  outcome_price, outcome_pct_change, evaluated_at,
  was_flag_useful (bool/nullable)  -- filled in by a scheduled job
```

## 6. Background Jobs

- **price_poller** — every N minutes during market hours (9:15–15:30 IST),
  fetches LTP for all watchlist symbols, writes to `price_history`.
- **alert_checker** — runs right after each poll; evaluates active alerts
  against the latest price, writes to `alert_log`, triggers `notifier`.
- **indicator_calculator** — computes RSI, SMA/EMA, realized volatility
  (via `pandas-ta` or manual calc) on a schedule (e.g. end-of-day + a couple
  of intraday snapshots).
- **agent_runner** — daily by default, or triggered on-demand from the UI;
  assembles context (see §7) and calls the LLM.
- **feedback_evaluator** — runs daily; for any `agent_analysis` row whose
  `target_review_date` has passed, looks up the actual price move and
  populates `agent_feedback`.

## 7. AI Agent Design

**Principle: the LLM interprets, it doesn't compute.** All indicators are
computed deterministically in Python and passed in as structured input —
this keeps the agent's output grounded and makes cost/latency predictable.

**Per-analysis input to the LLM:**
- Symbol, current price, recent OHLCV summary
- Computed indicators: RSI, SMA/EMA, realized volatility, recent % change
- Optional recent news headlines for the symbol
- User's risk profile (time horizon, loss tolerance, experience level)
- A short summary of *past* flags on this symbol and how they played out
  (pulled from `agent_feedback`) — this is the adaptability mechanism, see
  below
- Market-wide volatility regime indicator (e.g. rolling realized volatility
  on Nifty, or India VIX if you wire that in later)

**Output (structured JSON):**
- Plain-language trend summary
- Risk flag: low / medium / high, relative to the user's risk band
- Explicit caveats/confidence notes
- No direct buy/sell instruction — educational framing only, with a
  disclaimer surfaced in the UI wherever this output is shown

### Addressing adaptability

Since the concern is the agent staying static and stale, adaptability here
is built as an **observable feedback loop**, not a black-box retrain:

1. Every analysis is logged with what was flagged and why (`indicators_snapshot`).
2. A scheduled job checks back N days later, records what actually happened,
   and marks whether the flag was directionally useful.
3. Future prompts for the same symbol include a short digest of this
   history ("recent high-volatility flags on this symbol preceded ~5%
   pullbacks within a week, 3 of the last 4 times") — the LLM adapts its
   framing based on this real, inspectable track record rather than a
   fixed rule.
4. The risk profile itself isn't frozen — the UI should periodically nudge
   you to redo the risk questionnaire (e.g. quarterly), so recommendations
   shift as your own risk tolerance changes, not just as the market does.
5. Because everything the agent "adapts" to lives in plain DB rows, you can
   always inspect *why* its tone shifted on a given symbol — nothing is
   hidden inside model weights.

This gets you meaningful adaptability without needing fine-tuning
infrastructure, which would be significant overkill for a personal project.

## 8. API Endpoints (draft)

```
GET    /watchlist
POST   /watchlist
DELETE /watchlist/{id}

GET    /alerts
POST   /alerts
PUT    /alerts/{id}
DELETE /alerts/{id}

GET    /prices/{symbol}
GET    /prices/{symbol}/history

GET    /analysis/{symbol}          # latest cached analysis
POST   /analysis/{symbol}/refresh  # trigger a new agent_runner pass on demand

GET    /risk-profile
PUT    /risk-profile

WS     /ws/prices                  # optional live push to frontend
```

## 9. Project Structure

```
backend/
  app/
    main.py
    db.py
    models.py                 # SQLAlchemy models
    routers/
      watchlist.py
      alerts.py
      prices.py
      analysis.py
      risk_profile.py
    services/
      data_fetch.py            # bsedata / nsepython wrappers
      indicators.py            # RSI, SMA/EMA, volatility calcs
      alert_engine.py
      ai_agent.py               # prompt assembly + LLM call
      notifier.py               # Telegram / email
    jobs/
      scheduler.py              # APScheduler setup, registers all jobs
  requirements.txt

frontend/
  src/
    components/
    pages/
    api/                        # fetch wrappers to FastAPI
  package.json
```

## 10. Notes / Open Decisions

- Telegram bot vs email for alerts — Telegram recommended for a phone-native
  push feel, trivial free setup.
- News headlines for the AI agent are optional at first pass — can be added
  later via Finnhub's free news endpoint without touching the rest of the
  pipeline.
- Market-wide volatility regime input is a nice-to-have, not required for
  v1 — can ship the agent without it and add it once the feedback loop has
  enough history to be useful anyway.