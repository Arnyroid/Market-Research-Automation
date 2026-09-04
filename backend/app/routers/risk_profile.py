"""Risk profile router — GET and PUT for the single-row user risk profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import RiskProfile

router = APIRouter()

_VALID_HORIZONS = {"short", "medium", "long"}
_VALID_TOLERANCES = {"low", "medium", "high"}
_VALID_EXPERIENCE = {"beginner", "intermediate", "experienced"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class RiskProfileOut(BaseModel):
    time_horizon: str
    loss_tolerance: str
    experience_level: str
    updated_at: str

    model_config = {"from_attributes": True}


class RiskProfileUpdate(BaseModel):
    time_horizon: str | None = None
    loss_tolerance: str | None = None
    experience_level: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=RiskProfileOut)
def get_risk_profile(db: Session = Depends(get_db)):
    profile = db.get(RiskProfile, 1)
    if not profile:
        # Auto-create with defaults on first access
        profile = RiskProfile(id=1)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("", response_model=RiskProfileOut)
def update_risk_profile(payload: RiskProfileUpdate, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    profile = db.get(RiskProfile, 1)
    if not profile:
        profile = RiskProfile(id=1)
        db.add(profile)

    if payload.time_horizon is not None:
        if payload.time_horizon not in _VALID_HORIZONS:
            raise HTTPException(400, f"time_horizon must be one of {_VALID_HORIZONS}")
        profile.time_horizon = payload.time_horizon

    if payload.loss_tolerance is not None:
        if payload.loss_tolerance not in _VALID_TOLERANCES:
            raise HTTPException(400, f"loss_tolerance must be one of {_VALID_TOLERANCES}")
        profile.loss_tolerance = payload.loss_tolerance

    if payload.experience_level is not None:
        if payload.experience_level not in _VALID_EXPERIENCE:
            raise HTTPException(400, f"experience_level must be one of {_VALID_EXPERIENCE}")
        profile.experience_level = payload.experience_level

    db.commit()
    db.refresh(profile)
    return profile
