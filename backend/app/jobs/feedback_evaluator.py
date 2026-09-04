"""
Feedback evaluator job.
For every agent_analysis row whose target_review_date has passed and that
has no feedback yet, fetches the current price, computes the outcome, and
writes an agent_feedback row — closing the adaptive loop.
"""
from __future__ import annotations

from datetime import date

from loguru import logger
from sqlalchemy import and_

from backend.app.core.db import SessionLocal
from backend.app.models import AgentAnalysis, AgentFeedback, PriceHistory


def run() -> None:
    logger.info("feedback_evaluator: starting")
    db = SessionLocal()
    try:
        today = date.today().isoformat()

        # Analyses whose review window has elapsed and have no feedback yet
        due = (
            db.query(AgentAnalysis)
            .outerjoin(AgentFeedback, AgentFeedback.analysis_id == AgentAnalysis.id)
            .filter(
                and_(
                    AgentAnalysis.target_review_date <= today,
                    AgentFeedback.id == None,  # noqa: E711
                )
            )
            .all()
        )

        if not due:
            logger.info("feedback_evaluator: nothing due today")
            return

        for analysis in due:
            try:
                # Price at time of analysis
                price_at = (
                    db.query(PriceHistory)
                    .filter(
                        PriceHistory.symbol == analysis.symbol,
                        PriceHistory.exchange == analysis.exchange,
                        PriceHistory.timestamp <= analysis.generated_at,
                    )
                    .order_by(PriceHistory.timestamp.desc())
                    .first()
                )

                # Most recent price
                price_now = (
                    db.query(PriceHistory)
                    .filter(
                        PriceHistory.symbol == analysis.symbol,
                        PriceHistory.exchange == analysis.exchange,
                    )
                    .order_by(PriceHistory.timestamp.desc())
                    .first()
                )

                if not price_at or not price_now:
                    logger.warning(
                        f"feedback_evaluator: insufficient price data for "
                        f"analysis {analysis.id} ({analysis.symbol})"
                    )
                    continue

                pct = (price_now.close - price_at.close) / price_at.close * 100

                # Simple heuristic: was the risk flag directionally correct?
                was_useful: bool | None = None
                if analysis.risk_flag == "high" and pct < -3:
                    was_useful = True   # flagged risky → stock fell
                elif analysis.risk_flag == "low" and pct > 3:
                    was_useful = True   # flagged safe → stock rose
                elif analysis.risk_flag in ("high", "low"):
                    was_useful = False  # flag went the wrong way

                fb = AgentFeedback(
                    analysis_id=analysis.id,
                    outcome_price=price_now.close,
                    outcome_pct_change=round(pct, 2),
                    was_flag_useful=was_useful,
                )
                db.add(fb)
                logger.info(
                    f"feedback_evaluator: analysis {analysis.id} "
                    f"({analysis.symbol}) outcome={pct:+.2f}%, useful={was_useful}"
                )

            except Exception as exc:
                logger.error(f"feedback_evaluator: error on analysis {analysis.id}: {exc}")

        db.commit()
        logger.info(f"feedback_evaluator: processed {len(due)} analyses")
    except Exception as exc:
        logger.error(f"feedback_evaluator job failed: {exc}")
        db.rollback()
    finally:
        db.close()
