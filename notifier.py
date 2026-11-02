"""Telegram delivery with per-direction anti-spam protection."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time

from aiogram import Bot

from analytics import Signal


class TelegramNotifier:
    def __init__(self, token: str | None, chat_id: str | None, cooldown_seconds: int = 900) -> None:
        self.token, self.chat_id = token, chat_id
        self.cooldown_seconds = cooldown_seconds
        self._last_sent: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._bot = Bot(token=token) if token else None

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send(self, signal: Signal) -> bool:
        if not self.enabled:
            return False
        async with self._lock:
            now = time.monotonic()
            if now - self._last_sent.get(signal.direction, float("-inf")) < self.cooldown_seconds:
                return False
            assert self._bot is not None
            await self._bot.send_message(chat_id=self.chat_id, text=self._format(signal))
            self._last_sent[signal.direction] = now
            return True

    async def close(self) -> None:
        """Release aiogram's HTTP session during graceful application shutdown."""
        if self._bot is not None:
            await self._bot.session.close()

    @staticmethod
    def _format(s: Signal) -> str:
        zone = "выше VWAP — покупатели сильнее" if s.price > s.vwap else "ниже VWAP — продавцы сильнее"
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        action = "Покупка (LONG)" if s.direction == "LONG" else "Продажа (SHORT)"
        momentum = "растёт" if (s.direction == "LONG") == (s.acceleration >= 0) else "замедляется"
        volume = "покупки" if s.delta_volume >= 0 else "продажи"
        return (
            "🚨 СИГНАЛ ПО ЗОЛОТУ — PAXG/USDT\n\n"
            f"Направление: {action}\n"
            f"Сила сигнала: {s.score:.0f}%\n\n"
            "Что делать:\n"
            f"• Вход: около текущей цены ${s.price:,.2f}\n"
            f"• Стоп-лосс: ${s.stop_loss:,.2f}\n"
            f"• Тейк-профит: ${s.take_profit:,.2f}\n\n"
            "Почему появился сигнал:\n"
            f"• Цена ${zone} (VWAP: ${s.vwap:,.2f})\n"
            f"• Скорость движения: {s.velocity:+.4f} $/мин\n"
            f"• Импульс: {momentum} ({s.acceleration:+.4f} $/мин²)\n"
            f"• Объём поддерживает {volume} (delta: {s.delta_volume:+.4f})\n\n"
            f"Время UTC: {stamp}\n"
            "⚠️ Уровни являются расчётным ориентиром: учитывайте риск и размер позиции."
        )
