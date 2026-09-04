"""
Notification service for alerts via Telegram and Email
"""
from typing import Optional
from loguru import logger
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

# Try to import telegram bot
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not available")


class NotifierService:
    """Service for sending notifications via Telegram and Email"""
    
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.email_sender = os.getenv("EMAIL_SENDER")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.email_recipient = os.getenv("EMAIL_RECIPIENT")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        self.telegram_bot = None
        if TELEGRAM_AVAILABLE and self.telegram_token:
            try:
                self.telegram_bot = Bot(token=self.telegram_token)
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def send_telegram_notification(self, message: str) -> bool:
        """
        Send notification via Telegram
        
        Args:
            message: Message to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.telegram_bot or not self.telegram_chat_id:
                logger.warning("Telegram bot or chat ID not configured")
                return False
            
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message
            )
            logger.info(f"Telegram notification sent: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def send_email_notification(self, subject: str, body: str) -> bool:
        """
        Send notification via Email
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.email_sender or not self.email_password or not self.email_recipient:
                logger.warning("Email credentials not configured")
                return False
            
            msg = MIMEMultipart()
            msg["From"] = self.email_sender
            msg["To"] = self.email_recipient
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def format_alert_message(self, symbol: str, condition: str, price: float, threshold: float) -> str:
        """
        Format alert message for notifications
        
        Args:
            symbol: Stock symbol
            condition: Alert condition (price_above, price_below, etc)
            price: Current price
            threshold: Alert threshold
            
        Returns:
            Formatted message
        """
        condition_map = {
            "price_above": f"crossed above ₹{threshold:.2f}",
            "price_below": f"crossed below ₹{threshold:.2f}",
            "pct_change": f"changed by {threshold:.2f}%"
        }
        
        condition_text = condition_map.get(condition, f"met condition {condition}")
        
        return f"🔔 ALERT: {symbol}\n{condition_text}\nCurrent Price: ₹{price:.2f}"
    
    def format_analysis_message(self, symbol: str, analysis: dict) -> str:
        """
        Format AI analysis message for notifications
        
        Args:
            symbol: Stock symbol
            analysis: Analysis dict from AI agent
            
        Returns:
            Formatted message
        """
        risk_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }
        
        risk_flag = analysis.get("risk_flag", "unknown")
        emoji = risk_emoji.get(risk_flag, "⚪")
        
        return f"""📊 AI ANALYSIS: {symbol}
{emoji} Risk Flag: {risk_flag.upper()}

📈 Trend: {analysis.get('trend_summary', 'N/A')}

🔍 Reasoning: {analysis.get('reasoning', 'N/A')}

⚠️ Caveats: {analysis.get('caveats', 'N/A')}

---
⚠️ Educational purposes only. Not financial advice."""
