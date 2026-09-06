# Market Research Automation - BSE Stock Data Fetcher & Portfolio Tracker

Comprehensive system to fetch BSE (Bombay Stock Exchange) stock data and track your investment portfolio with automated price updates, P&L calculations, and detailed analytics.

## 🌟 Features

### Stock Data Fetching
- 🔄 **Automated Fetching**: Fetch BSE stock data at configurable intervals
- 📊 **Real-time Data**: Uses official `bsedata` library for accurate, real-time stock prices
- 💰 **Price Tracking**: Get current prices, changes, and percentage movements
- 📋 **Custom Stock Lists**: Track your own portfolio or watchlist of stocks
- ⏰ **Flexible Scheduling**: Run once, at intervals, daily, or during market hours
- 💾 **Data Storage**: Saves data to CSV files with timestamps
- 🔁 **Retry Logic**: Automatic retry on failures with configurable attempts
- 📝 **Comprehensive Logging**: Detailed logs for monitoring and debugging

### Portfolio Management
- ⚡ **Quick Command Line Entry**: Add trades instantly without creating files
- 📈 **Trade Tracking**: Import and track all your BUY/SELL transactions
- 💼 **Portfolio Analytics**: Real-time portfolio valuation and performance metrics
- 📊 **P&L Calculation**: Automatic profit/loss calculation using FIFO method
- 🎯 **Realized vs Unrealized**: Separate tracking of realized and unrealized gains
- 📱 **Interactive Dashboard**: CLI dashboard with multiple viewing options
- 🔄 **Automatic Price Updates**: Fetch live prices for all portfolio stocks
- 📁 **Excel/CSV Import**: Easy trade import from Excel or CSV files (bulk import)
- 🗄️ **SQLite Database**: Efficient local storage with full transaction history

## 📁 Project Structure

```
Market-Research-Automation/
├── README.md                   # This file
├── .env.example                # Environment variables template
├── setup.bat / setup.sh        # One-click setup scripts
├── start.bat                   # One-click start script
│
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── routers/            # API endpoints
│   │   ├── services/           # Business logic
│   │   └── jobs/               # Background jobs
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── pages/              # React pages
│   │   ├── api/                # API client
│   │   └── hooks/              # Custom hooks
│   └── package.json
│
├── src/                        # Standalone Python module (legacy)
│   ├── config.py               # Module configuration
│   ├── bse_fetcher.py          # BSE data fetching
│   ├── portfolio_db.py         # SQLite database management
│   ├── portfolio_analyzer.py   # P&L calculations
│   └── ...
│
├── scripts/                    # Utility scripts
│   ├── add_trade.py            # Quick command-line trade entry
│   ├── report_generator.py     # Report generation
│   └── ...
│
├── docs/                       # All documentation
│   ├── QUICK_START.md
│   ├── SETUP_GUIDE.md
│   ├── ARCHITECTURE.md
│   └── *.md
│
├── data/                       # Stock data CSV files & portfolio.db
├── logs/                       # Application logs
└── tests/                      # Test suite
```

## 🚀 Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Market-Research-Automation
```

2. **Create virtual environment** (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment** (optional)
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## 📖 Quick Start

### Stock Data Fetching

```bash
# Fetch stock data once
python scheduler.py once

# Fetch your custom stock list
python scheduler.py once --custom

# Run every 30 minutes
python scheduler.py interval 30

# Run during market hours
python scheduler.py market
```

### Portfolio Management

#### Method 1: Quick Command Line Entry (Fastest) ⚡

```bash
# Add a BUY trade instantly (no file needed!)
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00

# Add a SELL trade
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL

# Interactive mode (guided entry)
python add_trade.py --interactive

# Update prices and view portfolio
python price_updater.py --all
python portfolio_dashboard.py --all
```

📖 **See [COMMAND_LINE_TRADE_ENTRY.md](COMMAND_LINE_TRADE_ENTRY.md) for complete guide**

#### Method 2: Bulk Import from Excel/CSV

```bash
# 1. Generate template
python trade_importer.py --template trades.xlsx

# 2. Edit trades.xlsx with your transactions

# 3. Import trades
python trade_importer.py --file trades.xlsx

# 4. Update prices and view
python price_updater.py --all
python portfolio_dashboard.py --all
```

📖 **See [BUY_TRANSACTION_GUIDE.md](BUY_TRANSACTION_GUIDE.md) for detailed instructions**

## 📊 Portfolio Management Features

### 1. Add Trades (Two Methods)

#### Method A: Quick Command Line Entry ⚡ (Recommended for Daily Use)

**Add BUY trade instantly:**
```bash
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
```

**Add SELL trade:**
```bash
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL
```

**Interactive mode (guided):**
```bash
python add_trade.py --interactive
```

**With specific date:**
```bash
python add_trade.py -d 2025-01-15 -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
```

**Common scrip codes:**
- `500325` - Reliance Industries Ltd
- `532540` - TCS Ltd
- `500180` - HDFC Bank Ltd
- `500112` - State Bank of India
- `500209` - Infosys Ltd

📖 **See [COMMAND_LINE_TRADE_ENTRY.md](COMMAND_LINE_TRADE_ENTRY.md) for complete guide**

#### Method B: Bulk Import from Excel/CSV (For Multiple Trades)

**Generate Template:**
```bash
python trade_importer.py --template my_trades.xlsx
```

**Import from Excel/CSV:**
```bash
python trade_importer.py --file trades.xlsx
python trade_importer.py --file trades.csv
```

**Trade File Format:**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
2025-01-20,532540,TCS Ltd,5,3320.00,BUY
2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL
```

📖 **See [BUY_TRANSACTION_GUIDE.md](BUY_TRANSACTION_GUIDE.md) for detailed instructions**

### 2. Update Prices

**Update all portfolio stocks:**
```bash
python price_updater.py --all
```

**Update specific stock:**
```bash
python price_updater.py --scrip 500325
```

### 3. View Portfolio Dashboard

**Complete dashboard:**
```bash
python portfolio_dashboard.py --all
```

**Output includes:**
- Portfolio summary (total invested, current value, P&L)
- Performance breakdown (gainers, losers)
- Best and worst performers
- Current holdings with individual P&L
- Recent trades history

**View specific sections:**
```bash
# Summary only
python portfolio_dashboard.py --summary

# Holdings only
python portfolio_dashboard.py --holdings

# Recent trades
python portfolio_dashboard.py --trades

# Analyze specific stock
python portfolio_dashboard.py --stock 500325
```

### 4. Recording SELL Transactions

#### Quick Method (Command Line):
```bash
# Sell shares instantly
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL

# View changes
python portfolio_dashboard.py --all
```

#### Bulk Method (CSV Import):
Create a CSV file with your sale:
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL
```

Import and view changes:
```bash
python trade_importer.py --file sell.csv
python portfolio_dashboard.py --all
```

The system automatically:
- Calculates realized P&L using FIFO method
- Updates holdings quantity
- Tracks both realized and unrealized gains
- Shows complete transaction history

📖 **See [SELL_TRANSACTION_GUIDE.md](SELL_TRANSACTION_GUIDE.md) for detailed guide**

## 📈 Portfolio Dashboard Example

```
📊 PORTFOLIO SUMMARY
+----------------+------------+
| Total Stocks   | 3          |
| Total Invested | ₹65,710.00 |
| Current Value  | ₹67,427.00 |
| Total P&L      | ₹1,717.00  |
| P&L %          | 2.61%      |
| Realized P&L   | ₹750.00    |
+----------------+------------+

💼 CURRENT HOLDINGS
Code   | Name                    | Qty | Avg Price | Current   | Value      | P&L       | P&L %
500325 | Reliance Industries Ltd | 15  | ₹1,455.00 | ₹1,559.00 | ₹23,385.00 | ₹1,560.00 | 6.67%
500180 | HDFC Bank Ltd           | 20  | ₹999.00   | ₹992.40   | ₹19,848.00 | ₹-132.00  | -0.66%
532540 | TCS Ltd                 | 5   | ₹3,326.00 | ₹3,279.80 | ₹16,399.00 | ₹-231.00  | -1.39%
```

## 🔧 Stock Data Fetching Usage

### Quick Start - Run Once

```bash
# Fetch top gainers/losers
python scheduler.py once

# Fetch your custom stock list
python scheduler.py once --custom
```

### Custom Stock Lists

Track your own portfolio or watchlist:

1. **Edit `custom_scrips.txt`** with your stock codes:
```text
500325  # Reliance Industries
532540  # TCS
500180  # HDFC Bank
```

2. **Run with `--custom` flag**:
```bash
python scheduler.py once --custom
python scheduler.py interval 30 --custom
```

📖 **See [CUSTOM_SCRIPS_GUIDE.md](CUSTOM_SCRIPS_GUIDE.md) for detailed instructions**

### Scheduled Modes

#### 1. Interval Mode (Default)
```bash
# Run every 60 minutes (default)
python scheduler.py interval

# Run every 30 minutes
python scheduler.py interval 30

# With custom scrips
python scheduler.py interval 30 --custom
```

#### 2. Daily Mode
```bash
# Run daily at 9:30 AM (default)
python scheduler.py daily

# Run daily at 2:00 PM
python scheduler.py daily 14:00

# With custom scrips
python scheduler.py daily 09:30 --custom
```

#### 3. Market Hours Mode
```bash
python scheduler.py market

# With custom scrips
python scheduler.py market --custom
```

Runs at: 9:15 AM, 10:00 AM, 11:00 AM, 12:00 PM, 1:00 PM, 2:00 PM, 3:00 PM, 3:30 PM (IST)

### Using as a Module

```python
from bse_fetcher import BSEStockFetcher

# Create fetcher instance
fetcher = BSEStockFetcher()

# Fetch stocks with current prices
df = fetcher.fetch_stocks(include_prices=True)

if df is not None:
    print(f"Fetched {len(df)} stocks")
    print(f"Average price: ₹{df['last_price'].mean():.2f}")
    
    # Save to CSV
    fetcher.save_to_csv(df)
    
    # Get statistics
    stats = fetcher.get_stock_count()
    print(stats)

# Fetch individual stock quote
quote = fetcher.fetch_stock_quote("500325")  # Reliance
if quote:
    print(f"Reliance: ₹{quote['currentValue']}")
```

## ⚙️ Configuration

Edit `.env` file or modify `config.py` directly:

| Variable | Default | Description |
|----------|---------|-------------|
| `FETCH_INTERVAL_MINUTES` | 60 | Minutes between fetches in interval mode |
| `FETCH_TIME` | 09:30 | Time for daily fetch (HH:MM format, IST) |
| `MAX_RETRIES` | 3 | Maximum retry attempts on failure |
| `RETRY_DELAY_SECONDS` | 5 | Seconds to wait between retries |

## 💾 Data Storage

### Stock Data (CSV Files)

1. **Timestamped files**: `data/bse_stocks_YYYYMMDD_HHMMSS.csv`
   - Historical record of each fetch
   
2. **Master file**: `data/bse_stocks_master.csv`
   - Always contains the latest data
   - Overwritten on each successful fetch

**Data Columns:**
- `securityID`: Security identifier (e.g., RELIANCE, TCS)
- `scrip_code`: BSE scrip code (e.g., 500325)
- `last_price`: Current trading price (₹)
- `price_change`: Absolute price change (₹)
- `price_change_percent`: Percentage price change (%)
- `category`: Stock category (TOP_GAINER, TOP_LOSER, etc.)
- `timestamp`: Fetch timestamp (ISO 8601)
- `source`: Data source (BSEDATA_LIBRARY)

### Portfolio Database (SQLite)

**Location:** `data/portfolio.db`

**Tables:**
1. **trades** - All buy/sell transactions
2. **portfolio** - Current holdings with P&L
3. **price_history** - Historical price data

**Direct Access:**
```bash
sqlite3 data/portfolio.db
SELECT * FROM portfolio;
SELECT * FROM trades ORDER BY trade_date DESC;
```

## 📝 Logging

Logs are stored in `logs/stock_fetcher.log` with:
- Daily rotation
- 30-day retention
- Detailed information about each operation
- Error tracking and debugging information

## 🔄 Running as a Background Service

### Linux/Mac (using systemd)

1. Create service file `/etc/systemd/system/bse-fetcher.service`:
```ini
[Unit]
Description=BSE Stock Data Fetcher
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/Market-Research-Automation
ExecStart=/path/to/venv/bin/python scheduler.py interval 60
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable bse-fetcher
sudo systemctl start bse-fetcher
sudo systemctl status bse-fetcher
```

### Windows (using Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., "At startup")
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `scheduler.py interval 60`
   - Start in: `C:\path\to\Market-Research-Automation`

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "scheduler.py", "interval", "60"]
```

Build and run:
```bash
docker build -t bse-fetcher .
docker run -d --name bse-fetcher -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs bse-fetcher
```

## 🔍 Troubleshooting

### Stock Data Fetching

**No data fetched:**
- Check internet connection
- Verify BSE website is accessible (bseindia.com)
- Check logs in `logs/stock_fetcher.log`
- Try running once: `python scheduler.py once`
- The bsedata library may have rate limits - use intervals of 30+ minutes

**Import errors:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Specifically install bsedata: `pip install bsedata`
- Activate virtual environment if using one

**Permission errors:**
- Ensure write permissions for `data/` and `logs/` directories
- Run: `chmod -R 755 data logs` (Linux/Mac)

### Portfolio Management

**Trade import fails:**
- Check CSV/Excel file format
- Use template: `python trade_importer.py --template trades.xlsx`
- Verify column names match requirements
- Check date format (YYYY-MM-DD)

**Wrong P&L calculation:**
- Verify all trades are imported correctly
- Check trade dates are in correct order
- System uses FIFO method for cost basis
- View detailed analysis: `python portfolio_dashboard.py --stock <code>`

**Prices not updating:**
- Check internet connection
- Verify BSE website is accessible
- Try updating single stock: `python price_updater.py --scrip 500325`
- Check if market is open (9:15 AM - 3:30 PM IST)

**Database locked:**
- Close any other programs accessing the database
- Check for processes: `lsof data/portfolio.db`
- Restart the application

## 📚 Documentation

Comprehensive guides available in the [`docs/`](docs/) folder:

- **[docs/PORTFOLIO_USAGE_GUIDE.md](docs/PORTFOLIO_USAGE_GUIDE.md)** - Complete portfolio management guide
- **[docs/SELL_TRANSACTION_GUIDE.md](docs/SELL_TRANSACTION_GUIDE.md)** - How to record SELL transactions
- **[docs/CUSTOM_SCRIPS_GUIDE.md](docs/CUSTOM_SCRIPS_GUIDE.md)** - Custom stock list management
- **[docs/SCHEMA_OPTIMIZATION.md](docs/SCHEMA_OPTIMIZATION.md)** - Database optimization for large portfolios
- **[docs/QUICK_START.md](docs/QUICK_START.md)** - Quick start guide

## 🎯 Common Workflows

### Daily Trading Routine (Quick Entry)
```bash
# 1. Add trade instantly
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00

# 2. Update prices
python price_updater.py --all

# 3. View portfolio
python portfolio_dashboard.py --all
```

### Recording a Sale (Quick)
```bash
# 1. Sell shares
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL

# 2. View changes
python portfolio_dashboard.py --all
```

### Multiple Trades in Sequence
```bash
# Add multiple trades
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
python add_trade.py -c 532540 -n "TCS Ltd" -q 5 -p 3320.00
python add_trade.py -c 500180 -n "HDFC Bank Ltd" -q 20 -p 997.00

# Update and view
python price_updater.py --all
python portfolio_dashboard.py --all
```

### Bulk Import (Historical Data)
```bash
# 1. Generate template
python trade_importer.py --template historical_trades.xlsx

# 2. Fill in all your past trades in Excel

# 3. Import
python trade_importer.py --file historical_trades.xlsx

# 4. Update prices
python price_updater.py --all

# 5. View portfolio
python portfolio_dashboard.py --all
```

### Daily Portfolio Check
```bash
# Update prices (after market close)
python price_updater.py --all

# View portfolio
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

# 4. Backup database
cp data/portfolio.db data/portfolio_backup_$(date +%Y%m%d).db
```

## 🌐 Data Source Information

This project uses the **bsedata** Python library:
- Official BSE data source
- Real-time stock prices and changes
- Top gainers and losers
- Individual stock quotes
- Recommended fetch interval: 30-60 minutes to respect rate limits

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use this project for your needs.

## ⚠️ Disclaimer

This tool is for educational and research purposes. Always verify data accuracy and comply with BSE's terms of service. Not financial advice.

## 💡 Support

For issues or questions:
- Check the documentation guides in [`docs/`](docs/)
- Review logs: `logs/stock_fetcher.log`
- Check configuration: `src/config.py`

## 📚 Documentation

Comprehensive guides available in the [`docs/`](docs/) folder:

- **[docs/COMMAND_LINE_TRADE_ENTRY.md](docs/COMMAND_LINE_TRADE_ENTRY.md)** - Quick command-line trade entry
- **[docs/BUY_TRANSACTION_GUIDE.md](docs/BUY_TRANSACTION_GUIDE.md)** - Complete guide for recording purchases
- **[docs/SELL_TRANSACTION_GUIDE.md](docs/SELL_TRANSACTION_GUIDE.md)** - How to record SELL transactions
- **[docs/PORTFOLIO_USAGE_GUIDE.md](docs/PORTFOLIO_USAGE_GUIDE.md)** - Complete portfolio management guide
- **[docs/CUSTOM_SCRIPS_GUIDE.md](docs/CUSTOM_SCRIPS_GUIDE.md)** - Custom stock list management
- **[docs/SCHEMA_OPTIMIZATION.md](docs/SCHEMA_OPTIMIZATION.md)** - Database optimization for large portfolios
- **[docs/QUICK_START.md](docs/QUICK_START.md)** - Quick start guide
- Open an issue on GitHub

## 🚀 Future Enhancements

### Completed ✅
- [x] Database storage (SQLite)
- [x] Portfolio tracking system
- [x] Real-time price updates
- [x] P&L calculations (FIFO method)
- [x] Trade import from Excel/CSV
- [x] Quick command-line trade entry (NEW!)
- [x] Interactive CLI dashboard
- [x] Realized vs Unrealized P&L tracking

### Planned 📋
- [ ] Report generator (Excel/PDF exports)
- [ ] Email/SMS notifications for price alerts
- [ ] Web dashboard for monitoring
- [ ] Support for NSE stocks
- [ ] Historical data analysis and charts
- [ ] API endpoint for data access
- [ ] Mobile app integration
- [ ] Tax reporting features
- [ ] Dividend tracking
- [ ] Multi-currency support

---

**Happy Investing! 📈💰**