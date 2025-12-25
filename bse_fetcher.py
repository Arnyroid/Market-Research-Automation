"""
BSE Stock Data Fetcher Module
Fetches list of BSE listed stocks using bsedata library
"""
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import time
from loguru import logger
from bsedata.bse import BSE
import config


class BSEStockFetcher:
    """Fetches BSE stock data using bsedata library"""
    
    def __init__(self):
        """Initialize the BSE stock fetcher"""
        self.bse = BSE()
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
        logger.info("BSE Stock Fetcher initialized with bsedata library")
    
    def fetch_top_gainers(self) -> Optional[pd.DataFrame]:
        """
        Fetch top gaining stocks
        Returns DataFrame with stock information
        """
        try:
            logger.info("Fetching top gainers from BSE...")
            gainers = self.bse.topGainers()
            
            if gainers:
                df = pd.DataFrame(gainers)
                logger.info(f"Successfully fetched {len(df)} top gainers")
                return df
            else:
                logger.warning("No top gainers data available")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching top gainers: {e}")
            return None
    
    def fetch_top_losers(self) -> Optional[pd.DataFrame]:
        """
        Fetch top losing stocks
        Returns DataFrame with stock information
        """
        try:
            logger.info("Fetching top losers from BSE...")
            losers = self.bse.topLosers()
            
            if losers:
                df = pd.DataFrame(losers)
                logger.info(f"Successfully fetched {len(df)} top losers")
                return df
            else:
                logger.warning("No top losers data available")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching top losers: {e}")
            return None
    
    def fetch_stock_quote(self, scrip_code: str) -> Optional[Dict]:
        """
        Fetch detailed quote for a specific stock
        
        Args:
            scrip_code: BSE scrip code (e.g., '500325' for Reliance)
        
        Returns:
            Dictionary with stock details
        """
        try:
            logger.info(f"Fetching quote for scrip code: {scrip_code}")
            quote = self.bse.getQuote(scrip_code)
            
            if quote:
                logger.info(f"Successfully fetched quote for {scrip_code}")
                return quote
            else:
                logger.warning(f"No quote data for {scrip_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching quote for {scrip_code}: {e}")
    
    def load_custom_scrips(self, filename: Optional[str] = None) -> List[str]:
        """
        Load custom scrip codes from file
        
        Args:
            filename: Path to file with scrip codes (default: custom_scrips.txt)
        
        Returns:
            List of scrip codes
        """
        try:
            if filename is None:
                filename = config.CUSTOM_SCRIPS_FILE
            
            scrip_codes = []
            
            if not filename.exists():
                logger.warning(f"Custom scrips file not found: {filename}")
                return scrip_codes
            
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        # Extract scrip code (first word before any comment)
                        scrip_code = line.split('#')[0].strip()
                        if scrip_code:
                            scrip_codes.append(scrip_code)
            
            logger.info(f"Loaded {len(scrip_codes)} custom scrip codes")
            return scrip_codes
            
        except Exception as e:
            logger.error(f"Error loading custom scrips: {e}")
            return []
    
    def fetch_custom_scrips(self, scrip_codes: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        Fetch quotes for custom list of scrip codes
        
        Args:
            scrip_codes: List of BSE scrip codes. If None, loads from custom_scrips.txt
        
        Returns:
            DataFrame with stock information
        """
        try:
            # Load scrip codes if not provided
            if scrip_codes is None:
                scrip_codes = self.load_custom_scrips()
            
            if not scrip_codes:
                logger.warning("No scrip codes to fetch")
                return None
            
            logger.info(f"Fetching quotes for {len(scrip_codes)} custom scrips...")
            
            all_quotes = []
            failed_scrips = []
            
            for scrip_code in scrip_codes:
                try:
                    quote = self.fetch_stock_quote(scrip_code)
                    
                    if quote:
                        # Extract relevant fields
                        stock_data = {
                            'scrip_code': scrip_code,
                            'security_id': quote.get('securityID', ''),
                            'company_name': quote.get('companyName', ''),
                            'last_price': quote.get('currentValue', 0),
                            'price_change': quote.get('change', 0),
                            'price_change_percent': quote.get('pChange', 0),
                            'open_price': quote.get('open', 0),
                            'high_price': quote.get('dayHigh', 0),
                            'low_price': quote.get('dayLow', 0),
                            'prev_close': quote.get('previousClose', 0),
                            'volume': quote.get('totalTradedVolume', 0),
                            'value': quote.get('totalTradedValue', 0),
                            'week_high_52': quote.get('52weekHigh', 0),
                            'week_low_52': quote.get('52weekLow', 0),
                            'face_value': quote.get('faceValue', 0),
                            'market_cap': quote.get('mktCap', 0),
                            'group': quote.get('group', ''),
                            'industry': quote.get('industry', ''),
                            'updated_on': quote.get('updatedOn', '')
                        }
                        all_quotes.append(stock_data)
                        logger.info(f"✓ {scrip_code}: {stock_data['company_name']} - ₹{stock_data['last_price']}")
                    else:
                        failed_scrips.append(scrip_code)
                        logger.warning(f"✗ Failed to fetch: {scrip_code}")
                    
                    # Rate limiting - small delay between requests
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_scrips.append(scrip_code)
                    logger.error(f"Error fetching {scrip_code}: {e}")
                    continue
            
            if all_quotes:
                df = pd.DataFrame(all_quotes)
                df['timestamp'] = datetime.now().isoformat()
                df['source'] = 'CUSTOM_SCRIPS'
                
                logger.info(f"Successfully fetched {len(all_quotes)} out of {len(scrip_codes)} scrips")
                if failed_scrips:
                    logger.warning(f"Failed scrips: {', '.join(failed_scrips)}")
                
                return df
            else:
                logger.error("No quotes fetched for any scrip")
                return None
                
        except Exception as e:
            logger.error(f"Error in fetch_custom_scrips: {e}")
            return None
            return None
    
    def fetch_category_stocks(self, category: str = "A") -> Optional[pd.DataFrame]:
        """
        Fetch stocks by category
        
        Args:
            category: Stock category (A, B, T, etc.)
        
        Returns:
            DataFrame with stock information
        """
        try:
            logger.info(f"Fetching stocks in category: {category}")
            stocks = self.bse.getScripCodes(category)
            
            if stocks:
                # Convert to DataFrame
                stock_list = []
                for code, name in stocks.items():
                    stock_list.append({
                        'scrip_code': code,
                        'scrip_name': name,
                        'category': category
                    })
                
                df = pd.DataFrame(stock_list)
                logger.info(f"Successfully fetched {len(df)} stocks in category {category}")
                return df
            else:
                logger.warning(f"No stocks found in category {category}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching category {category} stocks: {e}")
            return None
    
    def fetch_all_stocks(self) -> Optional[pd.DataFrame]:
        """
        Fetch all BSE listed stocks from multiple categories
        Returns comprehensive DataFrame with stock information
        """
        try:
            logger.info("Fetching all BSE stocks from multiple categories...")
            
            all_stocks = []
            categories = ['A', 'B', 'T', 'Z']  # Main BSE categories
            
            for category in categories:
                try:
                    logger.info(f"Fetching category {category}...")
                    df = self.fetch_category_stocks(category)
                    if df is not None and not df.empty:
                        all_stocks.append(df)
                        time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Could not fetch category {category}: {e}")
                    continue
            
            if all_stocks:
                # Combine all categories
                combined_df = pd.concat(all_stocks, ignore_index=True)
                
                # Add timestamp
                combined_df['timestamp'] = datetime.now().isoformat()
                combined_df['source'] = 'BSEDATA_LIBRARY'
                
                # Remove duplicates
                combined_df = combined_df.drop_duplicates(subset=['scrip_code'])
                
                logger.info(f"Successfully fetched {len(combined_df)} unique stocks")
                return combined_df
            else:
                logger.error("No stocks fetched from any category")
                return None
                
        except Exception as e:
            logger.error(f"Error in fetch_all_stocks: {e}")
            return None
    
    def fetch_stocks_with_prices(self, limit: int = 50) -> Optional[pd.DataFrame]:
        """
        Fetch stocks with current prices (top gainers + losers)
        This gives us real-time price data for active stocks
        
        Args:
            limit: Number of stocks to fetch from each category
        
        Returns:
            DataFrame with stock information including prices
        """
        try:
            logger.info("Fetching stocks with current prices...")
            
            all_stocks = []
            
            # Fetch top gainers
            gainers = self.fetch_top_gainers()
            if gainers is not None and not gainers.empty:
                gainers['category'] = 'TOP_GAINER'
                all_stocks.append(gainers)
            
            # Fetch top losers
            losers = self.fetch_top_losers()
            if losers is not None and not losers.empty:
                losers['category'] = 'TOP_LOSER'
                all_stocks.append(losers)
            
            if all_stocks:
                # Combine all data
                combined_df = pd.concat(all_stocks, ignore_index=True)
                
                # Add timestamp
                combined_df['timestamp'] = datetime.now().isoformat()
                combined_df['source'] = 'BSEDATA_LIBRARY'
                
                # Standardize column names
                combined_df = self.standardize_dataframe(combined_df)
                
                logger.info(f"Successfully fetched {len(combined_df)} stocks with prices")
                return combined_df
            else:
                logger.error("No stock data fetched")
                return None
                
        except Exception as e:
            logger.error(f"Error in fetch_stocks_with_prices: {e}")
            return None
    
    def standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame columns for consistency
        """
        try:
            # Common column mappings from bsedata library
            column_mapping = {
                'scripCode': 'scrip_code',
                'name': 'scrip_name',
                'LTP': 'last_price',
                'change': 'price_change',
                'pChange': 'price_change_percent',
                'open': 'open_price',
                'high': 'high_price',
                'low': 'low_price',
                'previousClose': 'prev_close',
                'totalTradedValue': 'traded_value',
                'totalTradedVolume': 'traded_volume',
                'yearHigh': 'year_high',
                'yearLow': 'year_low',
                'marketCap': 'market_cap'
            }
            
            df = df.rename(columns=column_mapping)
            
            return df
            
        except Exception as e:
            logger.error(f"Error standardizing dataframe: {e}")
            return df
    
    def fetch_stocks(self, retry: bool = True, include_prices: bool = True,
                    use_custom_scrips: bool = False, scrip_codes: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        Main method to fetch BSE stocks with retry logic
        
        Args:
            retry: Enable retry on failure
            include_prices: If True, fetch stocks with prices (faster, ~10 stocks)
                          If False, fetch all stocks (slower, thousands of stocks)
            use_custom_scrips: If True, fetch custom scrip list from file
            scrip_codes: Optional list of specific scrip codes to fetch
        
        Returns:
            DataFrame with stock information
        """
        attempts = 0
        max_attempts = config.MAX_RETRIES if retry else 1
        
        while attempts < max_attempts:
            try:
                # Priority 1: Specific scrip codes provided
                if scrip_codes:
                    df = self.fetch_custom_scrips(scrip_codes)
                # Priority 2: Use custom scrips from file
                elif use_custom_scrips:
                    df = self.fetch_custom_scrips()
                # Priority 3: Top gainers/losers (default)
                elif include_prices:
                    df = self.fetch_stocks_with_prices()
                # Priority 4: All stocks (comprehensive)
                else:
                    df = self.fetch_all_stocks()
                
                if df is not None and not df.empty:
                    return df
                
                # If failed, wait and retry
                attempts += 1
                if attempts < max_attempts:
                    logger.warning(f"Attempt {attempts} failed, retrying in {config.RETRY_DELAY_SECONDS}s...")
                    time.sleep(config.RETRY_DELAY_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in fetch_stocks attempt {attempts + 1}: {e}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(config.RETRY_DELAY_SECONDS)
        
        logger.error("All fetch attempts failed")
        return None
    
    def save_to_csv(self, df: pd.DataFrame, filename: Optional[str] = None) -> bool:
        """
        Save stock data to CSV file
        """
        try:
            if filename is None:
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = str(config.STOCK_DATA_FILE).format(date=date_str)
            
            df.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
            
            # Also update master file
            master_file = config.STOCK_MASTER_FILE
            df.to_csv(master_file, index=False)
            logger.info(f"Master file updated: {master_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            return False
    
    def get_stock_count(self) -> Dict[str, any]:
        """
        Get statistics about fetched stocks
        """
        try:
            if config.STOCK_MASTER_FILE.exists():
                df = pd.read_csv(config.STOCK_MASTER_FILE)
                stats = {
                    'total_stocks': len(df),
                    'last_updated': df['timestamp'].iloc[0] if 'timestamp' in df.columns else 'Unknown'
                }
                
                if 'category' in df.columns:
                    stats['by_category'] = df['category'].value_counts().to_dict()
                
                if 'last_price' in df.columns:
                    stats['avg_price'] = df['last_price'].mean()
                    stats['price_range'] = f"{df['last_price'].min()} - {df['last_price'].max()}"
                
                return stats
            else:
                return {'total_stocks': 0, 'last_updated': 'Never'}
                
        except Exception as e:
            logger.error(f"Error getting stock count: {e}")
            return {'error': str(e)}


def main():
    """Test function"""
    fetcher = BSEStockFetcher()
    
    logger.info("Starting BSE stock fetch using bsedata library...")
    
    # Fetch stocks with prices (faster, recommended for regular updates)
    logger.info("\n=== Fetching stocks with current prices ===")
    df = fetcher.fetch_stocks(include_prices=True)
    
    if df is not None:
        logger.info(f"Successfully fetched {len(df)} stocks")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info(f"\nSample data (first 5 stocks):")
        print(df.head().to_string())
        
        # Save to file
        fetcher.save_to_csv(df)
        
        # Get statistics
        stats = fetcher.get_stock_count()
        logger.info(f"\nStatistics: {stats}")
    else:
        logger.error("Failed to fetch stocks")
    
    # Optional: Fetch all stocks (uncomment if needed - takes longer)
    # logger.info("\n=== Fetching all BSE stocks ===")
    # df_all = fetcher.fetch_stocks(include_prices=False)
    # if df_all is not None:
    #     logger.info(f"Total stocks in all categories: {len(df_all)}")


if __name__ == "__main__":
    main()

# Made with Bob
