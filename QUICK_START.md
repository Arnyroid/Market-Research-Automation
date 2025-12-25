# Quick Start Guide - BSE Stock Fetcher

## 🚀 Installation (5 minutes)

### Option 1: Automated Setup (Recommended)

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## 📊 Usage Examples

### 1. Test Run (Fetch Once)
```bash
# Top gainers/losers
python scheduler.py once

# Your custom stocks
python scheduler.py once --custom
```
**Output:** Fetches stock data and saves to CSV

### 2. Custom Stock List
```bash
# Edit custom_scrips.txt with your stocks
nano custom_scrips.txt

# Add your scrip codes:
# 500325  # Reliance
# 532540  # TCS
# 500180  # HDFC Bank

# Fetch your custom list
python scheduler.py once --custom
```
**Use Case:** Track your portfolio or watchlist

### 3. Continuous Monitoring (Every 30 minutes)
```bash
python scheduler.py interval 30
python scheduler.py interval 30 --custom  # With custom stocks
```
**Use Case:** Regular market monitoring during trading hours

### 4. Daily Update (9:30 AM)
```bash
python scheduler.py daily 09:30
python scheduler.py daily 09:30 --custom  # With custom stocks
```
**Use Case:** Get market opening data daily

### 5. Market Hours Only
```bash
python scheduler.py market
python scheduler.py market --custom  # With custom stocks
```
**Use Case:** Active trading hours monitoring (9:15 AM - 3:30 PM IST)

## 📁 Where to Find Your Data

- **Latest Data:** `data/bse_stocks_master.csv`
- **Historical Data:** `data/bse_stocks_YYYYMMDD_HHMMSS.csv`
- **Logs:** `logs/stock_fetcher.log`

## 📈 Sample Output

```csv
securityID,scrip_code,last_price,price_change,price_change_percent,category
RELIANCE,500325,1557.95,-12.95,-0.82,TOP_GAINER
TCS,532540,4234.50,45.30,1.08,TOP_GAINER
HDFCBANK,500180,1678.25,-8.50,-0.50,TOP_LOSER
```

## 🔧 Common Commands

```bash
# Check if it's working
python bse_fetcher.py

# Run comprehensive tests
python test_fetcher.py

# View logs
tail -f logs/stock_fetcher.log

# Check data
cat data/bse_stocks_master.csv
```

## ⚙️ Configuration

Edit `.env` file:
```bash
FETCH_INTERVAL_MINUTES=60    # How often to fetch
FETCH_TIME=09:30              # Daily fetch time
MAX_RETRIES=3                 # Retry attempts
```

## 🎯 What You Get

- **Real-time prices** from BSE
- **Top gainers** (5 stocks)
- **Top losers** (5 stocks)
- **Price changes** (absolute and percentage)
- **Timestamps** for each fetch
- **Automatic CSV storage**

## 💡 Pro Tips

1. **Best Interval:** 30-60 minutes (respects rate limits)
2. **Market Hours:** Data is most relevant during 9:15 AM - 3:30 PM IST
3. **Weekends:** BSE is closed, data won't update
4. **Holidays:** Check BSE holiday calendar

## 🐛 Quick Troubleshooting

**Problem:** No data fetched
```bash
# Solution 1: Check internet
ping bseindia.com

# Solution 2: Check logs
cat logs/stock_fetcher.log

# Solution 3: Test manually
python bse_fetcher.py
```

**Problem:** Import errors
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt
```

**Problem:** Permission denied
```bash
# Solution: Fix permissions
chmod -R 755 data logs
```

## 📚 Next Steps

1. ✅ Run `python scheduler.py once` to test
2. ✅ Check `data/bse_stocks_master.csv` for results
3. ✅ Set up continuous monitoring with your preferred mode
4. ✅ Integrate with your analysis tools (Excel, Python, etc.)

## 🔗 Integration Examples

### Load in Python
```python
import pandas as pd

# Read latest data
df = pd.read_csv('data/bse_stocks_master.csv')

# Analyze
print(f"Average price: ₹{df['last_price'].mean():.2f}")
print(f"Top gainer: {df.loc[df['price_change_percent'].idxmax(), 'securityID']}")
```

### Load in Excel
1. Open Excel
2. Data → From Text/CSV
3. Select `data/bse_stocks_master.csv`
4. Import and analyze

### Use in Scripts
```bash
# Get latest data in bash
cat data/bse_stocks_master.csv | grep "TOP_GAINER"

# Count stocks
wc -l data/bse_stocks_master.csv
```

## 🎉 You're All Set!

Your BSE stock fetcher is ready to use. Start with a test run and then set up continuous monitoring based on your needs.

For detailed documentation, see [README.md](README.md)