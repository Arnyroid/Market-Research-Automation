"""
Scheduler for automated BSE stock data fetching
Runs at regular intervals or specific times
"""
import schedule
import time
from datetime import datetime
from loguru import logger
import config
from bse_fetcher import BSEStockFetcher


class StockDataScheduler:
    """Manages scheduled fetching of BSE stock data"""
    
    def __init__(self, use_custom_scrips: bool = False):
        """
        Initialize the scheduler
        
        Args:
            use_custom_scrips: If True, fetch custom scrips from file instead of top gainers/losers
        """
        self.fetcher = BSEStockFetcher()
        self.use_custom_scrips = use_custom_scrips
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
        logger.info(f"Stock Data Scheduler initialized (custom_scrips: {use_custom_scrips})")
    
    def fetch_and_save(self):
        """Fetch stocks and save to file"""
        try:
            logger.info("=" * 50)
            logger.info(f"Starting scheduled fetch at {datetime.now()}")
            
            # Fetch stocks (use custom scrips if configured)
            df = self.fetcher.fetch_stocks(use_custom_scrips=self.use_custom_scrips)
            
            if df is not None and not df.empty:
                # Save to CSV
                success = self.fetcher.save_to_csv(df)
                
                if success:
                    logger.info(f"Successfully fetched and saved {len(df)} stocks")
                    
                    # Log statistics
                    stats = self.fetcher.get_stock_count()
                    logger.info(f"Current statistics: {stats}")
                else:
                    logger.error("Failed to save stock data")
            else:
                logger.error("Failed to fetch stock data")
            
            logger.info("Scheduled fetch completed")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Error in scheduled fetch: {e}")
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        try:
            current_time = datetime.now().strftime("%H:%M")
            return config.MARKET_OPEN_TIME <= current_time <= config.MARKET_CLOSE_TIME
        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            return True  # Default to True to allow fetching
    
    def setup_interval_schedule(self, interval_minutes: int = None):
        """
        Setup schedule to run at regular intervals
        
        Args:
            interval_minutes: Minutes between each fetch (default from config)
        """
        if interval_minutes is None:
            interval_minutes = config.FETCH_INTERVAL_MINUTES
        
        schedule.every(interval_minutes).minutes.do(self.fetch_and_save)
        logger.info(f"Scheduled to run every {interval_minutes} minutes")
    
    def setup_daily_schedule(self, time_str: str = None):
        """
        Setup schedule to run at specific time daily
        
        Args:
            time_str: Time in HH:MM format (default from config)
        """
        if time_str is None:
            time_str = config.FETCH_TIME
        
        schedule.every().day.at(time_str).do(self.fetch_and_save)
        logger.info(f"Scheduled to run daily at {time_str}")
    
    def setup_market_hours_schedule(self):
        """
        Setup schedule to run during market hours only
        Runs every hour during market hours (9:15 AM - 3:30 PM IST)
        """
        # Schedule at market open
        schedule.every().day.at("09:15").do(self.fetch_and_save)
        
        # Schedule every hour during market hours
        for hour in range(10, 16):  # 10 AM to 3 PM
            schedule.every().day.at(f"{hour:02d}:00").do(self.fetch_and_save)
        
        # Schedule at market close
        schedule.every().day.at("15:30").do(self.fetch_and_save)
        
        logger.info("Scheduled to run during market hours (9:15 AM - 3:30 PM IST)")
    
    def run_once(self):
        """Run the fetch operation once immediately"""
        logger.info("Running one-time fetch...")
        self.fetch_and_save()
    
    def run_continuous(self):
        """Run the scheduler continuously"""
        logger.info("Starting continuous scheduler...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous scheduler: {e}")


def main():
    """Main function to run the scheduler"""
    import sys
    
    # Check for --custom flag
    use_custom = "--custom" in sys.argv
    if use_custom:
        sys.argv.remove("--custom")
        print("📋 Using custom scrips from custom_scrips.txt")
    
    scheduler = StockDataScheduler(use_custom_scrips=use_custom)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "once":
            # Run once and exit
            scheduler.run_once()
            
        elif mode == "interval":
            # Run at regular intervals
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else config.FETCH_INTERVAL_MINUTES
            scheduler.setup_interval_schedule(interval)
            scheduler.run_continuous()
            
        elif mode == "daily":
            # Run once daily at specific time
            time_str = sys.argv[2] if len(sys.argv) > 2 else config.FETCH_TIME
            scheduler.setup_daily_schedule(time_str)
            scheduler.run_continuous()
            
        elif mode == "market":
            # Run during market hours
            scheduler.setup_market_hours_schedule()
            scheduler.run_continuous()
            
        else:
            print("Usage: python scheduler.py [once|interval|daily|market] [options] [--custom]")
            print("  once              - Run once and exit")
            print("  interval [mins]   - Run every N minutes (default: 60)")
            print("  daily [HH:MM]     - Run daily at specific time (default: 09:30)")
            print("  market            - Run during market hours only")
            print("  --custom          - Use custom scrips from custom_scrips.txt")
            print("\nExamples:")
            print("  python scheduler.py once --custom")
            print("  python scheduler.py interval 30 --custom")
            sys.exit(1)
    else:
        # Default: run at regular intervals
        print("No mode specified, using default interval mode")
        print(f"Running every {config.FETCH_INTERVAL_MINUTES} minutes")
        print("Use 'python scheduler.py once' to run once, or see help for other modes")
        scheduler.setup_interval_schedule()
        scheduler.run_continuous()


if __name__ == "__main__":
    main()

# Made with Bob
