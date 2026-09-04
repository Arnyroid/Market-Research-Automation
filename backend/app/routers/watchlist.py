"""
Watchlist router - endpoints for managing watched stocks
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from ..db import get_db
from ..models import Watchlist, PriceHistory
from pydantic import BaseModel

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistItem(BaseModel):
    symbol: str
    exchange: str  # NSE or BSE
    
    class Config:
        from_attributes = True


class WatchlistResponse(WatchlistItem):
    id: int
    added_at: datetime


@router.get("", response_model=List[WatchlistResponse])
async def get_watchlist(db: Session = Depends(get_db)):
    """Get all watched stocks"""
    try:
        items = db.query(Watchlist).all()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=WatchlistResponse)
async def add_to_watchlist(item: WatchlistItem, db: Session = Depends(get_db)):
    """Add a stock to watchlist"""
    try:
        # Check if already exists
        existing = db.query(Watchlist).filter(Watchlist.symbol == item.symbol).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"{item.symbol} already in watchlist")
        
        watchlist_entry = Watchlist(
            symbol=item.symbol,
            exchange=item.exchange,
            added_at=datetime.utcnow()
        )
        db.add(watchlist_entry)
        db.commit()
        db.refresh(watchlist_entry)
        return watchlist_entry
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{watchlist_id}")
async def remove_from_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    """Remove a stock from watchlist"""
    try:
        item = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Watchlist item not found")
        
        db.delete(item)
        db.commit()
        return {"message": f"Removed {item.symbol} from watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/exists")
async def check_in_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Check if symbol is in watchlist"""
    try:
        item = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
        return {"exists": item is not None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
