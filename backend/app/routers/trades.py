"""
Trades router — manual trade entry, file upload import, and portfolio view.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import Portfolio, Trade

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class TradeCreate(BaseModel):
    trade_date: str        # YYYY-MM-DD
    symbol: str
    exchange: str = "BSE"
    company_name: str | None = None
    trade_type: str        # BUY | SELL
    quantity: int
    price: float
    brokerage: float = 0.0
    notes: str | None = None


class TradeOut(BaseModel):
    id: int
    trade_date: str
    symbol: str
    exchange: str
    company_name: str | None
    trade_type: str
    quantity: int
    price: float
    brokerage: float

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    company_name: str | None
    total_quantity: int
    avg_buy_price: float
    total_invested: float
    current_price: float | None
    current_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None

    model_config = {"from_attributes": True}


# ── Trade endpoints ───────────────────────────────────────────────────────────

@router.get("", response_model=list[TradeOut])
def list_trades(symbol: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Trade)
    if symbol:
        q = q.filter(Trade.symbol == symbol)
    return q.order_by(Trade.trade_date.desc()).all()


@router.post("", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def add_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    if payload.trade_type.upper() not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="trade_type must be BUY or SELL")

    trade = Trade(
        trade_date=payload.trade_date,
        symbol=payload.symbol,
        exchange=payload.exchange.upper(),
        company_name=payload.company_name,
        trade_type=payload.trade_type.upper(),
        quantity=payload.quantity,
        price=payload.price,
        brokerage=payload.brokerage,
        notes=payload.notes,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    _recalculate_portfolio(payload.symbol, payload.exchange.upper(), db)
    return trade


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_trades(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accept a CSV or XLSX file and bulk-insert trades."""
    import io
    import pandas as pd

    content = await file.read()
    fname = (file.filename or "").lower()

    try:
        if fname.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    # Normalise column names
    df.columns = df.columns.str.lower().str.strip()
    rename = {
        "date": "trade_date", "scrip_code": "symbol", "scrip": "symbol",
        "code": "symbol", "type": "trade_type", "action": "trade_type",
        "qty": "quantity", "rate": "price", "company": "company_name",
        "name": "company_name",
    }
    df = df.rename(columns=rename)

    required = {"trade_date", "symbol", "quantity", "price", "trade_type"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing columns: {missing}")

    imported = 0
    symbols_touched: set[tuple[str, str]] = set()

    for _, row in df.iterrows():
        try:
            exch = str(row.get("exchange", "BSE")).upper()
            trade = Trade(
                trade_date=str(row["trade_date"])[:10],
                symbol=str(row["symbol"]).strip(),
                exchange=exch,
                company_name=str(row.get("company_name", "")) or None,
                trade_type=str(row["trade_type"]).upper().strip(),
                quantity=int(row["quantity"]),
                price=float(row["price"]),
                brokerage=float(row.get("brokerage", 0) or 0),
                notes=str(row.get("notes", "")) or None,
            )
            db.add(trade)
            symbols_touched.add((trade.symbol, trade.exchange))
            imported += 1
        except Exception:
            continue  # skip malformed rows

    db.commit()
    for sym, exch in symbols_touched:
        _recalculate_portfolio(sym, exch, db)

    return {"imported": imported, "skipped": len(df) - imported}


# ── Portfolio endpoint ────────────────────────────────────────────────────────

@router.get("/portfolio", response_model=list[PortfolioOut])
def get_portfolio(db: Session = Depends(get_db)):
    return db.query(Portfolio).filter(Portfolio.total_quantity > 0).all()


# ── Internal helper ───────────────────────────────────────────────────────────

def _recalculate_portfolio(symbol: str, exchange: str, db: Session) -> None:
    """FIFO recalculation — rebuild the portfolio row from all trades."""
    trades = (
        db.query(Trade)
        .filter(Trade.symbol == symbol, Trade.exchange == exchange)
        .order_by(Trade.trade_date.asc())
        .all()
    )

    qty = 0
    invested = 0.0

    for t in trades:
        if t.trade_type == "BUY":
            qty += t.quantity
            invested += t.quantity * t.price + t.brokerage
        elif t.trade_type == "SELL" and qty > 0:
            avg = invested / qty
            sell_qty = min(t.quantity, qty)
            invested -= sell_qty * avg
            qty -= sell_qty

    row = db.query(Portfolio).filter(
        Portfolio.symbol == symbol, Portfolio.exchange == exchange
    ).first()

    if qty == 0:
        if row:
            db.delete(row)
    else:
        avg_price = round(invested / qty, 2) if qty > 0 else 0.0
        if row is None:
            row = Portfolio(symbol=symbol, exchange=exchange)
            db.add(row)
        row.total_quantity = qty
        row.avg_buy_price = avg_price
        row.total_invested = round(invested, 2)

    db.commit()
