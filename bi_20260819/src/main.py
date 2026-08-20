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
    ENTRY_SIGNAL_HOLD_CANDLES,
    LOOP_INTERVAL_SECONDS,
    INTRABAR_COLOR_CHANGE_PCT,
    INTRABAR_COLOR_CONFIRM_SECONDS,
    MIN_INTRABAR_MA7_TURN_ATR_RATIO,
    MA7_EXIT_CONFIRM_CANDLES,
    MAX_CANDLE_RANGE_ATR,
    MAX_CLOSE_MOVE_ATR,
    MAX_ENTRY_PULLBACK_PCT,
    MAX_POSITION_VALUE_USDT,
    MIN_ENTRY_ATR_PCT,
    MIN_ENTRY_PULLBACK_PCT,
    MIN_ENTRY_MA7_TURN_ATR_RATIO,
    MIN_ENTRY_RVOL,
    MIN_EXIT_MA7_TURN_ATR_RATIO,
    PAPER_FEE_RATE,
    PENDING_ENTRY_MINUTES,
    RVOL_LOOKBACK,
    SIGNAL_TIMEFRAME,
    STATUS_FILE,
    STOP_LOSS_PCT,
    TARGET_PERCENTAGE,
    TRAILING_TP_ACTIVATION_PCT,
    TRAILING_TP_CONFIRM_SECONDS,
    TRAILING_TP_DISTANCE_PCT,
    TRAILING_TP_EMERGENCY_DISTANCE_PCT,
    TRAILING_TP_MIN_LOCK_PCT,
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
        stored_confirmations = saved_status.get("ma7_exit_confirmations") or {}
        self.ma7_exit_confirmations = {
            "long": int(stored_confirmations.get("long") or 0),
            "short": int(stored_confirmations.get("short") or 0),
        }
        stored_entry_modes = saved_status.get("position_entry_modes") or {}
        self.position_entry_modes = {
            "long": stored_entry_modes.get("long"),
            "short": stored_entry_modes.get("short"),
        }
        stored_trailing = saved_status.get("trailing_take_profit") or {}
        self.trailing_take_profit = {
            "long": stored_trailing.get("long"),
            "short": stored_trailing.get("short"),
        }
        stored_pending = saved_status.get("pending_entry")
        self.pending_entry = (
            stored_pending if isinstance(stored_pending, dict) else None
        )
        stored_retained = saved_status.get("retained_entry_signal")
        self.retained_entry_signal = (
            stored_retained if isinstance(stored_retained, dict) else None
        )
        stored_intrabar = saved_status.get("intrabar_color_change")
        self.intrabar_color_change = (
            stored_intrabar if isinstance(stored_intrabar, dict) else {}
        )
        self.current_status = {
            "balance": self.executor.get_balance(),
            "max_position_value": self.executor.get_balance(),
            "fee_rate": PAPER_FEE_RATE,
            "total_realized_pnl": self.executor.get_total_realized_pnl(),
            "symbol": TRADING_SYMBOL,
            "current_price": None,
            "signal_timeframe": SIGNAL_TIMEFRAME,
            "entry_ma7_turn_atr_ratio": MIN_ENTRY_MA7_TURN_ATR_RATIO,
            "min_entry_rvol": MIN_ENTRY_RVOL,
            "rvol_lookback": RVOL_LOOKBACK,
            "exit_ma7_turn_atr_ratio": MIN_EXIT_MA7_TURN_ATR_RATIO,
            "ma7_exit_confirm_candles": MA7_EXIT_CONFIRM_CANDLES,
            "stop_loss_pct": STOP_LOSS_PCT,
            "trailing_tp_activation_pct": TRAILING_TP_ACTIVATION_PCT,
            "trailing_tp_confirm_seconds": TRAILING_TP_CONFIRM_SECONDS,
            "trailing_tp_distance_pct": TRAILING_TP_DISTANCE_PCT,
            "trailing_tp_emergency_distance_pct": (
                TRAILING_TP_EMERGENCY_DISTANCE_PCT
            ),
            "trailing_tp_min_lock_pct": TRAILING_TP_MIN_LOCK_PCT,
            "trailing_take_profit": dict(self.trailing_take_profit),
            "entry_pullback_atr_ratio": ENTRY_PULLBACK_ATR_RATIO,
            "entry_pullback_pct_range": [
                MIN_ENTRY_PULLBACK_PCT,
                MAX_ENTRY_PULLBACK_PCT,
            ],
            "pending_entry_minutes": PENDING_ENTRY_MINUTES,
            "entry_signal_hold_candles": ENTRY_SIGNAL_HOLD_CANDLES,
            "intrabar_color_change_pct": INTRABAR_COLOR_CHANGE_PCT,
            "intrabar_color_confirm_seconds": (
                INTRABAR_COLOR_CONFIRM_SECONDS
            ),
            "min_intrabar_ma7_turn_atr_ratio": (
                MIN_INTRABAR_MA7_TURN_ATR_RATIO
            ),
            "intrabar_color_change": dict(self.intrabar_color_change),
            "pending_entry": self.pending_entry,
            "retained_entry_signal": self.retained_entry_signal,
            "ma7_exit_extremes": dict(self.ma7_exit_extremes),
            "ma7_exit_confirmations": dict(self.ma7_exit_confirmations),
            "position_entry_modes": dict(self.position_entry_modes),
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
                "volume": None,
                "volume_median": None,
                "rvol": None,
            },
            "signal": "waiting",
            "spike_protection": False,
            "low_volatility_protection": False,
            "low_volume_protection": False,
            "last_processed_candle": self.last_processed_candle,
            "mode": "paper" if DRY_RUN else "live",
            "running": False,
            "error": None,
        }

    def refresh_status(self):
        with self.lock:
            self.current_status["balance"] = self.executor.get_balance()
            self.current_status["max_position_value"] = (
                self.current_status["balance"]
            )
            self.current_status["positions"] = self.executor.position_summaries(
                TRADING_SYMBOL
            )
            self.current_status["total_realized_pnl"] = (
                self.executor.get_total_realized_pnl()
            )
            self.current_status["ma7_exit_extremes"] = dict(
                self.ma7_exit_extremes
            )
            self.current_status["ma7_exit_confirmations"] = dict(
                self.ma7_exit_confirmations
            )
            self.current_status["position_entry_modes"] = dict(
                self.position_entry_modes
            )
            self.current_status["trailing_take_profit"] = dict(
                self.trailing_take_profit
            )
            self.current_status["pending_entry"] = self.pending_entry
            self.current_status["retained_entry_signal"] = (
                self.retained_entry_signal
            )
            self.current_status["intrabar_color_change"] = dict(
                self.intrabar_color_change
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
    def favorable_move_pct(position_side, entry_price, mark_price):
        if entry_price <= 0 or mark_price <= 0:
            return 0.0
        direction = 1 if position_side == "long" else -1
        return (mark_price - entry_price) / entry_price * 100 * direction

    def enforce_trailing_take_profit(self, current_price, now=None):
        now = now or datetime.now(timezone.utc)
        closed_sides = set()
        positions = self.executor.get_positions(TRADING_SYMBOL)
        for position_side in ("long", "short"):
            position = positions.get(position_side)
            if self.position_quantity(position) <= 0:
                self.trailing_take_profit[position_side] = None
                continue

            entry_mode = self.position_entry_modes.get(position_side)
            if entry_mode not in {"manual", "strategy"}:
                entry_mode = "strategy"
                self.position_entry_modes[position_side] = entry_mode
            if entry_mode == "manual":
                self.trailing_take_profit[position_side] = None
                continue

            entry_price = float(position.get("entryPrice") or 0)
            mark_price = float(position.get("markPrice") or current_price or 0)
            current_profit_pct = self.favorable_move_pct(
                position_side, entry_price, mark_price
            )
            state = self.trailing_take_profit.get(position_side)
            if not isinstance(state, dict):
                state = {"armed": False, "peak_profit_pct": 0.0}

            peak_profit_pct = max(
                float(state.get("peak_profit_pct") or 0),
                current_profit_pct,
            )
            armed = bool(state.get("armed")) or (
                peak_profit_pct >= TRAILING_TP_ACTIVATION_PCT
            )
            stop_profit_pct = (
                max(
                    TRAILING_TP_MIN_LOCK_PCT,
                    peak_profit_pct - TRAILING_TP_DISTANCE_PCT,
                )
                if armed
                else None
            )
            breach_started_at = state.get("breach_started_at")
            if not armed or current_profit_pct > stop_profit_pct:
                breach_started_at = None
            elif not breach_started_at:
                breach_started_at = now.isoformat()

            breach_seconds = 0.0
            if breach_started_at:
                try:
                    breach_time = datetime.fromisoformat(breach_started_at)
                    breach_seconds = max((now - breach_time).total_seconds(), 0.0)
                except (TypeError, ValueError):
                    breach_started_at = now.isoformat()

            drawdown_pct = peak_profit_pct - current_profit_pct
            emergency = (
                armed
                and drawdown_pct >= TRAILING_TP_EMERGENCY_DISTANCE_PCT
            )
            confirmed = (
                armed
                and breach_started_at is not None
                and breach_seconds >= TRAILING_TP_CONFIRM_SECONDS
            )
            self.trailing_take_profit[position_side] = {
                "armed": armed,
                "peak_profit_pct": peak_profit_pct,
                "current_profit_pct": current_profit_pct,
                "stop_profit_pct": stop_profit_pct,
                "breach_started_at": breach_started_at,
                "breach_seconds": breach_seconds,
            }

            if not emergency and not confirmed:
                continue

            print(
                f"移動停利觸發：{position_side.upper()} "
                f"最高獲利 {peak_profit_pct:.3f}%，"
                f"目前 {current_profit_pct:.3f}%（回撤距離 "
                f"{TRAILING_TP_DISTANCE_PCT:.3f}%，"
                f"確認 {breach_seconds:.0f} 秒）。"
            )
            trade = self.executor.close_position(
                TRADING_SYMBOL,
                position_side,
                exit_reason="trailing_tp",
            )
            if trade is not None:
                self.reset_ma7_exit_tracking(position_side)
                closed_sides.add(position_side)

        self.current_status["trailing_take_profit"] = dict(
            self.trailing_take_profit
        )
        return closed_sides

    @staticmethod
    def next_ma7_exit_confirmation(current_count, candidate, adverse_candle):
        if candidate and adverse_candle:
            return int(current_count) + 1
        return 0

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
                self.ma7_exit_confirmations[position_side] = 0
                self.position_entry_modes[position_side] = None
                continue

            entry_mode = self.position_entry_modes.get(position_side)
            if entry_mode not in {"manual", "strategy"}:
                entry_mode = "strategy"
                self.position_entry_modes[position_side] = entry_mode
            if entry_mode == "manual":
                self.ma7_exit_extremes[position_side] = None
                self.ma7_exit_confirmations[position_side] = 0
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
        self.ma7_exit_confirmations[position_side] = 0
        self.trailing_take_profit[position_side] = None
        self.position_entry_modes[position_side] = None
        ratios = self.current_status.setdefault(
            "ma7_exit_ratios", {"long": 0.0, "short": 0.0}
        )
        ratios[position_side] = 0.0

    @staticmethod
    def entry_pullback_pct(atr_pct):
        return min(
            max(atr_pct * ENTRY_PULLBACK_ATR_RATIO, MIN_ENTRY_PULLBACK_PCT),
            MAX_ENTRY_PULLBACK_PCT,
        )

    def resolve_entry_signal(self, result):
        raw_signal = "hold"
        if result["long_timing"]:
            raw_signal = "long"
        elif result["short_timing"]:
            raw_signal = "short"

        if result["spike_detected"]:
            self.retained_entry_signal = None
            self.current_status["retained_entry_signal"] = None
            return "hold"

        if raw_signal in {"long", "short"}:
            if (
                self.pending_entry
                and self.pending_entry.get("side") != raw_signal
            ):
                self.clear_pending_entry("出現反方向 MA7 轉彎")
            self.retained_entry_signal = {
                "side": raw_signal,
                "signal_candle": result["candle_time"],
                "remaining_candles": ENTRY_SIGNAL_HOLD_CANDLES,
                "signal_low": float(result["signal_low"]),
                "signal_high": float(result["signal_high"]),
            }
            print(
                f"保留 {raw_signal.upper()} 轉彎訊號 "
                f"{ENTRY_SIGNAL_HOLD_CANDLES} 根 K 線"
            )

        retained = self.retained_entry_signal
        if not retained:
            return "hold"

        retained["signal_low"] = min(
            float(retained["signal_low"]), float(result["signal_low"])
        )
        retained["signal_high"] = max(
            float(retained["signal_high"]), float(result["signal_high"])
        )
        side = retained.get("side")
        direction_ok = (
            result["ma7_rising"] if side == "long"
            else result["ma7_falling"]
        )
        candle_ok = (
            result["latest_green"] if side == "long"
            else result["latest_red"]
        )
        eligible = (
            side in {"long", "short"}
            and not result["low_volatility"]
            and result["entry_volume_ok"]
            and direction_ok
            and candle_ok
        )
        if eligible:
            result["signal_low"] = retained["signal_low"]
            result["signal_high"] = retained["signal_high"]
            was_retained = (
                retained.get("signal_candle") != result["candle_time"]
            )
            self.retained_entry_signal = None
            self.current_status["retained_entry_signal"] = None
            if was_retained:
                print(f"沿用保留的 {side.upper()} 轉彎訊號")
            return side

        if retained.get("signal_candle") != result["candle_time"]:
            retained["remaining_candles"] = (
                int(retained.get("remaining_candles") or 0) - 1
            )
            if retained["remaining_candles"] <= 0:
                print(f"保留的 {str(side).upper()} 轉彎訊號已到期")
                self.retained_entry_signal = None
                self.current_status["retained_entry_signal"] = None
                return "hold"

        self.current_status["retained_entry_signal"] = retained
        return "hold"

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
        pending_side = pending.get("side")
        if (
            pending_side in {"long", "short"}
            and self.position_quantity(positions[pending_side]) > 0
        ):
            self.clear_pending_entry(f"已有 {pending_side.upper()} 持倉")
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

        entry_rvol = float(pending.get("entry_rvol") or 0)
        if entry_rvol < MIN_ENTRY_RVOL:
            self.clear_pending_entry(
                f"RVOL {entry_rvol:.3f} 低於 {MIN_ENTRY_RVOL:.3f}"
            )
            return None

        position_side = pending.get("side")
        target_price = float(pending.get("target_price") or 0)
        invalidation_price = float(pending.get("invalidation_price") or 0)
        if position_side == "long":
            invalidated = current_price <= invalidation_price
            reached_target = current_price <= target_price
        elif position_side == "short":
            invalidated = current_price >= invalidation_price
            reached_target = current_price >= target_price
        else:
            self.clear_pending_entry("方向格式錯誤")
            return None

        self.current_status["pending_entry"] = pending

        if invalidated:
            self.clear_pending_entry(
                f"價格 {current_price:.2f} 突破訊號失效價 "
                f"{invalidation_price:.2f}"
            )
            return None
        if not reached_target:
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
        self.position_entry_modes[position_side] = "strategy"
        print(
            f"待進場成交 {position_side.upper()}：mark={current_price:.2f}, "
            f"target={target_price:.2f}"
        )
        self.pending_entry = None
        self.current_status["pending_entry"] = None
        return trade

    def queue_entry_signal(self, signal, result, blocked_sides=None):
        blocked_sides = blocked_sides or set()
        if signal not in {"long", "short"} or signal in blocked_sides:
            return None

        positions = self.executor.get_positions(TRADING_SYMBOL)
        if self.position_quantity(positions[signal]) > 0:
            self.clear_pending_entry(f"已有 {signal.upper()} 持倉")
            return None

        if self.pending_entry:
            if self.pending_entry.get("side") == signal:
                return self.pending_entry
            self.clear_pending_entry("出現反方向新訊號")

        entry_rvol = float(result["indicators"].get("rvol") or 0)
        if entry_rvol < MIN_ENTRY_RVOL:
            print(
                f"取消建立待進場 {signal.upper()}：RVOL="
                f"{entry_rvol:.3f}（門檻 {MIN_ENTRY_RVOL:.3f}）。"
            )
            return None

        signal_close = float(result["indicators"]["close"])
        atr_pct = float(result["indicators"]["atr_pct"])
        pullback_pct = self.entry_pullback_pct(atr_pct)
        if signal == "long":
            target_price = signal_close * (1 - pullback_pct / 100)
            invalidation_price = float(result["signal_low"])
        else:
            target_price = signal_close * (1 + pullback_pct / 100)
            invalidation_price = float(result["signal_high"])

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
            "pullback_pct": pullback_pct,
            "entry_rvol": entry_rvol,
            "target_locked": True,
        }
        self.current_status["pending_entry"] = self.pending_entry
        print(
            f"建立待進場 {signal.upper()}：target={target_price:.2f}, "
            f"pullback={pullback_pct:.3f}%, "
            f"valid={PENDING_ENTRY_MINUTES}m"
        )
        return self.pending_entry

    def update_intrabar_color_change(self, live_candle, current_price, now=None):
        now = now or datetime.now(timezone.utc)
        open_price = float(live_candle["open"])
        high_price = float(live_candle["high"])
        low_price = float(live_candle["low"])
        if open_price <= 0 or current_price <= 0:
            return None
        timestamp = live_candle["timestamp"]
        candle_time = (
            timestamp.isoformat()
            if hasattr(timestamp, "isoformat")
            else str(timestamp)
        )
        upper_trigger = open_price * (1 + INTRABAR_COLOR_CHANGE_PCT / 100)
        lower_trigger = open_price * (1 - INTRABAR_COLOR_CHANGE_PCT / 100)
        state = self.intrabar_color_change
        if state.get("candle_time") != candle_time:
            state = {
                "candle_time": candle_time,
                "open": open_price,
                "seen_green": high_price >= upper_trigger,
                "seen_red": low_price <= lower_trigger,
                "candidate": None,
                "candidate_started_at": None,
                "triggered": False,
            }
        state["seen_green"] = bool(state.get("seen_green")) or (
            high_price >= upper_trigger
        )
        state["seen_red"] = bool(state.get("seen_red")) or (
            low_price <= lower_trigger
        )
        state["current_move_pct"] = (current_price - open_price) / open_price * 100
        if state.get("triggered"):
            self.intrabar_color_change = state
            return None
        candidate = None
        if state["seen_green"] and current_price <= lower_trigger:
            candidate = "short"
        elif state["seen_red"] and current_price >= upper_trigger:
            candidate = "long"
        if candidate is None:
            state["candidate"] = None
            state["candidate_started_at"] = None
            state["color_change_confirmed_side"] = None
            state["waiting_for_ma7_pre_turn"] = False
            self.intrabar_color_change = state
            return None
        if state.get("candidate") != candidate:
            state["candidate"] = candidate
            state["candidate_started_at"] = now.isoformat()
            self.intrabar_color_change = state
            return None
        try:
            started_at = datetime.fromisoformat(
                str(state["candidate_started_at"]).replace("Z", "+00:00")
            )
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            state["candidate_started_at"] = now.isoformat()
            self.intrabar_color_change = state
            return None
        confirm_seconds = max((now - started_at).total_seconds(), 0.0)
        state["confirm_seconds"] = confirm_seconds
        if confirm_seconds < INTRABAR_COLOR_CONFIRM_SECONDS:
            self.intrabar_color_change = state
            return None
        state["color_change_confirmed_side"] = candidate
        self.intrabar_color_change = state
        return candidate

    @staticmethod
    def intrabar_ma7_pre_turn(signal, result, df, live_price):
        closed = df.iloc[:-1]
        if len(closed) < 7:
            return False, None, 0.0
        projected_ma7 = (
            float(closed["close"].iloc[-6:].sum()) + float(live_price)
        ) / 7
        current_ma7 = float(result["indicators"].get("ma7") or 0)
        atr14 = float(result["indicators"].get("atr14") or 0)
        turn_atr_ratio = (
            abs(projected_ma7 - current_ma7) / atr14
            if atr14 > 0
            else 0.0
        )
        if signal == "short":
            direction_ok = (
                result["ma7_rising"] and projected_ma7 < current_ma7
            )
        elif signal == "long":
            direction_ok = (
                result["ma7_falling"] and projected_ma7 > current_ma7
            )
        else:
            direction_ok = False
        eligible = (
            direction_ok
            and turn_atr_ratio >= MIN_INTRABAR_MA7_TURN_ATR_RATIO
        )
        return eligible, projected_ma7, turn_atr_ratio

    def execute_intrabar_color_change(
        self, signal, result, live_candle, current_price
    ):
        close_side = "short" if signal == "long" else "long"
        positions = self.executor.get_positions(TRADING_SYMBOL)
        position = positions.get(close_side)
        entry_mode = self.position_entry_modes.get(close_side)
        if entry_mode not in {"manual", "strategy"}:
            entry_mode = "strategy"
        if self.position_quantity(position) > 0 and entry_mode == "strategy":
            color_change = "紅轉綠" if signal == "long" else "綠轉紅"
            print(f"同根 K {color_change}確認，立即平 {close_side.upper()}。")
            trade = self.executor.close_position(
                TRADING_SYMBOL,
                close_side,
                exit_reason="intrabar_color_change",
            )
            if trade is not None:
                self.reset_ma7_exit_tracking(close_side)
        atr14 = float(result["indicators"].get("atr14") or 0)
        live_range = float(live_candle["high"]) - float(live_candle["low"])
        live_range_atr = live_range / atr14 if atr14 > 0 else float("inf")
        if live_range_atr > MAX_CANDLE_RANGE_ATR:
            print(
                "同根 K 變色成立，但振幅過大，僅平倉、不建立新倉："
                f"range/ATR={live_range_atr:.2f}"
            )
            return None
        entry_result = dict(result)
        entry_result["candle_time"] = self.intrabar_color_change["candle_time"]
        entry_result["signal_low"] = float(live_candle["low"])
        entry_result["signal_high"] = float(live_candle["high"])
        indicators = dict(result["indicators"])
        indicators["close"] = float(live_candle["close"])
        indicators["volume"] = float(live_candle["volume"])
        volume_median = float(indicators.get("volume_median") or 0)
        indicators["rvol"] = (
            indicators["volume"] / volume_median
            if volume_median > 0
            else 0.0
        )
        entry_result["indicators"] = indicators
        self.current_status["signal"] = signal
        queued = self.queue_entry_signal(signal, entry_result)
        if queued is not None:
            return self.process_pending_entry(current_price)
        return None

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
        closed["volume_median"] = (
            closed["volume"].shift(1).rolling(RVOL_LOOKBACK).median()
        )
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
        ma7_rising = float(latest["ma7"]) > float(previous["ma7"])
        ma7_falling = float(latest["ma7"]) < float(previous["ma7"])
        ma25_rising = float(latest["ma25"]) > float(previous["ma25"])
        ma99_rising = float(latest["ma99"]) > float(previous["ma99"])
        ma25_falling = float(latest["ma25"]) < float(previous["ma25"])
        ma99_falling = float(latest["ma99"]) < float(previous["ma99"])
        atr14 = float(latest["atr14"])
        latest_close = float(latest["close"])
        atr_pct = atr14 / latest_close * 100 if latest_close > 0 else 0.0
        latest_volume = float(latest["volume"])
        volume_median = float(latest["volume_median"])
        if pd.isna(volume_median) or volume_median <= 0:
            volume_median = 0.0
        rvol = latest_volume / volume_median if volume_median > 0 else 0.0
        entry_volume_ok = rvol >= MIN_ENTRY_RVOL
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
            and entry_volume_ok
            and long_timing
        ):
            signal = "long"
        elif (
            not spike_detected
            and not low_volatility
            and entry_volume_ok
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
            "entry_volume_ok": entry_volume_ok,
            "ma7_turns_up": ma7_turns_up,
            "ma7_turns_down": ma7_turns_down,
            "ma7_rising": ma7_rising,
            "ma7_falling": ma7_falling,
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
                "volume": latest_volume,
                "volume_median": volume_median,
                "rvol": rvol,
            },
        }

    def process_symbol(self):
        with self.lock:
            current_price = self.executor.get_mark_price(TRADING_SYMBOL)
            self.current_status["current_price"] = current_price
            stop_closed_sides = self.enforce_fixed_stop_loss(current_price)
            trailing_closed_sides = self.enforce_trailing_take_profit(
                current_price
            )
            positions = self.executor.get_positions(TRADING_SYMBOL)
            pending_trade = self.process_pending_entry(
                current_price, positions=positions
            )
            if (
                stop_closed_sides
                or trailing_closed_sides
                or pending_trade is not None
            ):
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
            self.current_status["low_volume_protection"] = not result[
                "entry_volume_ok"
            ]
            self.current_status["current_price"] = current_price
            live_candle = df.iloc[-1]
            live_candle_price = float(live_candle["close"])
            intrabar_signal = self.update_intrabar_color_change(
                live_candle, live_candle_price
            )
            self.current_status["intrabar_color_change"] = dict(
                self.intrabar_color_change
            )
            if intrabar_signal in {"long", "short"}:
                (
                    ma7_pre_turn_ok,
                    projected_ma7,
                    ma7_turn_atr_ratio,
                ) = self.intrabar_ma7_pre_turn(
                    intrabar_signal, result, df, live_candle_price
                )
                self.intrabar_color_change["projected_ma7"] = projected_ma7
                self.intrabar_color_change["ma7_turn_atr_ratio"] = (
                    ma7_turn_atr_ratio
                )
                self.intrabar_color_change["min_ma7_turn_atr_ratio"] = (
                    MIN_INTRABAR_MA7_TURN_ATR_RATIO
                )
                self.intrabar_color_change["ma7_pre_turn_ok"] = (
                    ma7_pre_turn_ok
                )
                self.intrabar_color_change["waiting_for_ma7_pre_turn"] = (
                    not ma7_pre_turn_ok
                )
                if ma7_pre_turn_ok:
                    self.intrabar_color_change["triggered"] = True
                    self.intrabar_color_change["triggered_side"] = (
                        intrabar_signal
                    )
                    self.intrabar_color_change["triggered_at"] = (
                        datetime.now(timezone.utc).isoformat()
                    )
                    self.intrabar_color_change["candidate"] = None
                    self.intrabar_color_change[
                        "candidate_started_at"
                    ] = None
                    self.execute_intrabar_color_change(
                        intrabar_signal, result, live_candle, current_price
                    )
                self.current_status["intrabar_color_change"] = dict(
                    self.intrabar_color_change
                )
            if result["candle_time"] == self.last_processed_candle:
                self.refresh_status()
                return

            closed_sides = set(stop_closed_sides | trailing_closed_sides)

            positions = self.executor.get_positions(TRADING_SYMBOL)
            long_quantity = self.position_quantity(positions["long"])
            short_quantity = self.position_quantity(positions["short"])
            candle_time = result["candle_time"]
            signal = self.resolve_entry_signal(result)
            self.current_status["signal"] = signal
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
            elif not result["entry_volume_ok"]:
                print(
                    "成交量不足，暫停新開倉："
                    f"RVOL={result['indicators']['rvol']:.3f} "
                    f"（門檻 {MIN_ENTRY_RVOL:.3f}）。"
                )

            current_ma7 = float(result["indicators"]["ma7"])
            atr14 = float(result["indicators"]["atr14"])
            exit_ratios = self.update_ma7_exit_tracking(
                positions, current_ma7, atr14
            )
            exit_atr_ok = (
                result["indicators"]["atr_pct"] >= MIN_ENTRY_ATR_PCT
            )
            exit_candidates = {
                "long": (
                    long_quantity > 0
                    and exit_atr_ok
                    and exit_ratios["long"]
                    >= MIN_EXIT_MA7_TURN_ATR_RATIO
                ),
                "short": (
                    short_quantity > 0
                    and exit_atr_ok
                    and exit_ratios["short"]
                    >= MIN_EXIT_MA7_TURN_ATR_RATIO
                ),
            }
            adverse_candles = {
                "long": result["latest_red"],
                "short": result["latest_green"],
            }
            for position_side in ("long", "short"):
                self.ma7_exit_confirmations[position_side] = (
                    self.next_ma7_exit_confirmation(
                        self.ma7_exit_confirmations[position_side],
                        exit_candidates[position_side],
                        adverse_candles[position_side],
                    )
                )
            self.current_status["ma7_exit_confirmations"] = dict(
                self.ma7_exit_confirmations
            )
            close_long = (
                exit_candidates["long"]
                and self.ma7_exit_confirmations["long"]
                >= MA7_EXIT_CONFIRM_CANDLES
            )
            close_short = (
                exit_candidates["short"]
                and self.ma7_exit_confirmations["short"]
                >= MA7_EXIT_CONFIRM_CANDLES
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
                    confirmations = self.ma7_exit_confirmations[position_side]
                    if confirmations > 0:
                        print(
                            f"{position_side.upper()} MA7 平倉確認 "
                            f"{confirmations}/{MA7_EXIT_CONFIRM_CANDLES}，"
                            "等待下一根同方向反轉 K 線。"
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
            if self.position_quantity(positions[position_side]) > 0:
                self.refresh_status()
                return False

            self.clear_pending_entry("改用手動開倉")
            self.retained_entry_signal = None
            self.current_status["retained_entry_signal"] = None
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
                self.position_entry_modes[position_side] = "manual"
                self.ma7_exit_extremes[position_side] = None
                self.trailing_take_profit[position_side] = None
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
