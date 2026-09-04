"""Corporate actions router — dividends, bonus shares, stock splits."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import CorporateAction, Portfolio

router = APIRouter()

_VALID_TYPES = {"DIVIDEND", "BONUS", "SPLIT", "RIGHTS"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class CorporateActionCreate(BaseModel):
    action_date: str          # YYYY-MM-DD
    symbol: str
    exchange: str = "BSE"
    company_name: str | None = None
    action_type: str          # DIVIDEND | BONUS | SPLIT | RIGHTS
    quantity: float | None = None
    amount: float | None = None    # dividend total ₹
    ratio: str | None = None       # e.g. "1:2"
    notes: str | None = None


class CorporateActionOut(BaseModel):
    id: int
    action_date: str
    symbol: str
    exchange: str
    company_name: str | None
    action_type: str
    quantity: float | None
    amount: float | None
    ratio: str | None
    notes: str | None

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CorporateActionOut])
def list_actions(symbol: str | None = None, db: Session = Depends(get_db)):
    q = db.query(CorporateAction)
    if symbol:
        q = q.filter(CorporateAction.symbol == symbol)
    return q.order_by(CorporateAction.action_date.desc()).all()


@router.post("", response_model=CorporateActionOut, status_code=status.HTTP_201_CREATED)
def record_action(payload: CorporateActionCreate, db: Session = Depends(get_db)):
    atype = payload.action_type.upper()
    if atype not in _VALID_TYPES:
        raise HTTPException(400, f"action_type must be one of {_VALID_TYPES}")

    exch = payload.exchange.upper()

    # ── Validate ratio for BONUS/SPLIT ───────────────────────────────────────
    if atype in ("BONUS", "SPLIT") and not payload.ratio:
        raise HTTPException(400, "ratio is required for BONUS and SPLIT actions")

    portfolio_row = db.query(Portfolio).filter(
        Portfolio.symbol == payload.symbol, Portfolio.exchange == exch
    ).first()

    qty_held = portfolio_row.total_quantity if portfolio_row else 0

    # ── Compute derived fields & update portfolio ─────────────────────────────
    final_qty: float | None = payload.quantity
    final_amount: float | None = payload.amount

    if atype == "DIVIDEND" and portfolio_row and payload.amount:
        # amount stored as per-share in the payload; compute total
        final_amount = round(qty_held * payload.amount, 2)
        final_qty = float(qty_held)

    elif atype in ("BONUS", "SPLIT") and portfolio_row and payload.ratio:
        try:
            a, b = map(int, payload.ratio.split(":"))
        except ValueError:
            raise HTTPException(400, "ratio must be in 'A:B' format, e.g. '1:2'")

        if atype == "BONUS":
            bonus_qty = (qty_held // b) * a
            new_qty = qty_held + bonus_qty
            new_avg = round(portfolio_row.total_invested / new_qty, 2) if new_qty else 0
            final_qty = float(bonus_qty)
        else:  # SPLIT
            multiplier = b / a
            new_qty = int(qty_held * multiplier)
            new_avg = round(portfolio_row.avg_buy_price / multiplier, 2)
            final_qty = float(new_qty - qty_held)

        portfolio_row.total_quantity = new_qty
        portfolio_row.avg_buy_price = new_avg

    action = CorporateAction(
        action_date=payload.action_date,
        symbol=payload.symbol,
        exchange=exch,
        company_name=payload.company_name,
        action_type=atype,
        quantity=final_qty,
        amount=final_amount,
        ratio=payload.ratio,
        notes=payload.notes,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
