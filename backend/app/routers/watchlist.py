"""Watchlist router — CRUD for tracked symbols."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import Watchlist
from backend.app.services.data_fetch import fetch_quote, search_symbols

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
    added_at: datetime

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

    # Auto-fill company_name from a live quote if the caller didn't provide one
    company_name = payload.company_name
    if not company_name:
        try:
            quote = fetch_quote(payload.symbol, exchange)
            if quote and quote.company_name:
                company_name = quote.company_name
        except Exception:
            pass  # Non-fatal — symbol still gets added without a name

    item = Watchlist(
        symbol=payload.symbol,
        exchange=exchange,
        company_name=company_name,
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


@router.post("/backfill-names", status_code=status.HTTP_200_OK)
def backfill_company_names(db: Session = Depends(get_db)):
    """
    One-shot: fetch company names for any watchlist entry that is missing one.
    Safe to call multiple times — only updates rows where company_name is null/empty.
    """
    rows = (
        db.query(Watchlist)
        .filter((Watchlist.company_name == None) | (Watchlist.company_name == ""))
        .all()
    )
    updated = 0
    for row in rows:
        try:
            quote = fetch_quote(row.symbol, row.exchange)
            if quote and quote.company_name:
                row.company_name = quote.company_name
                updated += 1
        except Exception:
            pass
    db.commit()
    return {"updated": updated, "total": len(rows)}


class SearchResult(BaseModel):
    symbol: str
    exchange: str
    company_name: str


@router.get("/search", response_model=list[SearchResult])
def search(q: str):
    """Search NSE equity master by symbol or company name fragment."""
    return [
        SearchResult(symbol=s.symbol, exchange=s.exchange, company_name=s.company_name or "")
        for s in search_symbols(q)
    ]
