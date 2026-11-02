"""Low-latency, NumPy-based momentum calculations."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import numpy as np


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class Signal:
    direction: str
    score: float
    price: float
    velocity: float
    acceleration: float
    vwap: float
    delta_volume: float
    delta_acceleration: float
    atr: float
    take_profit: float
    stop_loss: float


class AnalyticsEngine:
    def __init__(self, velocity_window: int = 5, atr_window: int = 14,
                 min_velocity: float = 0.15) -> None:
        self.velocity_window = velocity_window
        self.atr_window = atr_window
        self.min_velocity = min_velocity
        self._trades: list[tuple[float, float, int]] = []  # price, signed size, time

    def add_trade(self, price: float, size: float, side: str, timestamp: int) -> None:
        signed_size = size if side.lower() == "buy" else -size
        self._trades.append((price, signed_size, timestamp))
        if len(self._trades) > 10_000:
            del self._trades[:5_000]

    def evaluate(self, candles: Sequence[Candle]) -> Signal | None:
        minimum = max(self.velocity_window + 2, self.atr_window + 1)
        if len(candles) < minimum:
            return None

        recent = candles[-max(60, self.atr_window + 1):]
        high = np.fromiter((c.high for c in recent), dtype=float)
        low = np.fromiter((c.low for c in recent), dtype=float)
        close = np.fromiter((c.close for c in recent), dtype=float)
        volume = np.fromiter((c.volume for c in recent), dtype=float)
        typical = (high + low + close) / 3.0
        vwap = float(np.dot(typical, volume) / volume.sum()) if volume.sum() else float(close[-1])
        velocity = float((close[-1] - close[-1 - self.velocity_window]) / self.velocity_window)
        prior_velocity = float((close[-2] - close[-2 - self.velocity_window]) / self.velocity_window)
        acceleration = velocity - prior_velocity
        true_ranges = np.maximum(high[1:] - low[1:], np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
        atr = float(np.mean(true_ranges[-self.atr_window:]))

        # Use actual public-trade aggressor sides when available. Candle body/volume is a safe fallback.
        cutoff = recent[0].timestamp
        deltas = np.fromiter((size for _, size, stamp in self._trades if stamp >= cutoff), dtype=float)
        if deltas.size:
            delta_volume = float(deltas.sum())
            split = max(1, deltas.size // 2)
            delta_acceleration = float(deltas[-split:].sum() - deltas[:-split].sum())
        else:
            signed = np.where(close >= np.r_[close[0], close[:-1]], volume, -volume)
            delta_volume = float(signed.sum())
            delta_acceleration = float(signed[-3:].sum() - signed[-6:-3].sum())

        direction = "LONG" if velocity >= 0 else "SHORT"
        directional_acceleration = acceleration if direction == "LONG" else -acceleration
        favorable_price = close[-1] > vwap if direction == "LONG" else close[-1] < vwap
        favorable_delta = delta_volume > 0 if direction == "LONG" else delta_volume < 0
        favorable_delta_accel = delta_acceleration > 0 if direction == "LONG" else delta_acceleration < 0
        checks = (
            abs(velocity) >= self.min_velocity, directional_acceleration > 0,
            favorable_price, favorable_delta, favorable_delta_accel,
        )
        score = 100.0 * sum(checks) / len(checks)
        risk = max(atr, abs(velocity) * 2, 0.01)
        price = float(close[-1])
        take_profit = price + 2 * risk if direction == "LONG" else price - 2 * risk
        stop_loss = price - risk if direction == "LONG" else price + risk
        return Signal(direction, score, price, velocity, acceleration, vwap, delta_volume,
                      delta_acceleration, atr, take_profit, stop_loss)
