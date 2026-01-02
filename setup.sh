#!/bin/bash
# Setup script for BSE Stock Data Fetcher & Portfolio Manager

echo "🚀 Setting up BSE Stock Data Fetcher & Portfolio Manager..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating data and logs directories..."
mkdir -p data
mkdir -p logs
mkdir -p reports

# Copy environment file
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your settings"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "from portfolio_db import PortfolioDB; db = PortfolioDB(); db.create_tables(); print('✅ Database initialized successfully!')"

echo ""
echo "✨ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 STOCK DATA FETCHING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Edit .env file if needed: nano .env"
echo "  3. Run once to test: python3 scheduler.py once"
echo "  4. Run continuously: python3 scheduler.py interval"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💼 PORTFOLIO MANAGEMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📝 Quick Trade Entry:"
echo "    - Add BUY:     python3 add_trade.py -c 500325 -n \"Reliance\" -q 10 -p 2500"
echo "    - Add SELL:    python3 add_trade.py -c 500325 -n \"Reliance\" -q 5 -p 2600 -t SELL"
echo "    - Interactive: python3 add_trade.py --interactive"
echo ""
echo "  📦 Bulk Import:"
echo "    - Generate template: python3 trade_importer.py --template trades.xlsx"
echo "    - Import trades:     python3 trade_importer.py --file trades.xlsx"
echo ""
echo "  💰 Corporate Actions:"
echo "    - Dividend: python3 corporate_actions.py --dividend --date 2025-03-15 --code 500325 --name \"Reliance\" --amount 10.50"
echo "    - Bonus:    python3 corporate_actions.py --bonus --date 2025-06-01 --code 500325 --name \"Reliance\" --ratio \"1:2\""
echo "    - Split:    python3 corporate_actions.py --split --date 2025-09-01 --code 500325 --name \"Reliance\" --ratio \"1:2\""
echo "    - View:     python3 corporate_actions.py --list"
echo ""
echo "  📈 Price Updates:"
echo "    - Update all:    python3 price_updater.py --all"
echo "    - Update single: python3 price_updater.py --scrip 500325"
echo ""
echo "  📊 View Portfolio:"
echo "    - Dashboard:     python3 portfolio_dashboard.py --all"
echo "    - Single stock:  python3 portfolio_dashboard.py --scrip 500325"
echo "    - Summary only:  python3 portfolio_dashboard.py --summary"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔔 ALERT SYSTEM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🎯 Set Alerts:"
echo "    - Target price: python3 alert_manager.py --add --scrip 500325 --name \"Reliance\" --type TARGET_PRICE --condition ABOVE --value 2500"
echo "    - Stop loss:    python3 alert_manager.py --add --scrip 500325 --name \"Reliance\" --type STOP_LOSS --condition BELOW --value 2200"
echo "    - Price change: python3 alert_manager.py --add --scrip 500325 --name \"Reliance\" --type PRICE_CHANGE --condition CHANGE_UP --value 5"
echo ""
echo "  📋 Manage Alerts:"
echo "    - List active:  python3 alert_manager.py --list"
echo "    - View history: python3 alert_manager.py --history"
echo "    - Deactivate:   python3 alert_manager.py --deactivate --id 1"
echo "    - Delete:       python3 alert_manager.py --delete --id 1"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 REPORTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📊 Generate Reports:"
echo "    - CSV reports: python3 report_generator.py --csv"
echo "    - PDF report:  python3 report_generator.py --pdf"
echo "    - Both:        python3 report_generator.py --csv --pdf"
echo "    - Custom name: python3 report_generator.py --csv --output my_portfolio"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  DATABASE MANAGEMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🔄 Reset Database:"
echo "    - Reset all:         python3 reset_database.py --all"
echo "    - Reset trades only: python3 reset_database.py --table trades"
echo "    - Reset alerts only: python3 reset_database.py --table alert_rules"
echo ""
echo "  💾 Backup Database:"
echo "    - cp data/portfolio.db data/portfolio_backup_\$(date +%Y%m%d_%H%M%S).db"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 DOCUMENTATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📖 Guides:"
echo "    - QUICK_START.md                - Quick start guide"
echo "    - README.md                     - Complete documentation"
echo "    - COMMAND_LINE_TRADE_ENTRY.md   - Trade entry guide"
echo "    - CORPORATE_ACTIONS_GUIDE.md    - Dividends & bonus guide"
echo "    - ALERT_SYSTEM_GUIDE.md         - Alert system guide"
echo "    - PORTFOLIO_USAGE_GUIDE.md      - Portfolio management guide"
echo "    - BUY_TRANSACTION_GUIDE.md      - Purchase guide"
echo "    - SELL_TRANSACTION_GUIDE.md     - Sales guide"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 QUICK START"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. source venv/bin/activate"
echo "  2. python3 add_trade.py --interactive"
echo "  3. python3 price_updater.py --all"
echo "  4. python3 portfolio_dashboard.py --all"
echo "  5. python3 report_generator.py --pdf"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Happy Trading! 📈"
echo ""

