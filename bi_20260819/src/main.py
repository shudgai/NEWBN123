import json
import os
import sys
import threading

import ccxt
import pandas as pd

from src.config import (
    DRY_RUN,
    LOOP_INTERVAL_SECONDS,
    MAX_CANDLE_RANGE_ATR,
    MAX_CLOSE_MOVE_ATR,
    MAX_POSITION_VALUE_USDT,
    PAPER_FEE_RATE,
    SIGNAL_TIMEFRAME,
    STATUS_FILE,
    TARGET_PERCENTAGE,
    TRADING_SYMBOL,
)
from src.data_handler import DataHandler
from src.executor import Executor


def save_status(data):
    temporary_file = STATUS_FILE.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, allow_nan=False)
    os.replace(temporary_file, STATUS_FILE)


def load_last_processed_candle():
    if not STATUS_FILE.exists():
        return None
    try:
        with STATUS_FILE.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle).get("last_processed_candle")
    except (OSError, json.JSONDecodeError):
        return None


class TradingBot:
    def __init__(self):
        self.data_handler = DataHandler()
        self.executor = Executor()
        self.lock = threading.RLock()
        self.last_processed_candle = load_last_processed_candle()
        self.current_status = {
            "balance": self.executor.get_balance(),
            "max_position_value": MAX_POSITION_VALUE_USDT,
            "fee_rate": PAPER_FEE_RATE,
            "total_realized_pnl": self.executor.get_total_realized_pnl(),
            "symbol": TRADING_SYMBOL,
            "current_price": None,
            "signal_timeframe": SIGNAL_TIMEFRAME,
            "positions": self.executor.position_summaries(TRADING_SYMBOL),
            "indicators": {
                "ma7": None,
                "ma25": None,
                "ma99": None,
                "close": None,
                "atr14": None,
                "range_atr_ratio": None,
                "close_move_atr_ratio": None,
            },
            "signal": "waiting",
            "spike_protection": False,
            "last_processed_candle": self.last_processed_candle,
            "mode": "paper" if DRY_RUN else "live",
            "running": False,
            "error": None,
        }

    def refresh_status(self):
        with self.lock:
            self.current_status["balance"] = self.executor.get_balance()
            self.current_status["positions"] = self.executor.position_summaries(
                TRADING_SYMBOL
            )
            self.current_status["total_realized_pnl"] = (
                self.executor.get_total_realized_pnl()
            )
            save_status(self.current_status)
            return dict(self.current_status)

    def set_error(self, message):
        with self.lock:
            self.current_status["error"] = str(message)
            self.current_status["running"] = False
            save_status(self.current_status)

    def run(self, stop_event=None):
        stop_event = stop_event or threading.Event()
        print("BTC MA7/MA25/MA99 紙交易機器人啟動中...")
        with self.lock:
            self.current_status["running"] = True
            self.current_status["error"] = None
            save_status(self.current_status)

        try:
            while not stop_event.is_set():
                self.process_symbol()
                stop_event.wait(LOOP_INTERVAL_SECONDS)
        finally:
            with self.lock:
                self.current_status["running"] = False
                save_status(self.current_status)
            print("BTC 均線紙交易機器人已停止。")

    @staticmethod
    def position_quantity(position):
        if not position:
            return 0.0
        return float(position.get("contracts") or position.get("amount") or 0)

    @staticmethod
    def calculate_hybrid_signal(df):
        if df is None or len(df) < 101:
            return None

        closed = df.iloc[:-1].copy()
        if len(closed) < 100:
            return None

        closed["ma7"] = closed["close"].rolling(7).mean()
        closed["ma25"] = closed["close"].rolling(25).mean()
        closed["ma99"] = closed["close"].rolling(99).mean()
        previous_close = closed["close"].shift(1)
        true_range = pd.concat(
            [
                closed["high"] - closed["low"],
                (closed["high"] - previous_close).abs(),
                (closed["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        # Shift keeps the evaluated candle out of its own ATR baseline.
        closed["atr14"] = true_range.shift(1).rolling(14).mean()
        latest = closed.iloc[-1]
        previous = closed.iloc[-2]
        before_previous = closed.iloc[-3]

        ma7_turns_up = (
            float(before_previous["ma7"]) > float(previous["ma7"])
            and float(latest["ma7"]) > float(previous["ma7"])
        )
        ma7_turns_down = (
            float(before_previous["ma7"]) < float(previous["ma7"])
            and float(latest["ma7"]) < float(previous["ma7"])
        )
        ma7_rising_two = (
            float(before_previous["ma7"]) < float(previous["ma7"])
            < float(latest["ma7"])
        )
        ma7_falling_two = (
            float(before_previous["ma7"]) > float(previous["ma7"])
            > float(latest["ma7"])
        )
        ma25_rising = float(latest["ma25"]) > float(previous["ma25"])
        ma99_rising = float(latest["ma99"]) > float(previous["ma99"])
        ma25_falling = float(latest["ma25"]) < float(previous["ma25"])
        ma99_falling = float(latest["ma99"]) < float(previous["ma99"])
        atr14 = float(latest["atr14"])
        candle_range = float(latest["high"]) - float(latest["low"])
        close_move = abs(float(latest["close"]) - float(previous["close"]))
        range_atr_ratio = candle_range / atr14 if atr14 > 0 else float("inf")
        close_move_atr_ratio = close_move / atr14 if atr14 > 0 else float("inf")
        spike_detected = (
            range_atr_ratio > MAX_CANDLE_RANGE_ATR
            or close_move_atr_ratio > MAX_CLOSE_MOVE_ATR
        )
        signal = "hold"
        if (
            not spike_detected
            and ma7_turns_up
            and ma25_rising
            and ma99_rising
        ):
            signal = "long"
        elif (
            not spike_detected
            and ma7_turns_down
            and ma25_falling
            and ma99_falling
        ):
            signal = "short"

        timestamp = latest["timestamp"]
        candle_time = (
            timestamp.isoformat()
            if hasattr(timestamp, "isoformat")
            else str(timestamp)
        )
        return {
            "signal": signal,
            "spike_detected": spike_detected,
            "ma7_turns_up": ma7_turns_up,
            "ma7_turns_down": ma7_turns_down,
            "ma7_rising_two": ma7_rising_two,
            "ma7_falling_two": ma7_falling_two,
            "ma25_rising": ma25_rising,
            "ma99_rising": ma99_rising,
            "ma25_falling": ma25_falling,
            "ma99_falling": ma99_falling,
            "candle_time": candle_time,
            "indicators": {
                "ma7": float(latest["ma7"]),
                "ma25": float(latest["ma25"]),
                "ma99": float(latest["ma99"]),
                "close": float(latest["close"]),
                "atr14": atr14,
                "range_atr_ratio": range_atr_ratio,
                "close_move_atr_ratio": close_move_atr_ratio,
            },
        }

    def process_symbol(self):
        df = self.data_handler.fetch_ohlcv(
            TRADING_SYMBOL,
            timeframe=SIGNAL_TIMEFRAME,
            limit=150,
        )
        result = self.calculate_hybrid_signal(df)
        if result is None:
            return

        with self.lock:
            self.current_status["indicators"] = result["indicators"]
            self.current_status["signal"] = result["signal"]
            self.current_status["spike_protection"] = result["spike_detected"]
            self.current_status["current_price"] = self.executor.get_mark_price(
                TRADING_SYMBOL
            )
            if result["candle_time"] == self.last_processed_candle:
                self.refresh_status()
                return

            positions = self.executor.get_positions(TRADING_SYMBOL)
            long_quantity = self.position_quantity(positions["long"])
            short_quantity = self.position_quantity(positions["short"])
            candle_time = result["candle_time"]
            signal = result["signal"]
            if result["spike_detected"]:
                print(
                    "偵測到異常 K 線，暫停新開倉："
                    f"range/ATR={result['indicators']['range_atr_ratio']:.2f}, "
                    f"close-move/ATR={result['indicators']['close_move_atr_ratio']:.2f}"
                )

            close_long = long_quantity > 0 and result["ma7_falling_two"]
            close_short = short_quantity > 0 and result["ma7_rising_two"]
            if close_long:
                print("MA7 已連續兩根向下，平多單。")
                self.executor.close_position(TRADING_SYMBOL, "long")
                long_quantity = 0.0
            if close_short:
                print("MA7 已連續兩根向上，平空單。")
                self.executor.close_position(TRADING_SYMBOL, "short")
                short_quantity = 0.0

            if signal == "long" and long_quantity == 0:
                amount = self.executor.calculate_amount(
                    TRADING_SYMBOL,
                    target_percentage=TARGET_PERCENTAGE,
                    reference_price=result["indicators"]["close"],
                )
                self.executor.place_order(
                    TRADING_SYMBOL,
                    "buy",
                    amount,
                    position_side="long",
                    reference_price=result["indicators"]["close"],
                )
            elif signal == "short" and short_quantity == 0:
                amount = self.executor.calculate_amount(
                    TRADING_SYMBOL,
                    target_percentage=TARGET_PERCENTAGE,
                    reference_price=result["indicators"]["close"],
                )
                self.executor.place_order(
                    TRADING_SYMBOL,
                    "sell",
                    amount,
                    position_side="short",
                    reference_price=result["indicators"]["close"],
                )

            self.last_processed_candle = candle_time
            self.current_status["last_processed_candle"] = candle_time
            self.refresh_status()

    def manual_close(self, position_side):
        if position_side not in {"long", "short"}:
            raise ValueError("position_side must be long or short")
        with self.lock:
            position = self.executor.get_positions(TRADING_SYMBOL).get(
                position_side
            )
            if not position:
                self.refresh_status()
                return False
            trade = self.executor.close_position(
                TRADING_SYMBOL,
                position_side,
            )
            self.refresh_status()
            return trade is not None


if __name__ == "__main__":
    bot = None
    try:
        bot = TradingBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n收到停止指令。")
    except (RuntimeError, ccxt.BaseError) as exc:
        print(f"啟動失敗: {exc}", file=sys.stderr)
        if bot:
            bot.set_error(exc)
        raise SystemExit(1)
