"""
SQLAlchemy ORM models for the stock watchlist and AI trading assistant
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class Watchlist(Base):
    """Watchlist entries for tracked stocks"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True)
    exchange = Column(String(10), nullable=False)  # NSE or BSE
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prices = relationship("PriceHistory", back_populates="watchlist", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="watchlist", cascade="all, delete-orphan")
    analyses = relationship("AgentAnalysis", back_populates="watchlist", cascade="all, delete-orphan")


class PriceHistory(Base):
    """Historical price data for watchlist symbols"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), ForeignKey("watchlist.symbol"), nullable=False)
    exchange = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="prices")


class AlertConditionType(str, enum.Enum):
    """Types of alert conditions"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PCT_CHANGE = "pct_change"


class Alert(Base):
    """Alert rules for price movements"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), ForeignKey("watchlist.symbol"), nullable=False)
    exchange = Column(String(10), nullable=False)
    condition_type = Column(SQLEnum(AlertConditionType), nullable=False)
    threshold = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="alerts")
    logs = relationship("AlertLog", back_populates="alert", cascade="all, delete-orphan")


class AlertLog(Base):
    """Log of triggered alerts"""
    __tablename__ = "alert_log"
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    price_at_trigger = Column(Float, nullable=False)
    notified = Column(Boolean, default=False)
    
    # Relationships
    alert = relationship("Alert", back_populates="logs")


class RiskProfile(Base):
    """User's risk profile (single row table)"""
    __tablename__ = "risk_profile"
    
    id = Column(Integer, primary_key=True)
    time_horizon = Column(String(50), nullable=True)  # short-term, medium-term, long-term
    loss_tolerance = Column(String(50), nullable=True)  # conservative, moderate, aggressive
    experience_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentAnalysis(Base):
    """AI agent analysis results"""
    __tablename__ = "agent_analysis"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), ForeignKey("watchlist.symbol"), nullable=False)
    exchange = Column(String(10), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Technical indicators snapshot
    indicators_snapshot = Column(JSON, nullable=True)  # {rsi, sma, ema, volatility, pct_change, etc}
    
    # Optional news context
    news_context = Column(JSON, nullable=True)  # {headlines: []}
    
    # LLM output
    llm_output = Column(Text, nullable=False)  # Plain-language trend summary
    
    # Risk flag
    risk_flag = Column(String(20), nullable=False)  # low, medium, high
    
    # When to evaluate feedback
    target_review_date = Column(DateTime, nullable=True)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="analyses")
    feedback = relationship("AgentFeedback", back_populates="analysis", cascade="all, delete-orphan")


class AgentFeedback(Base):
    """Feedback on agent analysis (observed outcomes)"""
    __tablename__ = "agent_feedback"
    
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey("agent_analysis.id"), nullable=False)
    
    # Outcome data
    outcome_price = Column(Float, nullable=True)
    outcome_pct_change = Column(Float, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    
    # Was the flag useful?
    was_flag_useful = Column(Boolean, nullable=True)
    
    # Relationships
    analysis = relationship("AgentAnalysis", back_populates="feedback")
