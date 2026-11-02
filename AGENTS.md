```markdown
# High-Frequency Momentum & Volume Alert Bot (Bybit PAXG/USDT System)

## 1. Project Overview
A lightweight, high-performance async Python service that connects to Bybit (REST & WebSocket) to fetch live market data for Pax Gold (`PAXGUSDT`) as a real-time proxy for spot Gold (XAU/USD). 

The bot calculates price dynamics via first/second derivatives (velocity and acceleration) alongside cumulative volume integrals (VWAP and Delta Volume), evaluates a probabilistic signal score, and delivers instant actionable alerts to Telegram when high-probability thresholds ($\ge 80\%$) are breached.

---

## 2. Tech Stack & Dependencies
- **Language:** Python 3.11+
- **Async Framework:** `asyncio`
- **Exchange Integration:** `pybit` (Official Bybit SDK) or `ccxt.pro` / `httpx` + `websockets`
- **Data Processing & Math:** `pandas`, `numpy`
- **Notifications:** `aiogram 3.x` (or direct `httpx` calls to Telegram Bot API)
- **Environment Management:** `python-dotenv`

---

## 3. Mathematical & Analytical Engine

The analytics module treats discrete price ticks/candles $P(t)$ as a continuous function over time $t$.

### A. First Derivative (Price Velocity / Speed)
Measures the velocity of price change over a rolling window $N$:
$$v(t) = \frac{P(t) - P(t - N \cdot \Delta t)}{N \cdot \Delta t}$$

### B. Second Derivative (Price Acceleration / Impulse)
Measures the rate of velocity change to detect explosive breakouts or momentum decay:
$$a(t) = \frac{v(t) - v(t - \Delta t)}{\Delta t}$$

### C. Volume Integrals (VWAP & Delta Volume)
Computes real-time Volume-Weighted Average Price and cumulative buying vs. selling volume delta from Bybit orderbook trades:
$$\text{VWAP} = \frac{\sum_{i=1}^{k} P_i \cdot V_i}{\sum_{i=1}^{k} V_i}$$
$$\text{Delta Volume} = \sum (V_{\text{buy}} - V_{\text{sell}})$$

### D. Probabilistic Scoring Engine ($S \in [0, 100]\%$)
A composite score calculated using weighted criteria:
1. **Velocity Check:** $v(t) > \text{threshold}_v$ (Strong unidirectional movement)
2. **Acceleration Check:** $a(t) > 0$ (Price movement is expanding, not fading)
3. **Institutional Level Check:** $P(t) > \text{VWAP}$ (Price trades above volume-weighted accumulation)
4. **Volume Confirmation:** Net Delta Volume is positive and accelerating

**Trigger Condition:** Dispatch Telegram alert ONLY if $S \ge 80\%$.

---

## 4. Architecture & Directory Structure


```

.
├── .env                # API Keys, Telegram Token, Chat ID
├── config.py           # Configuration parameters and thresholds
├── bybit_client.py     # Bybit REST & WebSocket data fetcher (pybit / ccxt)
├── analytics.py        # Derivative computations, VWAP, math & score engine
├── notifier.py         # Async Telegram alert manager with anti-spam cooldown
└── main.py             # Event loop & application entry point

```

---

## 5. Detailed Component Requirements for Code Generation

### `bybit_client.py`
- Connect to Bybit Public V5 API (No private API keys required for read-only market data).
- Primary symbol: `PAXGUSDT` (Spot or Linear Perpetual).
- Maintain a rolling local buffer (e.g., last 200 candles of 1-minute interval or tick stream) in memory using `collections.deque` or `pandas.DataFrame`.

### `analytics.py`
- Vectorized math execution using `numpy` for minimal latency.
- Dynamically recalculate $v(t)$, $a(t)$, VWAP, and Delta Volume upon each new candle/tick received.
- Calculate ATR (Average True Range) to determine volatility-based Stop Loss (SL) and Take Profit (TP) bounds.

### `notifier.py`
- Anti-spam cooldown: Restrict duplicate alerts for the same direction (e.g., maximum 1 alert per 15 minutes).
- Payload format:
  ```text
  🚨 GOLD (PAXG/USDT) MOMENTUM ALERT

  • Direction: LONG (Score: 85%)
  • Current Price: $2,745.20
  • Velocity (v): +1.42 $/min
  • Acceleration (a): +0.35 $/min²
  • VWAP: $2,741.80 (Bullish Zone)

  🎯 Target (TP): $2,758.00
  🛡 Stop Loss (SL): $2,739.00
  ⏰ Time (UTC): 2026-11-02 14:00:00

```

---

## 6. Setup & Execution Guide

1. Install required packages:
```bash
pip install pybit pandas numpy aiogram python-dotenv

```


2. Create a `.env` file:
```env
TELEGRAM_BOT_TOKEN="your_bot_token_here"
TELEGRAM_CHAT_ID="your_chat_id_here"
SYMBOL="PAXGUSDT"
POLL_INTERVAL=5

```


3. Run the application:
```bash
python main.py

```



```

```