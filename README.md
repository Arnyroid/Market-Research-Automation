# Market Research Automation - BSE Stock Data Fetcher

Automated system to fetch and track BSE (Bombay Stock Exchange) listed stocks at regular intervals using the official `bsedata` Python library.

## Features

- 🔄 **Automated Fetching**: Fetch BSE stock data at configurable intervals
- 📊 **Real-time Data**: Uses official `bsedata` library for accurate, real-time stock prices
- 💰 **Price Tracking**: Get current prices, changes, and percentage movements
- 📋 **Custom Stock Lists**: Track your own portfolio or watchlist of stocks
- ⏰ **Flexible Scheduling**: Run once, at intervals, daily, or during market hours
- 💾 **Data Storage**: Saves data to CSV files with timestamps
- 🔁 **Retry Logic**: Automatic retry on failures with configurable attempts
- 📝 **Comprehensive Logging**: Detailed logs for monitoring and debugging
- ⚙️ **Configurable**: Easy configuration via environment variables

## Project Structure

```
Market-Research-Automation/
├── bse_fetcher.py          # Core fetching logic
├── scheduler.py            # Scheduling and automation
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── data/                  # Stock data (CSV files)
└── logs/                  # Application logs
```

## Installation

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

## Usage

### Quick Start - Run Once

Fetch stock data immediately and exit:
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
Run every N minutes:
```bash
# Run every 60 minutes (default)
python scheduler.py interval

# Run every 30 minutes
python scheduler.py interval 30

# With custom scrips
python scheduler.py interval 30 --custom
```

#### 2. Daily Mode
Run once daily at a specific time:
```bash
# Run daily at 9:30 AM (default)
python scheduler.py daily

# Run daily at 2:00 PM
python scheduler.py daily 14:00

# With custom scrips
python scheduler.py daily 09:30 --custom
```

#### 3. Market Hours Mode
Run during BSE market hours (9:15 AM - 3:30 PM IST):
```bash
python scheduler.py market

# With custom scrips
python scheduler.py market --custom
```

This mode runs at:
- Market open: 9:15 AM
- Every hour: 10:00 AM, 11:00 AM, 12:00 PM, 1:00 PM, 2:00 PM, 3:00 PM
- Market close: 3:30 PM

### Using as a Module

```python
from bse_fetcher import BSEStockFetcher

# Create fetcher instance
fetcher = BSEStockFetcher()

# Fetch stocks with current prices (recommended - faster)
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

## Configuration

Edit `.env` file or modify `config.py` directly:

| Variable | Default | Description |
|----------|---------|-------------|
| `FETCH_INTERVAL_MINUTES` | 60 | Minutes between fetches in interval mode |
| `FETCH_TIME` | 09:30 | Time for daily fetch (HH:MM format, IST) |
| `MAX_RETRIES` | 3 | Maximum retry attempts on failure |
| `RETRY_DELAY_SECONDS` | 5 | Seconds to wait between retries |

## Data Output

### CSV Files

Stock data is saved in two locations:

1. **Timestamped files**: `data/bse_stocks_YYYYMMDD_HHMMSS.csv`
   - Historical record of each fetch
   
2. **Master file**: `data/bse_stocks_master.csv`
   - Always contains the latest data
   - Overwritten on each successful fetch

### Data Columns

- `securityID`: Security identifier (e.g., RELIANCE, TCS)
- `scrip_code`: BSE scrip code (e.g., 500325)
- `last_price`: Current trading price (₹)
- `price_change`: Absolute price change (₹)
- `price_change_percent`: Percentage price change (%)
- `category`: Stock category (TOP_GAINER, TOP_LOSER, etc.)
- `timestamp`: Fetch timestamp (ISO 8601)
- `source`: Data source (BSEDATA_LIBRARY)

### Sample Data

```csv
securityID,scrip_code,last_price,price_change,price_change_percent,category,timestamp,source
RELIANCE,500325,1557.95,-12.95,-0.82,TOP_GAINER,2025-12-25T16:09:55.543108,BSEDATA_LIBRARY
TCS,532540,4234.50,45.30,1.08,TOP_GAINER,2025-12-25T16:09:55.543108,BSEDATA_LIBRARY
```

## Logging

Logs are stored in `logs/stock_fetcher.log` with:
- Daily rotation
- 30-day retention
- Detailed information about each fetch operation
- Error tracking and debugging information

## Running as a Background Service

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

## Troubleshooting

### No data fetched
- Check internet connection
- Verify BSE website is accessible (bseindia.com)
- Check logs in `logs/stock_fetcher.log`
- Try running once: `python scheduler.py once`
- The bsedata library may have rate limits - use intervals of 30+ minutes

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Specifically install bsedata: `pip install bsedata`
- Activate virtual environment if using one

### Permission errors
- Ensure write permissions for `data/` and `logs/` directories
- Run: `chmod -R 755 data logs` (Linux/Mac)

### Empty or incorrect data
- The system fetches top gainers/losers by default (faster, ~10 stocks)
- For comprehensive data, modify `fetch_stocks(include_prices=False)` in code
- Check if BSE market is open (9:15 AM - 3:30 PM IST on trading days)

## Data Source Information

This project uses the **bsedata** Python library:
- Official BSE data source
- Real-time stock prices and changes
- Top gainers and losers
- Individual stock quotes
- Recommended fetch interval: 30-60 minutes to respect rate limits

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this project for your needs.

## Disclaimer

This tool is for educational and research purposes. Always verify data accuracy and comply with BSE's terms of service. Not financial advice.

## Support

For issues or questions:
- Check the logs: `logs/stock_fetcher.log`
- Review configuration: `config.py`
- Open an issue on GitHub

## Future Enhancements

- [ ] Database storage (SQLite/PostgreSQL)
- [ ] Real-time stock price tracking
- [ ] Email/SMS notifications
- [ ] Web dashboard for monitoring
- [ ] Support for NSE stocks
- [ ] Historical data analysis
- [ ] Export to multiple formats (JSON, Excel)
- [ ] API endpoint for data access

---

**Happy Automating! 🚀**