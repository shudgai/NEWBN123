import ccxt
import pandas as pd


class DataHandler:
    def __init__(self, exchange=None):
        self.exchange = exchange or ccxt.binance({
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })

    def fetch_ohlcv(self, symbol, timeframe="1h", limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except ccxt.BaseError as exc:
            print(f"無法取得 {symbol} K 線: {exc}")
            return None

    def fetch_ticker(self, symbol):
        try:
            return self.exchange.fetch_ticker(symbol)
        except ccxt.BaseError as exc:
            print(f"無法取得 {symbol} 報價: {exc}")
            return None
