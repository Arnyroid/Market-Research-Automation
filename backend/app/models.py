"""
SQLAlchemy ORM models — one class per database table.

Tables
------
  watchlist          – symbols the user is tracking (NSE or BSE)
  price_history      – OHLCV rows written by the price poller
  trades             – buy / sell transactions
  portfolio          – aggregated current holdings (derived from trades)
  alerts             – active alert rules
  alert_log          – history of triggered alerts
  risk_profile       – single-row user risk preferences
  agent_analysis     – LLM-generated analysis for a symbol
  agent_feedback     – outcome data written N days after an analysis
  corporate_actions  – dividends, bonus shares, stock splits
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.db import Base


# ── Watchlist ────────────────────────────────────────────────────────────────

class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False)   # NSE | BSE
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # one watchlist entry → many alerts
    alerts: Mapped[list["Alert"]] = relationship(back_populates="watchlist_entry",
                                                  cascade="all, delete-orphan")


# ── Price History ─────────────────────────────────────────────────────────────

class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=True)
    high: Mapped[float] = mapped_column(Float, nullable=True)
    low: Mapped[float] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)


# ── Trades ────────────────────────────────────────────────────────────────────

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)   # YYYY-MM-DD
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False, default="BSE")
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    trade_type: Mapped[str] = mapped_column(String(4), nullable=False)    # BUY | SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    brokerage: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    # Populated by _recalculate_portfolio for SELL trades — FIFO realized gain/loss
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── Portfolio (aggregated holdings) ─────────────────────────────────────────

class Portfolio(Base):
    __tablename__ = "portfolio"
    __table_args__ = (UniqueConstraint("symbol", "exchange", name="uq_portfolio_symbol_exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False, default="BSE")
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_buy_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_invested: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_price: Mapped[float] = mapped_column(Float, nullable=True)
    current_value: Mapped[float] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=True)
    unrealized_pnl_pct: Mapped[float] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(),
                                                    server_default=func.now())


# ── Alerts ────────────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # nullable FK — alert can exist for a watchlist item, or stand-alone for a
    # portfolio stock not currently on the watchlist
    watchlist_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("watchlist.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False)
    # price_above | price_below | pct_change_up | pct_change_down
    condition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    repeating: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    watchlist_entry: Mapped["Watchlist | None"] = relationship(back_populates="alerts")
    logs: Mapped[list["AlertLog"]] = relationship(back_populates="alert",
                                                    cascade="all, delete-orphan")


class AlertLog(Base):
    __tablename__ = "alert_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    price_at_trigger: Mapped[float] = mapped_column(Float, nullable=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    alert: Mapped["Alert"] = relationship(back_populates="logs")


# ── Risk Profile (single-row) ────────────────────────────────────────────────

class RiskProfile(Base):
    __tablename__ = "risk_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # short | medium | long
    time_horizon: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    # low | medium | high
    loss_tolerance: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    # beginner | intermediate | experienced
    experience_level: Mapped[str] = mapped_column(String(15), nullable=False, default="intermediate")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                  onupdate=func.now())


# ── Agent Analysis ────────────────────────────────────────────────────────────

class AgentAnalysis(Base):
    __tablename__ = "agent_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Structured snapshot: {"rsi": 58.3, "sma_20": 2340.5, "ema_50": 2280.1, ...}
    indicators_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Fundamental data snapshot from screener.in (P/E, ROE, ROCE, shareholding, peers…)
    fundamentals_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Optional: [{"headline": "...", "source": "...", "published": "..."}]
    news_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Full LLM text response
    llm_output: Mapped[str] = mapped_column(Text, nullable=True)
    # low | medium | high
    risk_flag: Mapped[str] = mapped_column(String(10), nullable=True)
    # Structured LLM response: {"summary": "...", "risk_flag": "...", "caveats": "..."}
    structured_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # When feedback_evaluator should evaluate outcome
    target_review_date: Mapped[str] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD

    feedback: Mapped[list["AgentFeedback"]] = relationship(back_populates="analysis",
                                                             cascade="all, delete-orphan")


# ── Agent Feedback ────────────────────────────────────────────────────────────

class AgentFeedback(Base):
    __tablename__ = "agent_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent_analysis.id", ondelete="CASCADE"), nullable=False
    )
    outcome_price: Mapped[float] = mapped_column(Float, nullable=True)
    outcome_pct_change: Mapped[float] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # True if the risk_flag was directionally correct, None if undecided
    was_flag_useful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # True if the BUY/HOLD/SELL/AVOID recommendation was accurate, None if undecided
    was_rec_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    analysis: Mapped["AgentAnalysis"] = relationship(back_populates="feedback")


# ── Corporate Actions ─────────────────────────────────────────────────────────

class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_date: Mapped[str] = mapped_column(String(10), nullable=False)   # YYYY-MM-DD
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), nullable=False, default="BSE")
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    # DIVIDEND | BONUS | SPLIT | RIGHTS
    action_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)     # for dividends
    ratio: Mapped[str] = mapped_column(String(10), nullable=True)   # e.g. "1:2"
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
