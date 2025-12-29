# How to Record BUY Transactions - Complete Guide

## Overview
This comprehensive guide shows you how to record BUY (purchase) transactions in your portfolio tracking system, from creating your first trade entry to managing multiple purchases.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Creating Your First BUY Entry](#creating-your-first-buy-entry)
3. [Multiple Purchase Methods](#multiple-purchase-methods)
4. [Understanding the Data](#understanding-the-data)
5. [Viewing Your Purchases](#viewing-your-purchases)
6. [Common Scenarios](#common-scenarios)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 3-Step Process to Record a Purchase

```bash
# Step 1: Generate a template
python trade_importer.py --template my_purchases.xlsx

# Step 2: Edit the template with your purchase details
# (Open my_purchases.xlsx in Excel/LibreOffice)

# Step 3: Import your purchases
python trade_importer.py --file my_purchases.xlsx
```

---

## Creating Your First BUY Entry

### Method 1: Using Excel Template (Recommended)

#### Step 1: Generate Template

```bash
python trade_importer.py --template my_first_purchase.xlsx
```

This creates an Excel file with the correct column headers:
- `trade_date`
- `scrip_code`
- `scrip_name`
- `quantity`
- `price`
- `trade_type`

#### Step 2: Fill in Your Purchase Details

Open `my_first_purchase.xlsx` in Excel and enter your data:

| trade_date | scrip_code | scrip_name              | quantity | price   | trade_type |
|------------|------------|-------------------------|----------|---------|------------|
| 2025-01-15 | 500325     | Reliance Industries Ltd | 10       | 1450.00 | BUY        |

**Important Notes:**
- **trade_date**: Use YYYY-MM-DD format (e.g., 2025-01-15)
- **scrip_code**: BSE scrip code (6 digits, e.g., 500325)
- **scrip_name**: Company name (for reference)
- **quantity**: Number of shares purchased (whole numbers)
- **price**: Price per share (can include decimals)
- **trade_type**: Must be exactly "BUY" (all caps)

#### Step 3: Import the File

```bash
python trade_importer.py --file my_first_purchase.xlsx
```

**Expected Output:**
```
✅ Successfully imported 1 trades!
📊 Database: /path/to/portfolio.db

Import Summary:
- Total trades: 1
- Successful: 1
- Failed: 0
```

#### Step 4: Verify Import

```bash
python portfolio_dashboard.py --trades
```

You should see your purchase in the recent trades list.

---

### Method 2: Using CSV File

#### Step 1: Create CSV File

Create a file named `purchase.csv`:

```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
```

**Tips:**
- Use any text editor (Notepad, VS Code, etc.)
- Save with `.csv` extension
- Don't add extra spaces around commas
- Keep header row exactly as shown

#### Step 2: Import CSV

```bash
python trade_importer.py --file purchase.csv
```

---

### Method 3: Quick Command Line Entry

For a single quick entry, create the CSV directly:

```bash
# Create CSV file with one purchase
echo "trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY" > quick_buy.csv

# Import it
python trade_importer.py --file quick_buy.csv

# View result
python portfolio_dashboard.py --all
```

---

## Multiple Purchase Methods

### Recording Multiple Purchases at Once

#### Example: Multiple Stocks on Same Day

**File: `multiple_purchases.csv`**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
2025-01-15,532540,TCS Ltd,5,3320.00,BUY
2025-01-15,500180,HDFC Bank Ltd,20,997.00,BUY
```

Import all at once:
```bash
python trade_importer.py --file multiple_purchases.csv
```

#### Example: Same Stock, Multiple Purchases

**File: `reliance_purchases.csv`**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
2025-02-10,500325,Reliance Industries Ltd,5,1480.00,BUY
2025-03-05,500325,Reliance Industries Ltd,15,1520.00,BUY
```

This records three separate purchases of Reliance at different times and prices.

#### Example: Historical Portfolio Import

**File: `complete_portfolio.csv`**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2024-01-10,500325,Reliance Industries Ltd,20,1350.00,BUY
2024-02-15,532540,TCS Ltd,10,3200.00,BUY
2024-03-20,500180,HDFC Bank Ltd,30,950.00,BUY
2024-06-10,500325,Reliance Industries Ltd,10,1400.00,BUY
2024-09-05,532540,TCS Ltd,5,3350.00,BUY
2025-01-15,500180,HDFC Bank Ltd,20,997.00,BUY
```

Import your entire trading history:
```bash
python trade_importer.py --file complete_portfolio.csv
```

---

## Understanding the Data

### Required Fields Explained

#### 1. trade_date
**Format:** YYYY-MM-DD

**Examples:**
- ✅ Correct: `2025-01-15`
- ✅ Correct: `2024-12-31`
- ❌ Wrong: `15-01-2025`
- ❌ Wrong: `01/15/2025`
- ❌ Wrong: `15 Jan 2025`

**Tips:**
- Always use 4-digit year
- Use 2-digit month (01-12)
- Use 2-digit day (01-31)
- Separate with hyphens (-)

#### 2. scrip_code
**Format:** 6-digit BSE scrip code

**Common Stocks:**
- `500325` - Reliance Industries Ltd
- `532540` - TCS Ltd
- `500180` - HDFC Bank Ltd
- `500112` - State Bank of India
- `500209` - Infosys Ltd
- `532174` - ICICI Bank Ltd

**How to Find:**
- Visit BSE website (bseindia.com)
- Search for company name
- Look for "Scrip Code" in stock details
- It's always a 6-digit number

#### 3. scrip_name
**Format:** Company name (for reference)

**Examples:**
- `Reliance Industries Ltd`
- `Tata Consultancy Services Ltd`
- `HDFC Bank Ltd`

**Tips:**
- Use official company name
- Include "Ltd" if applicable
- This is for your reference only
- System uses scrip_code for identification

#### 4. quantity
**Format:** Whole number (integer)

**Examples:**
- ✅ Correct: `10`
- ✅ Correct: `100`
- ✅ Correct: `1`
- ❌ Wrong: `10.5` (no decimals)
- ❌ Wrong: `10 shares` (no text)

**Tips:**
- Must be positive number
- No decimal points
- Represents number of shares

#### 5. price
**Format:** Decimal number (price per share)

**Examples:**
- ✅ Correct: `1450.00`
- ✅ Correct: `1450.50`
- ✅ Correct: `1450`
- ❌ Wrong: `₹1450` (no currency symbol)
- ❌ Wrong: `1,450.00` (no commas)

**Tips:**
- Price per share, not total amount
- Can include decimals (e.g., 1450.75)
- Don't use currency symbols
- Don't use thousand separators (commas)

#### 6. trade_type
**Format:** Exactly "BUY" (all caps)

**Examples:**
- ✅ Correct: `BUY`
- ❌ Wrong: `buy` (lowercase)
- ❌ Wrong: `Buy` (mixed case)
- ❌ Wrong: `PURCHASE`
- ❌ Wrong: `B`

---

## Viewing Your Purchases

### View All Trades

```bash
python portfolio_dashboard.py --trades
```

**Output:**
```
📝 RECENT TRADES (Last 10)
+------------+--------+-------------------------+--------+-------+-----------+------------+
| Date       |   Code | Name                    | Type   |   Qty | Price     | Total      |
+============+========+=========================+========+=======+===========+============+
| 2025-01-15 | 500325 | Reliance Industries Ltd | BUY    |    10 | ₹1,450.00 | ₹14,500.00 |
| 2025-01-15 | 532540 | TCS Ltd                 | BUY    |     5 | ₹3,320.00 | ₹16,600.00 |
| 2025-01-15 | 500180 | HDFC Bank Ltd           | BUY    |    20 | ₹997.00   | ₹19,940.00 |
+------------+--------+-------------------------+--------+-------+-----------+------------+
```

### View Current Holdings

```bash
python portfolio_dashboard.py --holdings
```

**Output:**
```
💼 CURRENT HOLDINGS
+--------+-------------------------+-------+-------------+------------+-----------+------------+-----------+---------+
|   Code | Name                    |   Qty | Avg Price   | Invested   | Current   | Value      | P&L       | P&L %   |
+========+=========================+=======+=============+============+===========+============+===========+=========+
| 500325 | Reliance Industries Ltd |    10 | ₹1,450.00   | ₹14,500.00 | ₹1,559.00 | ₹15,590.00 | ₹1,090.00 | 7.52%   |
| 532540 | TCS Ltd                 |     5 | ₹3,320.00   | ₹16,600.00 | ₹3,279.80 | ₹16,399.00 | ₹-201.00  | -1.21%  |
| 500180 | HDFC Bank Ltd           |    20 | ₹997.00     | ₹19,940.00 | ₹992.40   | ₹19,848.00 | ₹-92.00   | -0.46%  |
+--------+-------------------------+-------+-------------+------------+-----------+------------+-----------+---------+
```

### View Complete Portfolio

```bash
python portfolio_dashboard.py --all
```

Shows:
- Portfolio summary
- Performance breakdown
- Current holdings
- Recent trades

### Analyze Specific Stock

```bash
python portfolio_dashboard.py --stock 500325
```

**Output:**
```
🔍 STOCK ANALYSIS: 500325
Company: Reliance Industries Ltd

📊 Trading Activity:
Total Trades  1
Buy Trades    1
Sell Trades   0
First Trade   2025-01-15
Last Trade    2025-01-15

💼 Current Position:
Quantity          10
Avg Buy Price     ₹1,450.00
Total Invested    ₹14,500.00
Current Price     ₹1,559.00
Current Value     ₹15,590.00
Unrealized P&L    ₹1,090.00
Unrealized P&L %  7.52%
```

---

## Common Scenarios

### Scenario 1: First Time Investor

**Situation:** You just bought your first stock.

**Example:**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,5,1450.00,BUY
```

**Steps:**
```bash
# 1. Create the file
echo "trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,5,1450.00,BUY" > first_stock.csv

# 2. Import
python trade_importer.py --file first_stock.csv

# 3. Update price
python price_updater.py --all

# 4. View portfolio
python portfolio_dashboard.py --all
```

### Scenario 2: Building Position Over Time

**Situation:** You're buying the same stock at different times (Dollar Cost Averaging).

**Example:**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
2025-02-15,500325,Reliance Industries Ltd,10,1480.00,BUY
2025-03-15,500325,Reliance Industries Ltd,10,1520.00,BUY
```

**Result:**
- Total quantity: 30 shares
- Average price: ₹1,483.33
- System automatically calculates weighted average

### Scenario 3: Diversified Portfolio

**Situation:** You're buying multiple stocks across sectors.

**Example:**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
2025-01-15,532540,TCS Ltd,5,3320.00,BUY
2025-01-15,500180,HDFC Bank Ltd,20,997.00,BUY
2025-01-15,500112,State Bank of India,30,650.00,BUY
2025-01-15,500209,Infosys Ltd,8,1580.00,BUY
```

**Portfolio Summary:**
- 5 different stocks
- Total invested: ₹82,530.00
- Diversified across IT, Banking, Energy sectors

### Scenario 4: Importing Historical Trades

**Situation:** You've been investing for years and want to import all past trades.

**Steps:**

1. **Gather all trade confirmations** (broker statements, emails, etc.)

2. **Create comprehensive CSV:**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2023-01-10,500325,Reliance Industries Ltd,20,1250.00,BUY
2023-03-15,532540,TCS Ltd,10,3100.00,BUY
2023-06-20,500180,HDFC Bank Ltd,30,900.00,BUY
2023-09-10,500325,Reliance Industries Ltd,15,1300.00,BUY
2024-01-15,532540,TCS Ltd,5,3250.00,BUY
2024-06-20,500180,HDFC Bank Ltd,20,950.00,BUY
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
```

3. **Import all at once:**
```bash
python trade_importer.py --file historical_trades.csv
```

4. **Verify import:**
```bash
python portfolio_dashboard.py --trades
```

### Scenario 5: Fractional Purchases (Bonus/Split)

**Situation:** You received bonus shares or stock split.

**Note:** Record as separate BUY transaction with price = 0

**Example (1:1 Bonus):**
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY
2025-06-15,500325,Reliance Industries Ltd,10,0.00,BUY
```

**Result:**
- Original: 10 shares @ ₹1,450
- Bonus: 10 shares @ ₹0
- Total: 20 shares
- Average price: ₹725 (₹14,500 / 20)

---

## Best Practices

### 1. Record Immediately

Record purchases as soon as you make them:

```bash
# Create today's purchase file
DATE=$(date +%Y-%m-%d)
echo "trade_date,scrip_code,scrip_name,quantity,price,trade_type
$DATE,500325,Reliance Industries Ltd,10,1450.00,BUY" > purchase_$DATE.csv

# Import
python trade_importer.py --file purchase_$DATE.csv
```

### 2. Use Consistent Naming

Keep your files organized:
```
trades/
├── 2025-01-15_reliance_buy.csv
├── 2025-02-10_tcs_buy.csv
├── 2025-03-05_hdfc_buy.csv
└── 2025_Q1_all_trades.csv
```

### 3. Verify Before Importing

Always check your file before importing:

```bash
# View file contents
cat purchase.csv

# Or open in Excel to verify
# Then import
python trade_importer.py --file purchase.csv
```

### 4. Update Prices After Import

```bash
# Import trades
python trade_importer.py --file purchases.csv

# Update current prices
python price_updater.py --all

# View updated portfolio
python portfolio_dashboard.py --all
```

### 5. Keep Backup of Trade Files

```bash
# Create backup directory
mkdir -p trades_backup

# Copy all trade files
cp *.csv trades_backup/

# Or create dated backup
cp purchase.csv trades_backup/purchase_$(date +%Y%m%d).csv
```

### 6. Regular Database Backups

```bash
# Backup database weekly
cp data/portfolio.db data/portfolio_backup_$(date +%Y%m%d).db

# Keep last 4 weeks
find data/ -name "portfolio_backup_*.db" -mtime +28 -delete
```

### 7. Validate Data Entry

**Checklist before importing:**
- [ ] Date format is YYYY-MM-DD
- [ ] Scrip code is 6 digits
- [ ] Quantity is whole number
- [ ] Price has no currency symbols or commas
- [ ] Trade type is exactly "BUY"
- [ ] No extra spaces in data
- [ ] File saved with .csv extension

---

## Troubleshooting

### Issue 1: "Column not found" Error

**Problem:**
```
❌ Error: Required column 'trade_date' not found
```

**Solution:**
Check your CSV header row. It must be exactly:
```csv
trade_date,scrip_code,scrip_name,quantity,price,trade_type
```

**Common mistakes:**
- Extra spaces: `trade_date , scrip_code`
- Wrong names: `date,code,name,qty,rate,type`
- Missing columns

### Issue 2: Date Format Error

**Problem:**
```
❌ Error: Invalid date format for row 1
```

**Solution:**
Use YYYY-MM-DD format:
- ✅ Correct: `2025-01-15`
- ❌ Wrong: `15/01/2025`, `Jan 15, 2025`, `15-01-2025`

### Issue 3: Import Shows 0 Successful

**Problem:**
```
Import Summary:
- Total trades: 3
- Successful: 0
- Failed: 3
```

**Solution:**
Check the log file for specific errors:
```bash
tail -n 50 logs/stock_fetcher.log
```

Common causes:
- Invalid date format
- Non-numeric quantity or price
- Wrong trade_type (not "BUY")
- Missing required fields

### Issue 4: Duplicate Entries

**Problem:** Same trade imported twice.

**Solution:**
The system allows duplicates (you might buy same stock multiple times). To avoid:

1. Check existing trades before importing:
```bash
python portfolio_dashboard.py --trades
```

2. If duplicate found, you can manually remove from database:
```bash
sqlite3 data/portfolio.db
DELETE FROM trades WHERE id = <trade_id>;
.quit
```

### Issue 5: Wrong Scrip Code

**Problem:** Imported with wrong scrip code.

**Solution:**

1. **Find the trade ID:**
```bash
sqlite3 data/portfolio.db
SELECT * FROM trades WHERE scrip_code = '500325';
.quit
```

2. **Delete wrong entry:**
```bash
sqlite3 data/portfolio.db
DELETE FROM trades WHERE id = <trade_id>;
.quit
```

3. **Import correct entry:**
```bash
python trade_importer.py --file corrected_purchase.csv
```

### Issue 6: Excel File Not Working

**Problem:**
```
❌ Error: Excel file format cannot be determined
```

**Solution:**
Use CSV format instead:

1. Open Excel file
2. Save As → CSV (Comma delimited)
3. Import the CSV file:
```bash
python trade_importer.py --file purchase.csv
```

### Issue 7: Price Not Showing Decimals

**Problem:** Price shows as 1450 instead of 1450.50

**Solution:**
This is just display formatting. The actual value is stored correctly. To verify:
```bash
sqlite3 data/portfolio.db
SELECT * FROM trades WHERE scrip_code = '500325';
.quit
```

---

## Quick Reference

### Create and Import Single Purchase

```bash
# One-liner to create and import
echo "trade_date,scrip_code,scrip_name,quantity,price,trade_type
2025-01-15,500325,Reliance Industries Ltd,10,1450.00,BUY" > buy.csv && python trade_importer.py --file buy.csv
```

### Template Generation

```bash
python trade_importer.py --template purchases.xlsx
```

### Import and View

```bash
python trade_importer.py --file purchases.csv && python portfolio_dashboard.py --all
```

### Complete Workflow

```bash
# 1. Generate template
python trade_importer.py --template my_trades.xlsx

# 2. Edit file (open in Excel)

# 3. Import
python trade_importer.py --file my_trades.xlsx

# 4. Update prices
python price_updater.py --all

# 5. View portfolio
python portfolio_dashboard.py --all
```

---

## Summary

✅ **Key Points:**
1. Use template for correct format
2. Date format: YYYY-MM-DD
3. Trade type must be "BUY" (all caps)
4. Import multiple purchases at once
5. Update prices after import
6. Verify import with dashboard
7. Keep backups of trade files

✅ **Common File Formats:**
- Excel: `.xlsx` (use template)
- CSV: `.csv` (manual creation)
- Both work equally well

✅ **After Import:**
- Update prices: `python price_updater.py --all`
- View portfolio: `python portfolio_dashboard.py --all`
- Analyze stock: `python portfolio_dashboard.py --stock <code>`

✅ **Best Practice:**
Record trades immediately → Update prices → Review portfolio

---

**Last Updated:** 2025-12-29
**Version:** 1.0