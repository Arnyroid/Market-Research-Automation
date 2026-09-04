# Stock Watchlist & AI Trading Assistant - Implementation Guide

This is a complete implementation of the architecture specification for a personal-use web application to track Indian equities with custom price alerts and AI-assisted trend analysis.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### Backend Setup

1. **Create virtual environment:**
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate  # Windows
# or
source venv/bin/activate  # macOS/Linux
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Create `.env` file:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Required environment variables:**
```
ANTHROPIC_API_KEY=sk-...  # Get from https://console.anthropic.com/
TELEGRAM_BOT_TOKEN=...    # Get from BotFather on Telegram (optional)
TELEGRAM_CHAT_ID=...      # Your Telegram chat ID (optional)
EMAIL_SENDER=...          # Gmail account
EMAIL_PASSWORD=...        # Gmail app password
```

5. **Initialize database and start server:**
```bash
python -m uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start development server:**
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, scheduler setup
│   ├── db.py                # Database configuration
│   ├── models.py            # SQLAlchemy ORM models
│   ├── routers/
│   │   ├── watchlist.py
│   │   ├── alerts.py
│   │   ├── prices.py
│   │   ├── analysis.py
│   │   └── risk_profile.py
│   ├── services/
│   │   ├── data_fetch.py      # BSE/NSE data fetching
│   │   ├── indicators.py      # Technical indicator calculations
│   │   ├── ai_agent.py        # Claude LLM integration
│   │   └── notifier.py        # Telegram/Email notifications
│   └── jobs/
│       └── scheduler.py       # APScheduler background jobs
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── pages/
│   │   ├── WatchlistPage.jsx
│   │   └── AlertsPage.jsx
│   ├── components/
│   ├── api/
│   │   └── client.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
├── vite.config.js
└── index.html
```

## 🗄️ Database Schema

The SQLite database includes the following tables:

- **watchlist** - Tracked stock symbols
- **price_history** - Historical OHLCV data
- **alerts** - Alert rules (price_above, price_below, pct_change)
- **alert_log** - Triggered alerts and notification status
- **risk_profile** - User's risk profile (single row)
- **agent_analysis** - AI analysis results with indicators snapshot
- **agent_feedback** - Observed outcomes for feedback loop

Database file: `data/watchlist.db`

## 🔄 Background Jobs

The scheduler automatically runs the following jobs:

| Job | Frequency | Description |
|-----|-----------|-------------|
| price_poller | Every 5 min | Fetch latest prices for watchlist symbols |
| alert_checker | Every 5 min | Check and trigger alerts, send notifications |
| indicator_calculator | Daily 16:00 IST | Calculate technical indicators |
| agent_runner | Daily 08:00 IST | Run AI analysis on all watchlist symbols |
| feedback_evaluator | Daily 17:00 IST | Evaluate analysis outcomes, populate feedback |

**Note:** Times are configurable in `backend/app/main.py`

## 📊 API Endpoints

### Watchlist
- `GET /watchlist` - Get all watched stocks
- `POST /watchlist` - Add stock to watchlist
- `DELETE /watchlist/{id}` - Remove stock from watchlist

### Alerts
- `GET /alerts` - Get all alerts
- `POST /alerts` - Create new alert
- `PUT /alerts/{id}` - Update alert
- `DELETE /alerts/{id}` - Delete alert
- `GET /alerts/symbol/{symbol}` - Get alerts for a symbol
- `GET /alerts/{alert_id}/logs` - Get alert trigger logs

### Prices
- `GET /prices/{symbol}` - Get current price
- `GET /prices/{symbol}/history` - Get price history (default 30 days)
- `POST /prices/refresh/{symbol}` - Manually refresh price

### Analysis
- `GET /analysis/{symbol}` - Get latest AI analysis
- `POST /analysis/{symbol}/refresh` - Trigger new analysis
- `GET /analysis/{symbol}/history` - Get analysis history
- `GET /analysis/feedback/{analysis_id}` - Get feedback for analysis

### Risk Profile
- `GET /risk-profile` - Get user's risk profile
- `POST /risk-profile` - Create risk profile
- `PUT /risk-profile` - Update risk profile

### Health
- `GET /health` - Health check

## 🤖 AI Agent

The AI agent provides trend analysis and risk flags by:

1. **Computing indicators deterministically** - RSI, SMA/EMA, volatility, MACD, Bollinger Bands
2. **Assembling structured input** - Current price, recent OHLCV, indicators, user risk profile
3. **Calling Claude LLM** - Gets plain-language trend summary and risk flag
4. **Building observable feedback loop** - Past analyses and their outcomes are included in future prompts

**Output structure:**
```json
{
  "trend_summary": "Plain language trend description",
  "risk_flag": "low|medium|high",
  "reasoning": "Detailed explanation",
  "caveats": "Important caveats",
  "technical_outlook": "Indicator-based outlook",
  "confidence_score": 0.75
}
```

## 🔔 Notifications

### Telegram (Recommended)
1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `.env`

### Email (Gmail)
1. Enable 2FA on Gmail
2. Generate [App Password](https://myaccount.google.com/apppasswords)
3. Add `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECIPIENT` to `.env`

## 📊 Technical Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.9+ |
| Database | SQLite |
| Scheduler | APScheduler |
| Data Fetch | bsedata, nsepython, yfinance |
| Indicators | pandas-ta (with fallbacks) |
| AI | Claude 3.5 Sonnet API |
| Notifications | Telegram Bot API, SMTP/Gmail |

## 🔧 Configuration

Key environment variables in `.env`:

```
# API
HOST=0.0.0.0
PORT=8000
DEBUG=False

# AI/LLM
ANTHROPIC_API_KEY=sk-...

# Notifications
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
EMAIL_SENDER=...
EMAIL_PASSWORD=...

# Market Hours
MARKET_OPEN_TIME=09:15
MARKET_CLOSE_TIME=15:30
```

## 🚀 Deployment

### Backend (Production)
```bash
pip install -r requirements.txt
# Use a production ASGI server
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Frontend (Production)
```bash
npm run build
# Serve the dist/ folder with any static server
```

### Database
SQLite database is stored in `data/watchlist.db`. Backup regularly for production use.

## 📝 Notes

- **Personal use only** - No multi-user authentication
- **No real trading** - This is for analysis and alerts only
- **Educational purposes** - Not financial advice
- **Unofficial data sources** - bsedata and nsepython are unofficial scrapers; consider upgrading to official APIs (Upstox, Angel One) for production

## 🔄 Upgrade Path

To use official APIs instead of scrapers:
- Replace `DataFetchService` with Upstox or Angel One SDK
- No changes needed downstream - all interfaces remain the same

## 📚 Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Claude API Documentation](https://docs.anthropic.com/)

## ⚠️ Disclaimer

This software is provided for educational and personal analysis purposes only. It is not financial advice. Always conduct your own research and consult with a financial advisor before making investment decisions.

Stock markets involve risk of loss. Past performance is not indicative of future results.
