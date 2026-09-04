"""
Alerts router - endpoints for managing price alerts
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..db import get_db
from ..models import Alert, AlertLog, AlertConditionType
from pydantic import BaseModel

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    symbol: str
    exchange: str
    condition_type: AlertConditionType
    threshold: float


class AlertUpdate(BaseModel):
    condition_type: Optional[AlertConditionType] = None
    threshold: Optional[float] = None
    active: Optional[bool] = None


class AlertResponse(AlertCreate):
    id: int
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertLogResponse(BaseModel):
    id: int
    alert_id: int
    triggered_at: datetime
    price_at_trigger: float
    notified: bool
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[AlertResponse])
async def get_alerts(db: Session = Depends(get_db)):
    """Get all alerts"""
    try:
        alerts = db.query(Alert).all()
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol/{symbol}", response_model=List[AlertResponse])
async def get_alerts_for_symbol(symbol: str, db: Session = Depends(get_db)):
    """Get alerts for a specific symbol"""
    try:
        alerts = db.query(Alert).filter(Alert.symbol == symbol).all()
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=AlertResponse)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """Create a new alert"""
    try:
        new_alert = Alert(
            symbol=alert.symbol,
            exchange=alert.exchange,
            condition_type=alert.condition_type,
            threshold=alert.threshold,
            active=True,
            created_at=datetime.utcnow()
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: int, update: AlertUpdate, db: Session = Depends(get_db)):
    """Update an alert"""
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        if update.condition_type is not None:
            alert.condition_type = update.condition_type
        if update.threshold is not None:
            alert.threshold = update.threshold
        if update.active is not None:
            alert.active = update.active
        
        db.commit()
        db.refresh(alert)
        return alert
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert"""
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        db.delete(alert)
        db.commit()
        return {"message": "Alert deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}/logs", response_model=List[AlertLogResponse])
async def get_alert_logs(alert_id: int, db: Session = Depends(get_db)):
    """Get logs for an alert"""
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        logs = db.query(AlertLog).filter(AlertLog.alert_id == alert_id).order_by(AlertLog.triggered_at.desc()).all()
        return logs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
