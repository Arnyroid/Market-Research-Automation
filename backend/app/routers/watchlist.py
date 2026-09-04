"""Watchlist router — CRUD for tracked symbols."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import Watchlist
from backend.app.services.data_fetch import search_symbols

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class WatchlistAdd(BaseModel):
    symbol: str
    exchange: str          # NSE | BSE
    company_name: str | None = None
    sector: str | None = None


class WatchlistOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    company_name: str | None
    sector: str | None
    added_at: str

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[WatchlistOut])
def list_watchlist(db: Session = Depends(get_db)):
    return db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(payload: WatchlistAdd, db: Session = Depends(get_db)):
    exchange = payload.exchange.upper()
    if exchange not in ("NSE", "BSE"):
        raise HTTPException(status_code=400, detail="exchange must be NSE or BSE")

    existing = (
        db.query(Watchlist)
        .filter(Watchlist.symbol == payload.symbol, Watchlist.exchange == exchange)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in watchlist")

    item = Watchlist(
        symbol=payload.symbol,
        exchange=exchange,
        company_name=payload.company_name,
        sector=payload.sector,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Watchlist, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    db.delete(item)
    db.commit()


@router.get("/search")
def search(q: str, db: Session = Depends(get_db)):
    """Search for symbols by name/ticker (NSE-only via nsepython for now)."""
    return search_symbols(q)
