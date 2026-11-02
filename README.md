# PAXG/USDT Momentum Alert Bot

Public Bybit V5 market-data monitor for PAXG/USDT. It computes velocity, acceleration, VWAP, signed trade-volume delta and ATR-based targets, then sends Telegram alerts through aiogram at the configured score threshold.

## Run

1. Create and fill `.env` from `.env.example`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run: `python main.py`.

No Bybit API key is needed. Without Telegram variables, the service runs but deliberately sends no messages.
