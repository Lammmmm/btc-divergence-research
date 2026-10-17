BTCUSDT perpetual divergence research backtest
==============================================
Analysis date: 2026-10-16 Asia/Shanghai.
Read BTCUSDT_Divergence_Backtest.html for assumptions, limitations and tables.
Data frozen at 2026-10-16 00:00 UTC (exclusive); 2020 is warmup only.

Reproduce from this directory (Python 3, numpy, pandas, requests):
  python backtest_divergence.py
  python verify_backtest.py
Raw JSON is included. fetch_market.py optionally downloads only missing caches.
No authentication, account access, keys, orders or trading APIs are used.

results.json contains summaries for 5/10/20-bar holding periods, timeframes,
individual indicators, current4/all10 combinations, directions and time splits.
trades.json contains every completed event for these scenarios; do not pool
different scenarios as independent trades or sum into a portfolio equity curve.
signals_*.npz contains computed indicators, signals and divergence lengths.
checks.json documents data consistency checks and remaining discrepancies.

Current4 = MACD, RSI, OBV, MFI.
Explore_* candidates were chosen after looking at single-indicator results:
these are post-hoc exploration, not independently held-out discoveries.
Pine source detection logic copyright LonesomeTheBlue; see original Pine header
for MPL 2.0 notice. Python port reproduces that detection logic for research.
No comparison against TradingView's compiler or per-bar export was performed.
