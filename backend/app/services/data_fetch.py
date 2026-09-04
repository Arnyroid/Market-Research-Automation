"""
Data fetching service for NSE and BSE stock prices
"""
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

# Try to import bsedata
try:
    from bsedata.bse import BSE
    BSE_AVAILABLE = True
except ImportError:
    BSE_AVAILABLE = False
    logger.warning("bsedata not available, will use yfinance as fallback")

# Try to import nsepython
try:
    import nsepython
    NSE_AVAILABLE = True
except ImportError:
    NSE_AVAILABLE = False
    logger.warning("nsepython not available, will use yfinance as fallback")

import yfinance as yf


class DataFetchService:
    """Service for fetching stock data from NSE and BSE"""
    
    def __init__(self):
        self.bse = None
        if BSE_AVAILABLE:
            try:
                self.bse = BSE()
            except Exception as e:
                logger.error(f"Failed to initialize BSE: {e}")
    
    def fetch_nse_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest price for NSE symbol
        
        Args:
            symbol: NSE symbol (e.g., 'RELIANCE')
            
        Returns:
            Dict with price data or None if fetch fails
        """
        try:
            if NSE_AVAILABLE:
                quote = nsepython.nse_get_quote(symbol)
                return {
                    "symbol": symbol,
                    "exchange": "NSE",
                    "price": quote.get("lastPrice", 0),
                    "change": quote.get("change", 0),
                    "pct_change": quote.get("pctChange", 0),
                    "timestamp": datetime.utcnow(),
                    "open": quote.get("open", None),
                    "high": quote.get("dayHigh", None),
                    "low": quote.get("dayLow", None),
                    "volume": quote.get("totalTradedVolume", None)
                }
        except Exception as e:
            logger.error(f"NSE fetch error for {symbol}: {e}")
        
        # Fallback to yfinance for NSE
        return self._fetch_yfinance(f"{symbol}.NS")
    
    def fetch_bse_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest price for BSE symbol
        
        Args:
            symbol: BSE symbol/scrip code
            
        Returns:
            Dict with price data or None if fetch fails
        """
        try:
            if BSE_AVAILABLE and self.bse:
                quote = self.bse.getQuote(symbol)
                if quote:
                    return {
                        "symbol": symbol,
                        "exchange": "BSE",
                        "price": float(quote.get("ltp", 0)),
                        "change": float(quote.get("change", 0)),
                        "pct_change": float(quote.get("pctchange", 0)),
                        "timestamp": datetime.utcnow(),
                        "open": float(quote.get("open", None)) if quote.get("open") else None,
                        "high": float(quote.get("high", None)) if quote.get("high") else None,
                        "low": float(quote.get("low", None)) if quote.get("low") else None,
                        "volume": int(quote.get("volume", None)) if quote.get("volume") else None
                    }
        except Exception as e:
            logger.error(f"BSE fetch error for {symbol}: {e}")
        
        # Fallback to yfinance for BSE
        return self._fetch_yfinance(f"{symbol}.BO")
    
    def _fetch_yfinance(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fallback to yfinance for price data
        
        Args:
            ticker: Ticker symbol with exchange suffix (e.g., 'RELIANCE.NS')
            
        Returns:
            Dict with price data or None
        """
        try:
            data = yf.download(ticker, period="1d", progress=False)
            if data.empty:
                return None
            
            latest = data.iloc[-1]
            return {
                "symbol": ticker.split(".")[0],
                "exchange": "NSE" if ".NS" in ticker else "BSE",
                "price": float(latest["Close"]),
                "change": 0,
                "pct_change": 0,
                "timestamp": datetime.utcnow(),
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "volume": int(latest["Volume"])
            }
        except Exception as e:
            logger.error(f"YFinance fetch error for {ticker}: {e}")
            return None
    
    def fetch_historical_data(self, symbol: str, exchange: str, days: int = 30) -> Optional[list]:
        """
        Fetch historical OHLCV data
        
        Args:
            symbol: Stock symbol
            exchange: NSE or BSE
            days: Number of days of history
            
        Returns:
            List of OHLCV records or None
        """
        try:
            ticker = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
            data = yf.download(ticker, period=f"{days}d", progress=False)
            
            if data.empty:
                return None
            
            records = []
            for index, row in data.iterrows():
                records.append({
                    "timestamp": index.to_pydatetime(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                    "symbol": symbol,
                    "exchange": exchange
                })
            
            return records
        except Exception as e:
            logger.error(f"Historical data fetch error for {symbol}: {e}")
            return None
