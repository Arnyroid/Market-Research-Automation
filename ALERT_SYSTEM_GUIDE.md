# Portfolio Alert System Guide

## Overview

The Portfolio Alert System provides real-time notifications for important portfolio events. Get desktop notifications when stocks hit target prices, trigger stop-losses, or experience significant price changes.

## Alert Types

### 1. **Target Price Alerts**
Get notified when a stock reaches your target price (for buying or selling).

**Use Cases:**
- Set selling targets for profit-taking
- Set buying targets for entry points
- Track resistance/support levels

**Example:**
```bash
# Alert when Reliance crosses ₹2500 (upward)
python3 alert_manager.py --add --scrip 500325 --name "Reliance Industries" \
  --type TARGET_PRICE --condition ABOVE --value 2500

# Alert when Reliance drops below ₹2200 (downward)
python3 alert_manager.py --add --scrip 500325 --name "Reliance Industries" \
  --type TARGET_PRICE --condition BELOW --value 2200
```

### 2. **Stop-Loss Alerts**
Protect your investments with automatic stop-loss notifications.

**Use Cases:**
- Risk management
- Prevent large losses
- Automatic exit signals

**Example:**
```bash
# Stop-loss at ₹2200
python3 alert_manager.py --add --scrip 500325 --name "Reliance Industries" \
  --type STOP_LOSS --condition BELOW --value 2200 \
  --notes "Emergency exit point"
```

### 3. **Price Change Alerts**
Get notified of significant daily price movements (percentage-based).

**Use Cases:**
- Catch sudden price surges
- Detect unusual volatility
- Monitor market sentiment

**Example:**
```bash
# Alert on 5% price increase
python3 alert_manager.py --add --scrip 500325 --name "Reliance Industries" \
  --type PRICE_CHANGE --condition CHANGE_UP --value 5

# Alert on 5% price decrease
python3 alert_manager.py --add --scrip 500325 --name "Reliance Industries" \
  --type PRICE_CHANGE --condition CHANGE_DOWN --value 5
```

## Command-Line Usage

### Add Alert Rules

```bash
# Basic syntax
python3 alert_manager.py --add \
  --scrip <SCRIP_CODE> \
  --name "<COMPANY_NAME>" \
  --type <ALERT_TYPE> \
  --condition <CONDITION> \
  --value <THRESHOLD> \
  --notes "<OPTIONAL_NOTES>"
```

**Parameters:**
- `--scrip`: BSE scrip code (e.g., 500325 for Reliance)
- `--name`: Company name
- `--type`: Alert type (TARGET_PRICE, STOP_LOSS, PRICE_CHANGE)
- `--condition`: Condition (ABOVE, BELOW, CHANGE_UP, CHANGE_DOWN)
- `--value`: Threshold value (price or percentage)
- `--notes`: Optional notes

### List Active Alerts

```bash
# List all active alerts
python3 alert_manager.py --list
```

**Output:**
```
📋 Active Alerts (3):
================================================================================

ID: 1
Stock: Reliance Industries (500325)
Type: TARGET_PRICE
Condition: ABOVE 2500.0
Notes: Target price for selling

ID: 2
Stock: Reliance Industries (500325)
Type: STOP_LOSS
Condition: BELOW 2200.0
Notes: Stop loss protection

ID: 3
Stock: Reliance Industries (500325)
Type: PRICE_CHANGE
Condition: CHANGE_UP 5.0
Notes: Alert on 5% price increase
```

### View Alert History

```bash
# View last 7 days of triggered alerts
python3 alert_manager.py --history

# View last 30 days
python3 alert_manager.py --history --days 30
```

### Deactivate Alert

```bash
# Temporarily disable an alert (keeps it in database)
python3 alert_manager.py --deactivate --id 1
```

### Delete Alert

```bash
# Permanently remove an alert
python3 alert_manager.py --delete --id 1
```

## Desktop Notifications

Alerts are delivered via desktop notifications:

### macOS
- Native notification center
- Sound alert included
- Appears in top-right corner

### Windows
- Windows 10/11 toast notifications
- Action center integration
- Customizable duration

### Linux
- notify-send integration
- Desktop environment compatible
- Configurable appearance

### Fallback
If desktop notifications aren't available, alerts are displayed in the console with clear formatting.

## Integration with Price Updates

Alerts are automatically checked when you update prices:

```bash
# Update all portfolio prices (checks all alerts)
python3 price_updater.py --all

# Update single stock (checks alerts for that stock)
python3 price_updater.py --scrip 500325
```

**Alert checking happens automatically:**
1. Price is fetched from BSE
2. Previous price is retrieved from database
3. All active alerts for the stock are checked
4. Matching alerts trigger desktop notifications
5. Alert history is logged

## Alert Conditions Explained

### TARGET_PRICE
- **ABOVE**: Triggers when current price >= threshold
- **BELOW**: Triggers when current price <= threshold

### STOP_LOSS
- **BELOW**: Triggers when current price <= threshold
- (Typically used with BELOW only)

### PRICE_CHANGE
- **CHANGE_UP**: Triggers when price increases by threshold %
- **CHANGE_DOWN**: Triggers when price decreases by threshold %

**Formula:** `change_percent = ((current_price - previous_price) / previous_price) * 100`

## Best Practices

### 1. **Set Realistic Targets**
```bash
# Good: Reasonable 10% target
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 2750

# Avoid: Unrealistic 100% target
# (May never trigger)
```

### 2. **Use Stop-Loss for Risk Management**
```bash
# Set stop-loss at 5-10% below purchase price
# If bought at ₹2500, set stop-loss at ₹2250 (10% loss)
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type STOP_LOSS --condition BELOW --value 2250
```

### 3. **Monitor Volatility with Price Change Alerts**
```bash
# For volatile stocks: 3-5% threshold
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type PRICE_CHANGE --condition CHANGE_UP --value 3

# For stable stocks: 1-2% threshold
python3 alert_manager.py --add --scrip 532174 --name "HDFC Bank" \
  --type PRICE_CHANGE --condition CHANGE_UP --value 1
```

### 4. **Review and Update Regularly**
```bash
# Check alert history weekly
python3 alert_manager.py --history --days 7

# Deactivate outdated alerts
python3 alert_manager.py --deactivate --id 5

# Add new alerts based on market conditions
```

### 5. **Combine Multiple Alert Types**
```bash
# For a single stock, set:
# 1. Target price (profit-taking)
# 2. Stop-loss (risk management)
# 3. Price change alerts (volatility monitoring)

# Example for Reliance:
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 2800

python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type STOP_LOSS --condition BELOW --value 2200

python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type PRICE_CHANGE --condition CHANGE_UP --value 5
```

## Automated Alert Checking

### Option 1: Manual Updates
```bash
# Run manually when needed
python3 price_updater.py --all
```

### Option 2: Scheduled Updates
Use the scheduler to automatically check prices and alerts:

```bash
# Update prices every hour during market hours
python3 scheduler.py --mode market_hours
```

### Option 3: Cron Job (Linux/macOS)
```bash
# Edit crontab
crontab -e

# Add line to check every 30 minutes during market hours (9:30 AM - 3:30 PM IST)
*/30 9-15 * * 1-5 cd /path/to/project && python3 price_updater.py --all
```

### Option 4: Task Scheduler (Windows)
1. Open Task Scheduler
2. Create new task
3. Set trigger: Daily at 9:30 AM
4. Set action: Run `python3 price_updater.py --all`
5. Set repeat: Every 30 minutes for 6 hours

## Alert Database Schema

Alerts are stored in two tables:

### alert_rules
Stores active and inactive alert configurations.

**Columns:**
- `id`: Unique alert ID
- `scrip_code`: BSE scrip code
- `scrip_name`: Company name
- `alert_type`: Type of alert
- `condition`: Trigger condition
- `threshold_value`: Threshold price/percentage
- `is_active`: Active status (1/0)
- `created_at`: Creation timestamp
- `last_triggered`: Last trigger timestamp
- `notes`: User notes

### alert_history
Logs all triggered alerts.

**Columns:**
- `id`: Unique history ID
- `alert_rule_id`: Reference to alert rule
- `scrip_code`: BSE scrip code
- `scrip_name`: Company name
- `alert_type`: Type of alert
- `trigger_price`: Price that triggered alert
- `threshold_value`: Threshold value
- `message`: Alert message
- `triggered_at`: Trigger timestamp
- `notification_sent`: Notification status

## Troubleshooting

### Desktop Notifications Not Working

**macOS:**
```bash
# Check if notifications are enabled for Terminal
# System Preferences > Notifications > Terminal > Allow Notifications
```

**Windows:**
```bash
# Install win10toast if missing
pip install win10toast
```

**Linux:**
```bash
# Install notify-send if missing
sudo apt-get install libnotify-bin  # Ubuntu/Debian
sudo yum install libnotify           # CentOS/RHEL
```

### Alerts Not Triggering

1. **Check if alert is active:**
   ```bash
   python3 alert_manager.py --list
   ```

2. **Verify price updates are running:**
   ```bash
   python3 price_updater.py --scrip 500325
   ```

3. **Check alert history:**
   ```bash
   python3 alert_manager.py --history
   ```

4. **Review logs:**
   ```bash
   tail -f logs/stock_fetcher.log
   ```

### Alert Triggered Multiple Times

Alerts trigger every time the condition is met. To prevent repeated notifications:

1. **Deactivate after first trigger:**
   ```bash
   python3 alert_manager.py --deactivate --id 1
   ```

2. **Delete after trigger:**
   ```bash
   python3 alert_manager.py --delete --id 1
   ```

3. **Adjust threshold:**
   - For TARGET_PRICE: Set higher/lower threshold
   - For PRICE_CHANGE: Increase percentage threshold

## Examples

### Example 1: Day Trading Setup
```bash
# Set tight stop-loss (2% below entry)
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type STOP_LOSS --condition BELOW --value 2450

# Set profit target (3% above entry)
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 2575

# Monitor for sudden moves
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type PRICE_CHANGE --condition CHANGE_UP --value 2
```

### Example 2: Long-Term Investment
```bash
# Set wide stop-loss (15% below entry)
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type STOP_LOSS --condition BELOW --value 2125

# Set ambitious target (25% above entry)
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 3125

# Monitor for major moves only
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type PRICE_CHANGE --condition CHANGE_DOWN --value 10
```

### Example 3: Swing Trading
```bash
# Multiple targets for partial exits
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 2600 \
  --notes "Exit 33% position"

python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 2700 \
  --notes "Exit 33% position"

python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type TARGET_PRICE --condition ABOVE --value 2800 \
  --notes "Exit remaining 34%"

# Trailing stop-loss
python3 alert_manager.py --add --scrip 500325 --name "Reliance" \
  --type STOP_LOSS --condition BELOW --value 2400
```

## Tips

1. **Start Simple**: Begin with basic target and stop-loss alerts
2. **Test First**: Add alerts for one stock and verify they work
3. **Adjust Thresholds**: Fine-tune based on stock volatility
4. **Review Regularly**: Check alert history to optimize settings
5. **Clean Up**: Delete or deactivate outdated alerts
6. **Use Notes**: Add context to remember why you set each alert
7. **Combine with Analysis**: Use alerts alongside technical analysis
8. **Don't Over-Alert**: Too many alerts can cause notification fatigue

## Support

For issues or questions:
1. Check logs: `logs/stock_fetcher.log`
2. Review alert history: `python3 alert_manager.py --history`
3. Test notifications manually
4. Verify database tables exist: `alert_rules` and `alert_history`

---

**Happy Trading! 📈**