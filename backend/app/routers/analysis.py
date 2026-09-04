"""
Analysis router - endpoints for AI agent analysis
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta
from ..db import get_db
from ..models import (
    AgentAnalysis, AgentFeedback, Watchlist, PriceHistory,
    RiskProfile
)
from ..services import AIAgentService, IndicatorsService, DataFetchService
from pydantic import BaseModel

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisResponse(BaseModel):
    id: int
    symbol: str
    generated_at: datetime
    indicators_snapshot: Optional[dict]
    news_context: Optional[dict]
    llm_output: str
    risk_flag: str
    target_review_date: Optional[datetime]
    
    class Config:
        from_attributes = True


class FeedbackResponse(BaseModel):
    id: int
    analysis_id: int
    outcome_price: Optional[float]
    outcome_pct_change: Optional[float]
    evaluated_at: Optional[datetime]
    was_flag_useful: Optional[bool]
    
    class Config:
        from_attributes = True


@router.get("/{symbol}", response_model=Optional[AnalysisResponse])
async def get_latest_analysis(symbol: str, db: Session = Depends(get_db)):
    """Get the latest analysis for a symbol"""
    try:
        analysis = db.query(AgentAnalysis).filter(
            AgentAnalysis.symbol == symbol
        ).order_by(desc(AgentAnalysis.generated_at)).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"No analysis found for {symbol}")
        
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/refresh")
async def refresh_analysis(symbol: str, db: Session = Depends(get_db)):
    """Trigger a new analysis for a symbol"""
    try:
        # Verify symbol is in watchlist
        watchlist_entry = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
        if not watchlist_entry:
            raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
        
        # Fetch price history for indicators
        data_service = DataFetchService()
        price_history = data_service.fetch_historical_data(symbol, watchlist_entry.exchange, 30)
        
        if not price_history:
            raise HTTPException(status_code=500, detail=f"Could not fetch price history for {symbol}")
        
        # Calculate indicators
        indicators = IndicatorsService.calculate_all_indicators(price_history)
        current_price = indicators.get("current_price", 0)
        
        # Get user's risk profile
        risk_profile = db.query(RiskProfile).first()
        risk_profile_dict = None
        if risk_profile:
            risk_profile_dict = {
                "time_horizon": risk_profile.time_horizon,
                "loss_tolerance": risk_profile.loss_tolerance,
                "experience_level": risk_profile.experience_level
            }
        
        # Get feedback history for context
        feedback_history_records = db.query(AgentAnalysis, AgentFeedback).filter(
            AgentAnalysis.symbol == symbol,
            AgentAnalysis.id == AgentFeedback.analysis_id
        ).order_by(desc(AgentAnalysis.generated_at)).limit(5).all()
        
        feedback_history = []
        for analysis, feedback in feedback_history_records:
            if feedback:
                feedback_history.append({
                    "outcome_pct_change": feedback.outcome_pct_change,
                    "was_flag_useful": feedback.was_flag_useful
                })
        
        # Generate analysis
        ai_service = AIAgentService()
        analysis_result = ai_service.analyze_symbol(
            symbol=symbol,
            current_price=current_price,
            indicators=indicators,
            risk_profile=risk_profile_dict,
            feedback_history=feedback_history
        )
        
        if not analysis_result:
            # Use fallback
            analysis_result = ai_service.generate_default_analysis(symbol, indicators)
        
        # Store analysis
        new_analysis = AgentAnalysis(
            symbol=symbol,
            exchange=watchlist_entry.exchange,
            generated_at=datetime.utcnow(),
            indicators_snapshot=indicators,
            news_context=None,
            llm_output=analysis_result.get("trend_summary", ""),
            risk_flag=analysis_result.get("risk_flag", "medium"),
            target_review_date=datetime.utcnow() + timedelta(days=7)
        )
        
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        
        return new_analysis
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/history")
async def get_analysis_history(symbol: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get analysis history for a symbol"""
    try:
        analyses = db.query(AgentAnalysis).filter(
            AgentAnalysis.symbol == symbol
        ).order_by(desc(AgentAnalysis.generated_at)).limit(limit).all()
        
        return analyses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{analysis_id}", response_model=Optional[FeedbackResponse])
async def get_feedback(analysis_id: int, db: Session = Depends(get_db)):
    """Get feedback for an analysis"""
    try:
        feedback = db.query(AgentFeedback).filter(
            AgentFeedback.analysis_id == analysis_id
        ).first()
        
        return feedback
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
