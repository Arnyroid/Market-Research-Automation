# Quick Reference Card

## 🚀 60-Second Start

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Visit: http://localhost:5173 (frontend) & http://localhost:8000/docs (API)

---

## 📁 Key Files to Know

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app & scheduler |
| `backend/app/models.py` | Database schema |
| `backend/app/services/ai_agent.py` | Claude integration |
| `backend/app/jobs/scheduler.py` | Background jobs |
| `frontend/src/api/client.js` | API wrapper |
| `.env` | Configuration (create from `.env.example`) |

---

## 🔌 API Endpoints (Quick)

### Watchlist
```
GET    /watchlist
POST   /watchlist                    {symbol, exchange}
DELETE /watchlist/{id}
```

### Alerts
```
GET    /alerts
POST   /alerts                       {symbol, exchange, condition_type, threshold}
PUT    /alerts/{id}                  {active, condition_type, threshold}
DELETE /alerts/{id}
```

### Prices
```
GET    /prices/{symbol}
GET    /prices/{symbol}/history?days=30
POST   /prices/refresh/{symbol}
```

### Analysis
```
GET    /analysis/{symbol}
POST   /analysis/{symbol}/refresh
GET    /analysis/{symbol}/history?limit=10
GET    /analysis/feedback/{analysis_id}
```

### Risk Profile
```
GET    /risk-profile
POST   /risk-profile                 {time_horizon, loss_tolerance, experience_level}
PUT    /risk-profile
```

---

## 🛠️ Common Tasks

### Add a Stock
```bash
curl -X POST http://localhost:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","exchange":"NSE"}'
```

### Create Alert
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

### Get Analysis
```bash
curl http://localhost:8000/analysis/RELIANCE
```

### Set Risk Profile
```bash
curl -X POST http://localhost:8000/risk-profile \
  -H "Content-Type: application/json" \
  -d '{
    "time_horizon":"medium-term",
    "loss_tolerance":"moderate",
    "experience_level":"intermediate"
  }'
```

---

## ⚙️ Environment Variables

```
ANTHROPIC_API_KEY=sk-...              # Claude API key
TELEGRAM_BOT_TOKEN=123456:ABC-DEF     # Telegram bot
TELEGRAM_CHAT_ID=987654321            # Your chat ID
EMAIL_SENDER=your@gmail.com           # Gmail address
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx    # App password
```

---

## 🔄 Background Jobs Timeline

| Time | Job | Frequency |
|------|-----|-----------|
| Every 5 min | price_poller | Fetch prices |
| Every 5 min | alert_checker | Trigger alerts |
| Daily 16:00 | indicator_calculator | Calculate indicators |
| Daily 08:00 | agent_runner | Generate analysis |
| Daily 17:00 | feedback_evaluator | Score past analyses |

*(Times adjustable in `backend/app/main.py`)*

---

## 📊 Database

```bash
# Location
data/watchlist.db

# View in SQLite GUI
# Download DB Browser for SQLite from: https://sqlitebrowser.org/

# Query from terminal
sqlite3 data/watchlist.db "SELECT * FROM watchlist;"
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change `PORT` in `.env` or kill process on port 8000 |
| ModuleNotFoundError | Make sure venv is activated and packages installed |
| Claude API error | Check ANTHROPIC_API_KEY in `.env` |
| Prices not updating | Check watchlist has symbols, wait 5 min for next poll |
| Frontend can't connect | Verify backend running at localhost:8000 |

---

## 📈 System Status

```bash
# Check if backend is running
curl http://localhost:8000/health

# Response should be:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123456",
  "scheduler_running": true
}
```

---

## 🎯 First Steps

1. Create `.env` from `.env.example`
2. Add ANTHROPIC_API_KEY
3. Start backend: `python -m uvicorn app.main:app --reload`
4. Start frontend: `npm run dev`
5. Go to http://localhost:5173
6. Add 3 stocks to watchlist
7. Create 2 price alerts
8. Set your risk profile
9. Manually trigger analysis: POST `/analysis/{symbol}/refresh`
10. Check results back in 7 days!

---

## 📖 Full Documentation

- **Setup Guide**: `SETUP_GUIDE.md` (5-min guide)
- **Implementation**: `IMPLEMENTATION_GUIDE.md` (full API + features)
- **Architecture**: `docs/ARCHITECTURE.md` (system design + diagrams)
- **Summary**: `IMPLEMENTATION_SUMMARY.md` (what was built)

---

## 🚀 Production Checklist

- [ ] Environment variables configured
- [ ] API keys verified (Claude, optional: Telegram/Email)
- [ ] Database initialized (auto-created)
- [ ] Backend runs without errors
- [ ] Frontend builds successfully
- [ ] Added 3+ test stocks
- [ ] Created 2+ test alerts
- [ ] Verified price updates (wait 5 min)
- [ ] Tested notification delivery
- [ ] Monitored logs for 24 hours

Ready to deploy! 🎉

---

## 📞 Quick Help

```bash
# Backend logs show everything
# Frontend browser console shows UI errors
# Database location: ./data/watchlist.db
# API interactive docs: http://localhost:8000/docs
```

---

**Version**: 1.0  
**Last Updated**: September 4, 2026  
**Status**: Production Ready ✅
