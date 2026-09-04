# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                            │
│  (Watchlist | Alerts | Analysis | Risk Profile Management)     │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST (Axios)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                            │
├──────────────────────────────────────────────────────────────────┤
│ Routers:                                                         │
│  ├─ /watchlist     (add, remove, list stocks)                   │
│  ├─ /alerts        (create, manage price alerts)                │
│  ├─ /prices        (current price, history)                     │
│  ├─ /analysis      (AI trend analysis & refresh)                │
│  └─ /risk-profile  (user risk settings)                         │
└────────┬──────────────┬──────────────┬────────────────┬─────────┘
         │              │              │                │
    ┌────▼──┐      ┌────▼──┐     ┌────▼──┐        ┌────▼──┐
    │Services│      │Services│     │Services│        │Services│
    ├────────┤      ├────────┤     ├────────┤        ├────────┤
    │data_   │      │indica- │     │ai_     │        │notifi- │
    │fetch   │      │tors    │     │agent   │        │er      │
    │        │      │        │     │        │        │        │
    │• BSE   │      │• RSI   │     │• Claude│        │• Tele- │
    │• NSE   │      │• SMA   │     │  API   │        │  gram  │
    │• Yahoo │      │• EMA   │     │• Prompt│        │• Email │
    │ Finance│      │• Vol   │     │ Build  │        │        │
    └────┬───┘      │• MACD  │     │• Parse │        └────────┘
         │          │• BB    │     │  Output│
         │          └────────┘     └────┬───┘
         │                             │
    ┌────▼────────────────────────────▼─────┐
    │       APScheduler Background Jobs       │
    ├────────────────────────────────────────┤
    │ Every 5 min:   price_poller            │
    │ Every 5 min:   alert_checker           │
    │ Daily 16:00:   indicator_calculator    │
    │ Daily 08:00:   agent_runner            │
    │ Daily 17:00:   feedback_evaluator      │
    └────────────────┬───────────────────────┘
                     │
         ┌───────────┴──────────┐
         ▼                      ▼
    ┌─────────────┐        ┌──────────────┐
    │   SQLite    │        │  Notifications│
    │  Database   │        ├──────────────┤
    │             │        │ Telegram Bot │
    │ • watchlist │        │ SMTP/Gmail   │
    │ • prices    │        │ (async)      │
    │ • alerts    │        └──────────────┘
    │ • analyses  │
    │ • feedback  │
    │ • risk      │
    └─────────────┘
```

## Data Flow: Price Alert Processing

```
1. Market Open (09:15 IST)
   ▼
2. price_poller job (every 5 min)
   - Fetches latest LTP from BSE/NSE for all watchlist symbols
   - Stores in price_history table
   ▼
3. alert_checker job (immediately after)
   - Queries active alerts
   - Compares latest price to alert thresholds
   - If condition met: creates alert_log entry
   - Triggers notification (Telegram/Email)
   ▼
4. User receives notification
   "🔔 ALERT: RELIANCE crossed above ₹2500"
```

## Data Flow: AI Analysis Generation

```
Morning (08:00 IST)
   ▼
agent_runner job starts
   ▼
For each watchlist symbol:
   ├─ Fetch 30-day price history
   ├─ Calculate indicators
   │  ├─ RSI(14)
   │  ├─ SMA(20,50)
   │  ├─ EMA(20,50)
   │  ├─ Volatility
   │  ├─ MACD
   │  └─ Bollinger Bands
   ├─ Get user risk profile
   ├─ Fetch past feedback history for symbol
   │  "This stock: high flags 3/4 times preceded 5%+ drops"
   ├─ Build prompt with all context
   ├─ Call Claude API
   │  "Stock is overbought (RSI=78), high volatility suggests
   │   sell pressure. However, SMA shows uptrend. Risk: MEDIUM"
   ├─ Parse JSON response
   ├─ Store analysis in agent_analysis table
   └─ Set target_review_date = now + 7 days

After 7 days (feedback_evaluator job, 17:00 IST)
   ├─ Look up the analysis
   ├─ Get price when analysis was made
   ├─ Get current price
   ├─ Calculate % change
   ├─ Determine if flag was useful
   │  "Flagged HIGH risk: price dropped 6% ✓ Useful!"
   └─ Store in agent_feedback
      Next time this stock is analyzed, history will show:
      "Recent HIGH flags preceded drops 3 of 4 times"
```

## Database Schema (Simplified)

```
watchlist
  ├─ id (PK)
  ├─ symbol (UNIQUE)
  ├─ exchange (NSE|BSE)
  └─ added_at

price_history
  ├─ id (PK)
  ├─ symbol (FK→watchlist)
  ├─ timestamp
  ├─ open, high, low, close
  └─ volume

alerts
  ├─ id (PK)
  ├─ symbol (FK)
  ├─ condition_type (price_above|price_below|pct_change)
  ├─ threshold
  ├─ active
  └─ created_at

alert_log
  ├─ id (PK)
  ├─ alert_id (FK)
  ├─ triggered_at
  ├─ price_at_trigger
  └─ notified

risk_profile (single row)
  ├─ id (PK)
  ├─ time_horizon (short|medium|long)
  ├─ loss_tolerance (conservative|moderate|aggressive)
  ├─ experience_level (beginner|intermediate|advanced)
  └─ updated_at

agent_analysis
  ├─ id (PK)
  ├─ symbol (FK)
  ├─ generated_at
  ├─ indicators_snapshot (JSON)
  ├─ llm_output (text)
  ├─ risk_flag (low|medium|high)
  └─ target_review_date

agent_feedback
  ├─ id (PK)
  ├─ analysis_id (FK)
  ├─ outcome_price
  ├─ outcome_pct_change
  ├─ evaluated_at
  └─ was_flag_useful
```

## Technology Stack & Interactions

```
┌──────────────┐
│   Browser    │  React 18 + Vite
│  (Frontend)  │  - Components
│              │  - Pages
└────────┬─────┘  - Routing
         │        - State Management
         │ HTTP/JSON
         ▼
┌──────────────────────┐
│   FastAPI Server     │  Python 3.9+
│   (Port 8000)        │  - Async handlers
│                      │  - Pydantic validation
└────────┬─────────────┘  - CORS middleware
         │                - 200+ lines per router
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────────────┐
│ SQLite │ │ Background Job │  APScheduler
│Database│ │   Scheduler    │  - 5 scheduled jobs
└────────┘ │   (APScheduler)│  - Cron triggers
           │                │  - Interval triggers
           └────────┬───────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    ┌─────────┐ ┌────────┐ ┌────────┐
    │Data     │ │Claude  │ │Notifi- │
    │Sources  │ │API     │ │cations │
    │(BSE/    │ │(LLM)   │ │(Tele/  │
    │NSE/     │ │        │ │Email)  │
    │Yahoo)   │ │        │ │        │
    └─────────┘ └────────┘ └────────┘
```

## API Request/Response Flow Example

```
Frontend Action: User clicks "Add to Watchlist"
                       ▼
POST /watchlist
{
  "symbol": "RELIANCE",
  "exchange": "NSE"
}
                       ▼
Backend: watchlist.py router
- Validate input (Pydantic)
- Check if already exists
- Insert into database
- Commit transaction
                       ▼
HTTP 200 Response
{
  "id": 1,
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "added_at": "2024-01-15T10:30:00"
}
                       ▼
Frontend: Updates UI
- Show in watchlist list
- Enable alert creation for this symbol
```

## Feedback Loop: The Adaptation Mechanism

```
Day 1 - Morning (08:00 IST)
┌─────────────────────────────────┐
│ agent_runner analyzes RELIANCE   │
│ ┌──────────────────────────────┐ │
│ │ Indicators:                  │ │
│ │ - RSI: 75 (overbought)       │ │
│ │ - SMA: Moving down           │ │
│ │ - Volatility: High           │ │
│ │                              │ │
│ │ Past feedback history: empty │ │
│ │                              │ │
│ │ Analysis: "HIGH RISK"        │ │
│ │ target_review_date = Day 8   │ │
│ └──────────────────────────────┘ │
└─────────────────────────────────┘
      Price: ₹2500

Day 8 - Afternoon (17:00 IST)
┌──────────────────────────────┐
│ feedback_evaluator checks    │
│ ┌────────────────────────────┤
│ │ Price Day 1: ₹2500         │
│ │ Price Day 8: ₹2340         │
│ │ % Change: -6.4%            │
│ │                            │
│ │ Flag was HIGH RISK         │
│ │ Actual: DROPPED            │
│ │                            │
│ │ → was_flag_useful = TRUE ✓ │
│ └────────────────────────────┘
└──────────────────────────────┘

Day 9 - Morning (08:00 IST)
┌───────────────────────────────────┐
│ agent_runner analyzes RELIANCE     │
│ again                             │
│ ┌─────────────────────────────────┤
│ │ Indicators: [same as before]    │
│ │                                 │
│ │ Past feedback history:          │
│ │ "Recent HIGH-risk flags on this │
│ │ stock preceded ~6% drops, 1 of  │
│ │ 1 times analyzed. High accuracy."│
│ │                                 │
│ │ Analysis: "HIGH RISK (pattern   │
│ │ shows strong predictive value)  │
│ │ confidence: HIGH"               │
│ └─────────────────────────────────┘
└───────────────────────────────────┘

Result: LLM adapts based on ACTUAL DATA, not retraining
```

## Scaling Path

From personal-use MVP to production:

```
Phase 1: Personal Use (Current)
├─ Single-user, SQLite
├─ Unofficial data sources (bsedata, nsepython)
├─ Free Claude API tier
└─ Email/Telegram notifications

Phase 2: Resilient Personal
├─ PostgreSQL instead of SQLite
├─ Scheduled backups
├─ Error monitoring (Sentry)
├─ Structured logging
└─ Rate limiting

Phase 3: Multi-User (if needed)
├─ User authentication (JWT)
├─ Multi-tenancy support
├─ API key management
├─ Usage analytics
└─ Billing system

Phase 4: Production Ready
├─ Kubernetes deployment
├─ Redis caching
├─ Upgrade to official APIs (Upstox, Angel One)
├─ Premium LLM features
└─ Mobile app
```

## Performance Characteristics

```
Database Queries
├─ Watchlist fetch: O(1) - returns all rows instantly
├─ Price lookup: O(log n) - indexed on timestamp
├─ Alert check: O(m) - m = number of active alerts
└─ Analysis retrieval: O(1) - latest per symbol cached

Background Jobs
├─ price_poller: 5-10 seconds per 10 stocks
├─ indicator_calculator: 30-60 seconds for 10 stocks
├─ agent_runner: 2-3 seconds per stock (Claude API latency)
└─ feedback_evaluator: < 1 second per completed analysis

API Response Times
├─ GET watchlist: < 50ms
├─ POST analysis/refresh: 3-5 seconds (Claude latency)
├─ GET prices: < 100ms (cached, otherwise 1-2s network)
└─ POST alerts: < 50ms
```
