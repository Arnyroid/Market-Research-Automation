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
echo "To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Edit .env file if needed: nano .env"
echo "  3. Run once to test: python scheduler.py once"
echo "  4. Run continuously: python scheduler.py interval"
echo ""
echo "For more options, see README.md"

# Made with Bob
