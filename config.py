"""
Configuration settings for BSE Stock Data Automation
"""
import os
from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Custom scrips configuration
CUSTOM_SCRIPS_FILE = BASE_DIR / "custom_scrips.txt"

# Scheduling configuration
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))  # Default: 1 hour
FETCH_TIME = os.getenv("FETCH_TIME", "09:30")  # Default: 9:30 AM IST (market open time)

# Data source configuration
BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
BSE_EQUITY_URL = "https://www.bseindia.com/corporates/List_Scrips.html"

# File paths
STOCK_DATA_FILE = DATA_DIR / "bse_stocks_{date}.csv"
STOCK_MASTER_FILE = DATA_DIR / "bse_stocks_master.csv"
LOG_FILE = LOGS_DIR / "stock_fetcher.log"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Data columns to save
STOCK_COLUMNS = [
    "scrip_code",
    "scrip_name",
    "group",
    "face_value",
    "isin_number",
    "industry",
    "status",
    "timestamp"
]

# Market hours (IST)
MARKET_OPEN_TIME = "09:15"
MARKET_CLOSE_TIME = "15:30"

 
