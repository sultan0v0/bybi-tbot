"""Public Bybit V5 REST bootstrap and WebSocket market-data client."""
from __future__ import annotations

import asyncio
from collections import deque
import json
import logging
from collections.abc import AsyncIterator

import httpx
import websockets

from analytics import Candle

LOG = logging.getLogger(__name__)
REST_URL = "https://api.bybit.com/v5/market/kline"
WS_URLS = {
    "spot": "wss://stream.bybit.com/v5/public/spot",
    "linear": "wss://stream.bybit.com/v5/public/linear",
}


class BybitPublicClient:
    def __init__(self, symbol: str, category: str = "spot", interval: str = "1", buffer_size: int = 200,
                 poll_interval: float = 5.0) -> None:
        if category not in WS_URLS:
            raise ValueError("BYBIT_CATEGORY must be 'spot' or 'linear'")
        self.symbol, self.category, self.interval = symbol, category, interval
        self.poll_interval = poll_interval
        self.candles: deque[Candle] = deque(maxlen=buffer_size)

    async def bootstrap(self) -> None:
        params = {"category": self.category, "symbol": self.symbol, "interval": self.interval, "limit": self.candles.maxlen}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(REST_URL, params=params)
            response.raise_for_status()
        rows = response.json()["result"]["list"]
        for row in sorted(rows, key=lambda value: int(value[0])):
            self._upsert_candle(self._candle(row))
        LOG.info("Loaded %d %s-minute candles for %s", len(self.candles), self.interval, self.symbol)

    async def refresh_latest(self) -> None:
        """REST heartbeat/fallback when the WebSocket has no market events."""
        params = {"category": self.category, "symbol": self.symbol, "interval": self.interval, "limit": 2}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(REST_URL, params=params)
            response.raise_for_status()
        for row in sorted(response.json()["result"]["list"], key=lambda value: int(value[0])):
            self._upsert_candle(self._candle(row))

    async def events(self) -> AsyncIterator[str]:
        topics = [f"kline.{self.interval}.{self.symbol}", f"publicTrade.{self.symbol}"]
        retry = 1
        while True:
            try:
                async with websockets.connect(WS_URLS[self.category], ping_interval=20, ping_timeout=20) as socket:
                    await socket.send(json.dumps({"op": "subscribe", "args": topics}))
                    LOG.info("WebSocket connected; subscribing to %s", ", ".join(topics))
                    retry = 1
                    while True:
                        try:
                            raw = await asyncio.wait_for(socket.recv(), timeout=self.poll_interval)
                        except TimeoutError:
                            await self.refresh_latest()
                            LOG.info("WebSocket is connected but market is quiet for %.0fs; refreshed latest candle via REST",
                                     self.poll_interval)
                            yield "candle"
                            continue
                        payload = json.loads(raw)
                        topic = payload.get("topic", "")
                        if payload.get("success") is False:
                            raise RuntimeError(f"Bybit subscription rejected: {payload}")
                        if payload.get("success") is True:
                            LOG.info("Bybit subscription confirmed")
                            continue
                        if topic.startswith("kline"):
                            for row in payload.get("data", []):
                                self._upsert_candle(Candle(int(row["start"]), float(row["open"]), float(row["high"]),
                                                           float(row["low"]), float(row["close"]), float(row["volume"])))
                            yield "candle"
                        elif topic.startswith("publicTrade"):
                            for trade in payload.get("data", []):
                                yield json.dumps({"trade": trade})
            except (OSError, RuntimeError, websockets.WebSocketException, httpx.HTTPError) as exc:
                LOG.warning("Bybit connection failed (%s); retrying in %ss", exc, retry)
                await asyncio.sleep(retry)
                retry = min(retry * 2, 30)

    def _upsert_candle(self, candle: Candle) -> None:
        if self.candles and self.candles[-1].timestamp == candle.timestamp:
            self.candles[-1] = candle
        else:
            self.candles.append(candle)

    @staticmethod
    def _candle(row: list[str]) -> Candle:
        return Candle(int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]))
