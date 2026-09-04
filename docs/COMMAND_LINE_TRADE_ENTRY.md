# Command Line Trade Entry - Quick Guide

## Overview
Add trades directly from the command line without creating CSV/Excel files. Perfect for quick entries and real-time portfolio updates.

---

## Quick Start

### Add a BUY Trade (Simplest Method)

```bash
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
```

**Output:**
```
================================================================================
✅ TRADE ADDED SUCCESSFULLY!
================================================================================
📅 Date:        2025-12-29 (today)
🏢 Company:     Reliance Industries Ltd (500325)
📊 Type:        BUY
📦 Quantity:    10 shares
💰 Price:       ₹1,450.00 per share
💵 Total:       ₹14,500.00
================================================================================

💡 Next steps:
   1. Update prices: python price_updater.py --all
   2. View portfolio: python portfolio_dashboard.py --all
```

---

## Usage Methods

### Method 1: Quick Entry (Recommended for Daily Use)

**BUY Trade:**
```bash
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
```

**SELL Trade:**
```bash
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL
```

**Features:**
- ✅ Uses today's date automatically
- ✅ Defaults to BUY if type not specified
- ✅ Shortest command possible
- ✅ Perfect for quick entries

### Method 2: Full Command (With Date)

**Specify exact date:**
```bash
python add_trade.py --date 2025-01-15 --code 500325 --name "Reliance Industries Ltd" --quantity 10 --price 1450.00 --type BUY
```

**Use case:**
- Recording past trades
- Backdating entries
- Historical data import

### Method 3: Interactive Mode (Guided Entry)

```bash
python add_trade.py --interactive
```

**Interactive prompts:**
```
📝 INTERACTIVE TRADE ENTRY
================================================================================
Enter trade details (or 'q' to quit)

📅 Trade Date (YYYY-MM-DD) [today]: 2025-01-15
🔢 Scrip Code (6 digits): 500325
🏢 Company Name: Reliance Industries Ltd
📊 Trade Type (BUY/SELL): BUY
📦 Quantity: 10
💰 Price per share: 1450.00

📋 CONFIRM TRADE DETAILS:
--------------------------------------------------------------------------------
Date:     2025-01-15
Company:  Reliance Industries Ltd (500325)
Type:     BUY
Quantity: 10 shares
Price:    ₹1,450.00 per share
Total:    ₹14,500.00
--------------------------------------------------------------------------------

✅ Add this trade? (y/n): y
```

**Features:**
- ✅ Step-by-step guidance
- ✅ Confirmation before adding
- ✅ Default values (today's date)
- ✅ Input validation
- ✅ Cancel anytime with 'q'

---

## Command Options

### Short Form (Quick)

| Option | Description | Example |
|--------|-------------|---------|
| `-c` | Scrip code (6 digits) | `-c 500325` |
| `-n` | Company name | `-n "Reliance Industries Ltd"` |
| `-q` | Quantity | `-q 10` |
| `-p` | Price per share | `-p 1450.00` |
| `-t` | Trade type (BUY/SELL) | `-t SELL` |
| `-d` | Date (YYYY-MM-DD) | `-d 2025-01-15` |
| `-i` | Interactive mode | `-i` |

### Long Form (Explicit)

| Option | Description | Example |
|--------|-------------|---------|
| `--code` | Scrip code | `--code 500325` |
| `--name` | Company name | `--name "Reliance Industries Ltd"` |
| `--quantity` | Quantity | `--quantity 10` |
| `--price` | Price per share | `--price 1450.00` |
| `--type` | Trade type | `--type SELL` |
| `--date` | Date | `--date 2025-01-15` |
| `--interactive` | Interactive mode | `--interactive` |

---

## Common Scrip Codes

Quick reference for popular stocks:

| Code | Company | Sector |
|------|---------|--------|
| 500325 | Reliance Industries Ltd | Energy |
| 532540 | TCS Ltd | IT |
| 500180 | HDFC Bank Ltd | Banking |
| 500112 | State Bank of India | Banking |
| 500209 | Infosys Ltd | IT |
| 532174 | ICICI Bank Ltd | Banking |
| 500010 | HDFC Ltd | Finance |
| 532215 | Axis Bank Ltd | Banking |
| 500696 | Hindustan Unilever Ltd | FMCG |
| 500820 | Asian Paints Ltd | Paints |

---

## Real-World Examples

### Example 1: Just Bought Stock Today

```bash
# Quick entry - uses today's date
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
```

### Example 2: Recording Yesterday's Trade

```bash
# Specify date
python add_trade.py -d 2025-12-28 -c 532540 -n "TCS Ltd" -q 5 -p 3320.00
```

### Example 3: Selling Shares

```bash
# SELL trade
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL
```

### Example 4: Multiple Trades in Sequence

```bash
# Buy multiple stocks
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
python add_trade.py -c 532540 -n "TCS Ltd" -q 5 -p 3320.00
python add_trade.py -c 500180 -n "HDFC Bank Ltd" -q 20 -p 997.00

# Update prices and view
python price_updater.py --all
python portfolio_dashboard.py --all
```

### Example 5: Recording Historical Trade

```bash
# Trade from last month
python add_trade.py -d 2024-11-15 -c 500112 -n "State Bank of India" -q 30 -p 620.00
```

### Example 6: Partial Sale

```bash
# Original purchase
python add_trade.py -d 2025-01-15 -c 500325 -n "Reliance Industries Ltd" -q 20 -p 1450.00

# Partial sale later
python add_trade.py -d 2025-12-29 -c 500325 -n "Reliance Industries Ltd" -q 8 -p 1600.00 -t SELL
```

---

## Complete Workflows

### Workflow 1: Daily Trading Routine

```bash
# Morning: Buy stocks
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
python add_trade.py -c 532540 -n "TCS Ltd" -q 5 -p 3320.00

# Evening: Update prices and review
python price_updater.py --all
python portfolio_dashboard.py --all
```

### Workflow 2: Quick Check and Trade

```bash
# Check current portfolio
python portfolio_dashboard.py --summary

# Add new trade
python add_trade.py -c 500180 -n "HDFC Bank Ltd" -q 15 -p 997.00

# View updated portfolio
python price_updater.py --all
python portfolio_dashboard.py --all
```

### Workflow 3: Selling with Analysis

```bash
# Analyze stock before selling
python portfolio_dashboard.py --stock 500325

# Record sale
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1600.00 -t SELL

# View realized P&L
python portfolio_dashboard.py --summary
```

---

## Comparison: Command Line vs CSV Import

### Command Line Method (add_trade.py)

**Pros:**
- ✅ Instant entry - no file creation needed
- ✅ Perfect for single trades
- ✅ Interactive mode for guidance
- ✅ Immediate feedback
- ✅ Quick for daily use
- ✅ Less typing for frequent traders

**Cons:**
- ❌ Not ideal for bulk imports
- ❌ No visual spreadsheet view
- ❌ One trade at a time

**Best for:**
- Daily trading activities
- Quick entries
- Real-time portfolio updates
- Single trade recording

### CSV Import Method (trade_importer.py)

**Pros:**
- ✅ Bulk import multiple trades
- ✅ Visual editing in Excel
- ✅ Easy to review before import
- ✅ Good for historical data
- ✅ Can prepare offline

**Cons:**
- ❌ Need to create file first
- ❌ Extra steps involved
- ❌ Slower for single trades

**Best for:**
- Historical portfolio import
- Multiple trades at once
- Offline preparation
- Bulk data entry

---

## Tips and Tricks

### Tip 1: Create Aliases (Bash/Zsh)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Quick trade aliases
alias buy='python /path/to/add_trade.py'
alias sell='python /path/to/add_trade.py -t SELL'
alias portfolio='python /path/to/portfolio_dashboard.py --all'
alias prices='python /path/to/price_updater.py --all'

# Usage
buy -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
sell -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00
portfolio
```

### Tip 2: Use Tab Completion

Most terminals support tab completion for file paths and commands:
```bash
python add_<TAB>  # Completes to add_trade.py
```

### Tip 3: Command History

Use up arrow to recall previous commands and modify:
```bash
# First trade
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00

# Press UP arrow, modify quantity and price
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1480.00
```

### Tip 4: Save Common Commands

Create a file `my_trades.sh`:
```bash
#!/bin/bash
# My common trades

# Reliance
alias buy_reliance='python add_trade.py -c 500325 -n "Reliance Industries Ltd"'

# TCS
alias buy_tcs='python add_trade.py -c 532540 -n "TCS Ltd"'

# HDFC Bank
alias buy_hdfc='python add_trade.py -c 500180 -n "HDFC Bank Ltd"'

# Usage: buy_reliance -q 10 -p 1450.00
```

### Tip 5: Quick Price Check Before Trading

```bash
# Check current price
python portfolio_dashboard.py --stock 500325

# Add trade
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
```

### Tip 6: Batch Entry Script

Create `batch_trades.sh`:
```bash
#!/bin/bash
# Add multiple trades

python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
python add_trade.py -c 532540 -n "TCS Ltd" -q 5 -p 3320.00
python add_trade.py -c 500180 -n "HDFC Bank Ltd" -q 20 -p 997.00

# Update and view
python price_updater.py --all
python portfolio_dashboard.py --all
```

Run with: `bash batch_trades.sh`

---

## Input Validation

The tool validates all inputs automatically:

### Date Validation
```bash
# ✅ Correct
python add_trade.py -d 2025-01-15 ...

# ❌ Wrong - will show error
python add_trade.py -d 15-01-2025 ...
python add_trade.py -d 01/15/2025 ...
```

### Scrip Code Validation
```bash
# ✅ Correct - 6 digits
python add_trade.py -c 500325 ...

# ❌ Wrong - will show error
python add_trade.py -c 500 ...
python add_trade.py -c ABC123 ...
```

### Quantity Validation
```bash
# ✅ Correct - positive integer
python add_trade.py -q 10 ...

# ❌ Wrong - will show error
python add_trade.py -q -5 ...
python add_trade.py -q 10.5 ...
```

### Price Validation
```bash
# ✅ Correct - positive number
python add_trade.py -p 1450.00 ...
python add_trade.py -p 1450.50 ...

# ❌ Wrong - will show error
python add_trade.py -p -1450 ...
python add_trade.py -p 0 ...
```

### Trade Type Validation
```bash
# ✅ Correct
python add_trade.py -t BUY ...
python add_trade.py -t SELL ...

# ❌ Wrong - will show error
python add_trade.py -t buy ...
python add_trade.py -t Purchase ...
```

---

## Error Handling

### Error 1: Missing Arguments

**Command:**
```bash
python add_trade.py -c 500325
```

**Error:**
```
❌ Error: Missing required arguments
   Use --interactive for guided entry or provide all arguments
```

**Solution:**
Provide all required arguments: code, name, quantity, price

### Error 2: Invalid Date Format

**Command:**
```bash
python add_trade.py -d 15-01-2025 -c 500325 -n "Reliance" -q 10 -p 1450
```

**Error:**
```
❌ Invalid date format: 15-01-2025
   Use YYYY-MM-DD format (e.g., 2025-01-15)
```

**Solution:**
Use correct date format: `2025-01-15`

### Error 3: Invalid Scrip Code

**Command:**
```bash
python add_trade.py -c 500 -n "Reliance" -q 10 -p 1450
```

**Error:**
```
❌ Invalid scrip code: 500
   Must be 6-digit BSE scrip code (e.g., 500325)
```

**Solution:**
Use 6-digit scrip code: `500325`

---

## Integration with Other Tools

### With Price Updater

```bash
# Add trade and update prices in one go
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00 && python price_updater.py --all
```

### With Dashboard

```bash
# Add trade and view portfolio
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00 && python portfolio_dashboard.py --all
```

### Complete Pipeline

```bash
# Add trade → Update prices → View portfolio
python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00 && \
python price_updater.py --all && \
python portfolio_dashboard.py --all
```

---

## When to Use Each Method

### Use Command Line (add_trade.py) When:
- ✅ Adding single trade immediately after execution
- ✅ Quick daily entries
- ✅ Real-time portfolio updates
- ✅ You want instant feedback
- ✅ Recording trades on-the-go

### Use CSV Import (trade_importer.py) When:
- ✅ Importing historical portfolio (10+ trades)
- ✅ Bulk data entry
- ✅ You have trades in spreadsheet already
- ✅ Need to review before importing
- ✅ Preparing data offline

### Use Interactive Mode When:
- ✅ Learning the system
- ✅ Unsure about command syntax
- ✅ Want step-by-step guidance
- ✅ Need confirmation before adding

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                  QUICK TRADE ENTRY COMMANDS                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  BUY (Today):                                               │
│  python add_trade.py -c CODE -n "NAME" -q QTY -p PRICE     │
│                                                              │
│  SELL (Today):                                              │
│  python add_trade.py -c CODE -n "NAME" -q QTY -p PRICE -t SELL │
│                                                              │
│  With Date:                                                  │
│  python add_trade.py -d YYYY-MM-DD -c CODE -n "NAME" -q QTY -p PRICE │
│                                                              │
│  Interactive:                                                │
│  python add_trade.py --interactive                          │
│                                                              │
│  Help:                                                       │
│  python add_trade.py --help                                 │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Common Codes: 500325=Reliance, 532540=TCS, 500180=HDFC   │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary

✅ **Command Line Trade Entry Benefits:**
- Instant trade recording
- No file creation needed
- Perfect for daily use
- Interactive mode available
- Automatic validation
- Immediate feedback

✅ **Three Usage Methods:**
1. Quick entry (shortest command)
2. Full command (with all options)
3. Interactive mode (guided)

✅ **Best Practices:**
- Use quick entry for daily trades
- Use interactive mode when learning
- Create aliases for frequent use
- Combine with price updater
- View portfolio after adding

✅ **Next Steps:**
- Try interactive mode first
- Create your own aliases
- Integrate into daily workflow
- Combine with other tools

---

**Last Updated:** 2025-12-29
**Version:** 1.0