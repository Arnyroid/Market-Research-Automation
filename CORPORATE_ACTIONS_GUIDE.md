# Corporate Actions Guide

## Overview

The Corporate Actions module helps you track and manage dividends, bonus shares, stock splits, and rights issues in your portfolio. It automatically updates your holdings and maintains a complete history of all corporate actions.

## Supported Corporate Actions

### 1. **Dividends** 💰
Record cash dividends received from companies.

**What it does:**
- Records dividend amount per share
- Calculates total dividend based on your holdings
- Maintains dividend history for tax purposes

**Example:**
```bash
# Record dividend of ₹10.50 per share
python3 corporate_actions.py --dividend \
  --date 2025-03-15 \
  --code 500325 \
  --name "Reliance Industries" \
  --amount 10.50 \
  --notes "Interim dividend"
```

### 2. **Bonus Shares** 🎁
Record bonus shares issued by companies.

**What it does:**
- Calculates bonus shares based on ratio
- Updates portfolio quantity automatically
- Adjusts average cost per share (cost basis spread over more shares)
- Maintains bonus history

**Example:**
```bash
# Record 1:2 bonus (1 bonus share for every 2 held)
python3 corporate_actions.py --bonus \
  --date 2025-06-01 \
  --code 500325 \
  --name "Reliance Industries" \
  --ratio "1:2" \
  --notes "Bonus issue announced"
```

**How Bonus Works:**
- If you hold 100 shares
- Bonus ratio is 1:2
- You receive: (100 ÷ 2) × 1 = 50 bonus shares
- New total: 150 shares
- Average price adjusts: Original investment ÷ 150 shares

### 3. **Stock Splits** ✂️
Record stock splits (face value reduction).

**What it does:**
- Calculates new share quantity based on split ratio
- Adjusts share price proportionally
- Updates portfolio automatically
- Maintains split history

**Example:**
```bash
# Record 1:2 split (1 share becomes 2)
python3 corporate_actions.py --split \
  --date 2025-09-01 \
  --code 500325 \
  --name "Reliance Industries" \
  --ratio "1:2" \
  --notes "Stock split from ₹10 to ₹5 face value"
```

**How Split Works:**
- If you hold 100 shares at ₹2500 each
- Split ratio is 1:2
- You get: 100 × 2 = 200 shares
- New price: ₹2500 ÷ 2 = ₹1250 per share
- Total value remains same: ₹2,50,000

## Command-Line Usage

### Record Dividend

```bash
python3 corporate_actions.py --dividend \
  --date YYYY-MM-DD \
  --code SCRIP_CODE \
  --name "COMPANY_NAME" \
  --amount AMOUNT_PER_SHARE \
  --notes "OPTIONAL_NOTES"
```

**Parameters:**
- `--date`: Dividend payment date
- `--code`: BSE scrip code (6 digits)
- `--name`: Company name
- `--amount`: Dividend amount per share (in ₹)
- `--notes`: Optional notes

**Output:**
```
================================================================================
💰 DIVIDEND RECORDED SUCCESSFULLY!
================================================================================
📅 Date:              2025-03-15
🏢 Company:           Reliance Industries (500325)
📦 Shares Held:       100
💵 Per Share:         ₹10.50
💰 Total Dividend:    ₹1,050.00
📝 Notes:             Interim dividend
================================================================================
```

### Record Bonus Shares

```bash
python3 corporate_actions.py --bonus \
  --date YYYY-MM-DD \
  --code SCRIP_CODE \
  --name "COMPANY_NAME" \
  --ratio "BONUS:HELD" \
  --notes "OPTIONAL_NOTES"
```

**Ratio Format:**
- `1:1` = 1 bonus for every 1 held (100% bonus)
- `1:2` = 1 bonus for every 2 held (50% bonus)
- `1:4` = 1 bonus for every 4 held (25% bonus)
- `2:5` = 2 bonus for every 5 held (40% bonus)

**Output:**
```
================================================================================
🎁 BONUS SHARES RECORDED SUCCESSFULLY!
================================================================================
📅 Date:              2025-06-01
🏢 Company:           Reliance Industries (500325)
📊 Bonus Ratio:       1:2
📦 Shares Held:       100
🎁 Bonus Received:    50 shares
📈 New Total:         150 shares
💰 Old Avg Price:     ₹2,500.00
💰 New Avg Price:     ₹1,666.67
📝 Notes:             Bonus issue announced
================================================================================

💡 Portfolio updated with bonus shares!
```

### Record Stock Split

```bash
python3 corporate_actions.py --split \
  --date YYYY-MM-DD \
  --code SCRIP_CODE \
  --name "COMPANY_NAME" \
  --ratio "OLD:NEW" \
  --notes "OPTIONAL_NOTES"
```

**Ratio Format:**
- `1:2` = 1 share becomes 2 (2-for-1 split)
- `1:5` = 1 share becomes 5 (5-for-1 split)
- `1:10` = 1 share becomes 10 (10-for-1 split)

**Output:**
```
================================================================================
✂️  STOCK SPLIT RECORDED SUCCESSFULLY!
================================================================================
📅 Date:              2025-09-01
🏢 Company:           Reliance Industries (500325)
📊 Split Ratio:       1:2
📦 Old Quantity:      100
📈 New Quantity:      200
💰 Old Avg Price:     ₹2,500.00
💰 New Avg Price:     ₹1,250.00
📝 Notes:             Stock split from ₹10 to ₹5 face value
================================================================================
```

### View Corporate Actions History

```bash
# View all corporate actions
python3 corporate_actions.py --list

# View only dividends
python3 corporate_actions.py --list --type DIVIDEND

# View only bonus shares
python3 corporate_actions.py --list --type BONUS

# View only stock splits
python3 corporate_actions.py --list --type SPLIT

# View actions for specific stock
python3 corporate_actions.py --list --code 500325
```

**Output:**
```
📋 Corporate Actions (3):
====================================================================================================

2025-09-01 - SPLIT
Company: Reliance Industries (500325)
Ratio: 1:2
Shares: 100
Notes: Stock split from ₹10 to ₹5 face value
----------------------------------------------------------------------------------------------------

2025-06-01 - BONUS
Company: Reliance Industries (500325)
Ratio: 1:2
Shares: 50
Notes: Bonus issue announced
----------------------------------------------------------------------------------------------------

2025-03-15 - DIVIDEND
Company: Reliance Industries (500325)
Shares: 100
Total Dividend: ₹1,050.00
Notes: Interim dividend
----------------------------------------------------------------------------------------------------
```

## Real-World Examples

### Example 1: Quarterly Dividend

```bash
# Company declares ₹8 per share dividend
python3 corporate_actions.py --dividend \
  --date 2025-03-31 \
  --code 500325 \
  --name "Reliance Industries" \
  --amount 8.00 \
  --notes "Q4 FY2024-25 dividend"

# If you hold 200 shares, you receive ₹1,600
```

### Example 2: Bonus Issue

```bash
# Company announces 1:1 bonus (100% bonus)
python3 corporate_actions.py --bonus \
  --date 2025-07-15 \
  --code 532540 \
  --name "TCS Ltd" \
  --ratio "1:1" \
  --notes "1:1 bonus issue"

# Before: 50 shares at ₹3,500 = ₹1,75,000
# After: 100 shares at ₹1,750 = ₹1,75,000 (value unchanged)
```

### Example 3: Stock Split

```bash
# Company splits stock 1:5 (₹10 to ₹2 face value)
python3 corporate_actions.py --split \
  --date 2025-10-01 \
  --code 500180 \
  --name "HDFC Bank" \
  --ratio "1:5" \
  --notes "Face value reduction from ₹10 to ₹2"

# Before: 20 shares at ₹1,500 = ₹30,000
# After: 100 shares at ₹300 = ₹30,000 (value unchanged)
```

### Example 4: Multiple Dividends in a Year

```bash
# Interim dividend (Q2)
python3 corporate_actions.py --dividend \
  --date 2025-09-30 \
  --code 500112 \
  --name "State Bank of India" \
  --amount 5.50 \
  --notes "Interim dividend Q2"

# Final dividend (Q4)
python3 corporate_actions.py --dividend \
  --date 2026-03-31 \
  --code 500112 \
  --name "State Bank of India" \
  --amount 7.50 \
  --notes "Final dividend Q4"

# Total annual dividend: ₹13 per share
```

## Understanding the Impact

### Dividend Impact
- **Portfolio Value**: No change
- **Cash Flow**: Increases (you receive cash)
- **Quantity**: No change
- **Average Price**: No change
- **Tax**: Dividend income is taxable

### Bonus Impact
- **Portfolio Value**: No immediate change
- **Cash Flow**: No change
- **Quantity**: Increases
- **Average Price**: Decreases (cost spread over more shares)
- **Tax**: No immediate tax (taxed when you sell)

### Split Impact
- **Portfolio Value**: No change
- **Cash Flow**: No change
- **Quantity**: Increases
- **Average Price**: Decreases proportionally
- **Tax**: No tax implications

## Tax Considerations

### Dividends
- Taxable as "Income from Other Sources"
- TDS may be deducted at source
- Include in ITR under appropriate head
- Keep dividend records for tax filing

### Bonus Shares
- Not taxable at the time of receipt
- Cost of acquisition is ZERO
- Taxed as capital gains when sold
- Holding period starts from original purchase date

### Stock Splits
- Not a taxable event
- Cost of acquisition remains same (spread over more shares)
- Holding period continues from original purchase

## Best Practices

### 1. **Record Immediately**
```bash
# Record corporate actions as soon as announced
# Don't wait for credit to demat account
python3 corporate_actions.py --bonus --date 2025-06-01 ...
```

### 2. **Keep Notes**
```bash
# Add detailed notes for future reference
--notes "1:2 bonus announced on 2025-05-15, record date 2025-05-25"
```

### 3. **Verify Portfolio**
```bash
# After recording, verify portfolio is updated correctly
python3 portfolio_dashboard.py --all
```

### 4. **Maintain Records**
```bash
# Regularly export corporate actions for tax filing
python3 corporate_actions.py --list > corporate_actions_2025.txt
```

### 5. **Track Dividends**
```bash
# View all dividends for the year
python3 corporate_actions.py --list --type DIVIDEND

# Calculate total dividend income
# Sum up all dividend amounts for tax filing
```

## Common Scenarios

### Scenario 1: Received Bonus but Not Reflected

**Problem:** Bonus shares credited to demat but portfolio not updated

**Solution:**
```bash
# Manually record the bonus
python3 corporate_actions.py --bonus \
  --date CREDIT_DATE \
  --code SCRIP_CODE \
  --name "COMPANY_NAME" \
  --ratio "RATIO"
```

### Scenario 2: Multiple Dividends

**Problem:** Company pays interim and final dividends

**Solution:**
```bash
# Record each dividend separately
python3 corporate_actions.py --dividend --date 2025-09-30 --amount 5.00 ...
python3 corporate_actions.py --dividend --date 2026-03-31 --amount 8.00 ...
```

### Scenario 3: Fractional Shares

**Problem:** Bonus calculation results in fractional shares

**Solution:**
- System rounds down to nearest whole number
- Companies typically pay cash for fractional shares
- Record cash received as dividend

### Scenario 4: Rights Issue

**Problem:** Need to track rights issue

**Solution:**
```bash
# Record as a BUY trade at rights price
python3 add_trade.py --code 500325 --name "Reliance" \
  --qty 25 --price 2200 --type BUY --notes "Rights issue 1:4 @ ₹2200"
```

## Integration with Portfolio

### Automatic Updates

When you record corporate actions:

1. **Bonus/Split**: Portfolio quantity and average price update automatically
2. **Dividend**: Recorded in corporate actions table (cash not added to portfolio)
3. **History**: All actions logged for audit trail

### Viewing Impact

```bash
# View updated portfolio
python3 portfolio_dashboard.py --all

# View corporate actions history
python3 corporate_actions.py --list

# Generate report with corporate actions
python3 report_generator.py --pdf
```

## Troubleshooting

### Issue: "Stock not found in portfolio"

**Cause:** Trying to record corporate action for stock you don't own

**Solution:**
```bash
# First add a BUY trade
python3 add_trade.py --code 500325 --name "Reliance" --qty 10 --price 2500

# Then record corporate action
python3 corporate_actions.py --bonus --date 2025-06-01 --code 500325 ...
```

### Issue: "Invalid ratio format"

**Cause:** Ratio not in correct format

**Solution:**
```bash
# Correct format: "BONUS:HELD" or "OLD:NEW"
--ratio "1:2"  # Correct
--ratio "1-2"  # Wrong
--ratio "1/2"  # Wrong
```

### Issue: Portfolio quantity mismatch

**Cause:** Bonus/split recorded incorrectly

**Solution:**
```bash
# View corporate actions
python3 corporate_actions.py --list --code 500325

# If wrong, reset and re-record
python3 reset_database.py --table corporate_actions
python3 reset_database.py --table portfolio
# Re-import trades and record actions correctly
```

## Tips

1. **Record Promptly**: Record corporate actions as soon as announced
2. **Use Notes**: Add detailed notes for future reference
3. **Verify**: Always verify portfolio after recording
4. **Keep Records**: Maintain corporate actions history for tax filing
5. **Backup**: Backup database before recording major actions
6. **Check Dates**: Use record date, not announcement date
7. **Fractional Shares**: Round down and record cash separately
8. **Rights Issue**: Record as regular BUY trade with notes

## Support

For issues or questions:
1. Check logs: `logs/stock_fetcher.log`
2. View corporate actions: `python3 corporate_actions.py --list`
3. Verify portfolio: `python3 portfolio_dashboard.py --all`
4. Check database: Ensure `corporate_actions` table exists

---

**Happy Investing! 📈**