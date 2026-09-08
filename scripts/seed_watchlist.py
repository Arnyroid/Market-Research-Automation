"""
Seed script — adds 40 well-known NSE-listed stocks to the watchlist.

Run from repo root (with venv activated):
  python scripts/seed_watchlist.py

Safe to run multiple times — skips symbols already in the watchlist.
"""
import pathlib
import sqlite3
from datetime import datetime

DB_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "portfolio.db"

# 40 well-known NSE stocks across diverse sectors
STOCKS = [
    # Large-cap blue chips
    ("RELIANCE",    "NSE", "Reliance Industries Ltd",          "Energy"),
    ("TCS",         "NSE", "Tata Consultancy Services Ltd",    "IT"),
    ("HDFCBANK",    "NSE", "HDFC Bank Ltd",                    "Banking"),
    ("INFY",        "NSE", "Infosys Ltd",                      "IT"),
    ("ICICIBANK",   "NSE", "ICICI Bank Ltd",                   "Banking"),
    ("HINDUNILVR",  "NSE", "Hindustan Unilever Ltd",           "FMCG"),
    ("ITC",         "NSE", "ITC Ltd",                          "FMCG"),
    ("SBIN",        "NSE", "State Bank of India",              "Banking"),
    ("BHARTIARTL",  "NSE", "Bharti Airtel Ltd",                "Telecom"),
    ("KOTAKBANK",   "NSE", "Kotak Mahindra Bank Ltd",          "Banking"),

    # Mid-cap & sector leaders
    ("WIPRO",       "NSE", "Wipro Ltd",                        "IT"),
    ("HCLTECH",     "NSE", "HCL Technologies Ltd",             "IT"),
    ("AXISBANK",    "NSE", "Axis Bank Ltd",                    "Banking"),
    ("BAJFINANCE",  "NSE", "Bajaj Finance Ltd",                "NBFC"),
    ("MARUTI",      "NSE", "Maruti Suzuki India Ltd",          "Auto"),
    ("TATAMOTORS",  "NSE", "Tata Motors Ltd",                  "Auto"),
    ("TITAN",       "NSE", "Titan Company Ltd",                "Consumer"),
    ("SUNPHARMA",   "NSE", "Sun Pharmaceutical Industries Ltd","Pharma"),
    ("DRREDDY",     "NSE", "Dr Reddy's Laboratories Ltd",      "Pharma"),
    ("CIPLA",       "NSE", "Cipla Ltd",                        "Pharma"),

    # Infrastructure & industrials
    ("LT",          "NSE", "Larsen & Toubro Ltd",              "Infrastructure"),
    ("POWERGRID",   "NSE", "Power Grid Corporation of India",  "Power"),
    ("NTPC",        "NSE", "NTPC Ltd",                         "Power"),
    ("ONGC",        "NSE", "Oil & Natural Gas Corporation Ltd","Energy"),
    ("COALINDIA",   "NSE", "Coal India Ltd",                   "Mining"),
    ("JSWSTEEL",    "NSE", "JSW Steel Ltd",                    "Metals"),
    ("TATASTEEL",   "NSE", "Tata Steel Ltd",                   "Metals"),
    ("HINDALCO",    "NSE", "Hindalco Industries Ltd",          "Metals"),
    ("ULTRACEMCO",  "NSE", "UltraTech Cement Ltd",             "Cement"),
    ("GRASIM",      "NSE", "Grasim Industries Ltd",            "Diversified"),

    # Consumer & retail
    ("ASIANPAINT",  "NSE", "Asian Paints Ltd",                 "Consumer"),
    ("NESTLEIND",   "NSE", "Nestle India Ltd",                 "FMCG"),
    ("DMART",       "NSE", "Avenue Supermarts Ltd",            "Retail"),
    ("PIDILITIND",  "NSE", "Pidilite Industries Ltd",          "Chemicals"),
    ("BRITANNIA",   "NSE", "Britannia Industries Ltd",         "FMCG"),

    # New-age & emerging
    ("ZOMATO",      "NSE", "Zomato Ltd",                       "Consumer Tech"),
    ("NYKAA",       "NSE", "FSN E-Commerce Ventures Ltd",      "Consumer Tech"),
    ("DELHIVERY",   "NSE", "Delhivery Ltd",                    "Logistics"),
    ("POLICYBZR",   "NSE", "PB Fintech Ltd",                   "Fintech"),
    ("IRCTC",       "NSE", "Indian Railway Catering & Tourism","Travel"),
]


def seed():
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}")
        print("Start the backend once first so it creates the DB, then re-run.")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Read existing (symbol, exchange) pairs
    existing = {
        (row[0], row[1])
        for row in cur.execute("SELECT symbol, exchange FROM watchlist")
    }

    added = 0
    skipped = 0
    now = datetime.utcnow().isoformat()

    for symbol, exchange, company_name, sector in STOCKS:
        if (symbol, exchange) in existing:
            print(f"–  {symbol:15s} already in watchlist, skipping")
            skipped += 1
            continue

        cur.execute(
            "INSERT INTO watchlist (symbol, exchange, company_name, sector, added_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (symbol, exchange, company_name, sector, now),
        )
        print(f"✓  Added {symbol:15s}  ({company_name})")
        added += 1

    con.commit()
    con.close()
    print(f"\nDone — {added} added, {skipped} skipped.")
    if added:
        print("Refresh the Watchlist page in your browser to see them.")


if __name__ == "__main__":
    seed()
