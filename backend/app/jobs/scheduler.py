"""
Background scheduler jobs for the watchlist system
"""
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import (
    Watchlist, PriceHistory, Alert, AlertLog, AlertConditionType,
    AgentAnalysis, AgentFeedback, RiskProfile
)
from ..services import (
    DataFetchService, IndicatorsService, AIAgentService, NotifierService
)
import asyncio


class SchedulerJobs:
    """Container for all scheduler jobs"""
    
    @staticmethod
    def price_poller():
        """
        Fetch latest prices for all watched symbols
        Runs every N minutes during market hours
        """
        logger.info("Starting price_poller job")
        try:
            db = SessionLocal()
            data_service = DataFetchService()
            
            watchlist_items = db.query(Watchlist).all()
            
            for item in watchlist_items:
                try:
                    if item.exchange == "NSE":
                        price_data = data_service.fetch_nse_price(item.symbol)
                    else:
                        price_data = data_service.fetch_bse_price(item.symbol)
                    
                    if price_data:
                        price_entry = PriceHistory(
                            symbol=item.symbol,
                            exchange=item.exchange,
                            timestamp=price_data["timestamp"],
                            open=price_data.get("open"),
                            high=price_data.get("high"),
                            low=price_data.get("low"),
                            close=price_data["price"],
                            volume=price_data.get("volume")
                        )
                        db.add(price_entry)
                        logger.info(f"Stored price for {item.symbol}: ₹{price_data['price']}")
                except Exception as e:
                    logger.error(f"Error fetching price for {item.symbol}: {e}")
            
            db.commit()
            logger.info("price_poller job completed successfully")
        except Exception as e:
            logger.error(f"price_poller job failed: {e}")
        finally:
            db.close()
    
    @staticmethod
    def alert_checker():
        """
        Check if any active alerts should trigger based on latest prices
        Runs right after price_poller
        """
        logger.info("Starting alert_checker job")
        try:
            db = SessionLocal()
            notifier = NotifierService()
            
            # Get all active alerts
            active_alerts = db.query(Alert).filter(Alert.active == True).all()
            
            for alert in active_alerts:
                try:
                    # Get latest price
                    latest_price = db.query(PriceHistory).filter(
                        PriceHistory.symbol == alert.symbol
                    ).order_by(PriceHistory.timestamp.desc()).first()
                    
                    if not latest_price:
                        continue
                    
                    current_price = latest_price.close
                    should_trigger = False
                    
                    if alert.condition_type == AlertConditionType.PRICE_ABOVE:
                        should_trigger = current_price >= alert.threshold
                    elif alert.condition_type == AlertConditionType.PRICE_BELOW:
                        should_trigger = current_price <= alert.threshold
                    elif alert.condition_type == AlertConditionType.PCT_CHANGE:
                        # Get price from 24 hours ago
                        yesterday = datetime.utcnow() - timedelta(hours=24)
                        old_price = db.query(PriceHistory).filter(
                            PriceHistory.symbol == alert.symbol,
                            PriceHistory.timestamp < yesterday
                        ).order_by(PriceHistory.timestamp.desc()).first()
                        
                        if old_price:
                            pct_change = ((current_price - old_price.close) / old_price.close) * 100
                            should_trigger = abs(pct_change) >= abs(alert.threshold)
                    
                    if should_trigger:
                        # Create alert log
                        alert_log = AlertLog(
                            alert_id=alert.id,
                            triggered_at=datetime.utcnow(),
                            price_at_trigger=current_price,
                            notified=False
                        )
                        db.add(alert_log)
                        
                        # Send notification
                        message = notifier.format_alert_message(
                            alert.symbol,
                            alert.condition_type.value,
                            current_price,
                            alert.threshold
                        )
                        
                        # Try to send Telegram (async wrapper)
                        try:
                            asyncio.run(notifier.send_telegram_notification(message))
                            alert_log.notified = True
                        except Exception as e:
                            logger.error(f"Failed to send Telegram notification: {e}")
                        
                        # Try to send email (sync)
                        notifier.send_email_notification(
                            subject=f"Alert: {alert.symbol}",
                            body=message
                        )
                        
                        logger.info(f"Alert triggered for {alert.symbol}: {message}")
                except Exception as e:
                    logger.error(f"Error checking alert {alert.id}: {e}")
            
            db.commit()
            logger.info("alert_checker job completed successfully")
        except Exception as e:
            logger.error(f"alert_checker job failed: {e}")
        finally:
            db.close()
    
    @staticmethod
    def indicator_calculator():
        """
        Calculate technical indicators for all watched symbols
        Runs daily or multiple times intraday
        """
        logger.info("Starting indicator_calculator job")
        try:
            db = SessionLocal()
            data_service = DataFetchService()
            
            watchlist_items = db.query(Watchlist).all()
            
            for item in watchlist_items:
                try:
                    price_history = data_service.fetch_historical_data(
                        item.symbol,
                        item.exchange,
                        days=30
                    )
                    
                    if price_history:
                        indicators = IndicatorsService.calculate_all_indicators(price_history)
                        logger.info(f"Calculated indicators for {item.symbol}: RSI={indicators.get('rsi_14', 'N/A')}, Volatility={indicators.get('volatility', 'N/A')}")
                except Exception as e:
                    logger.error(f"Error calculating indicators for {item.symbol}: {e}")
            
            logger.info("indicator_calculator job completed successfully")
        except Exception as e:
            logger.error(f"indicator_calculator job failed: {e}")
        finally:
            db.close()
    
    @staticmethod
    def agent_runner():
        """
        Run AI agent analysis for all watched symbols
        Runs daily by default or on-demand
        """
        logger.info("Starting agent_runner job")
        try:
            db = SessionLocal()
            data_service = DataFetchService()
            ai_service = AIAgentService()
            notifier = NotifierService()
            
            watchlist_items = db.query(Watchlist).all()
            risk_profile = db.query(RiskProfile).first()
            
            risk_profile_dict = None
            if risk_profile:
                risk_profile_dict = {
                    "time_horizon": risk_profile.time_horizon,
                    "loss_tolerance": risk_profile.loss_tolerance,
                    "experience_level": risk_profile.experience_level
                }
            
            for item in watchlist_items:
                try:
                    # Fetch price history
                    price_history = data_service.fetch_historical_data(
                        item.symbol,
                        item.exchange,
                        days=30
                    )
                    
                    if not price_history:
                        continue
                    
                    # Calculate indicators
                    indicators = IndicatorsService.calculate_all_indicators(price_history)
                    current_price = indicators.get("current_price", 0)
                    
                    # Get feedback history
                    feedback_history_records = db.query(AgentAnalysis, AgentFeedback).filter(
                        AgentAnalysis.symbol == item.symbol,
                        AgentAnalysis.id == AgentFeedback.analysis_id
                    ).order_by(AgentAnalysis.generated_at.desc()).limit(5).all()
                    
                    feedback_history = []
                    for analysis, feedback in feedback_history_records:
                        if feedback:
                            feedback_history.append({
                                "outcome_pct_change": feedback.outcome_pct_change,
                                "was_flag_useful": feedback.was_flag_useful
                            })
                    
                    # Generate analysis
                    analysis_result = ai_service.analyze_symbol(
                        symbol=item.symbol,
                        current_price=current_price,
                        indicators=indicators,
                        risk_profile=risk_profile_dict,
                        feedback_history=feedback_history
                    )
                    
                    if not analysis_result:
                        analysis_result = ai_service.generate_default_analysis(item.symbol, indicators)
                    
                    # Store analysis
                    new_analysis = AgentAnalysis(
                        symbol=item.symbol,
                        exchange=item.exchange,
                        generated_at=datetime.utcnow(),
                        indicators_snapshot=indicators,
                        news_context=None,
                        llm_output=analysis_result.get("trend_summary", ""),
                        risk_flag=analysis_result.get("risk_flag", "medium"),
                        target_review_date=datetime.utcnow() + timedelta(days=7)
                    )
                    db.add(new_analysis)
                    
                    logger.info(f"Generated analysis for {item.symbol}: {analysis_result.get('risk_flag')} risk")
                except Exception as e:
                    logger.error(f"Error running agent analysis for {item.symbol}: {e}")
            
            db.commit()
            logger.info("agent_runner job completed successfully")
        except Exception as e:
            logger.error(f"agent_runner job failed: {e}")
        finally:
            db.close()
    
    @staticmethod
    def feedback_evaluator():
        """
        Evaluate feedback on past analyses
        For any analysis whose target_review_date has passed,
        check actual price movement and mark if flag was useful
        """
        logger.info("Starting feedback_evaluator job")
        try:
            db = SessionLocal()
            data_service = DataFetchService()
            
            # Get analyses that need feedback evaluation
            analyses_to_evaluate = db.query(AgentAnalysis).filter(
                AgentAnalysis.target_review_date <= datetime.utcnow()
            ).all()
            
            for analysis in analyses_to_evaluate:
                try:
                    # Check if feedback already exists
                    existing_feedback = db.query(AgentFeedback).filter(
                        AgentFeedback.analysis_id == analysis.id
                    ).first()
                    
                    if existing_feedback:
                        continue  # Already evaluated
                    
                    # Get price at analysis time and current price
                    price_at_analysis = db.query(PriceHistory).filter(
                        PriceHistory.symbol == analysis.symbol,
                        PriceHistory.timestamp <= analysis.generated_at
                    ).order_by(PriceHistory.timestamp.desc()).first()
                    
                    current_price_entry = db.query(PriceHistory).filter(
                        PriceHistory.symbol == analysis.symbol
                    ).order_by(PriceHistory.timestamp.desc()).first()
                    
                    if price_at_analysis and current_price_entry:
                        outcome_price = current_price_entry.close
                        outcome_pct_change = IndicatorsService.calculate_percent_change(
                            current_price_entry.close,
                            price_at_analysis.close
                        )
                        
                        # Determine if flag was useful (simple heuristic)
                        was_useful = None
                        if analysis.risk_flag == "high" and outcome_pct_change < -5:
                            was_useful = True  # High risk flag preceded a drop
                        elif analysis.risk_flag == "low" and outcome_pct_change > 5:
                            was_useful = True  # Low risk flag preceded a rise
                        elif analysis.risk_flag == "medium":
                            was_useful = None  # Hard to judge
                        else:
                            was_useful = False
                        
                        feedback = AgentFeedback(
                            analysis_id=analysis.id,
                            outcome_price=outcome_price,
                            outcome_pct_change=outcome_pct_change,
                            evaluated_at=datetime.utcnow(),
                            was_flag_useful=was_useful
                        )
                        db.add(feedback)
                        logger.info(f"Evaluated feedback for {analysis.symbol}: {outcome_pct_change:+.2f}%, flag useful: {was_useful}")
                except Exception as e:
                    logger.error(f"Error evaluating feedback for analysis {analysis.id}: {e}")
            
            db.commit()
            logger.info("feedback_evaluator job completed successfully")
        except Exception as e:
            logger.error(f"feedback_evaluator job failed: {e}")
        finally:
            db.close()
