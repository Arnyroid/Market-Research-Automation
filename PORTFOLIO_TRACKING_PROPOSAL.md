# Portfolio Tracking System - Architecture Proposal

## 📊 Your Requirements

You have:
- Trade history (Date, Script, Quantity, Average Price, Buy/Sell)
- Need to compare purchase price vs current market price
- Want automated tracking and analysis

## 🎯 Recommended Approach: **Hybrid System**

### Phase 1: Start with SQLite (Best Choice)
**Why SQLite?**
- ✅ No separate server needed (file-based)
- ✅ Full SQL capabilities
- ✅ Easy to migrate to MySQL later
- ✅ Built into Python
- ✅ Can still export to Excel
- ✅ Perfect for single-user applications

### Phase 2: Optional MySQL Migration
**When to migrate:**
- Multiple users need access
- Web dashboard required
- Very large data (100k+ trades)

## 🏗️ Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Trade Data                       │
│              (Excel/CSV - Import Once)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  SQLite Database                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   trades     │  │  portfolio   │  │ price_history│  │
│  │              │  │              │  │              │  │
│  │ - date       │  │ - scrip_code │  │ - scrip_code │  │
│  │ - scrip_code │  │ - quantity   │  │ - date       │  │
│  │ - quantity   │  │ - avg_price  │  │ - price      │  │
│  │ - price      │  │ - current_val│  │ - source     │  │
│  │ - type       │  │ - profit_loss│  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              BSE Data Fetcher (Existing)                 │
│         Fetches current prices automatically             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Portfolio Analyzer                          │
│  - Calculate P&L for each stock                          │
│  - Overall portfolio performance                         │
│  - Generate reports (Excel/PDF)                          │
│  - Send alerts for significant changes                   │
└─────────────────────────────────────────────────────────┘
```

## 📋 Database Schema

### Table 1: `trades`
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date DATE NOT NULL,
    scrip_code VARCHAR(10) NOT NULL,
    scrip_name VARCHAR(100),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    trade_type VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    total_value DECIMAL(15, 2),
    brokerage DECIMAL(10, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table 2: `portfolio` (Current Holdings)
```sql
CREATE TABLE portfolio (
    scrip_code VARCHAR(10) PRIMARY KEY,
    scrip_name VARCHAR(100),
    total_quantity INTEGER NOT NULL,
    avg_buy_price DECIMAL(10, 2) NOT NULL,
    total_invested DECIMAL(15, 2) NOT NULL,
    current_price DECIMAL(10, 2),
    current_value DECIMAL(15, 2),
    profit_loss DECIMAL(15, 2),
    profit_loss_percent DECIMAL(10, 2),
    last_updated TIMESTAMP
);
```

### Table 3: `price_history`
```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scrip_code VARCHAR(10) NOT NULL,
    price_date DATE NOT NULL,
    open_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    close_price DECIMAL(10, 2),
    volume INTEGER,
    source VARCHAR(20),
    UNIQUE(scrip_code, price_date)
);
```

## 🚀 Implementation Plan

### Step 1: Import Your Trade Data
```python
# Import from Excel/CSV
import pandas as pd
import sqlite3

# Read your trade sheet
df = pd.read_excel('my_trades.xlsx')

# Connect to database
conn = sqlite3.connect('portfolio.db')

# Import trades
df.to_sql('trades', conn, if_exists='append', index=False)
```

### Step 2: Calculate Current Portfolio
```python
# Aggregate trades to get current holdings
portfolio = calculate_portfolio_from_trades(trades)
# Updates portfolio table with current holdings
```

### Step 3: Fetch Current Prices
```python
# Use existing BSE fetcher
from bse_fetcher import BSEStockFetcher

fetcher = BSEStockFetcher()
# Fetch prices for all portfolio stocks
# Update portfolio table with current prices
```

### Step 4: Calculate P&L
```python
# For each stock:
# P&L = (Current Price - Avg Buy Price) × Quantity
# P&L % = (P&L / Total Invested) × 100
```

## 💡 Features You'll Get

### 1. Portfolio Dashboard
```
╔════════════════════════════════════════════════════════╗
║           YOUR PORTFOLIO SUMMARY                       ║
╠════════════════════════════════════════════════════════╣
║ Total Invested:     ₹5,00,000                          ║
║ Current Value:      ₹5,75,000                          ║
║ Total P&L:          ₹75,000 (15.00%)                   ║
║ Today's Change:     ₹2,500 (0.43%)                     ║
╚════════════════════════════════════════════════════════╝

Top Performers:
1. TCS         +25.5%  ₹15,000
2. Reliance    +18.2%  ₹12,000
3. HDFC Bank   +12.8%  ₹8,500

Underperformers:
1. Stock X     -8.5%   -₹3,200
2. Stock Y     -5.2%   -₹1,800
```

### 2. Individual Stock Analysis
```
RELIANCE (500325)
─────────────────────────────────────────
Quantity:           100 shares
Avg Buy Price:      ₹1,450.00
Total Invested:     ₹1,45,000
Current Price:      ₹1,557.95
Current Value:      ₹1,55,795
Profit/Loss:        ₹10,795 (7.44%)
Last Updated:       25 Dec 2025, 4:00 PM
```

### 3. Trade History
```
Recent Trades:
Date        Script    Type  Qty   Price      Total
──────────────────────────────────────────────────
24-Dec-25   TCS       BUY   10    ₹3,320    ₹33,200
20-Dec-25   INFY      SELL  5     ₹1,662    ₹8,310
15-Dec-25   RELIANCE  BUY   20    ₹1,450    ₹29,000
```

### 4. Automated Reports
- Daily P&L summary email
- Weekly performance report
- Monthly Excel export
- Tax calculation (FIFO/LIFO)

## 📊 Comparison: SQLite vs MySQL vs Excel

| Feature | SQLite | MySQL | Excel |
|---------|--------|-------|-------|
| Setup | ✅ Easy | ⚠️ Complex | ✅ Easy |
| Performance | ✅ Fast | ✅ Very Fast | ❌ Slow (large data) |
| Multi-user | ❌ No | ✅ Yes | ⚠️ Limited |
| Queries | ✅ Full SQL | ✅ Full SQL | ⚠️ Limited |
| Automation | ✅ Easy | ✅ Easy | ⚠️ Difficult |
| Backup | ✅ Copy file | ⚠️ Dump needed | ✅ Copy file |
| Cost | ✅ Free | ✅ Free | 💰 License |
| Migration | ✅ Easy to MySQL | N/A | ⚠️ Difficult |

## 🎯 My Recommendation

### Start with SQLite because:

1. **No Setup Required** - Just a file, no server
2. **Full SQL Power** - Complex queries, joins, aggregations
3. **Easy Integration** - Works seamlessly with Python
4. **Excel Export** - Can generate Excel reports anytime
5. **Future-Proof** - Easy to migrate to MySQL if needed

### Keep Excel for:
- Initial data import
- Report generation
- Manual analysis
- Sharing with others

## 🛠️ What I'll Build for You

### Core Modules:

1. **`portfolio_db.py`** - Database setup and management
2. **`trade_importer.py`** - Import trades from Excel/CSV
3. **`portfolio_analyzer.py`** - Calculate P&L, performance
4. **`price_updater.py`** - Fetch and update current prices
5. **`report_generator.py`** - Generate Excel/PDF reports
6. **`portfolio_dashboard.py`** - CLI dashboard (optional: Web UI)

### Integration with Existing System:
- Use existing `bse_fetcher.py` for price updates
- Use existing `scheduler.py` for automation
- Add portfolio-specific scheduling

## 📈 Sample Workflow

```bash
# One-time setup
python setup_portfolio.py

# Import your trades
python trade_importer.py --file my_trades.xlsx

# Update current prices
python price_updater.py

# View portfolio
python portfolio_dashboard.py

# Generate report
python report_generator.py --format excel

# Automate (add to scheduler)
python scheduler.py portfolio --interval 60
```

## 🎁 Bonus Features

1. **Tax Calculation** - FIFO/LIFO for capital gains
2. **Dividend Tracking** - Record and track dividends
3. **Alerts** - Price targets, stop-loss notifications
4. **Benchmarking** - Compare with Sensex/Nifty
5. **Sector Analysis** - Performance by sector
6. **Risk Metrics** - Portfolio volatility, beta

## 🚦 Next Steps

Would you like me to:
1. ✅ **Build the SQLite-based portfolio system** (Recommended)
2. ⚠️ Build MySQL-based system (if you need multi-user)
3. 📊 Build Excel-only solution (simpler but limited)

I recommend **Option 1** - it gives you the best of both worlds!

Let me know and I'll start building the portfolio tracking system! 🚀