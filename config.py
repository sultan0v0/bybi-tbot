"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True, slots=True)
class Settings:
    symbol: str = os.getenv("SYMBOL", "PAXGUSDT")
    category: str = os.getenv("BYBIT_CATEGORY", "spot")
    interval: str = os.getenv("CANDLE_INTERVAL", "1")
    buffer_size: int = _int("BUFFER_SIZE", 200)
    velocity_window: int = _int("VELOCITY_WINDOW", 5)
    atr_window: int = _int("ATR_WINDOW", 14)
    min_velocity: float = _float("MIN_VELOCITY", 0.15)
    score_threshold: float = _float("SCORE_THRESHOLD", 65.0)
    alert_cooldown_seconds: int = _int("ALERT_COOLDOWN_SECONDS", 900)
    poll_interval: float = _float("POLL_INTERVAL", 5.0)
    telegram_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")


settings = Settings()
