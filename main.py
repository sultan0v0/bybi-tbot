"""Application entry point."""
from __future__ import annotations

import asyncio
import json
import logging
import time

from analytics import AnalyticsEngine
from bybit_client import BybitPublicClient
from config import settings
from notifier import TelegramNotifier


async def run() -> None:
    client = BybitPublicClient(settings.symbol, settings.category, settings.interval, settings.buffer_size,
                               settings.poll_interval)
    engine = AnalyticsEngine(settings.velocity_window, settings.atr_window, settings.min_velocity)
    notifier = TelegramNotifier(settings.telegram_token, settings.telegram_chat_id, settings.alert_cooldown_seconds)
    await client.bootstrap()
    logging.info("Monitoring %s. Telegram notifications: %s", settings.symbol, "on" if notifier.enabled else "off")
    last_status_at = 0.0
    try:
        async for event in client.events():
            if event != "candle":
                trade = json.loads(event)["trade"]
                engine.add_trade(float(trade["p"]), float(trade["v"]), trade["S"], int(trade["T"]))
                continue
            signal = engine.evaluate(tuple(client.candles))
            if not signal:
                continue
            now = time.monotonic()
            if now - last_status_at >= 30:
                logging.info("%s %.2f | %s score %.0f%% | v=%+.4f | a=%+.4f | VWAP %.2f",
                             settings.symbol, signal.price, signal.direction, signal.score,
                             signal.velocity, signal.acceleration, signal.vwap)
                last_status_at = now
            if signal.score < settings.score_threshold:
                continue
            if await notifier.send(signal):
                logging.warning("%s alert sent: %.0f%%", signal.direction, signal.score)
            else:
                logging.info("%s signal met threshold but was suppressed by the direction cooldown", signal.direction)
    finally:
        await notifier.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
