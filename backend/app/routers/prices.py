"""
Prices router - endpoints for getting price data
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from ..db import get_db
from ..models import PriceHistory, Watchlist
from ..services import DataFetchService
from pydantic import BaseModel

router = APIRouter(prefix="/prices", tags=["prices"])


class PriceDataResponse(BaseModel):
    symbol: str
    exchange: str
    timestamp: datetime
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: float
    volume: Optional[int]
    
    class Config:
        from_attributes = True


class CurrentPriceResponse(BaseModel):
    symbol: str
    exchange: str
    current_price: float
    change: float
    pct_change: float
    timestamp: datetime


@router.get("/{symbol}", response_model=CurrentPriceResponse)
async def get_current_price(symbol: str, db: Session = Depends(get_db)):
    """Get current price for a symbol"""
    try:
        # Try to get latest from database first
        latest = db.query(PriceHistory).filter(
            PriceHistory.symbol == symbol
        ).order_by(desc(PriceHistory.timestamp)).first()
        
        if latest and (datetime.utcnow() - latest.timestamp).seconds < 300:  # Less than 5 minutes old
            return {
                "symbol": symbol,
                "exchange": latest.exchange,
                "current_price": latest.close,
                "change": 0,
                "pct_change": 0,
                "timestamp": latest.timestamp
            }
        
        # Fetch fresh data
        data_service = DataFetchService()
        
        # Try to get watchlist entry to determine exchange
        watchlist_entry = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
        exchange = watchlist_entry.exchange if watchlist_entry else "NSE"
        
        if exchange == "NSE":
            price_data = data_service.fetch_nse_price(symbol)
        else:
            price_data = data_service.fetch_bse_price(symbol)
        
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Could not fetch price for {symbol}")
        
        return price_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/history", response_model=List[PriceDataResponse])
async def get_price_history(symbol: str, days: int = 30, db: Session = Depends(get_db)):
    """Get price history for a symbol"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        history = db.query(PriceHistory).filter(
            PriceHistory.symbol == symbol,
            PriceHistory.timestamp >= cutoff_date
        ).order_by(PriceHistory.timestamp.asc()).all()
        
        if not history:
            # Try to fetch fresh history
            data_service = DataFetchService()
            watchlist_entry = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
            exchange = watchlist_entry.exchange if watchlist_entry else "NSE"
            
            price_records = data_service.fetch_historical_data(symbol, exchange, days)
            if price_records:
                for record in price_records:
                    price_entry = PriceHistory(
                        symbol=record["symbol"],
                        exchange=record["exchange"],
                        timestamp=record["timestamp"],
                        open=record["open"],
                        high=record["high"],
                        low=record["low"],
                        close=record["close"],
                        volume=record["volume"]
                    )
                    db.add(price_entry)
                
                db.commit()
                history = db.query(PriceHistory).filter(
                    PriceHistory.symbol == symbol,
                    PriceHistory.timestamp >= cutoff_date
                ).order_by(PriceHistory.timestamp.asc()).all()
        
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh/{symbol}")
async def refresh_price(symbol: str, db: Session = Depends(get_db)):
    """Manually refresh price for a symbol"""
    try:
        data_service = DataFetchService()
        
        # Get exchange from watchlist
        watchlist_entry = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
        if not watchlist_entry:
            raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
        
        exchange = watchlist_entry.exchange
        
        if exchange == "NSE":
            price_data = data_service.fetch_nse_price(symbol)
        else:
            price_data = data_service.fetch_bse_price(symbol)
        
        if not price_data:
            raise HTTPException(status_code=500, detail=f"Failed to fetch price for {symbol}")
        
        # Store in database
        price_entry = PriceHistory(
            symbol=symbol,
            exchange=exchange,
            timestamp=price_data["timestamp"],
            open=price_data.get("open"),
            high=price_data.get("high"),
            low=price_data.get("low"),
            close=price_data["price"],
            volume=price_data.get("volume")
        )
        db.add(price_entry)
        db.commit()
        
        return {
            "symbol": symbol,
            "price": price_data["price"],
            "timestamp": price_data["timestamp"]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
