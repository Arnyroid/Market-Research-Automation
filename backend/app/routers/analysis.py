"""
Analysis router — cached AI analysis per symbol and on-demand refresh.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models import AgentAnalysis
from backend.app.services.ai_agent import run_analysis

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class AnalysisOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    generated_at: str
    risk_flag: str | None
    indicators_snapshot: dict | None
    structured_output: dict | None
    llm_output: str | None
    target_review_date: str | None

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{symbol}", response_model=AnalysisOut)
def get_latest_analysis(symbol: str, exchange: str = "NSE", db: Session = Depends(get_db)):
    """Return the most recent cached analysis for a symbol."""
    row = (
        db.query(AgentAnalysis)
        .filter(AgentAnalysis.symbol == symbol, AgentAnalysis.exchange == exchange.upper())
        .order_by(AgentAnalysis.generated_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No analysis found — trigger a refresh first")
    return row


@router.post("/{symbol}/refresh", status_code=202)
def refresh_analysis(
    symbol: str,
    exchange: str = "NSE",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Trigger a new agent_runner pass for this symbol (runs in background)."""
    background_tasks.add_task(_run_and_store, symbol, exchange.upper())
    return {"detail": f"Analysis refresh queued for {symbol}/{exchange.upper()}"}


@router.get("/{symbol}/history", response_model=list[AnalysisOut])
def get_analysis_history(
    symbol: str,
    exchange: str = "NSE",
    limit: int = 10,
    db: Session = Depends(get_db),
):
    return (
        db.query(AgentAnalysis)
        .filter(AgentAnalysis.symbol == symbol, AgentAnalysis.exchange == exchange.upper())
        .order_by(AgentAnalysis.generated_at.desc())
        .limit(limit)
        .all()
    )


# ── Background helper ─────────────────────────────────────────────────────────

def _run_and_store(symbol: str, exchange: str) -> None:
    from backend.app.core.db import SessionLocal
    db = SessionLocal()
    try:
        analysis = run_analysis(symbol, exchange, db)
        if analysis:
            db.add(analysis)
            db.commit()
    except Exception as exc:
        from loguru import logger
        logger.error(f"On-demand analysis failed for {symbol}: {exc}")
        db.rollback()
    finally:
        db.close()
