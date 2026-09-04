# Portfolio Tracking System - Usage Guide

## Overview
Complete guide to using the Portfolio Tracking System for managing your BSE stock investments.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Importing Trades](#importing-trades)
3. [Updating Prices](#updating-prices)
4. [Viewing Portfolio Data](#viewing-portfolio-data)
5. [Database Management](#database-management)
6. [Advanced Features](#advanced-features)

---

## Quick Start

### 1. Setup (First Time Only)
```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### 2. Import Your Trades
```bash
# Create a trades file (Excel or CSV)
python trade_importer.py --template trades_template.xlsx

# Edit the template with your trades, then import
python trade_importer.py --file trades.xlsx
```

### 3. Update Current Prices
```bash
# Update prices for all stocks in portfolio
python price_updater.py --all
```

### 4. View Your Portfolio
```bash
# View complete dashboard
python portfolio_dashboard.py --all
```

---

## Importing Trades

### Creating Trade File

**Option 1: Generate Template**
```bash
python trade_importer.py --template my_trades.xlsx
```

This creates a template with columns:
- `trade_date`: Date of trade (YYYY-MM-DD)
- `scrip_code`: BSE scrip code (e.g., 500325)
- `scrip_name`: Company name (e.g., Reliance Industries Ltd)
- `quantity`: Number of shares
- `price`: Price per share
- `trade_type`: BUY or SELL

**Option 2: Use Your Own Format**
You can use your own Excel/CSV file with custom column names. The importer will ask you to map your columns to the required fields.

### Import Examples

**Basic Import:**
```bash
python trade_importer.py --file trades.xlsx
```

**Import with Custom Column Mapping:**
```bash
python trade_importer.py --file my_trades.csv
```
The system will prompt you to map columns like:
```
Available columns: Date, Stock Code, Company, Shares, Rate, Type
Map 'trade_date' to: Date
Map 'scrip_code' to: Stock Code
...
```

**Import from CSV:**
```bash
python trade_importer.py --file trades.csv
```

### Trade File Format

**Excel/CSV Structure:**
```
trade_date  | scrip_code | scrip_name              | quantity | price   | trade_type
2025-01-15  | 500325     | Reliance Industries Ltd | 10       | 1450.00 | BUY
2025-01-20  | 532540     | TCS Ltd                 | 5        | 3320.00 | BUY
2025-02-10  | 500180     | HDFC Bank Ltd           | 20       | 997.00  | BUY
```

**Important Notes:**
- Date format: YYYY-MM-DD (e.g., 2025-01-15)
- Trade type: Must be either "BUY" or "SELL"
- Scrip code: BSE scrip code (6 digits)
- Price: Per share price (decimals allowed)
- Quantity: Number of shares (whole numbers)

---

## Updating Prices

### Update All Portfolio Stocks
```bash
python price_updater.py --all
```
This fetches current prices for all stocks in your portfolio from BSE.

### Update Specific Stock
```bash
python price_updater.py --scrip 500325
```

### Scheduling Automatic Updates

**Update during market hours (9:15 AM - 3:30 PM):**
```bash
# Add to crontab (Linux/Mac)
*/15 9-15 * * 1-5 cd /path/to/project && venv/bin/python price_updater.py --all
```

**Update once daily after market close:**
```bash
# Add to crontab (Linux/Mac)
0 16 * * 1-5 cd /path/to/project && venv/bin/python price_updater.py --all
```

---

## Viewing Portfolio Data

### Complete Dashboard
```bash
python portfolio_dashboard.py --all
```
Shows:
- Portfolio summary (total invested, current value, P&L)
- Performance breakdown (gainers, losers)
- Best and worst performers
- Current holdings with individual P&L
- Recent trades

**Sample Output:**
```
📊 PORTFOLIO SUMMARY
Total Stocks   | 3
Total Invested | ₹65,710.00
Current Value  | ₹67,427.00
Total P&L      | ₹1,717.00
P&L %          | 2.61%

💼 CURRENT HOLDINGS
Code   | Name                    | Qty | Avg Price | Current | P&L      | P&L %
500325 | Reliance Industries Ltd | 20  | ₹1,455.00 | ₹1,559.00 | ₹2,080.00 | 7.15%
...
```

### View Only Summary
```bash
python portfolio_dashboard.py --summary
```

### View Only Holdings
```bash
python portfolio_dashboard.py --holdings
# or
python portfolio_dashboard.py -H
```

### View Recent Trades
```bash
python portfolio_dashboard.py --trades
```

### Analyze Specific Stock
```bash
python portfolio_dashboard.py --stock 500325
```
Shows detailed analysis:
- Trading activity (total trades, buy/sell count)
- Current position (quantity, avg price, P&L)
- Realized and unrealized P&L
- First and last trade dates

---

## Database Management

### Database Location
```
data/portfolio.db
```

### Database Tables

**1. trades** - All buy/sell transactions
```sql
- id: Auto-increment primary key
- trade_date: Date of transaction
- scrip_code: BSE scrip code
- scrip_name: Company name
- quantity: Number of shares
- price: Price per share
- trade_type: BUY or SELL
- created_at: Record creation timestamp
```

**2. portfolio** - Current holdings
```sql
- scrip_code: BSE scrip code (primary key)
- scrip_name: Company name
- quantity: Current holding quantity
- avg_price: Average purchase price
- total_invested: Total amount invested
- current_price: Latest market price
- current_value: Current market value
- unrealized_pnl: Profit/Loss on holdings
- last_updated: Last price update timestamp
```

**3. price_history** - Historical price data
```sql
- id: Auto-increment primary key
- scrip_code: BSE scrip code
- price: Stock price
- timestamp: Price fetch time
```

### Direct Database Access

**Using SQLite CLI:**
```bash
sqlite3 data/portfolio.db

# View all trades
SELECT * FROM trades ORDER BY trade_date DESC;

# View portfolio
SELECT * FROM portfolio;

# View price history
SELECT * FROM price_history ORDER BY timestamp DESC LIMIT 10;
```

**Using Python:**
```python
from portfolio_db import PortfolioDB

db = PortfolioDB()
trades = db.get_all_trades()
portfolio = db.get_portfolio()
```

---

## Advanced Features

### Portfolio Analysis

**Calculate Holdings with FIFO:**
```python
from portfolio_analyzer import PortfolioAnalyzer

analyzer = PortfolioAnalyzer()
holdings = analyzer.calculate_holdings_from_trades()
```

**Get Performance Metrics:**
```python
performance = analyzer.get_portfolio_performance()
print(f"Total P&L: {performance['total_pnl']}")
print(f"P&L %: {performance['total_pnl_percentage']}")
```

**Analyze Specific Stock:**
```python
analysis = analyzer.get_stock_analysis('500325')
print(f"Unrealized P&L: {analysis['unrealized_pnl']}")
```

### Custom Queries

**Find Top Gainers:**
```python
from portfolio_db import PortfolioDB

db = PortfolioDB()
portfolio = db.get_portfolio()
gainers = [s for s in portfolio if s['unrealized_pnl'] > 0]
gainers.sort(key=lambda x: x['unrealized_pnl_percentage'], reverse=True)
```

**Calculate Total Investment:**
```python
total = sum(s['total_invested'] for s in portfolio)
```

### Backup and Restore

**Backup Database:**
```bash
cp data/portfolio.db data/portfolio_backup_$(date +%Y%m%d).db
```

**Restore from Backup:**
```bash
cp data/portfolio_backup_20250127.db data/portfolio.db
```

---

## Common Workflows

### Daily Workflow
```bash
# 1. Update prices (after market close)
python price_updater.py --all

# 2. View portfolio
python portfolio_dashboard.py --all
```

### Adding New Trades
```bash
# 1. Add trades to Excel file
# 2. Import trades
python trade_importer.py --file new_trades.xlsx

# 3. Update prices
python price_updater.py --all

# 4. View updated portfolio
python portfolio_dashboard.py --all
```

### Monthly Review
```bash
# 1. Update all prices
python price_updater.py --all

# 2. View complete dashboard
python portfolio_dashboard.py --all

# 3. Analyze each stock
python portfolio_dashboard.py --stock 500325
python portfolio_dashboard.py --stock 500180
python portfolio_dashboard.py --stock 532540

# 4. Backup database
cp data/portfolio.db data/portfolio_backup_$(date +%Y%m%d).db
```

---

## Troubleshooting

### Issue: Import fails with "Column not found"
**Solution:** Use the column mapping feature or generate a template:
```bash
python trade_importer.py --template trades_template.xlsx
```

### Issue: Prices not updating
**Solution:** Check internet connection and BSE website availability:
```bash
python price_updater.py --scrip 500325
```

### Issue: Database locked
**Solution:** Close any other programs accessing the database:
```bash
# Check for processes
lsof data/portfolio.db

# Kill if necessary
kill -9 <PID>
```

### Issue: Wrong P&L calculation
**Solution:** Ensure all trades are imported correctly:
```bash
# View all trades
python portfolio_dashboard.py --trades

# Re-import if needed
python trade_importer.py --file trades.xlsx
```

---

## Tips and Best Practices

1. **Regular Price Updates**: Update prices at least once daily during trading days
2. **Backup Regularly**: Backup your database weekly or before major changes
3. **Verify Imports**: Always check the import summary after importing trades
4. **Use Templates**: Generate templates to ensure correct format
5. **Monitor Performance**: Review your portfolio dashboard regularly
6. **Keep Trade Records**: Maintain your original trade files as backup

---

## Next Steps

- [ ] Set up automated price updates (cron job)
- [ ] Create monthly backup routine
- [ ] Explore report generation features (coming soon)
- [ ] Optimize database for large portfolios (see SCHEMA_OPTIMIZATION.md)

---

## Support

For issues or questions:
1. Check this guide
2. Review SCHEMA_OPTIMIZATION.md for performance tips
3. Check README.md for system overview
4. Review code comments in individual modules

---

**Last Updated:** 2025-12-27
**Version:** 1.0