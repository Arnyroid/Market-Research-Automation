"""
Notification delivery — multi-channel, all independent.

Supported channels (configure via NOTIFY_CHANNELS in .env):
  telegram   — Telegram Bot API (recommended for mobile push)
  email      — SMTP (Gmail, Outlook, or any server)
  whatsapp   — WhatsApp via Twilio API (free sandbox for testing)
  ntfy       — ntfy.sh, zero-signup push to phone via free open-source app

Any combination can be active at once; each fires independently.
A failure in one channel does not prevent the others from running.

Public API
----------
  send_alert_notification(symbol, exchange, condition, threshold, current_price)
  send_message(text, title="Stock Alert")   ← generic, plain text
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import httpx
from loguru import logger

from backend.app.core.config import get_settings

settings = get_settings()


# ── Public API ────────────────────────────────────────────────────────────────

def send_alert_notification(
    symbol: str,
    exchange: str,
    condition: str,
    threshold: float,
    current_price: float,
) -> None:
    """Format a stock alert and dispatch it to all configured channels."""
    condition_labels = {
        "price_above":     f"crossed above ₹{threshold:,.2f}",
        "price_below":     f"dropped below ₹{threshold:,.2f}",
        "pct_change_up":   f"surged +{threshold:.1f}%",
        "pct_change_down": f"fell -{threshold:.1f}%",
    }
    desc = condition_labels.get(condition, f"{condition} {threshold}")
    title = f"Alert: {symbol} ({exchange})"
    body  = (
        f"{symbol} ({exchange}) has {desc}\n"
        f"Current price: ₹{current_price:,.2f}\n\n"
        f"This is automated — not financial advice."
    )
    send_message(body, title=title)


def send_message(text: str, title: str = "Stock Alert") -> None:
    """
    Dispatch a message to every channel listed in settings.notify_channels.
    Channels are tried in parallel (sequentially here for simplicity, but
    each failure is isolated).
    """
    channels = [c.strip().lower() for c in settings.notify_channels_list if c.strip()]

    if not channels:
        logger.warning("notify_channels is empty — no notification will be sent")
        return

    dispatched = 0
    for channel in channels:
        try:
            if channel == "telegram":
                _send_telegram(text)
                dispatched += 1
            elif channel == "email":
                _send_email(title, text)
                dispatched += 1
            elif channel == "whatsapp":
                _send_whatsapp(text)
                dispatched += 1
            elif channel == "ntfy":
                _send_ntfy(title, text)
                dispatched += 1
            else:
                logger.warning(f"Unknown notification channel '{channel}' — skipping")
        except Exception as exc:
            logger.error(f"Channel '{channel}' failed: {exc}")

    if dispatched == 0:
        logger.warning("All notification channels failed or were misconfigured")


# ── Telegram ──────────────────────────────────────────────────────────────────

def _send_telegram(text: str) -> None:
    """
    Requires: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    Setup:  1. Message @BotFather → /newbot → copy token
            2. Message your bot once, then visit
               https://api.telegram.org/bot<TOKEN>/getUpdates to get chat_id
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return

    # Telegram Markdown v1 — wrap in code-safe asterisks
    md_text = text.replace("_", r"\_")  # escape underscores outside bold
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": md_text,
        "parse_mode": "Markdown",
    }
    resp = httpx.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    logger.info("Telegram notification sent")


# ── Email (SMTP) ──────────────────────────────────────────────────────────────

def _send_email(subject: str, body: str) -> None:
    """
    Requires: SMTP_USER, SMTP_PASSWORD, SMTP_TO
    Works with Gmail (enable App Passwords), Outlook, or any SMTP server.
    SMTP_HOST defaults to smtp.gmail.com, SMTP_PORT to 587 (STARTTLS).
    """
    if not settings.smtp_user or not settings.smtp_to:
        logger.warning("Email: SMTP_USER or SMTP_TO not set")
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = settings.smtp_user
    msg["To"]      = settings.smtp_to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, [settings.smtp_to], msg.as_string())
    logger.info("Email notification sent")


# ── WhatsApp via Twilio ───────────────────────────────────────────────────────

def _send_whatsapp(text: str) -> None:
    """
    Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
              TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO
    Free tier: use Twilio sandbox (whatsapp:+14155238886).
    Setup:  1. Sign up at https://twilio.com (no credit card for sandbox)
            2. Follow sandbox join instructions in the Twilio console
            3. Set FROM = whatsapp:+14155238886
               Set TO   = whatsapp:+91XXXXXXXXXX  (your number)
    Production: buy a Twilio number with WhatsApp capability.
    """
    if not all([
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.twilio_whatsapp_from,
        settings.twilio_whatsapp_to,
    ]):
        logger.warning("WhatsApp: one or more TWILIO_* env vars not set")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    resp = httpx.post(
        url,
        data={
            "From": settings.twilio_whatsapp_from,
            "To":   settings.twilio_whatsapp_to,
            "Body": text,
        },
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=15,
    )
    resp.raise_for_status()
    logger.info("WhatsApp notification sent")


# ── ntfy.sh (zero-signup push) ────────────────────────────────────────────────

def _send_ntfy(title: str, text: str) -> None:
    """
    Requires: NTFY_TOPIC  (e.g. "my-stock-alerts-abc123" — make it unguessable)
    No account, no login needed for the free public ntfy.sh server.

    Setup:
      1. Install the free ntfy app → https://ntfy.sh  (Android / iOS)
      2. Tap Subscribe → enter your topic name
      3. Set NTFY_TOPIC=<that-same-topic> in .env
      4. Optionally set NTFY_PRIORITY=urgent for banner alerts

    Self-host: set NTFY_SERVER=https://your-ntfy-instance.com
    Access control: ntfy supports token auth — add NTFY_TOKEN if your
    server requires it (public ntfy.sh topics don't need one).
    """
    if not settings.ntfy_topic:
        logger.warning("ntfy: NTFY_TOPIC not set — skipping")
        return

    url = f"{settings.ntfy_server.rstrip('/')}/{settings.ntfy_topic}"

    headers: dict[str, str] = {
        "Title":    title,
        "Priority": settings.ntfy_priority,
        "Tags":     "chart_with_upwards_trend,bell",
        "Content-Type": "text/plain; charset=utf-8",
    }

    # Optional bearer-token auth (for self-hosted or protected ntfy topics)
    if getattr(settings, "ntfy_token", ""):
        headers["Authorization"] = f"Bearer {settings.ntfy_token}"

    resp = httpx.post(url, content=text.encode("utf-8"), headers=headers, timeout=10)
    resp.raise_for_status()
    logger.info(f"ntfy notification sent → {url}")
