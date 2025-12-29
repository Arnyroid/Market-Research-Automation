"""
Portfolio Dashboard
View your portfolio, trades, and performance in a formatted display
"""
import pandas as pd
from datetime import datetime
from typing import Optional
from loguru import logger
from tabulate import tabulate
import config
from portfolio_db import PortfolioDB
from portfolio_analyzer import PortfolioAnalyzer
from price_updater import PriceUpdater


class PortfolioDashboard:
    """Display portfolio data in formatted views"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize dashboard
        
        Args:
            db_path: Path to database file
        """
        self.db = PortfolioDB(db_path)
        self.analyzer = PortfolioAnalyzer(db_path)
        self.updater = PriceUpdater(db_path)
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
    
    def show_portfolio_summary(self):
        """Display portfolio summary"""
        print("\n" + "="*80)
        print("📊 PORTFOLIO SUMMARY".center(80))
        print("="*80)
        
        # Get performance metrics
        performance = self.analyzer.get_portfolio_performance()
        
        # Summary table
        summary_data = [
            ["Total Stocks", performance.get('total_stocks', 0)],
            ["Total Invested", f"₹{performance.get('total_invested', 0):,.2f}"],
            ["Current Value", f"₹{performance.get('current_value', 0):,.2f}"],
            ["Total P&L", f"₹{performance.get('total_profit_loss', 0):,.2f}"],
            ["P&L %", f"{performance.get('total_profit_loss_percent', 0):.2f}%"],
            ["Realized P&L", f"₹{performance.get('total_realized_pnl', 0):,.2f}"],
        ]
        
        print(tabulate(summary_data, tablefmt="grid"))
        
        # Performance breakdown
        if performance.get('gainers', 0) > 0 or performance.get('losers', 0) > 0:
            print("\n📈 Performance Breakdown:")
            perf_data = [
                ["Gainers", performance.get('gainers', 0)],
                ["Losers", performance.get('losers', 0)],
                ["Neutral", performance.get('neutral', 0)]
            ]
            print(tabulate(perf_data, headers=["Category", "Count"], tablefmt="simple"))
        
        # Best/Worst performers
        if 'best_performer' in performance and performance['best_performer'].get('pnl_percent'):
            print("\n🏆 Best Performer:")
            best = performance['best_performer']
            print(f"   {best['scrip_name']} ({best['scrip_code']}): {best['pnl_percent']:.2f}%")
        
        if 'worst_performer' in performance and performance['worst_performer'].get('pnl_percent'):
            print("\n📉 Worst Performer:")
            worst = performance['worst_performer']
            print(f"   {worst['scrip_name']} ({worst['scrip_code']}): {worst['pnl_percent']:.2f}%")
        
        print("\n" + "="*80 + "\n")
    
    def show_holdings(self):
        """Display current holdings"""
        print("\n" + "="*80)
        print("💼 CURRENT HOLDINGS".center(80))
        print("="*80 + "\n")
        
        portfolio = self.db.get_portfolio()
        
        if portfolio.empty:
            print("No holdings found.\n")
            return
        
        # Prepare data for display
        display_data = []
        for _, row in portfolio.iterrows():
            current_price = row.get('current_price') or 0
            current_value = row.get('current_value') or 0
            pnl = row.get('profit_loss') or 0
            pnl_pct = row.get('profit_loss_percent') or 0
            
            # Color code P&L
            pnl_str = f"₹{pnl:,.2f}"
            pnl_pct_str = f"{pnl_pct:.2f}%"
            
            display_data.append([
                row['scrip_code'],
                row['scrip_name'][:30],  # Truncate long names
                row['total_quantity'],
                f"₹{row['avg_buy_price']:,.2f}",
                f"₹{row['total_invested']:,.2f}",
                f"₹{current_price:,.2f}" if current_price > 0 else "N/A",
                f"₹{current_value:,.2f}" if current_value > 0 else "N/A",
                pnl_str,
                pnl_pct_str
            ])
        
        headers = ["Code", "Name", "Qty", "Avg Price", "Invested", "Current", "Value", "P&L", "P&L %"]
        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print("\n")
    
    def show_recent_trades(self, limit: int = 10):
        """Display recent trades"""
        print("\n" + "="*80)
        print(f"📝 RECENT TRADES (Last {limit})".center(80))
        print("="*80 + "\n")
        
        trades = self.db.get_all_trades()
        
        if trades.empty:
            print("No trades found.\n")
            return
        
        # Get recent trades
        recent = trades.head(limit)
        
        # Prepare data
        display_data = []
        for _, row in recent.iterrows():
            trade_type = "BUY" if row['trade_type'] == 'BUY' else "SELL"
            display_data.append([
                row['trade_date'],
                row['scrip_code'],
                row['scrip_name'][:25],
                trade_type,
                row['quantity'],
                f"₹{row['price']:,.2f}",
                f"₹{row['total_value']:,.2f}"
            ])
        
        headers = ["Date", "Code", "Name", "Type", "Qty", "Price", "Total"]
        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print("\n")
    
    def show_stock_detail(self, scrip_code: str):
        """Display detailed analysis for a stock"""
        print("\n" + "="*80)
        print(f"🔍 STOCK ANALYSIS: {scrip_code}".center(80))
        print("="*80 + "\n")
        
        analysis = self.analyzer.get_stock_analysis(scrip_code)
        
        if not analysis:
            print(f"No data found for {scrip_code}\n")
            return
        
        # Basic info
        print(f"Company: {analysis.get('scrip_name', 'N/A')}")
        print(f"Scrip Code: {analysis.get('scrip_code', 'N/A')}")
        print()
        
        # Trading activity
        print("📊 Trading Activity:")
        activity_data = [
            ["Total Trades", analysis.get('total_trades', 0)],
            ["Buy Trades", analysis.get('buy_trades', 0)],
            ["Sell Trades", analysis.get('sell_trades', 0)],
            ["First Trade", analysis.get('first_trade_date', 'N/A')],
            ["Last Trade", analysis.get('last_trade_date', 'N/A')]
        ]
        print(tabulate(activity_data, tablefmt="simple"))
        print()
        
        # Current position
        if analysis.get('current_quantity', 0) > 0:
            print("💼 Current Position:")
            position_data = [
                ["Quantity", analysis.get('current_quantity', 0)],
                ["Avg Buy Price", f"₹{analysis.get('avg_buy_price', 0):,.2f}"],
                ["Total Invested", f"₹{analysis.get('total_invested', 0):,.2f}"],
                ["Current Price", f"₹{analysis.get('current_price', 0):,.2f}"],
                ["Current Value", f"₹{analysis.get('current_value', 0):,.2f}"],
                ["Unrealized P&L", f"₹{analysis.get('unrealized_pnl', 0):,.2f}"],
                ["Unrealized P&L %", f"{analysis.get('unrealized_pnl_percent', 0):.2f}%"]
            ]
            print(tabulate(position_data, tablefmt="simple"))
        else:
            print("Status: Fully sold")
        print()
        
        # P&L summary
        print("💰 P&L Summary:")
        pnl_data = [
            ["Realized P&L", f"₹{analysis.get('realized_pnl', 0):,.2f}"],
            ["Unrealized P&L", f"₹{analysis.get('unrealized_pnl', 0):,.2f}"],
            ["Total P&L", f"₹{analysis.get('total_pnl', 0):,.2f}"]
        ]
        print(tabulate(pnl_data, tablefmt="simple"))
        print("\n" + "="*80 + "\n")
    
    def show_trades_by_stock(self, scrip_code: str):
        """Show all trades for a specific stock"""
        print("\n" + "="*80)
        print(f"📝 ALL TRADES: {scrip_code}".center(80))
        print("="*80 + "\n")
        
        trades = self.db.get_all_trades(scrip_code)
        
        if trades.empty:
            print(f"No trades found for {scrip_code}\n")
            return
        
        display_data = []
        for _, row in trades.iterrows():
            trade_type = "BUY" if row['trade_type'] == 'BUY' else "SELL"
            display_data.append([
                row['trade_date'],
                trade_type,
                row['quantity'],
                f"₹{row['price']:,.2f}",
                f"₹{row['total_value']:,.2f}",
                f"₹{row['brokerage']:,.2f}",
                row['notes'][:30] if row['notes'] else ""
            ])
        
        headers = ["Date", "Type", "Qty", "Price", "Total", "Brokerage", "Notes"]
        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print("\n")
    
    def update_and_show(self):
        """Update prices and show portfolio"""
        print("\n🔄 Updating prices from BSE...")
        stats = self.updater.update_portfolio_prices()
        print(f"✅ Updated {stats['success']} stocks")
        
        if stats['failed'] > 0:
            print(f"⚠️  Failed to update {stats['failed']} stocks")
        
        self.show_portfolio_summary()
        self.show_holdings()


def main():
    """Main function for command-line usage"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Portfolio Dashboard')
    parser.add_argument('--summary', '-s', action='store_true', help='Show portfolio summary')
    parser.add_argument('--holdings', '-H', action='store_true', help='Show current holdings')
    parser.add_argument('--trades', '-t', type=int, metavar='N', help='Show recent N trades')
    parser.add_argument('--stock', metavar='CODE', help='Show detailed analysis for stock')
    parser.add_argument('--stock-trades', metavar='CODE', help='Show all trades for stock')
    parser.add_argument('--update', '-u', action='store_true', help='Update prices before showing')
    parser.add_argument('--all', '-a', action='store_true', help='Show everything')
    
    args = parser.parse_args()
    
    dashboard = PortfolioDashboard()
    
    # Update prices if requested
    if args.update:
        print("\n🔄 Updating prices from BSE...")
        stats = dashboard.updater.update_portfolio_prices()
        print(f"✅ Updated {stats['success']} stocks\n")
    
    # Show requested views
    if args.all:
        dashboard.show_portfolio_summary()
        dashboard.show_holdings()
        dashboard.show_recent_trades(10)
    elif args.summary:
        dashboard.show_portfolio_summary()
    elif args.holdings:
        dashboard.show_holdings()
    elif args.trades:
        dashboard.show_recent_trades(args.trades)
    elif args.stock:
        dashboard.show_stock_detail(args.stock)
    elif args.stock_trades:
        dashboard.show_trades_by_stock(args.stock_trades)
    else:
        # Default: show summary and holdings
        dashboard.show_portfolio_summary()
        dashboard.show_holdings()


if __name__ == "__main__":
    main()
