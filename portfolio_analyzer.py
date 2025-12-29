"""
Portfolio Analyzer Module
Calculate portfolio holdings, P&L, and performance metrics
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from loguru import logger
import config
from portfolio_db import PortfolioDB


class PortfolioAnalyzer:
    """Analyze portfolio and calculate metrics"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize portfolio analyzer
        
        Args:
            db_path: Path to database file
        """
        self.db = PortfolioDB(db_path)
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
        logger.info("Portfolio Analyzer initialized")
    
    def calculate_holdings_from_trades(self) -> pd.DataFrame:
        """
        Calculate current holdings from all trades
        Uses FIFO (First In First Out) method
        
        Returns:
            DataFrame with current holdings
        """
        try:
            logger.info("Calculating holdings from trades...")
            
            # Get all trades
            trades = self.db.get_all_trades()
            
            if trades.empty:
                logger.warning("No trades found")
                return pd.DataFrame()
            
            # Sort by date
            trades = trades.sort_values('trade_date')
            
            # Calculate holdings for each scrip
            holdings = {}
            
            for scrip_code in trades['scrip_code'].unique():
                scrip_trades = trades[trades['scrip_code'] == scrip_code]
                
                total_quantity = 0
                total_invested = 0
                scrip_name = scrip_trades.iloc[0]['scrip_name']
                
                for _, trade in scrip_trades.iterrows():
                    if trade['trade_type'] == 'BUY':
                        total_quantity += trade['quantity']
                        total_invested += (trade['quantity'] * trade['price']) + trade['brokerage']
                    elif trade['trade_type'] == 'SELL':
                        # Calculate average price before sell
                        if total_quantity > 0:
                            avg_price = total_invested / total_quantity
                            # Reduce quantity and investment proportionally
                            sell_quantity = min(trade['quantity'], total_quantity)
                            total_quantity -= sell_quantity
                            total_invested -= (sell_quantity * avg_price)
                
                # Only add if we still hold shares
                if total_quantity > 0:
                    avg_buy_price = total_invested / total_quantity
                    holdings[scrip_code] = {
                        'scrip_code': scrip_code,
                        'scrip_name': scrip_name,
                        'total_quantity': total_quantity,
                        'avg_buy_price': round(avg_buy_price, 2),
                        'total_invested': round(total_invested, 2)
                    }
            
            if holdings:
                df = pd.DataFrame.from_dict(holdings, orient='index')
                logger.info(f"Calculated holdings for {len(df)} stocks")
                return df
            else:
                logger.info("No current holdings")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error calculating holdings: {e}")
            raise
    
    def update_portfolio_from_trades(self):
        """
        Update portfolio table based on trades
        """
        try:
            logger.info("Updating portfolio from trades...")
            
            holdings = self.calculate_holdings_from_trades()
            
            if holdings.empty:
                logger.info("No holdings to update")
                return
            
            # Update each holding in database
            for _, row in holdings.iterrows():
                self.db.update_portfolio(
                    scrip_code=row['scrip_code'],
                    scrip_name=row['scrip_name'],
                    total_quantity=int(row['total_quantity']),
                    avg_buy_price=float(row['avg_buy_price']),
                    total_invested=float(row['total_invested'])
                )
            
            logger.info(f"Portfolio updated with {len(holdings)} holdings")
            
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            raise
    
    def calculate_realized_pnl(self, scrip_code: str = None) -> pd.DataFrame:
        """
        Calculate realized P&L from sell transactions
        
        Args:
            scrip_code: Optional scrip code to filter
        
        Returns:
            DataFrame with realized P&L
        """
        try:
            logger.info("Calculating realized P&L...")
            
            trades = self.db.get_all_trades(scrip_code)
            
            if trades.empty:
                return pd.DataFrame()
            
            # Filter sell trades
            sell_trades = trades[trades['trade_type'] == 'SELL'].copy()
            
            if sell_trades.empty:
                logger.info("No sell trades found")
                return pd.DataFrame()
            
            realized_pnl = []
            
            for scrip in sell_trades['scrip_code'].unique():
                scrip_trades = trades[trades['scrip_code'] == scrip].sort_values('trade_date')
                scrip_sells = sell_trades[sell_trades['scrip_code'] == scrip]
                
                # Calculate average buy price at time of each sell
                for _, sell in scrip_sells.iterrows():
                    # Get all buys before this sell
                    prior_buys = scrip_trades[
                        (scrip_trades['trade_type'] == 'BUY') &
                        (scrip_trades['trade_date'] <= sell['trade_date'])
                    ]
                    
                    if not prior_buys.empty:
                        avg_buy = (prior_buys['quantity'] * prior_buys['price']).sum() / prior_buys['quantity'].sum()
                        
                        sell_value = sell['quantity'] * sell['price']
                        buy_value = sell['quantity'] * avg_buy
                        pnl = sell_value - buy_value - sell['brokerage']
                        pnl_percent = (pnl / buy_value * 100) if buy_value > 0 else 0
                        
                        realized_pnl.append({
                            'trade_date': sell['trade_date'],
                            'scrip_code': scrip,
                            'scrip_name': sell['scrip_name'],
                            'quantity': sell['quantity'],
                            'avg_buy_price': round(avg_buy, 2),
                            'sell_price': sell['price'],
                            'realized_pnl': round(pnl, 2),
                            'pnl_percent': round(pnl_percent, 2)
                        })
            
            if realized_pnl:
                df = pd.DataFrame(realized_pnl)
                logger.info(f"Calculated realized P&L for {len(df)} transactions")
                return df
            else:
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error calculating realized P&L: {e}")
            raise
    
    def get_portfolio_performance(self) -> Dict:
        """
        Get overall portfolio performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            logger.info("Calculating portfolio performance...")
            
            # Get portfolio summary
            summary = self.db.get_portfolio_summary()
            
            # Get portfolio with current prices
            portfolio = self.db.get_portfolio()
            
            if portfolio.empty:
                logger.warning("No portfolio data")
                return summary
            
            # Calculate additional metrics
            if not portfolio.empty and 'profit_loss_percent' in portfolio.columns:
                # Best and worst performers
                portfolio_sorted = portfolio.sort_values('profit_loss_percent', ascending=False)
                
                summary['best_performer'] = {
                    'scrip_code': portfolio_sorted.iloc[0]['scrip_code'],
                    'scrip_name': portfolio_sorted.iloc[0]['scrip_name'],
                    'pnl_percent': portfolio_sorted.iloc[0]['profit_loss_percent']
                }
                
                summary['worst_performer'] = {
                    'scrip_code': portfolio_sorted.iloc[-1]['scrip_code'],
                    'scrip_name': portfolio_sorted.iloc[-1]['scrip_name'],
                    'pnl_percent': portfolio_sorted.iloc[-1]['profit_loss_percent']
                }
                
                # Count gainers and losers
                summary['gainers'] = len(portfolio[portfolio['profit_loss'] > 0])
                summary['losers'] = len(portfolio[portfolio['profit_loss'] < 0])
                summary['neutral'] = len(portfolio[portfolio['profit_loss'] == 0])
            
            # Get realized P&L
            realized = self.calculate_realized_pnl()
            if not realized.empty:
                summary['total_realized_pnl'] = realized['realized_pnl'].sum()
            else:
                summary['total_realized_pnl'] = 0
            
            logger.info("Portfolio performance calculated")
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            raise
    
    def get_stock_analysis(self, scrip_code: str) -> Dict:
        """
        Get detailed analysis for a specific stock
        
        Args:
            scrip_code: BSE scrip code
        
        Returns:
            Dictionary with stock analysis
        """
        try:
            logger.info(f"Analyzing stock: {scrip_code}")
            
            # Get trades for this stock
            trades = self.db.get_all_trades(scrip_code)
            
            if trades.empty:
                logger.warning(f"No trades found for {scrip_code}")
                return {}
            
            # Get portfolio data
            portfolio = self.db.get_portfolio()
            stock_portfolio = portfolio[portfolio['scrip_code'] == scrip_code]
            
            analysis = {
                'scrip_code': scrip_code,
                'scrip_name': trades.iloc[0]['scrip_name'],
                'total_trades': len(trades),
                'buy_trades': len(trades[trades['trade_type'] == 'BUY']),
                'sell_trades': len(trades[trades['trade_type'] == 'SELL']),
                'first_trade_date': trades['trade_date'].min(),
                'last_trade_date': trades['trade_date'].max(),
            }
            
            # Current holding
            if not stock_portfolio.empty:
                holding = stock_portfolio.iloc[0]
                analysis['current_quantity'] = holding['total_quantity']
                analysis['avg_buy_price'] = holding['avg_buy_price']
                analysis['total_invested'] = holding['total_invested']
                analysis['current_price'] = holding.get('current_price', 0)
                analysis['current_value'] = holding.get('current_value', 0)
                analysis['unrealized_pnl'] = holding.get('profit_loss', 0)
                analysis['unrealized_pnl_percent'] = holding.get('profit_loss_percent', 0)
            else:
                analysis['current_quantity'] = 0
                analysis['status'] = 'Fully sold'
            
            # Realized P&L
            realized = self.calculate_realized_pnl(scrip_code)
            if not realized.empty:
                analysis['realized_pnl'] = realized['realized_pnl'].sum()
                analysis['realized_trades'] = len(realized)
            else:
                analysis['realized_pnl'] = 0
                analysis['realized_trades'] = 0
            
            # Total P&L
            unrealized = analysis.get('unrealized_pnl', 0) or 0
            realized = analysis.get('realized_pnl', 0) or 0
            analysis['total_pnl'] = unrealized + realized
            
            logger.info(f"Stock analysis complete for {scrip_code}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing stock {scrip_code}: {e}")
            raise


def main():
    """Test function"""
    analyzer = PortfolioAnalyzer()
    
    # Calculate and update portfolio
    logger.info("Updating portfolio from trades...")
    analyzer.update_portfolio_from_trades()
    
    # Get portfolio
    portfolio = analyzer.db.get_portfolio()
    print("\n📊 Current Portfolio:")
    print(portfolio.to_string())
    
    # Get performance
    performance = analyzer.get_portfolio_performance()
    print("\n📈 Portfolio Performance:")
    for key, value in performance.items():
        print(f"  {key}: {value}")
    
    # Analyze first stock
    if not portfolio.empty:
        scrip_code = portfolio.iloc[0]['scrip_code']
        analysis = analyzer.get_stock_analysis(scrip_code)
        print(f"\n🔍 Stock Analysis ({scrip_code}):")
        for key, value in analysis.items():
            print(f"  {key}: {value}")
    
    logger.info("Analysis complete!")


if __name__ == "__main__":
    main()
