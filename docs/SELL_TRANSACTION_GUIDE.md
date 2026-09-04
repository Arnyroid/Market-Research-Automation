# How to Record SELL Transactions - Complete Guide

## Overview
This guide demonstrates how to record a SELL transaction and shows the impact on your portfolio dashboard.

---

## Example Scenario

**Transaction Details:**
- **Stock:** Reliance Industries Ltd (500325)
- **Action:** SELL
- **Quantity:** 5 shares
- **Price:** ₹1,600.00 per share
- **Date:** 2025-12-27

---

## Step-by-Step Process

### Step 1: Create a Trade File

Create a CSV file with your SELL transaction:

**File: `sell_transaction_example.csv`**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL
```

**Important Notes:**
- `trade_type` must be exactly "SELL" (all caps)
- `quantity` is the number of shares you're selling
- `price` is the selling price per share
- Date format: YYYY-MM-DD

### Step 2: Import the SELL Transaction

```bash
python trade_importer.py --file sell_transaction_example.csv
```

**Output:**
```
✅ Successfully imported 1 trades!
📊 Database: /path/to/portfolio.db
```

### Step 3: View Updated Portfolio

```bash
python portfolio_dashboard.py --all
```

---

## Before vs After Comparison

### BEFORE SELLING (Initial Portfolio)

```
📊 PORTFOLIO SUMMARY
+----------------+------------+
| Total Stocks   | 3          |
| Total Invested | ₹65,710.00 |
| Current Value  | ₹67,427.00 |
| Total P&L      | ₹1,717.00  |
| P&L %          | 2.61%      |
| Realized P&L   | ₹0.00      |  ← No realized profit yet
+----------------+------------+

💼 CURRENT HOLDINGS
Code   | Name                    | Qty | Avg Price | Current   | Value      | P&L       | P&L %
500325 | Reliance Industries Ltd | 20  | ₹1,455.00 | ₹1,559.00 | ₹31,180.00 | ₹2,080.00 | 7.15%
                                  ↑
                              20 shares

📝 RECENT TRADES
Date       | Code   | Name                    | Type | Qty | Price     | Total
2025-12-27 | 500325 | Reliance Industries Ltd | BUY  | 10  | ₹1,450.00 | ₹14,500.00
2025-01-15 | 500325 | Reliance Industries Ltd | BUY  | 10  | ₹1,450.00 | ₹14,500.00
```

### AFTER SELLING (Updated Portfolio)

```
📊 PORTFOLIO SUMMARY
+----------------+------------+
| Total Stocks   | 3          |
| Total Invested | ₹65,710.00 |
| Current Value  | ₹67,427.00 |
| Total P&L      | ₹1,717.00  |
| P&L %          | 2.61%      |
| Realized P&L   | ₹750.00    |  ← ✅ Realized profit from sale!
+----------------+------------+

💼 CURRENT HOLDINGS
Code   | Name                    | Qty | Avg Price | Current   | Value      | P&L       | P&L %
500325 | Reliance Industries Ltd | 20  | ₹1,455.00 | ₹1,559.00 | ₹31,180.00 | ₹2,080.00 | 7.15%
                                  ↑
                          Still 20 shares (see note below)

📝 RECENT TRADES
Date       | Code   | Name                    | Type | Qty | Price     | Total
2025-12-27 | 500325 | Reliance Industries Ltd | SELL | 5   | ₹1,600.00 | ₹8,000.00  ← New SELL trade
2025-12-27 | 500325 | Reliance Industries Ltd | BUY  | 10  | ₹1,450.00 | ₹14,500.00
2025-01-15 | 500325 | Reliance Industries Ltd | BUY  | 10  | ₹1,450.00 | ₹14,500.00
```

---

## Key Changes Explained

### 1. Realized P&L Calculation

**How it's calculated (FIFO method):**

```
Original Purchases:
- 2025-01-15: Bought 10 shares @ ₹1,450.00 = ₹14,500.00
- 2025-12-27: Bought 10 shares @ ₹1,450.00 = ₹14,500.00
Total: 20 shares @ avg ₹1,450.00

Sale Transaction:
- 2025-12-27: Sold 5 shares @ ₹1,600.00 = ₹8,000.00

FIFO Calculation:
- Sold 5 shares from first purchase (2025-01-15)
- Cost basis: 5 × ₹1,450.00 = ₹7,250.00
- Sale proceeds: 5 × ₹1,600.00 = ₹8,000.00
- Realized P&L: ₹8,000.00 - ₹7,250.00 = ₹750.00 ✅
```

### 2. Holdings Update

**Important Note:** The holdings still show 20 shares because the portfolio table hasn't been recalculated yet. To update holdings:

```bash
# Recalculate portfolio from trades
python -c "from portfolio_analyzer import PortfolioAnalyzer; analyzer = PortfolioAnalyzer(); analyzer.calculate_holdings_from_trades()"
```

After recalculation, holdings will show:
```
Code   | Name                    | Qty | Avg Price | Current   | Value      | P&L       | P&L %
500325 | Reliance Industries Ltd | 15  | ₹1,450.00 | ₹1,559.00 | ₹23,385.00 | ₹1,635.00 | 7.50%
                                  ↑
                              15 shares (20 - 5 sold)
```

### 3. Trade History

The SELL transaction now appears at the top of recent trades:
- Shows SELL type
- Shows quantity sold (5)
- Shows selling price (₹1,600.00)
- Shows total proceeds (₹8,000.00)

---

## Detailed Stock Analysis

View detailed analysis for the stock you sold:

```bash
python portfolio_dashboard.py --stock 500325
```

**Output:**
```
🔍 STOCK ANALYSIS: 500325
Company: Reliance Industries Ltd

📊 Trading Activity:
Total Trades  3        ← Now includes the SELL
Buy Trades    2
Sell Trades   1        ← Your SELL transaction
First Trade   2025-01-15
Last Trade    2025-12-27

💼 Current Position:
Quantity          15   ← Updated quantity (20 - 5)
Avg Buy Price     ₹1,450.00
Total Invested    ₹21,750.00  ← Reduced (15 × ₹1,450)
Current Price     ₹1,559.00
Current Value     ₹23,385.00
Unrealized P&L    ₹1,635.00
Unrealized P&L %  7.52%

💰 P&L Summary:
Realized P&L    ₹750.00    ← Profit from sale
Unrealized P&L  ₹1,635.00  ← Profit on remaining 15 shares
Total P&L       ₹2,385.00  ← Combined profit
```

---

## Understanding FIFO (First In, First Out)

The system uses FIFO method to calculate which shares were sold:

### Example with Multiple Purchases:

```
Purchase History:
1. 2025-01-15: Buy 10 @ ₹1,450.00
2. 2025-12-27: Buy 10 @ ₹1,450.00

When you SELL 5 shares:
- System sells from Purchase #1 (oldest first)
- 5 shares from 2025-01-15 purchase are sold
- Remaining: 5 from Purchase #1 + 10 from Purchase #2 = 15 total

If you SELL 12 shares:
- 10 shares from Purchase #1 (all of it)
- 2 shares from Purchase #2
- Remaining: 8 shares from Purchase #2
```

---

## Multiple SELL Transactions

You can record multiple SELL transactions in one file:

**File: `multiple_sells.csv`**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL
2025-12-27,500180,HDFC Bank Ltd,10,1000.00,SELL
2025-12-27,532540,TCS Ltd,2,3300.00,SELL
```

Import all at once:
```bash
python trade_importer.py --file multiple_sells.csv
```

---

## Common Scenarios

### Scenario 1: Selling All Shares

```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500325,Reliance Industries Ltd,20,1600.00,SELL
```

Result:
- Quantity becomes 0
- All profit/loss is realized
- Stock remains in portfolio with 0 quantity

### Scenario 2: Selling at a Loss

```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500180,HDFC Bank Ltd,10,950.00,SELL
```

If bought at ₹997.00:
- Realized P&L: (₹950 - ₹997) × 10 = -₹470.00 (loss)

### Scenario 3: Partial Sales Over Time

```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL
2025-12-28,500325,Reliance Industries Ltd,5,1620.00,SELL
2025-12-29,500325,Reliance Industries Ltd,5,1580.00,SELL
```

Each sale is tracked separately with its own realized P&L.

---

## Best Practices

### 1. Record Sales Immediately
```bash
# Create file with today's date
echo "trade_date,scrip_code,scrip_name,quantity,price,trade_type" > sell_$(date +%Y%m%d).csv
echo "2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL" >> sell_$(date +%Y%m%d).csv
python trade_importer.py --file sell_$(date +%Y%m%d).csv
```

### 2. Verify Before Importing
```bash
# Check your file
cat sell_transaction.csv

# Import
python trade_importer.py --file sell_transaction.csv

# Verify import
python portfolio_dashboard.py --trades
```

### 3. Update Prices After Sale
```bash
# Import sale
python trade_importer.py --file sell_transaction.csv

# Update current prices
python price_updater.py --all

# View updated portfolio
python portfolio_dashboard.py --all
```

### 4. Keep Records
```bash
# Backup after major transactions
cp data/portfolio.db data/portfolio_backup_$(date +%Y%m%d).db

# Keep CSV files
mkdir -p trades_archive
cp sell_transaction.csv trades_archive/sell_$(date +%Y%m%d).csv
```

---

## Troubleshooting

### Issue: "Insufficient quantity to sell"

**Problem:** Trying to sell more shares than you own.

**Solution:**
```bash
# Check current holdings
python portfolio_dashboard.py --holdings

# Verify quantity before selling
python portfolio_dashboard.py --stock 500325
```

### Issue: Wrong realized P&L

**Problem:** P&L calculation seems incorrect.

**Solution:**
```bash
# Check all trades for the stock
python portfolio_dashboard.py --stock 500325

# Verify FIFO calculation manually
# Oldest purchases are sold first
```

### Issue: Holdings not updating

**Problem:** Quantity still shows old value after SELL.

**Solution:**
```bash
# Recalculate holdings from trades
python -c "from portfolio_analyzer import PortfolioAnalyzer; a = PortfolioAnalyzer(); a.calculate_holdings_from_trades()"

# View updated holdings
python portfolio_dashboard.py --holdings
```

---

## Tax Reporting

The realized P&L is useful for tax purposes:

```bash
# View all realized gains/losses
python portfolio_dashboard.py --summary

# Export to file for tax records
python portfolio_dashboard.py --all > portfolio_tax_report_$(date +%Y%m%d).txt
```

**Realized P&L shows:**
- Actual profit/loss from completed sales
- Used for capital gains tax calculation
- Separate from unrealized (paper) gains

---

## Quick Reference

### Record a SELL Transaction
```bash
# 1. Create CSV file
echo "trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-12-27,500325,Reliance Industries Ltd,5,1600.00,SELL" > sell.csv

# 2. Import
python trade_importer.py --file sell.csv

# 3. View changes
python portfolio_dashboard.py --all
```

### Check Realized P&L
```bash
python portfolio_dashboard.py --summary
```

### Analyze Specific Stock
```bash
python portfolio_dashboard.py --stock 500325
```

### View All Trades
```bash
python portfolio_dashboard.py --trades
```

---

## Summary

✅ **What Changed After SELL:**
1. **Realized P&L:** ₹0.00 → ₹750.00 (profit from sale)
2. **Trade History:** New SELL transaction appears
3. **Holdings:** Quantity reduces from 20 to 15 (after recalculation)
4. **Total P&L:** Includes both realized and unrealized gains

✅ **Key Points:**
- SELL transactions are recorded just like BUY transactions
- System uses FIFO method for cost basis calculation
- Realized P&L shows actual profit/loss from sales
- Holdings update automatically when recalculated
- All transactions are tracked in trade history

✅ **Next Steps:**
- Record all SELL transactions promptly
- Review realized P&L regularly
- Keep backup of database before major changes
- Use for tax reporting at year-end

---

**Last Updated:** 2025-12-27
**Version:** 1.0