# Custom Scrips Guide

This guide explains how to fetch data for your own custom list of BSE stocks.

## 📋 Quick Start

### 1. Edit Custom Scrips File

Open `custom_scrips.txt` and add your scrip codes:

```text
# Your Custom Stocks
500325  # Reliance Industries
532540  # TCS
500180  # HDFC Bank
```

### 2. Run with Custom Scrips

```bash
# Fetch once
python scheduler.py once --custom

# Fetch every 30 minutes
python scheduler.py interval 30 --custom

# Fetch daily at 9:30 AM
python scheduler.py daily 09:30 --custom
```

## 🔍 Finding Scrip Codes

### Method 1: BSE Website
1. Go to https://www.bseindia.com/
2. Search for your stock
3. The scrip code is shown in the URL and stock details

### Method 2: Common Stocks Reference

**Blue Chip Stocks:**
- 500325 - Reliance Industries
- 500180 - HDFC Bank
- 532540 - TCS
- 500209 - Infosys
- 532174 - ICICI Bank

**IT Sector:**
- 507685 - Wipro
- 532281 - HCL Technologies
- 532755 - Tech Mahindra

**Banking:**
- 500112 - State Bank of India
- 532215 - Axis Bank
- 500034 - Bajaj Finance

**Auto:**
- 532500 - Maruti Suzuki
- 500570 - Tata Motors
- 532454 - Bharti Airtel

**Pharma:**
- 500124 - Dr Reddy's Labs
- 532321 - Cipla
- 500087 - Sun Pharma

## 📝 Custom Scrips File Format

```text
# Lines starting with # are comments
# Add one scrip code per line
# You can add comments after the code

500325  # Reliance - Oil & Gas
532540  # TCS - IT Services
500180  # HDFC Bank - Banking

# Group your stocks by sector
# IT Sector
507685  # Wipro
532281  # HCL Tech

# Banking Sector
500112  # SBI
532215  # Axis Bank
```

## 📊 What Data You Get

For each custom scrip, you'll get:

- **Company Name**: Full company name
- **Security ID**: BSE security identifier
- **Current Price**: Last traded price (₹)
- **Price Change**: Absolute change (₹)
- **Price Change %**: Percentage change
- **Open/High/Low**: Day's trading range
- **Previous Close**: Yesterday's closing price
- **Volume**: Trading volume
- **52-Week High/Low**: Year's price range
- **Market Cap**: Market capitalization
- **Industry**: Sector/industry classification
- **Group**: BSE group (A, B, etc.)

## 💾 Output Format

### CSV File Structure

```csv
scrip_code,security_id,company_name,last_price,price_change,price_change_percent,...
500325,RELIANCE,Reliance Industries Ltd,1557.95,-12.95,-0.82,...
532540,TCS,Tata Consultancy Services Ltd,3320.35,9.85,0.30,...
```

### Sample Output

```
✓ 500325: Reliance Industries Ltd - ₹1557.95
✓ 532540: Tata Consultancy Services Ltd - ₹3320.35
✓ 500180: HDFC Bank Ltd - ₹997.10
```

## 🎯 Use Cases

### Portfolio Tracking
Track your investment portfolio:
```text
# My Portfolio
500325  # Reliance - 10 shares
532540  # TCS - 5 shares
500180  # HDFC Bank - 20 shares
```

### Sector Analysis
Monitor specific sectors:
```text
# IT Sector Watch
532540  # TCS
500209  # Infosys
507685  # Wipro
532281  # HCL Tech
532755  # Tech Mahindra
```

### Watchlist
Keep track of stocks you're interested in:
```text
# Stocks to Watch
500325  # Reliance - considering buy
532500  # Maruti - price target ₹17000
500112  # SBI - dividend play
```

## ⚙️ Advanced Usage

### Python Script

```python
from bse_fetcher import BSEStockFetcher

fetcher = BSEStockFetcher()

# Fetch specific scrips
scrips = ['500325', '532540', '500180']
df = fetcher.fetch_custom_scrips(scrips)

# Or load from file
df = fetcher.fetch_custom_scrips()

# Analyze
print(f"Average price: ₹{df['last_price'].mean():.2f}")
print(f"Top performer: {df.loc[df['price_change_percent'].idxmax(), 'company_name']}")
```

### Scheduled Monitoring

```bash
# Monitor your portfolio every hour during market hours
python scheduler.py market --custom

# Daily update at market open
python scheduler.py daily 09:15 --custom

# Frequent updates every 15 minutes
python scheduler.py interval 15 --custom
```

## 📈 Data Analysis Examples

### Load and Analyze in Python

```python
import pandas as pd

# Read latest data
df = pd.read_csv('data/bse_stocks_master.csv')

# Filter by sector
it_stocks = df[df['industry'].str.contains('Information Technology', na=False)]
print(f"IT Stocks Average: ₹{it_stocks['last_price'].mean():.2f}")

# Find gainers
gainers = df[df['price_change_percent'] > 0]
print(f"Gainers: {len(gainers)}")

# Calculate portfolio value (if you have quantities)
portfolio = {
    '500325': 10,  # 10 shares of Reliance
    '532540': 5,   # 5 shares of TCS
}

total_value = sum(
    df[df['scrip_code'] == code]['last_price'].values[0] * qty
    for code, qty in portfolio.items()
)
print(f"Portfolio Value: ₹{total_value:,.2f}")
```

### Excel Analysis

1. Open `data/bse_stocks_master.csv` in Excel
2. Create pivot tables by industry
3. Add conditional formatting for price changes
4. Create charts for visualization

## 🔄 Automation Tips

### 1. Regular Updates
```bash
# Add to crontab (Linux/Mac)
0 9,12,15 * * * cd /path/to/project && python scheduler.py once --custom
```

### 2. Email Alerts
Combine with email scripts to get alerts:
```python
# Check for significant changes
df = pd.read_csv('data/bse_stocks_master.csv')
big_movers = df[abs(df['price_change_percent']) > 5]

if not big_movers.empty:
    # Send email alert
    send_email(f"Big movers: {big_movers['company_name'].tolist()}")
```

### 3. Price Alerts
Set up price targets:
```python
targets = {
    '500325': 1600,  # Alert if Reliance > 1600
    '532540': 3500,  # Alert if TCS > 3500
}

df = pd.read_csv('data/bse_stocks_master.csv')
for code, target in targets.items():
    price = df[df['scrip_code'] == code]['last_price'].values[0]
    if price > target:
        print(f"🎯 Target reached: {code} at ₹{price}")
```

## ⚠️ Important Notes

1. **Rate Limiting**: The system adds 0.5s delay between each scrip to respect BSE rate limits
2. **Market Hours**: Data is most accurate during market hours (9:15 AM - 3:30 PM IST)
3. **Holidays**: BSE is closed on weekends and holidays
4. **Scrip Validation**: Invalid scrip codes will be logged as failed
5. **File Format**: Use plain text, one scrip per line

## 🐛 Troubleshooting

### Scrip Not Found
```
✗ Failed to fetch: 123456
```
**Solution**: Verify the scrip code on BSE website

### Slow Fetching
**Reason**: Each scrip takes ~0.5s to fetch (rate limiting)
**Solution**: For 20 scrips, expect ~10 seconds total

### No Data During Off-Hours
**Reason**: BSE updates prices only during market hours
**Solution**: Schedule fetches during 9:15 AM - 3:30 PM IST

## 📚 Resources

- BSE Website: https://www.bseindia.com/
- Stock Search: https://www.bseindia.com/stock-share-price/
- Market Timings: 9:15 AM - 3:30 PM IST (Mon-Fri)
- BSE Holidays: Check BSE holiday calendar

## 🎉 Examples

See `custom_scrips.txt` for a pre-configured list of popular stocks across different sectors!