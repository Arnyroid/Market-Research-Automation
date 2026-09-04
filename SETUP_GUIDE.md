# Stock Watchlist & AI Trading Assistant - Complete Setup Guide

## ✅ Implementation Complete!

Your project has been completely refactored and rebuilt according to the architecture specification. Here's what was implemented:

## 📦 What's Been Built

### Backend (`backend/` directory)
✅ **FastAPI Application** - Async REST API with CORS
✅ **SQLAlchemy ORM** - SQLite database with 7 tables
✅ **5 API Routers** - watchlist, alerts, prices, analysis, risk_profile
✅ **4 Service Layers** - data_fetch, indicators, ai_agent, notifier
✅ **5 Background Jobs** - price_poller, alert_checker, indicator_calculator, agent_runner, feedback_evaluator
✅ **APScheduler Integration** - Automatic job scheduling during market hours

### Frontend (`frontend/` directory)
✅ **React 18 App** - Modern UI with routing
✅ **Vite Build Tool** - Fast development and production builds
✅ **API Client Layer** - Axios wrapper for all backend endpoints
✅ **2 Feature Pages** - Watchlist management, Alert management
✅ **Tailwind CSS** - Responsive styling

### Database Schema
✅ `watchlist` - Track stocks
✅ `price_history` - OHLCV data
✅ `alerts` - Alert rules
✅ `alert_log` - Alert triggers
✅ `risk_profile` - User profile (single row)
✅ `agent_analysis` - AI analysis results
✅ `agent_feedback` - Feedback loop data

---

## 🚀 Getting Started (5 minutes)

### Step 1: Backend Setup

```bash
# Navigate to backend
cd backend

# Create Python virtual environment
python -m venv venv
.\venv\Scripts\Activate  # Windows PowerShell
# OR
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy the template
copy .env.example .env  # Windows
# OR
cp .env.example .env  # macOS/Linux

# Edit .env with your API keys:
# - ANTHROPIC_API_KEY (from https://console.anthropic.com)
# - TELEGRAM_BOT_TOKEN (optional, from @BotFather)
# - TELEGRAM_CHAT_ID (optional, from @userinfobot)
# - EMAIL credentials (optional)
```

### Step 3: Start Backend

```bash
# From backend directory with venv activated
python -m uvicorn app.main:app --reload

# You should see:
# INFO:     Started server process [12345]
# INFO:     Uvicorn running on http://0.0.0.0:8000

# API Docs will be at: http://localhost:8000/docs
```

### Step 4: Frontend Setup (in new terminal)

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start dev server
npm run dev

# Visit http://localhost:5173 in your browser
```

---

## 📊 API Endpoints Reference

### Watchlist Management
```
GET    /watchlist                    # List all watched stocks
POST   /watchlist                    # Add stock (body: symbol, exchange)
DELETE /watchlist/{id}               # Remove stock
GET    /watchlist/{symbol}/exists    # Check if in watchlist
```

### Price Alerts
```
GET    /alerts                       # List all alerts
GET    /alerts/symbol/{symbol}       # Get alerts for a symbol
POST   /alerts                       # Create alert
PUT    /alerts/{id}                  # Update alert
DELETE /alerts/{id}                  # Delete alert
GET    /alerts/{alert_id}/logs       # View trigger history
```

### Price Data
```
GET    /prices/{symbol}              # Current price
GET    /prices/{symbol}/history      # Historical prices
POST   /prices/refresh/{symbol}      # Manually refresh price
```

### AI Analysis
```
GET    /analysis/{symbol}            # Latest analysis
POST   /analysis/{symbol}/refresh    # Trigger new analysis
GET    /analysis/{symbol}/history    # Past analyses
GET    /analysis/feedback/{id}       # Feedback outcome
```

### User Settings
```
GET    /risk-profile                 # Get risk profile
POST   /risk-profile                 # Set risk profile
PUT    /risk-profile                 # Update risk profile
```

---

## 🤖 How the AI Agent Works

### 1. **Data Collection Phase**
- Fetches 30 days of historical price data
- Calculates technical indicators:
  - RSI (14), SMA (20/50), EMA (20/50)
  - Volatility (20-day realized)
  - Bollinger Bands, MACD
  - 52-week high/low

### 2. **Context Building Phase**
- Retrieves user's risk profile (time horizon, loss tolerance, experience)
- Pulls past analyses and their outcomes (feedback history)
- Includes recent news headlines (optional future feature)

### 3. **LLM Analysis Phase**
- Sends structured prompt to Claude 3.5 Sonnet
- Claude analyzes indicators + context
- Returns:
  - Trend summary (plain language)
  - Risk flag (low/medium/high)
  - Reasoning and caveats
  - Confidence score

### 4. **Feedback Loop Phase**
- Analysis stored with `target_review_date` (7 days ahead)
- 7 days later, feedback_evaluator checks actual price movement
- Records if flag was useful/accurate
- Future analyses for same symbol include this feedback
- **Result:** Agent improves recommendations based on past accuracy

---

## 🔔 Setting Up Notifications

### Telegram (Recommended - 2 minutes setup)
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts
3. Get your bot token (starts with numbers)
4. Message [@userinfobot](https://t.me/userinfobot) to get your chat ID
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=987654321
   ```

### Email (Gmail - 3 minutes setup)
1. Enable 2-Step Verification on Google Account
2. Generate [App Password](https://myaccount.google.com/apppasswords)
3. Add to `.env`:
   ```
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
   EMAIL_RECIPIENT=your-email@gmail.com
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

---

## 📅 Background Jobs Schedule

All jobs run automatically when the app starts. Times are IST (UTC+5:30):

| Job | When | What |
|-----|------|------|
| **price_poller** | Every 5 min | Fetches latest prices for all watched stocks |
| **alert_checker** | Every 5 min | Checks if any alerts should trigger |
| **indicator_calculator** | 16:00 (4 PM) | Calculates RSI, SMA, volatility, etc |
| **agent_runner** | 08:00 (8 AM) | Generates AI analysis for all stocks |
| **feedback_evaluator** | 17:00 (5 PM) | Records actual price moves vs predictions |

**Note:** Times can be adjusted in `backend/app/main.py` using cron expressions.

---

## 🧪 Testing the System

### 1. Add a Stock
```bash
curl -X POST http://localhost:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","exchange":"NSE"}'
```

### 2. Check Current Price
```bash
curl http://localhost:8000/prices/RELIANCE
```

### 3. Create an Alert
```bash
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "symbol":"RELIANCE",
    "exchange":"NSE",
    "condition_type":"price_above",
    "threshold":2500
  }'
```

### 4. Trigger AI Analysis
```bash
curl -X POST http://localhost:8000/analysis/RELIANCE/refresh
```

### 5. View Analysis Results
```bash
curl http://localhost:8000/analysis/RELIANCE
```

---

## 📁 File Structure Overview

```
Market-Research-Automation/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── db.py                   # SQLite setup
│   │   ├── models.py               # Database tables
│   │   ├── routers/                # API endpoints
│   │   ├── services/               # Business logic
│   │   └── jobs/                   # Background jobs
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/                  # React pages
│   │   ├── components/             # React components
│   │   ├── api/                    # API client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── data/
│   └── watchlist.db                # SQLite database (auto-created)
│
└── IMPLEMENTATION_GUIDE.md         # Full documentation
```

---

## ⚙️ Key Configuration Files

### `backend/.env`
Contains all sensitive configuration:
- API keys (Claude, Telegram, Gmail)
- Server settings (host, port, debug mode)
- Market hours

### `backend/requirements.txt`
All Python dependencies with versions

### `frontend/package.json`
All Node.js dependencies, build scripts

### `frontend/vite.config.js`
Frontend build configuration

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Python version
python --version  # Should be 3.9+

# Try installing dependencies individually
pip install fastapi uvicorn sqlalchemy

# Check for port conflicts
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # macOS/Linux
```

### Frontend Won't Connect to Backend
```bash
# Check backend is running at http://localhost:8000
# Check CORS is enabled (should be by default)
# Try accessing http://localhost:8000/docs in browser
```

### Prices Not Updating
```bash
# Check logs in backend console
# Verify watchlist has symbols
# Manually refresh: POST /prices/refresh/{symbol}
```

### Claude API Errors
```bash
# Verify ANTHROPIC_API_KEY is correct
# Check API key has permissions at https://console.anthropic.com/
# Try a simple curl to test:
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY"
```

---

## 📚 Next Steps

1. **Customize Risk Profile**
   - Set your time horizon, loss tolerance, experience level
   - Agent will adapt recommendations based on this

2. **Add Your Favorite Stocks**
   - Add 5-10 stocks to watchlist
   - Let system collect data for a few days

3. **Create Alerts**
   - Set up price alerts for your key levels
   - Configure Telegram/Email notifications

4. **Monitor Feedback Loop**
   - After 7 days, feedback will be available
   - Check if agent flags matched actual price moves

5. **Fine-tune Job Schedule**
   - Adjust in `backend/app/main.py` if you prefer different timing
   - Add more indicators if desired

---

## 🚀 Production Deployment

### Backend
```bash
# Use production ASGI server
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Frontend
```bash
# Build for production
npm run build

# Serve dist/ folder with any web server (nginx, Apache, S3+CloudFront, etc)
```

### Database
- Backup `data/watchlist.db` regularly
- Consider migrating to PostgreSQL for large scale

---

## 📖 Architecture Highlights

✅ **Deterministic + AI Hybrid** - Technical indicators computed deterministically, interpreted by LLM
✅ **Observable Feedback Loop** - Every analysis logged with outcomes, visible in database
✅ **Personal-Scale** - Single-user, no auth needed, SQLite database
✅ **Async Jobs** - Background processing doesn't block API
✅ **Type-Safe** - Pydantic models + SQLAlchemy ORM
✅ **Modular Services** - Easy to swap data sources or models
✅ **Scalable** - Can add more stocks, longer history without major changes

---

## ⚠️ Important Disclaimers

🚨 **This is for educational and personal analysis only**
🚨 **NOT financial advice - always do your own research**
🚨 **Stock markets involve risk of loss**
🚨 **Past performance ≠ future results**
🚨 **Consult a financial advisor before investing**

---

## 🎉 You're All Set!

Your Stock Watchlist & AI Trading Assistant is ready to use. Start by:

1. Setting your risk profile in `/risk-profile`
2. Adding 3-5 stocks to your watchlist
3. Creating a few price alerts
4. Checking back in a week for AI analysis feedback

Happy investing! 📈
