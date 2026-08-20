import json
import os
import sys
import threading
from datetime import datetime, timedelta, timezone

import ccxt
import pandas as pd

from src.config import (
    DRY_RUN,
    ENTRY_PULLBACK_ATR_RATIO,
    LOOP_INTERVAL_SECONDS,
    MAX_CANDLE_RANGE_ATR,
    MAX_CLOSE_MOVE_ATR,
    MAX_ENTRY_PULLBACK_PCT,
    MAX_POSITION_VALUE_USDT,
    MIN_ENTRY_ATR_PCT,
    MIN_ENTRY_PULLBACK_PCT,
    MIN_ENTRY_MA7_TURN_ATR_RATIO,
    MIN_EXIT_MA7_TURN_ATR_RATIO,
    MIN_PROFIT_SPACE_PCT,
    PAPER_FEE_RATE,
    PENDING_ENTRY_MINUTES,
    PROFIT_LOOKBACK_CANDLES,
    SIGNAL_TIMEFRAME,
    STATUS_FILE,
    STOP_LOSS_PCT,
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


def load_saved_status():
    if not STATUS_FILE.exists():
        return {}
    try:
        with STATUS_FILE.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (OSError, TypeError, json.JSONDecodeError):
        return {}


class TradingBot:
    def __init__(self):
        self.data_handler = DataHandler()
        self.executor = Executor()
        self.lock = threading.RLock()
        saved_status = load_saved_status()
        self.last_processed_candle = saved_status.get("last_processed_candle")
        stored_extremes = saved_status.get("ma7_exit_extremes") or {}
        self.ma7_exit_extremes = {
            "long": stored_extremes.get("long"),
            "short": stored_extremes.get("short"),
        }
        stored_pending = saved_status.get("pending_entry")
        self.pending_entry = (
            stored_pending if isinstance(stored_pending, dict) else None
        )
        self.current_status = {
            "balance": self.executor.get_balance(),
            "max_position_value": MAX_POSITION_VALUE_USDT,
            "fee_rate": PAPER_FEE_RATE,
            "total_realized_pnl": self.executor.get_total_realized_pnl(),
            "symbol": TRADING_SYMBOL,
            "current_price": None,
            "signal_timeframe": SIGNAL_TIMEFRAME,
            "entry_ma7_turn_atr_ratio": MIN_ENTRY_MA7_TURN_ATR_RATIO,
            "exit_ma7_turn_atr_ratio": MIN_EXIT_MA7_TURN_ATR_RATIO,
            "stop_loss_pct": STOP_LOSS_PCT,
            "entry_pullback_atr_ratio": ENTRY_PULLBACK_ATR_RATIO,
            "entry_pullback_pct_range": [
                MIN_ENTRY_PULLBACK_PCT,
                MAX_ENTRY_PULLBACK_PCT,
            ],
            "pending_entry_minutes": PENDING_ENTRY_MINUTES,
            "profit_lookback_candles": PROFIT_LOOKBACK_CANDLES,
            "min_profit_space_pct": MIN_PROFIT_SPACE_PCT,
            "pending_entry": self.pending_entry,
            "ma7_exit_extremes": dict(self.ma7_exit_extremes),
            "ma7_exit_ratios": {"long": 0.0, "short": 0.0},
            "positions": self.executor.position_summaries(TRADING_SYMBOL),
            "indicators": {
                "ma7": None,
                "ma25": None,
                "ma99": None,
                "close": None,
                "atr14": None,
                "atr_pct": None,
                "ma7_turn_atr_ratio": None,
                "range_atr_ratio": None,
                "close_move_atr_ratio": None,
            },
            "signal": "waiting",
            "spike_protection": False,
            "low_volatility_protection": False,
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
            self.current_status["ma7_exit_extremes"] = dict(
                self.ma7_exit_extremes
            )
            self.current_status["pending_entry"] = self.pending_entry
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
    def adverse_move_pct(position_side, entry_price, mark_price):
        if entry_price <= 0 or mark_price <= 0:
            return 0.0
        direction = 1 if position_side == "long" else -1
        return (entry_price - mark_price) / entry_price * 100 * direction

    def enforce_fixed_stop_loss(self, current_price):
        stopped_sides = set()
        positions = self.executor.get_positions(TRADING_SYMBOL)
        for position_side in ("long", "short"):
            position = positions.get(position_side)
            if self.position_quantity(position) <= 0:
                continue
            entry_price = float(position.get("entryPrice") or 0)
            mark_price = float(position.get("markPrice") or current_price or 0)
            adverse_move = self.adverse_move_pct(
                position_side, entry_price, mark_price
            )
            if adverse_move < STOP_LOSS_PCT:
                continue
            print(
                f"固定止損觸發：{position_side.upper()} "
                f"反向 {adverse_move:.3f}%（門檻 {STOP_LOSS_PCT:.3f}%）。"
            )
            trade = self.executor.close_position(
                TRADING_SYMBOL, position_side, exit_reason="stop_loss"
            )
            if trade is not None:
                self.reset_ma7_exit_tracking(position_side)
                stopped_sides.add(position_side)
        return stopped_sides

    @staticmethod
    def cumulative_ma7_reversal_ratio(
        position_side, extreme_ma7, current_ma7, atr14
    ):
        if extreme_ma7 is None or current_ma7 <= 0 or atr14 <= 0:
            return 0.0
        if position_side == "long":
            reversal = float(extreme_ma7) - current_ma7
        else:
            reversal = current_ma7 - float(extreme_ma7)
        return max(reversal / atr14, 0.0)

    def update_ma7_exit_tracking(self, positions, current_ma7, atr14):
        ratios = {"long": 0.0, "short": 0.0}
        for position_side in ("long", "short"):
            position = positions.get(position_side)
            if self.position_quantity(position) <= 0:
                self.ma7_exit_extremes[position_side] = None
                continue

            extreme = self.ma7_exit_extremes.get(position_side)
            if extreme is None:
                extreme = current_ma7
            elif position_side == "long":
                extreme = max(float(extreme), current_ma7)
            else:
                extreme = min(float(extreme), current_ma7)
            self.ma7_exit_extremes[position_side] = extreme
            ratios[position_side] = self.cumulative_ma7_reversal_ratio(
                position_side, extreme, current_ma7, atr14
            )

        self.current_status["ma7_exit_extremes"] = dict(
            self.ma7_exit_extremes
        )
        self.current_status["ma7_exit_ratios"] = ratios
        return ratios

    def reset_ma7_exit_tracking(self, position_side):
        self.ma7_exit_extremes[position_side] = None
        ratios = self.current_status.setdefault(
            "ma7_exit_ratios", {"long": 0.0, "short": 0.0}
        )
        ratios[position_side] = 0.0

    @staticmethod
    def profit_space_pct(position_side, entry_price, target_price):
        if entry_price <= 0 or target_price <= 0:
            return 0.0
        if position_side == "long":
            distance = target_price - entry_price
        else:
            distance = entry_price - target_price
        return max(distance / entry_price * 100, 0.0)

    @staticmethod
    def has_minimum_profit_space(profit_space):
        return profit_space + 1e-9 >= MIN_PROFIT_SPACE_PCT

    @staticmethod
    def entry_pullback_pct(atr_pct):
        return min(
            max(atr_pct * ENTRY_PULLBACK_ATR_RATIO, MIN_ENTRY_PULLBACK_PCT),
            MAX_ENTRY_PULLBACK_PCT,
        )

    def clear_pending_entry(self, reason=None):
        pending = self.pending_entry
        self.pending_entry = None
        self.current_status["pending_entry"] = None
        if pending and reason:
            print(
                f"取消待進場 {str(pending.get('side', '')).upper()}："
                f"{reason}"
            )

    def process_pending_entry(self, current_price, positions=None):
        pending = self.pending_entry
        if not pending:
            return None

        positions = positions or self.executor.get_positions(TRADING_SYMBOL)
        if any(
            self.position_quantity(positions[side]) > 0
            for side in ("long", "short")
        ):
            self.clear_pending_entry("已有持倉")
            return None

        try:
            expires_at = datetime.fromisoformat(
                str(pending["expires_at"]).replace("Z", "+00:00")
            )
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            self.clear_pending_entry("期限格式錯誤")
            return None

        if datetime.now(timezone.utc) >= expires_at:
            self.clear_pending_entry("等待超過期限")
            return None

        position_side = pending.get("side")
        target_price = float(pending.get("target_price") or 0)
        invalidation_price = float(pending.get("invalidation_price") or 0)
        pullback_pct = float(pending.get("pullback_pct") or 0)
        profit_target = float(pending.get("profit_target") or 0)
        if position_side == "long":
            favorable_extreme = max(
                float(pending.get("favorable_extreme") or 0), current_price
            )
            raw_target = favorable_extreme * (1 - pullback_pct / 100)
            profit_space_limit = profit_target / (
                1 + MIN_PROFIT_SPACE_PCT / 100
            )
            target_price = max(
                target_price, min(raw_target, profit_space_limit)
            )
            invalidated = current_price <= invalidation_price
            reached_target = current_price <= target_price
        elif position_side == "short":
            stored_extreme = float(
                pending.get("favorable_extreme") or current_price
            )
            favorable_extreme = min(stored_extreme, current_price)
            raw_target = favorable_extreme * (1 + pullback_pct / 100)
            profit_space_limit = profit_target / (
                1 - MIN_PROFIT_SPACE_PCT / 100
            )
            target_price = min(
                target_price, max(raw_target, profit_space_limit)
            )
            invalidated = current_price >= invalidation_price
            reached_target = current_price >= target_price
        else:
            self.clear_pending_entry("方向格式錯誤")
            return None

        pending["favorable_extreme"] = favorable_extreme
        pending["target_price"] = target_price
        pending["profit_space_pct"] = self.profit_space_pct(
            position_side, target_price, profit_target
        )
        self.current_status["pending_entry"] = pending

        if invalidated:
            self.clear_pending_entry(
                f"價格 {current_price:.2f} 突破訊號失效價 "
                f"{invalidation_price:.2f}"
            )
            return None
        if not reached_target:
            return None

        profit_space = self.profit_space_pct(
            position_side, current_price, profit_target
        )
        if not self.has_minimum_profit_space(profit_space):
            self.clear_pending_entry(
                f"剩餘利潤空間 {profit_space:.3f}% 小於 "
                f"{MIN_PROFIT_SPACE_PCT:.3f}%"
            )
            return None

        reference_price = float(pending.get("signal_close") or 0)
        amount = self.executor.calculate_amount(
            TRADING_SYMBOL,
            target_percentage=TARGET_PERCENTAGE,
            reference_price=reference_price,
        )
        trade = self.executor.place_order(
            TRADING_SYMBOL,
            "buy" if position_side == "long" else "sell",
            amount,
            position_side=position_side,
            reference_price=reference_price,
        )
        if trade is None:
            self.clear_pending_entry("觸價後下單失敗")
            return None

        current_ma7 = self.current_status.get("indicators", {}).get("ma7")
        self.ma7_exit_extremes[position_side] = (
            float(current_ma7) if current_ma7 is not None else None
        )
        print(
            f"待進場成交 {position_side.upper()}：mark={current_price:.2f}, "
            f"target={target_price:.2f}, space={profit_space:.3f}%"
        )
        self.pending_entry = None
        self.current_status["pending_entry"] = None
        return trade

    def queue_entry_signal(self, signal, result, blocked_sides=None):
        blocked_sides = blocked_sides or set()
        if signal not in {"long", "short"} or signal in blocked_sides:
            return None

        positions = self.executor.get_positions(TRADING_SYMBOL)
        if any(
            self.position_quantity(positions[side]) > 0
            for side in ("long", "short")
        ):
            self.clear_pending_entry("已有持倉")
            return None

        if self.pending_entry:
            if self.pending_entry.get("side") == signal:
                return self.pending_entry
            self.clear_pending_entry("出現反方向新訊號")

        signal_close = float(result["indicators"]["close"])
        atr_pct = float(result["indicators"]["atr_pct"])
        pullback_pct = self.entry_pullback_pct(atr_pct)
        if signal == "long":
            target_price = signal_close * (1 - pullback_pct / 100)
            profit_target = float(result["recent_high"])
            invalidation_price = float(result["signal_low"])
        else:
            target_price = signal_close * (1 + pullback_pct / 100)
            profit_target = float(result["recent_low"])
            invalidation_price = float(result["signal_high"])

        profit_space = self.profit_space_pct(
            signal, target_price, profit_target
        )
        if not self.has_minimum_profit_space(profit_space):
            print(
                f"略過 {signal.upper()}：預估利潤空間 "
                f"{profit_space:.3f}% 小於 {MIN_PROFIT_SPACE_PCT:.3f}%"
            )
            return None

        now = datetime.now(timezone.utc)
        self.pending_entry = {
            "side": signal,
            "signal_candle": result["candle_time"],
            "created_at": now.isoformat(),
            "expires_at": (
                now + timedelta(minutes=PENDING_ENTRY_MINUTES)
            ).isoformat(),
            "signal_close": signal_close,
            "signal_low": float(result["signal_low"]),
            "signal_high": float(result["signal_high"]),
            "target_price": target_price,
            "invalidation_price": invalidation_price,
            "profit_target": profit_target,
            "profit_space_pct": profit_space,
            "pullback_pct": pullback_pct,
            "favorable_extreme": signal_close,
        }
        self.current_status["pending_entry"] = self.pending_entry
        print(
            f"建立待進場 {signal.upper()}：target={target_price:.2f}, "
            f"pullback={pullback_pct:.3f}%, space={profit_space:.3f}%, "
            f"valid={PENDING_ENTRY_MINUTES}m"
        )
        return self.pending_entry

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
        profit_window = closed.tail(PROFIT_LOOKBACK_CANDLES)
        recent_high = float(profit_window["high"].max())
        recent_low = float(profit_window["low"].min())
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
        ma25_rising = float(latest["ma25"]) > float(previous["ma25"])
        ma99_rising = float(latest["ma99"]) > float(previous["ma99"])
        ma25_falling = float(latest["ma25"]) < float(previous["ma25"])
        ma99_falling = float(latest["ma99"]) < float(previous["ma99"])
        atr14 = float(latest["atr14"])
        latest_close = float(latest["close"])
        atr_pct = atr14 / latest_close * 100 if latest_close > 0 else 0.0
        ma7_turn_atr_ratio = (
            abs(float(latest["ma7"]) - float(previous["ma7"])) / atr14
            if atr14 > 0
            else 0.0
        )
        low_volatility = (
            atr_pct < MIN_ENTRY_ATR_PCT
            or ma7_turn_atr_ratio < MIN_ENTRY_MA7_TURN_ATR_RATIO
        )
        candle_range = float(latest["high"]) - float(latest["low"])
        close_move = abs(float(latest["close"]) - float(previous["close"]))
        range_atr_ratio = candle_range / atr14 if atr14 > 0 else float("inf")
        close_move_atr_ratio = close_move / atr14 if atr14 > 0 else float("inf")
        spike_detected = (
            range_atr_ratio > MAX_CANDLE_RANGE_ATR
            or close_move_atr_ratio > MAX_CLOSE_MOVE_ATR
        )
        latest_green = latest_close > float(latest["open"])
        latest_red = latest_close < float(latest["open"])
        previous_green = float(previous["close"]) > float(previous["open"])
        previous_red = float(previous["close"]) < float(previous["open"])
        signal = "hold"
        long_timing = ma7_turns_up and latest_green
        short_timing = ma7_turns_down and latest_red
        if (
            not spike_detected
            and not low_volatility
            and long_timing
        ):
            signal = "long"
        elif (
            not spike_detected
            and not low_volatility
            and short_timing
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
            "low_volatility": low_volatility,
            "ma7_turns_up": ma7_turns_up,
            "ma7_turns_down": ma7_turns_down,
            "ma25_rising": ma25_rising,
            "ma99_rising": ma99_rising,
            "ma25_falling": ma25_falling,
            "ma99_falling": ma99_falling,
            "latest_green": latest_green,
            "latest_red": latest_red,
            "previous_green": previous_green,
            "previous_red": previous_red,
            "long_timing": long_timing,
            "short_timing": short_timing,
            "candle_time": candle_time,
            "signal_low": float(latest["low"]),
            "signal_high": float(latest["high"]),
            "recent_high": recent_high,
            "recent_low": recent_low,
            "indicators": {
                "ma7": float(latest["ma7"]),
                "ma25": float(latest["ma25"]),
                "ma99": float(latest["ma99"]),
                "close": float(latest["close"]),
                "atr14": atr14,
                "atr_pct": atr_pct,
                "ma7_turn_atr_ratio": ma7_turn_atr_ratio,
                "range_atr_ratio": range_atr_ratio,
                "close_move_atr_ratio": close_move_atr_ratio,
            },
        }

    def process_symbol(self):
        with self.lock:
            current_price = self.executor.get_mark_price(TRADING_SYMBOL)
            self.current_status["current_price"] = current_price
            stop_closed_sides = self.enforce_fixed_stop_loss(current_price)
            positions = self.executor.get_positions(TRADING_SYMBOL)
            pending_trade = self.process_pending_entry(
                current_price, positions=positions
            )
            if stop_closed_sides or pending_trade is not None:
                self.refresh_status()

        df = self.data_handler.fetch_ohlcv(
            TRADING_SYMBOL,
            timeframe=SIGNAL_TIMEFRAME,
            limit=150,
        )
        result = self.calculate_hybrid_signal(df)
        if result is None:
            self.refresh_status()
            return

        with self.lock:
            self.current_status["indicators"] = result["indicators"]
            self.current_status["signal"] = result["signal"]
            self.current_status["spike_protection"] = result["spike_detected"]
            self.current_status["low_volatility_protection"] = result[
                "low_volatility"
            ]
            self.current_status["current_price"] = current_price
            if result["candle_time"] == self.last_processed_candle:
                self.refresh_status()
                return

            closed_sides = set(stop_closed_sides)

            positions = self.executor.get_positions(TRADING_SYMBOL)
            long_quantity = self.position_quantity(positions["long"])
            short_quantity = self.position_quantity(positions["short"])
            candle_time = result["candle_time"]
            signal = result["signal"]
            if result["spike_detected"]:
                self.clear_pending_entry("偵測到異常 K 線")
                print(
                    "偵測到異常 K 線，暫停新開倉："
                    f"range/ATR={result['indicators']['range_atr_ratio']:.2f}, "
                    f"close-move/ATR={result['indicators']['close_move_atr_ratio']:.2f}"
                )
            elif result["low_volatility"]:
                print(
                    "波動或 MA7 轉折幅度過小，暫停新開倉："
                    f"ATR={result['indicators']['atr_pct']:.4f}%, "
                    "MA7-turn/ATR="
                    f"{result['indicators']['ma7_turn_atr_ratio']:.3f}"
                )

            current_ma7 = float(result["indicators"]["ma7"])
            atr14 = float(result["indicators"]["atr14"])
            exit_ratios = self.update_ma7_exit_tracking(
                positions, current_ma7, atr14
            )
            exit_atr_ok = (
                result["indicators"]["atr_pct"] >= MIN_ENTRY_ATR_PCT
            )
            close_long = (
                long_quantity > 0
                and exit_atr_ok
                and exit_ratios["long"] >= MIN_EXIT_MA7_TURN_ATR_RATIO
            )
            close_short = (
                short_quantity > 0
                and exit_atr_ok
                and exit_ratios["short"] >= MIN_EXIT_MA7_TURN_ATR_RATIO
            )

            for position_side, quantity in (
                ("long", long_quantity),
                ("short", short_quantity),
            ):
                ratio = exit_ratios[position_side]
                if quantity > 0 and ratio > 0 and not (
                    close_long if position_side == "long" else close_short
                ):
                    print(
                        f"{position_side.upper()} MA7 累積反轉/ATR="
                        f"{ratio:.3f}（平倉門檻 "
                        f"{MIN_EXIT_MA7_TURN_ATR_RATIO:.3f}），繼續持倉。"
                    )

            if close_long:
                print(
                    "MA7 從持倉後高點累積回落達門檻，平多單："
                    f"ratio={exit_ratios['long']:.3f}"
                )
                trade = self.executor.close_position(
                    TRADING_SYMBOL, "long", exit_reason="ma7_cumulative"
                )
                if trade is not None:
                    self.reset_ma7_exit_tracking("long")
                    long_quantity = 0.0
                    closed_sides.add("long")
            if close_short:
                print(
                    "MA7 從持倉後低點累積回升達門檻，平空單："
                    f"ratio={exit_ratios['short']:.3f}"
                )
                trade = self.executor.close_position(
                    TRADING_SYMBOL, "short", exit_reason="ma7_cumulative"
                )
                if trade is not None:
                    self.reset_ma7_exit_tracking("short")
                    short_quantity = 0.0
                    closed_sides.add("short")

            queued_entry = self.queue_entry_signal(
                signal, result, blocked_sides=closed_sides
            )
            if queued_entry is not None:
                self.process_pending_entry(current_price)

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
                exit_reason="manual",
            )
            if trade is not None:
                self.reset_ma7_exit_tracking(position_side)
            self.refresh_status()
            return trade is not None

    def manual_open(self, position_side):
        if position_side not in {"long", "short"}:
            raise ValueError("position_side must be long or short")
        with self.lock:
            positions = self.executor.get_positions(TRADING_SYMBOL)
            if any(
                self.position_quantity(positions[side]) > 0
                for side in ("long", "short")
            ):
                self.refresh_status()
                return False

            self.clear_pending_entry("改用手動開倉")
            reference_price = self.executor.get_mark_price(TRADING_SYMBOL)
            amount = self.executor.calculate_amount(
                TRADING_SYMBOL,
                target_percentage=TARGET_PERCENTAGE,
                reference_price=reference_price,
            )
            trade = self.executor.place_order(
                TRADING_SYMBOL,
                "buy" if position_side == "long" else "sell",
                amount,
                position_side=position_side,
                reference_price=reference_price,
            )
            if trade is not None:
                current_ma7 = self.current_status.get(
                    "indicators", {}
                ).get("ma7")
                self.ma7_exit_extremes[position_side] = (
                    float(current_ma7) if current_ma7 is not None else None
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
