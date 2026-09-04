"""Alerts router — CRUD for price/% alert rules."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import Alert, AlertLog

router = APIRouter()

_VALID_CONDITIONS = {"price_above", "price_below", "pct_change_up", "pct_change_down"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    symbol: str
    exchange: str
    condition_type: str
    threshold: float
    notes: str | None = None


class AlertUpdate(BaseModel):
    threshold: float | None = None
    active: bool | None = None
    notes: str | None = None


class AlertOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    condition_type: str
    threshold: float
    active: bool
    notes: str | None
    created_at: str

    model_config = {"from_attributes": True}


class AlertLogOut(BaseModel):
    id: int
    alert_id: int
    triggered_at: str
    price_at_trigger: float
    notified: bool

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[AlertOut])
def list_alerts(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Alert)
    if active_only:
        q = q.filter(Alert.active == True)  # noqa: E712
    return q.order_by(Alert.created_at.desc()).all()


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    if payload.condition_type not in _VALID_CONDITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"condition_type must be one of {sorted(_VALID_CONDITIONS)}",
        )
    alert = Alert(
        symbol=payload.symbol,
        exchange=payload.exchange.upper(),
        condition_type=payload.condition_type,
        threshold=payload.threshold,
        notes=payload.notes,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.put("/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.threshold is not None:
        alert.threshold = payload.threshold
    if payload.active is not None:
        alert.active = payload.active
    if payload.notes is not None:
        alert.notes = payload.notes
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()


@router.get("/{alert_id}/log", response_model=list[AlertLogOut])
def get_alert_log(alert_id: int, db: Session = Depends(get_db)):
    return (
        db.query(AlertLog)
        .filter(AlertLog.alert_id == alert_id)
        .order_by(AlertLog.triggered_at.desc())
        .all()
    )
