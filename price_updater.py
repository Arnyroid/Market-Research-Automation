"""
Price Updater Module
Update portfolio with current prices from BSE
"""
from datetime import datetime
from typing import Dict, List
from loguru import logger
import config
from portfolio_db import PortfolioDB
from bse_fetcher import BSEStockFetcher


class PriceUpdater:
    """Update portfolio prices from BSE"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize price updater
        
        Args:
            db_path: Path to database file
        """
        self.db = PortfolioDB(db_path)
        self.fetcher = BSEStockFetcher()
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
        logger.info("Price Updater initialized")
    
    def update_portfolio_prices(self) -> Dict:
        """
        Update current prices for all portfolio stocks
        
        Returns:
            Dictionary with update statistics
        """
        try:
            logger.info("Updating portfolio prices...")
            
            # Get current portfolio
            portfolio = self.db.get_portfolio()
            
            if portfolio.empty:
                logger.warning("No portfolio holdings to update")
                return {'success': 0, 'failed': 0, 'total': 0}
            
            scrip_codes = portfolio['scrip_code'].tolist()
            logger.info(f"Fetching prices for {len(scrip_codes)} stocks")
            
            # Fetch prices
            price_data = {}
            failed_scrips = []
            
            for scrip_code in scrip_codes:
                try:
                    quote = self.fetcher.fetch_stock_quote(scrip_code)
                    
                    if quote and 'currentValue' in quote:
                        price = float(quote['currentValue'])
                        price_data[scrip_code] = price
                        
                        # Also save to price history
                        self.db.add_price_history(
                            scrip_code=scrip_code,
                            price_date=datetime.now().strftime('%Y-%m-%d'),
                            open_price=float(quote.get('open', 0)),
                            high_price=float(quote.get('dayHigh', 0)),
                            low_price=float(quote.get('dayLow', 0)),
                            close_price=price,
                            volume=int(quote.get('totalTradedVolume', 0)),
                            source='BSE'
                        )
                        
                        logger.info(f"✓ {scrip_code}: ₹{price}")
                    else:
                        failed_scrips.append(scrip_code)
                        logger.warning(f"✗ No price data for {scrip_code}")
                        
                except Exception as e:
                    failed_scrips.append(scrip_code)
                    logger.error(f"✗ Error fetching {scrip_code}: {e}")
            
            # Update portfolio with new prices
            if price_data:
                self.db.update_current_prices(price_data)
                logger.info(f"Updated prices for {len(price_data)} stocks")
            
            stats = {
                'success': len(price_data),
                'failed': len(failed_scrips),
                'total': len(scrip_codes),
                'failed_scrips': failed_scrips,
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error updating portfolio prices: {e}")
            raise
    
    def update_single_stock(self, scrip_code: str) -> bool:
        """
        Update price for a single stock
        
        Args:
            scrip_code: BSE scrip code
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Updating price for {scrip_code}...")
            
            quote = self.fetcher.fetch_stock_quote(scrip_code)
            
            if quote and 'currentValue' in quote:
                price = float(quote['currentValue'])
                
                # Update portfolio
                self.db.update_current_prices({scrip_code: price})
                
                # Save to history
                self.db.add_price_history(
                    scrip_code=scrip_code,
                    price_date=datetime.now().strftime('%Y-%m-%d'),
                    open_price=float(quote.get('open', 0)),
                    high_price=float(quote.get('dayHigh', 0)),
                    low_price=float(quote.get('dayLow', 0)),
                    close_price=price,
                    volume=int(quote.get('totalTradedVolume', 0)),
                    source='BSE'
                )
                
                logger.info(f"✓ Updated {scrip_code}: ₹{price}")
                return True
            else:
                logger.warning(f"✗ No price data for {scrip_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating {scrip_code}: {e}")
            return False


def main():
    """Main function for command-line usage"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Update portfolio prices from BSE')
    parser.add_argument('--scrip', '-s', help='Update single scrip code')
    parser.add_argument('--all', '-a', action='store_true', help='Update all portfolio stocks')
    
    args = parser.parse_args()
    
    updater = PriceUpdater()
    
    if args.scrip:
        # Update single stock
        print(f"\n📊 Updating price for {args.scrip}...")
        success = updater.update_single_stock(args.scrip)
        
        if success:
            print(f"✅ Price updated successfully!")
        else:
            print(f"❌ Failed to update price")
            sys.exit(1)
            
    elif args.all:
        # Update all stocks
        print("\n📊 Updating prices for all portfolio stocks...")
        stats = updater.update_portfolio_prices()
        
        print(f"\n✅ Update complete!")
        print(f"  Success: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Total: {stats['total']}")
        
        if stats['failed_scrips']:
            print(f"\n⚠️  Failed scrips: {', '.join(stats['failed_scrips'])}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

