"""
Alert engine — evaluates active alert rules against a new price tick
and fires the notifier when a rule is triggered.

Public API
----------
  check_alerts(symbol, exchange, current_price, db)  →  list[AlertLog]
"""
from __future__ import annotations

from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from backend.app.models import Alert, AlertLog
from backend.app.services import notifier


def check_alerts(
    symbol: str,
    exchange: str,
    current_price: float,
    prev_price: Optional[float],
    db: Session,
) -> list[AlertLog]:
    """
    Evaluate all active alerts for this symbol and fire any that are met.
    Deactivates a rule after it fires (one-shot behaviour).

    Returns a list of AlertLog rows that were written (already added to the
    session but not committed — caller owns the commit).
    """
    active_alerts = (
        db.query(Alert)
        .filter(
            Alert.symbol == symbol,
            Alert.exchange == exchange,
            Alert.active == True,  # noqa: E712
        )
        .all()
    )

    fired: list[AlertLog] = []

    for alert in active_alerts:
        triggered = _is_triggered(alert, current_price, prev_price)
        if not triggered:
            continue

        log = AlertLog(
            alert_id=alert.id,
            price_at_trigger=current_price,
            notified=False,
        )
        db.add(log)

        # Deactivate so it doesn't re-fire on the next tick
        alert.active = False

        # Try to send notification (best-effort — don't fail the whole job)
        try:
            notifier.send_alert_notification(
                symbol=symbol,
                exchange=exchange,
                condition=alert.condition_type,
                threshold=alert.threshold,
                current_price=current_price,
            )
            log.notified = True
        except Exception as exc:
            logger.error(f"Notification failed for alert {alert.id}: {exc}")

        fired.append(log)
        logger.info(
            f"Alert {alert.id} fired: {symbol}/{exchange} "
            f"{alert.condition_type} {alert.threshold} @ ₹{current_price}"
        )

    return fired


# ── Condition evaluation ──────────────────────────────────────────────────────

def _is_triggered(
    alert: Alert,
    current_price: float,
    prev_price: Optional[float],
) -> bool:
    ctype = alert.condition_type
    threshold = alert.threshold

    if ctype == "price_above":
        return current_price >= threshold

    if ctype == "price_below":
        return current_price <= threshold

    if ctype in ("pct_change_up", "pct_change_down") and prev_price and prev_price != 0:
        pct = (current_price - prev_price) / prev_price * 100
        if ctype == "pct_change_up":
            return pct >= threshold
        if ctype == "pct_change_down":
            return pct <= -abs(threshold)

    return False
