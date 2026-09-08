"""
scripts/seed_portfolio.py
=========================
Seeds the portfolio with a realistic mix of trades to test the Portfolio page.

Covers:
  - Large, mid, and small cap holdings (exercises the cap-tier tabs + analytics)
  - Multiple sectors (IT, FMCG, Banking, Energy, Pharma, Auto)
  - Partial SELL trades (exercises realized P&L column)
  - Multi-leg BUY (avg-price recalculation)
  - Spread across ~12 months of dates

Run:  python scripts/seed_portfolio.py
Safe to re-run: skips if any seed symbol already has trades.
"""
import sys, requests

BASE = "http://localhost:8000"


def post(payload: dict) -> dict:
    r = requests.post(f"{BASE}/trades", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def existing_symbols() -> set[str]:
    r = requests.get(f"{BASE}/trades", timeout=10)
    r.raise_for_status()
    return {t["symbol"] for t in r.json()}


TRADES = [
    # ── Large Cap — IT ────────────────────────────────────────────────────────
    {"trade_date": "2024-08-15", "symbol": "INFY",       "exchange": "NSE",
     "company_name": "Infosys Ltd",              "trade_type": "BUY",  "quantity": 30,  "price": 1620.00, "brokerage": 20},
    {"trade_date": "2024-11-10", "symbol": "INFY",       "exchange": "NSE",
     "company_name": "Infosys Ltd",              "trade_type": "BUY",  "quantity": 20,  "price": 1745.00, "brokerage": 15},
    {"trade_date": "2025-03-05", "symbol": "INFY",       "exchange": "NSE",
     "company_name": "Infosys Ltd",              "trade_type": "SELL", "quantity": 15,  "price": 1890.00, "brokerage": 18},

    # ── Large Cap — FMCG ─────────────────────────────────────────────────────
    {"trade_date": "2024-07-20", "symbol": "HINDUNILVR",  "exchange": "NSE",
     "company_name": "Hindustan Unilever Ltd",   "trade_type": "BUY",  "quantity": 25,  "price": 2380.00, "brokerage": 25},

    # ── Large Cap — Energy ───────────────────────────────────────────────────
    {"trade_date": "2024-09-12", "symbol": "RELIANCE",   "exchange": "NSE",
     "company_name": "Reliance Industries Ltd",  "trade_type": "BUY",  "quantity": 10,  "price": 2950.00, "brokerage": 20},
    {"trade_date": "2025-01-08", "symbol": "RELIANCE",   "exchange": "NSE",
     "company_name": "Reliance Industries Ltd",  "trade_type": "BUY",  "quantity": 5,   "price": 1280.00, "brokerage": 10},

    # ── Mid Cap — Auto ───────────────────────────────────────────────────────
    {"trade_date": "2024-10-03", "symbol": "MOTHERSON",  "exchange": "NSE",
     "company_name": "Samvardhana Motherson",    "trade_type": "BUY",  "quantity": 200, "price": 168.00,  "brokerage": 15},
    {"trade_date": "2025-02-14", "symbol": "MOTHERSON",  "exchange": "NSE",
     "company_name": "Samvardhana Motherson",    "trade_type": "SELL", "quantity": 100, "price": 145.00,  "brokerage": 12},

    # ── Mid Cap — Pharma ─────────────────────────────────────────────────────
    {"trade_date": "2024-12-01", "symbol": "ALKEM",      "exchange": "NSE",
     "company_name": "Alkem Laboratories Ltd",   "trade_type": "BUY",  "quantity": 8,   "price": 5400.00, "brokerage": 30},

    # ── Mid Cap — IT ─────────────────────────────────────────────────────────
    {"trade_date": "2025-01-22", "symbol": "MPHASIS",    "exchange": "NSE",
     "company_name": "Mphasis Ltd",              "trade_type": "BUY",  "quantity": 18,  "price": 2680.00, "brokerage": 22},

    # ── Small Cap — Chemicals ────────────────────────────────────────────────
    {"trade_date": "2024-11-25", "symbol": "FINEORG",    "exchange": "NSE",
     "company_name": "Fine Organic Industries",  "trade_type": "BUY",  "quantity": 12,  "price": 4200.00, "brokerage": 28},

    # ── Small Cap — Defence ──────────────────────────────────────────────────
    {"trade_date": "2025-03-18", "symbol": "PARAS",      "exchange": "NSE",
     "company_name": "Paras Defence & Space",    "trade_type": "BUY",  "quantity": 50,  "price": 980.00,  "brokerage": 20},

    # ── Small Cap — Finance ──────────────────────────────────────────────────
    {"trade_date": "2025-04-10", "symbol": "CREDITACC",  "exchange": "NSE",
     "company_name": "CreditAccess Grameen",     "trade_type": "BUY",  "quantity": 40,  "price": 1050.00, "brokerage": 18},
    {"trade_date": "2025-06-02", "symbol": "CREDITACC",  "exchange": "NSE",
     "company_name": "CreditAccess Grameen",     "trade_type": "SELL", "quantity": 20,  "price": 980.00,  "brokerage": 14},
]


def main():
    print("Checking existing trades…")
    skip = existing_symbols()
    if skip:
        print(f"  Already have trades for: {', '.join(sorted(skip))}")

    seed = [t for t in TRADES if t["symbol"] not in skip]
    if not seed:
        print("All seed symbols already present — nothing to add.")
        return

    print(f"Posting {len(seed)} trades…")
    ok = err = 0
    for t in seed:
        try:
            res = post(t)
            print(f"  ✓  {t['trade_type']:4s} {t['quantity']:4d} × {t['symbol']:12s} @ ₹{t['price']:,.2f}  →  id={res['id']}")
            ok += 1
        except Exception as e:
            print(f"  ✗  {t['symbol']:12s}  ERROR: {e}", file=sys.stderr)
            err += 1

    print(f"\nDone — {ok} inserted, {err} errors.")
    if ok:
        print("Reload the Portfolio page to see all holdings.")


if __name__ == "__main__":
    main()
