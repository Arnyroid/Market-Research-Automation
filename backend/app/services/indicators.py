"""
Technical indicators calculation service
"""
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from loguru import logger

# Try to use pandas-ta, fall back to manual calculations
try:
    import pandas_ta as ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("pandas-ta not available, using manual indicator calculations")


class IndicatorsService:
    """Service for calculating technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index
        
        Args:
            prices: List of close prices
            period: RSI period (default 14)
            
        Returns:
            RSI value or None
        """
        if len(prices) < period + 1:
            return None
        
        try:
            if TA_AVAILABLE:
                df = pd.DataFrame({"close": prices})
                rsi = ta.rsi(df["close"], length=period)
                return float(rsi.iloc[-1]) if not rsi.empty else None
            else:
                # Manual RSI calculation
                prices = np.array(prices, dtype=float)
                deltas = np.diff(prices)
                seed = deltas[:period + 1]
                
                up = seed[seed >= 0].sum() / period
                down = -seed[seed < 0].sum() / period
                
                rs = up / down if down != 0 else 0
                rsi = 100.0 - 100.0 / (1.0 + rs)
                
                # Calculate remaining RSI values
                for d in deltas[period + 1:]:
                    if d >= 0:
                        up = (up * (period - 1) + d) / period
                        down = down * (period - 1) / period
                    else:
                        up = up * (period - 1) / period
                        down = (down * (period - 1) - d) / period
                    
                    rs = up / down if down != 0 else 0
                    rsi = 100.0 - 100.0 / (1.0 + rs)
                
                return float(rsi)
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate Simple Moving Average
        
        Args:
            prices: List of close prices
            period: SMA period
            
        Returns:
            SMA value or None
        """
        if len(prices) < period:
            return None
        
        try:
            return float(np.mean(prices[-period:]))
        except Exception as e:
            logger.error(f"SMA calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate Exponential Moving Average
        
        Args:
            prices: List of close prices
            period: EMA period
            
        Returns:
            EMA value or None
        """
        if len(prices) < period:
            return None
        
        try:
            if TA_AVAILABLE:
                df = pd.DataFrame({"close": prices})
                ema = ta.ema(df["close"], length=period)
                return float(ema.iloc[-1]) if not ema.empty else None
            else:
                # Manual EMA calculation
                prices = np.array(prices, dtype=float)
                ema = prices[0]
                multiplier = 2 / (period + 1)
                
                for price in prices[1:]:
                    ema = price * multiplier + ema * (1 - multiplier)
                
                return float(ema)
        except Exception as e:
            logger.error(f"EMA calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate realized volatility (standard deviation of returns)
        
        Args:
            prices: List of close prices
            period: Volatility period
            
        Returns:
            Volatility (as annualized percentage) or None
        """
        if len(prices) < period:
            return None
        
        try:
            prices = np.array(prices[-period:], dtype=float)
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) * np.sqrt(252) * 100  # Annualized
            return float(volatility)
        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """
        Calculate Bollinger Bands
        
        Args:
            prices: List of close prices
            period: BB period
            std_dev: Standard deviation multiplier
            
        Returns:
            Dict with upper, middle, lower bands or None
        """
        if len(prices) < period:
            return None
        
        try:
            if TA_AVAILABLE:
                df = pd.DataFrame({"close": prices})
                bb = ta.bbands(df["close"], length=period, std=std_dev)
                if bb is not None and not bb.empty:
                    return {
                        "upper": float(bb.iloc[-1, 0]),
                        "middle": float(bb.iloc[-1, 1]),
                        "lower": float(bb.iloc[-1, 2])
                    }
            else:
                # Manual Bollinger Bands
                prices = np.array(prices[-period:], dtype=float)
                sma = np.mean(prices)
                std = np.std(prices)
                
                return {
                    "upper": float(sma + std_dev * std),
                    "middle": float(sma),
                    "lower": float(sma - std_dev * std)
                }
        except Exception as e:
            logger.error(f"Bollinger Bands calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
        """
        Calculate MACD
        
        Args:
            prices: List of close prices
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Dict with MACD, signal, histogram or None
        """
        if len(prices) < slow:
            return None
        
        try:
            if TA_AVAILABLE:
                df = pd.DataFrame({"close": prices})
                macd = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
                if macd is not None and not macd.empty:
                    return {
                        "macd": float(macd.iloc[-1, 0]),
                        "signal": float(macd.iloc[-1, 1]),
                        "histogram": float(macd.iloc[-1, 2])
                    }
            else:
                # Manual MACD using EMA
                prices_arr = np.array(prices, dtype=float)
                
                # Calculate EMAs
                ema_fast = prices_arr[0]
                ema_slow = prices_arr[0]
                
                mult_fast = 2 / (fast + 1)
                mult_slow = 2 / (slow + 1)
                
                for price in prices_arr[1:]:
                    ema_fast = price * mult_fast + ema_fast * (1 - mult_fast)
                    ema_slow = price * mult_slow + ema_slow * (1 - mult_slow)
                
                macd_line = ema_fast - ema_slow
                
                # Signal line (EMA of MACD)
                signal_line = macd_line
                mult_signal = 2 / (signal + 1)
                signal_line = macd_line * mult_signal + signal_line * (1 - mult_signal)
                
                return {
                    "macd": float(macd_line),
                    "signal": float(signal_line),
                    "histogram": float(macd_line - signal_line)
                }
        except Exception as e:
            logger.error(f"MACD calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_percent_change(current_price: float, previous_price: float) -> float:
        """
        Calculate percentage change
        
        Args:
            current_price: Current price
            previous_price: Previous price
            
        Returns:
            Percentage change
        """
        if previous_price == 0:
            return 0.0
        return ((current_price - previous_price) / previous_price) * 100
    
    @staticmethod
    def calculate_all_indicators(price_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate all indicators from price history
        
        Args:
            price_history: List of price data dicts with 'close' key
            
        Returns:
            Dict with all calculated indicators
        """
        try:
            if not price_history or len(price_history) < 2:
                return {}
            
            closes = [p["close"] for p in price_history]
            current_price = closes[-1]
            previous_price = closes[-2]
            
            indicators = {
                "rsi_14": IndicatorsService.calculate_rsi(closes, 14),
                "sma_20": IndicatorsService.calculate_sma(closes, 20),
                "sma_50": IndicatorsService.calculate_sma(closes, 50),
                "ema_20": IndicatorsService.calculate_ema(closes, 20),
                "ema_50": IndicatorsService.calculate_ema(closes, 50),
                "volatility": IndicatorsService.calculate_volatility(closes, 20),
                "bollinger_bands": IndicatorsService.calculate_bollinger_bands(closes, 20),
                "macd": IndicatorsService.calculate_macd(closes, 12, 26, 9),
                "pct_change": IndicatorsService.calculate_percent_change(current_price, previous_price),
                "current_price": current_price,
                "52week_high": max(closes) if closes else None,
                "52week_low": min(closes) if closes else None,
            }
            
            return indicators
        except Exception as e:
            logger.error(f"All indicators calculation error: {e}")
            return {}
