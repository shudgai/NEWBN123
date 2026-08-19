import json
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import ccxt

from src.config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    DRY_RUN,
    HEDGE_MODE,
    MAX_POSITION_VALUE_USDT,
    MAX_ENTRY_PRICE_DEVIATION_PCT,
    PAPER_BALANCE_USDT,
    PAPER_FEE_RATE,
    PAPER_LEVERAGE,
    PAPER_STATE_FILE,
)

TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")


class Executor:
    def __init__(
        self,
        exchange=None,
        dry_run=DRY_RUN,
        paper_balance=PAPER_BALANCE_USDT,
        paper_leverage=PAPER_LEVERAGE,
        hedge_mode=HEDGE_MODE,
        max_position_value=MAX_POSITION_VALUE_USDT,
        fee_rate=PAPER_FEE_RATE,
    ):
        self.dry_run = bool(dry_run)
        self.initial_paper_balance = float(paper_balance)
        self.paper_balance = float(paper_balance)
        self.paper_leverage = float(paper_leverage)
        self.hedge_mode = bool(hedge_mode)
        self.max_position_value = float(max_position_value)
        self.fee_rate = float(fee_rate)
        self.paper_positions = {}
        self.trade_history = []
        self.total_realized_pnl = 0.0

        credentials_missing = (
            not BINANCE_API_KEY
            or not BINANCE_API_SECRET
            or BINANCE_API_KEY == "YOUR_API_KEY"
            or BINANCE_API_SECRET == "YOUR_API_SECRET"
        )
        if not self.dry_run and exchange is None and credentials_missing:
            raise RuntimeError(
                "真實交易缺少 Binance 憑證，請在 .env 設定 "
                "BINANCE_API_KEY 與 BINANCE_API_SECRET。"
            )

        self.exchange = exchange or ccxt.binance({
            "apiKey": BINANCE_API_KEY or None,
            "secret": BINANCE_API_SECRET or None,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
        if self.dry_run:
            self._load_paper_state()

    @staticmethod
    def utc_now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def to_taipei_time(value):
        if not value:
            return value
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(TAIPEI_TIMEZONE).isoformat()

    @staticmethod
    def empty_position(symbol, side):
        return {
            "symbol": symbol,
            "side": side,
            "quantity": 0.0,
            "entry_price": 0.0,
            "mark_price": 0.0,
            "trade_value": 0.0,
            "entry_fee": 0.0,
            "unrealized_pnl": 0.0,
            "leverage": 0.0,
            "leveraged_pnl_pct": 0.0,
            "unleveraged_pnl_pct": 0.0,
        }

    def _load_paper_state(self):
        if not PAPER_STATE_FILE.exists():
            return
        try:
            with PAPER_STATE_FILE.open("r", encoding="utf-8") as file_handle:
                state = json.load(file_handle)
            self.paper_balance = float(
                state.get("balance", self.initial_paper_balance)
            )
            self.total_realized_pnl = float(
                state.get("total_realized_pnl", 0)
            )
            self.paper_positions = state.get("positions") or {}
            self.trade_history = state.get("trade_history") or []
            leverage_updated = False
            for positions in self.paper_positions.values():
                for position in positions.values():
                    quantity = float(position.get("contracts") or 0)
                    entry_price = float(position.get("entryPrice") or 0)
                    trade_value = quantity * entry_price
                    if float(position.get("leverage") or 0) != self.paper_leverage:
                        position["leverage"] = self.paper_leverage
                        position["initialMargin"] = (
                            trade_value / self.paper_leverage
                        )
                        leverage_updated = True
            if leverage_updated:
                self._save_paper_state()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.paper_balance = self.initial_paper_balance
            self.total_realized_pnl = 0.0
            self.paper_positions = {}
            self.trade_history = []

    def _save_paper_state(self):
        state = {
            "balance": self.paper_balance,
            "total_realized_pnl": self.total_realized_pnl,
            "positions": self.paper_positions,
            "trade_history": self.trade_history,
        }
        temporary_file = PAPER_STATE_FILE.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file_handle:
            json.dump(state, file_handle, ensure_ascii=False, allow_nan=False)
        os.replace(temporary_file, PAPER_STATE_FILE)

    def get_balance(self):
        if self.dry_run:
            return self.paper_balance

        balance = self.exchange.fetch_balance({"type": "future"})
        available = (balance.get("USDT") or {}).get("free")
        if available is None:
            available = (balance.get("free") or {}).get("USDT")
        if available is None:
            raise RuntimeError("Binance 回應中找不到可用 USDT 餘額。")
        return float(available)

    def get_total_realized_pnl(self):
        return self.total_realized_pnl if self.dry_run else 0.0

    def get_trade_history(self, trade_date=None):
        history = []
        for stored_trade in reversed(self.trade_history):
            trade = dict(stored_trade)
            trade["opened_at"] = self.to_taipei_time(trade.get("opened_at"))
            trade["closed_at"] = self.to_taipei_time(trade.get("closed_at"))
            history.append(trade)
        if trade_date:
            history = [
                trade
                for trade in history
                if trade.get("closed_at", "").startswith(trade_date)
            ]
        return history

    def get_mark_price(self, symbol):
        if hasattr(self.exchange, "fetch_funding_rate"):
            try:
                funding_rate = self.exchange.fetch_funding_rate(symbol)
                mark_price = funding_rate.get("markPrice")
                if mark_price is not None and float(mark_price) > 0:
                    return float(mark_price)
            except (ccxt.BaseError, KeyError, TypeError, ValueError):
                pass
        ticker_price = float(self.exchange.fetch_ticker(symbol)["last"])
        if ticker_price <= 0:
            raise ValueError("exchange returned a non-positive price")
        return ticker_price


    @staticmethod
    def price_deviation_pct(price, reference_price):
        if reference_price is None or float(reference_price) <= 0:
            return 0.0
        return (
            abs(float(price) - float(reference_price))
            / float(reference_price)
            * 100
        )

    def entry_price_is_safe(self, price, reference_price):
        deviation = self.price_deviation_pct(price, reference_price)
        if deviation > MAX_ENTRY_PRICE_DEVIATION_PCT:
            print(
                f"取消新開倉：標記價偏離最近收盤 {deviation:.3f}% "
                f"(上限 {MAX_ENTRY_PRICE_DEVIATION_PCT:.3f}%)。"
            )
            return False
        return True

    def calculate_amount(
        self, symbol, target_percentage=0.5, reference_price=None
    ):
        if not 0 < target_percentage <= 1:
            raise ValueError("target_percentage must be greater than 0 and at most 1")

        try:
            self.exchange.load_markets()
            balance = self.get_balance()
            if balance <= 0:
                print("可用 USDT 餘額不足。")
                return 0.0

            market = self.exchange.market(symbol)
            current_price = self.get_mark_price(symbol)
            if not self.entry_price_is_safe(current_price, reference_price):
                return 0.0

            budget = min(balance * target_percentage, self.max_position_value)
            amount = budget / current_price
            limits = market.get("limits") or {}
            min_cost = (limits.get("cost") or {}).get("min")
            min_amount = (limits.get("amount") or {}).get("min")

            if min_cost is not None and budget < float(min_cost):
                return 0.0
            if min_amount is not None and amount < float(min_amount):
                return 0.0

            precise_amount = float(
                self.exchange.amount_to_precision(symbol, amount)
            )
            if precise_amount * current_price > self.max_position_value:
                precise_amount = float(
                    self.exchange.amount_to_precision(
                        symbol,
                        self.max_position_value / current_price,
                    )
                )
            return precise_amount
        except (ccxt.BaseError, KeyError, TypeError, ValueError) as exc:
            print(f"計算下單數量失敗 {symbol}: {exc}")
            return 0.0

    def get_positions(self, symbol):
        positions = {"long": None, "short": None}
        if self.dry_run:
            stored = self.paper_positions.get(symbol, {})
            if stored:
                mark_price = self.get_mark_price(symbol)
                for side, position in stored.items():
                    entry_price = float(position["entryPrice"])
                    quantity = float(position["contracts"])
                    direction = 1 if side == "long" else -1
                    position["markPrice"] = mark_price
                    position["notional"] = quantity * mark_price
                    position["unrealizedPnl"] = (
                        (mark_price - entry_price) * quantity * direction
                    )
                    positions[side] = position
            return positions

        for position in self.exchange.fetch_positions([symbol]):
            contracts = float(position.get("contracts") or 0)
            side = position.get("side")
            if (
                position.get("symbol") == symbol
                and contracts > 0
                and side in positions
            ):
                positions[side] = position
        return positions

    def position_summary(self, symbol, side, position=None):
        position = position or self.get_positions(symbol).get(side)
        if not position:
            return self.empty_position(symbol, side)

        quantity = float(position.get("contracts") or position.get("amount") or 0)
        contract_size = float(position.get("contractSize") or 1)
        entry_price = float(position.get("entryPrice") or 0)
        mark_price = float(position.get("markPrice") or 0)
        leverage = float(position.get("leverage") or 1)
        trade_value = quantity * contract_size * entry_price
        entry_fee = float(position.get("entryFee") or 0)
        unrealized_pnl = float(position.get("unrealizedPnl") or 0)

        direction = 1 if side == "long" else -1
        unleveraged_pct = 0.0
        if entry_price > 0 and mark_price > 0:
            unleveraged_pct = (
                ((mark_price - entry_price) / entry_price) * 100 * direction
            )

        initial_margin = float(position.get("initialMargin") or 0)
        if initial_margin > 0:
            leveraged_pct = (unrealized_pnl / initial_margin) * 100
        else:
            leveraged_pct = unleveraged_pct * leverage

        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "mark_price": mark_price,
            "trade_value": trade_value,
            "entry_fee": entry_fee,
            "unrealized_pnl": unrealized_pnl,
            "leverage": leverage,
            "leveraged_pnl_pct": leveraged_pct,
            "unleveraged_pnl_pct": unleveraged_pct,
        }

    def estimated_close_result(self, symbol, position_side, position=None):
        position = position or self.get_positions(symbol).get(position_side)
        if not position:
            return {"gross_pnl": 0.0, "total_fees": 0.0, "net_pnl": 0.0}

        quantity = float(
            position.get("contracts") or position.get("amount") or 0
        )
        contract_size = float(position.get("contractSize") or 1)
        entry_price = float(position.get("entryPrice") or 0)
        mark_price = float(position.get("markPrice") or 0)
        direction = 1 if position_side == "long" else -1
        gross_pnl = (
            (mark_price - entry_price)
            * quantity
            * contract_size
            * direction
        )
        entry_fee = float(position.get("entryFee") or 0)
        exit_fee = quantity * contract_size * mark_price * self.fee_rate
        total_fees = entry_fee + exit_fee
        return {
            "gross_pnl": gross_pnl,
            "total_fees": total_fees,
            "net_pnl": gross_pnl - total_fees,
        }

    def position_summaries(self, symbol):
        positions = self.get_positions(symbol)
        return {
            side: self.position_summary(symbol, side, positions[side])
            for side in ("long", "short")
        }

    def place_order(
        self,
        symbol,
        side,
        amount,
        order_type="market",
        position_side=None,
        reduce_only=False,
        reference_price=None,
        exit_reason="strategy",
    ):
        amount = float(amount)
        if amount <= 0:
            print("下單數量無效。")
            return None

        position_side = position_side or (
            "long" if side == "buy" else "short"
        )

        if self.dry_run:
            if reduce_only:
                return self._close_paper_position(
                    symbol, position_side, exit_reason
                )

            symbol_positions = self.paper_positions.setdefault(symbol, {})
            has_open_position = any(
                float(position.get("contracts") or 0) > 0
                for position in symbol_positions.values()
            )
            if has_open_position:
                print(
                    "Skip entry: single-position mode already has a BTC "
                    "position."
                )
                return None

            entry_price = self.get_mark_price(symbol)
            if not self.entry_price_is_safe(entry_price, reference_price):
                return None
            trade_value = amount * entry_price
            if trade_value > self.max_position_value + 0.01:
                raise RuntimeError(
                    f"單筆成交金額 {trade_value:.2f} USDT 超過 "
                    f"{self.max_position_value:.2f} USDT 上限。"
                )

            entry_fee = trade_value * self.fee_rate
            self.paper_balance -= entry_fee
            symbol_positions[position_side] = {
                "id": uuid.uuid4().hex,
                "symbol": symbol,
                "contracts": amount,
                "contractSize": 1.0,
                "side": position_side,
                "entryPrice": entry_price,
                "markPrice": entry_price,
                "notional": trade_value,
                "entryFee": entry_fee,
                "unrealizedPnl": 0.0,
                "leverage": self.paper_leverage,
                "initialMargin": trade_value / self.paper_leverage,
                "hedged": True,
                "openedAt": self.utc_now(),
            }
            self._save_paper_state()
            print(
                f"[PAPER] OPEN {position_side.upper()} {amount} "
                f"fee={entry_fee:.6f}"
            )
            return {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "position_side": position_side,
                "fee": entry_fee,
                "dry_run": True,
            }

        params = {}
        if self.hedge_mode:
            params["positionSide"] = position_side.upper()
        if reduce_only and not self.hedge_mode:
            params["reduceOnly"] = True
        return self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            params=params,
        )

    def _close_paper_position(
        self, symbol, position_side, exit_reason="strategy"
    ):
        position = self.get_positions(symbol).get(position_side)
        if not position:
            return None

        quantity = float(position["contracts"])
        entry_price = float(position["entryPrice"])
        exit_price = float(position["markPrice"])
        direction = 1 if position_side == "long" else -1
        gross_pnl = (exit_price - entry_price) * quantity * direction
        entry_fee = float(position.get("entryFee") or 0)
        exit_value = quantity * exit_price
        exit_fee = exit_value * self.fee_rate
        total_fees = entry_fee + exit_fee
        net_pnl = gross_pnl - total_fees

        self.paper_balance += gross_pnl - exit_fee
        self.total_realized_pnl += net_pnl
        trade = {
            "id": position.get("id") or uuid.uuid4().hex,
            "symbol": symbol,
            "side": position_side,
            "leverage": float(position.get("leverage") or 1),
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "trade_value": quantity * entry_price,
            "gross_pnl": gross_pnl,
            "entry_fee": entry_fee,
            "exit_fee": exit_fee,
            "total_fees": total_fees,
            "net_realized_pnl": net_pnl,
            "opened_at": position.get("openedAt"),
            "closed_at": self.utc_now(),
            "exit_reason": exit_reason,
        }
        self.trade_history.append(trade)
        self.paper_positions.get(symbol, {}).pop(position_side, None)
        self._save_paper_state()
        print(
            f"[PAPER] CLOSE {position_side.upper()} "
            f"net={net_pnl:.6f} fees={total_fees:.6f}"
        )
        return trade

    def close_position(self, symbol, position_side, exit_reason="strategy"):
        position = self.get_positions(symbol).get(position_side)
        if not position:
            return None

        amount = float(position.get("contracts") or position.get("amount") or 0)
        if amount <= 0:
            return None

        close_side = "sell" if position_side == "long" else "buy"
        amount = float(self.exchange.amount_to_precision(symbol, amount))
        return self.place_order(
            symbol,
            close_side,
            amount,
            position_side=position_side,
            reduce_only=True,
            exit_reason=exit_reason,
        )
