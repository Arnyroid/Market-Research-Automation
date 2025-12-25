"""
Test script for BSE Stock Fetcher
Tests the fetcher with bsedata library
"""
import pandas as pd
from datetime import datetime
from loguru import logger
from bse_fetcher import BSEStockFetcher
import config


def test_basic_functionality():
    """Test basic fetcher functionality"""
    logger.info("=" * 60)
    logger.info("Testing BSE Stock Fetcher - Basic Functionality")
    logger.info("=" * 60)
    
    fetcher = BSEStockFetcher()
    
    # Test 1: Fetch top gainers
    logger.info("\n[Test 1] Fetching top gainers...")
    gainers = fetcher.fetch_top_gainers()
    if gainers is not None and not gainers.empty:
        logger.info(f"✓ Successfully fetched {len(gainers)} top gainers")
        logger.info(f"Columns: {gainers.columns.tolist()}")
        print("\nTop 3 Gainers:")
        print(gainers.head(3).to_string())
    else:
        logger.error("✗ Failed to fetch top gainers")
    
    # Test 2: Fetch top losers
    logger.info("\n[Test 2] Fetching top losers...")
    losers = fetcher.fetch_top_losers()
    if losers is not None and not losers.empty:
        logger.info(f"✓ Successfully fetched {len(losers)} top losers")
        print("\nTop 3 Losers:")
        print(losers.head(3).to_string())
    else:
        logger.error("✗ Failed to fetch top losers")
    
    # Test 3: Fetch stocks with prices
    logger.info("\n[Test 3] Fetching stocks with current prices...")
    df = fetcher.fetch_stocks(include_prices=True)
    if df is not None and not df.empty:
        logger.info(f"✓ Successfully fetched {len(df)} stocks with prices")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        # Save to file
        success = fetcher.save_to_csv(df)
        if success:
            logger.info("✓ Successfully saved data to CSV")
        else:
            logger.error("✗ Failed to save data to CSV")
    else:
        logger.error("✗ Failed to fetch stocks")
    
    # Test 4: Get statistics
    logger.info("\n[Test 4] Testing statistics retrieval...")
    stats = fetcher.get_stock_count()
    logger.info(f"✓ Statistics: {stats}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Basic functionality tests completed!")
    logger.info("=" * 60)


def test_stock_quote():
    """Test fetching individual stock quote"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Individual Stock Quote")
    logger.info("=" * 60)
    
    fetcher = BSEStockFetcher()
    
    # Test with Reliance Industries
    scrip_code = "500325"  # Reliance
    logger.info(f"\nFetching quote for Reliance (scrip: {scrip_code})...")
    
    quote = fetcher.fetch_stock_quote(scrip_code)
    
    if quote:
        logger.info("✓ Successfully fetched stock quote")
        logger.info(f"Stock details:")
        for key, value in list(quote.items())[:10]:  # Show first 10 fields
            logger.info(f"  {key}: {value}")
    else:
        logger.warning("✗ Could not fetch stock quote")
    
    logger.info("\n" + "=" * 60)
    logger.info("Stock quote test completed!")
    logger.info("=" * 60)


def test_scheduler_integration():
    """Test scheduler integration"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Scheduler Integration")
    logger.info("=" * 60)
    
    try:
        from scheduler import StockDataScheduler
        
        scheduler = StockDataScheduler()
        logger.info("✓ Scheduler initialized successfully")
        
        # Test market hours check
        is_market_hours = scheduler.is_market_hours()
        current_time = datetime.now().strftime("%H:%M")
        logger.info(f"✓ Current time: {current_time}")
        logger.info(f"✓ Market hours check: {is_market_hours}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Scheduler integration test completed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Scheduler test failed: {e}")


def test_data_quality():
    """Test data quality and completeness"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Data Quality")
    logger.info("=" * 60)
    
    try:
        if config.STOCK_MASTER_FILE.exists():
            df = pd.read_csv(config.STOCK_MASTER_FILE)
            
            logger.info(f"\n✓ Master file exists with {len(df)} records")
            logger.info(f"✓ Columns: {df.columns.tolist()}")
            
            # Check for required columns
            required_cols = ['scrip_code', 'last_price', 'timestamp']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if not missing_cols:
                logger.info("✓ All required columns present")
            else:
                logger.warning(f"✗ Missing columns: {missing_cols}")
            
            # Check for null values
            null_counts = df.isnull().sum()
            if null_counts.sum() == 0:
                logger.info("✓ No null values found")
            else:
                logger.warning(f"⚠ Null values found:\n{null_counts[null_counts > 0]}")
            
            # Show price statistics
            if 'last_price' in df.columns:
                logger.info(f"\n✓ Price Statistics:")
                logger.info(f"  Average: ₹{df['last_price'].mean():.2f}")
                logger.info(f"  Min: ₹{df['last_price'].min():.2f}")
                logger.info(f"  Max: ₹{df['last_price'].max():.2f}")
            
            # Show sample records
            logger.info(f"\n✓ Sample records:")
            print(df.head(3).to_string())
            
        else:
            logger.warning("✗ Master file does not exist yet")
        
        logger.info("\n" + "=" * 60)
        logger.info("Data quality test completed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Data quality test failed: {e}")


def main():
    """Run all tests"""
    logger.add(
        config.LOG_FILE,
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )
    
    print("\n" + "=" * 60)
    print("BSE STOCK FETCHER - TEST SUITE (BSEDATA LIBRARY)")
    print("=" * 60)
    
    try:
        # Run tests
        test_basic_functionality()
        test_stock_quote()
        test_data_quality()
        test_scheduler_integration()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Check data/ directory for generated CSV files")
        print("2. Check logs/ directory for detailed logs")
        print("3. Run 'python scheduler.py once' to test full automation")
        print("4. Run 'python scheduler.py interval 30' to start continuous fetching")
        print("\nNote: The fetcher now uses bsedata library for reliable data")
        print("=" * 60 + "\n")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise


if __name__ == "__main__":
    main()

# Made with Bob
