"""
Application configuration via pydantic-settings.
All values can be overridden through environment variables or a .env file.
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Project paths ────────────────────────────────────────────────────────
    base_dir: Path = Path(__file__).resolve().parents[3]  # repo root
    data_dir: Path = base_dir / "data"
    logs_dir: Path = base_dir / "logs"
    db_path: Path = base_dir / "data" / "portfolio.db"

    # ── Market data ──────────────────────────────────────────────────────────
    # How often (minutes) to poll prices during market hours
    price_poll_interval_minutes: int = 5
    market_open: str = "09:15"   # IST
    market_close: str = "15:30"  # IST

    # ── Notification channels ────────────────────────────────────────────────
    # Comma-separated list of channels to use.
    # Supported values: ntfy, telegram, email, whatsapp
    # Example: NOTIFY_CHANNELS=ntfy,email
    notify_channels: list[str] = ["ntfy"]

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email (SMTP — works with Gmail, Outlook, any SMTP server)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_to: str = ""

    # WhatsApp via Twilio (free sandbox available)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""   # e.g. whatsapp:+14155238886
    twilio_whatsapp_to: str = ""     # e.g. whatsapp:+919876543210

    # ntfy.sh — PRIMARY channel (zero-signup, free, open-source)
    # 1. Install the ntfy app on Android/iOS
    # 2. Subscribe to a unique topic (make it unguessable — it's your password)
    # 3. Set NTFY_TOPIC below and you're done
    ntfy_topic: str = ""             # e.g. "my-stock-alerts-xyz123"
    ntfy_server: str = "https://ntfy.sh"
    ntfy_priority: str = "high"      # min | low | default | high | urgent

    # ── AI / LLM ─────────────────────────────────────────────────────────────
    claude_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"
    # How many days after an analysis to check actual outcome
    agent_feedback_days: int = 7

    # ── CORS (for local React dev server) ────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    def ensure_dirs(self) -> None:
        """Create required directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    s = Settings()
    s.ensure_dirs()
    return s
