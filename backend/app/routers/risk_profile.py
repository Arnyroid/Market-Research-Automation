"""
Risk Profile router - endpoints for user risk profile management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from ..db import get_db
from ..models import RiskProfile
from pydantic import BaseModel

router = APIRouter(prefix="/risk-profile", tags=["risk-profile"])


class RiskProfileCreate(BaseModel):
    time_horizon: Optional[str] = None  # short-term, medium-term, long-term
    loss_tolerance: Optional[str] = None  # conservative, moderate, aggressive
    experience_level: Optional[str] = None  # beginner, intermediate, advanced


class RiskProfileResponse(RiskProfileCreate):
    id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.get("", response_model=Optional[RiskProfileResponse])
async def get_risk_profile(db: Session = Depends(get_db)):
    """Get user's risk profile"""
    try:
        profile = db.query(RiskProfile).first()
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=RiskProfileResponse)
async def create_risk_profile(profile: RiskProfileCreate, db: Session = Depends(get_db)):
    """Create or update risk profile"""
    try:
        # Check if profile already exists
        existing = db.query(RiskProfile).first()
        
        if existing:
            # Update existing
            existing.time_horizon = profile.time_horizon or existing.time_horizon
            existing.loss_tolerance = profile.loss_tolerance or existing.loss_tolerance
            existing.experience_level = profile.experience_level or existing.experience_level
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new
            new_profile = RiskProfile(
                time_horizon=profile.time_horizon,
                loss_tolerance=profile.loss_tolerance,
                experience_level=profile.experience_level,
                updated_at=datetime.utcnow()
            )
            db.add(new_profile)
            db.commit()
            db.refresh(new_profile)
            return new_profile
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=RiskProfileResponse)
async def update_risk_profile(profile: RiskProfileCreate, db: Session = Depends(get_db)):
    """Update risk profile"""
    try:
        existing = db.query(RiskProfile).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Risk profile not found")
        
        if profile.time_horizon is not None:
            existing.time_horizon = profile.time_horizon
        if profile.loss_tolerance is not None:
            existing.loss_tolerance = profile.loss_tolerance
        if profile.experience_level is not None:
            existing.experience_level = profile.experience_level
        
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
