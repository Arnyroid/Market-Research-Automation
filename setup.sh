#!/bin/bash
# Setup script for BSE Stock Data Fetcher

echo "🚀 Setting up BSE Stock Data Fetcher..."

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

# Copy environment file
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your settings"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "📊 Stock Data Fetching:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Edit .env file if needed: nano .env"
echo "  3. Run once to test: python scheduler.py once"
echo "  4. Run continuously: python scheduler.py interval"
echo ""
echo "💼 Portfolio Management:"
echo "  Quick trade entry:"
echo "    - Add BUY: python add_trade.py -c 500325 -n \"Reliance Industries Ltd\" -q 10 -p 1450.00"
echo "    - Add SELL: python add_trade.py -c 500325 -n \"Reliance Industries Ltd\" -q 5 -p 1600.00 -t SELL"
echo "    - Interactive: python add_trade.py --interactive"
echo ""
echo "  Bulk import:"
echo "    - Generate template: python trade_importer.py --template trades.xlsx"
echo "    - Import trades: python trade_importer.py --file trades.xlsx"
echo ""
echo "  View portfolio:"
echo "    - Update prices: python price_updater.py --all"
echo "    - View dashboard: python portfolio_dashboard.py --all"
echo ""
echo "📚 Documentation:"
echo "  - COMMAND_LINE_TRADE_ENTRY.md - Quick trade entry guide"
echo "  - BUY_TRANSACTION_GUIDE.md - Complete purchase guide"
echo "  - SELL_TRANSACTION_GUIDE.md - Sales guide"
echo "  - PORTFOLIO_USAGE_GUIDE.md - Complete portfolio guide"
echo "  - README.md - Full documentation"
echo ""
