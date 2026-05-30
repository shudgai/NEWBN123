import ccxt
import numpy as np
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('SOL/USDT', '1m', limit=20)
closes = [x[4] for x in ohlcv]
sma = np.mean(closes)
current = closes[-1]
deviation = (current - sma) / sma
print(f"Current: {current}, SMA: {sma}, Deviation: {deviation*100:.4f}%")
