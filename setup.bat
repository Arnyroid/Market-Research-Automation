@echo off
REM Setup script for BSE Stock Data Fetcher (Windows)

echo 🚀 Setting up BSE Stock Data Fetcher...

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo ✅ Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Create necessary directories
echo 📁 Creating data and logs directories...
if not exist data mkdir data
if not exist logs mkdir logs

REM Copy environment file
if not exist .env (
    echo ⚙️  Creating .env file from template...
    copy .env.example .env
    echo ✏️  Please edit .env file with your settings
) else (
    echo ℹ️  .env file already exists, skipping...
)

echo.
echo ✨ Setup complete!
echo.
echo To get started:
echo   1. Activate the virtual environment: venv\Scripts\activate
echo   2. Edit .env file if needed
echo   3. Run once to test: python scheduler.py once
echo   4. Run continuously: python scheduler.py interval
echo.
echo For more options, see README.md
pause
