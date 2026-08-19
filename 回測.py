#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回測 - 針對「新幣安」目前套用的策略,用歷史 K 線資料回測過去表現。

直接載入「新幣安」那個檔案,重用裡面的策略類別(EmaRsiCrossStrategy /
BollingerRsiReversionStrategy / MaTurnStrategy)、Signal / MarketSnapshot /
PositionInfo,確保回測用的判斷邏輯跟現在線上實際在跑的完全一樣,不是另外重寫一份、
容易跟正式邏輯漏同步的版本。只有「怎麼撮合成交、怎麼算損益」這部分是回測腳本自己的,
而且止損/移動停利的模擬邏輯也跟 bot 本體的 check_paper_stop_loss()/
check_paper_trailing_stop() 保持一致。

用法範例:
    python3 回測.py
    python3 回測.py --symbol BTCUSDT --interval 15m --days 180 --leverage 5 \\
        --risk-pct 0.02 --max-margin 50 --stop-loss-pct 0.01 --trailing-stop-pct 0.0025
    python3 回測.py --strategy ma_turn --ma-period 7

已知限制(誠實列出,回測結果不等於未來績效):
    - 進出場都用「K棒收盤價」當成交價,沒有模擬滑價、沒有逐筆撮合
    - 止損/止盈用K棒的最高/最低價判斷「有沒有觸及」,觸及就假設用那個價位成交;
      真實市場流動性不足或插針時,實際成交價可能更差
    - 止損/止盈判斷用的是「最新成交價」的K棒(跟策略訊號用同一份資料),不是像正式
      環境下單那樣用「標記價格」,兩者長期會有些微落差
    - 只回測歷史某一段區間,過去表現不保證未來獲利,行情環境改變策略可能完全失效
"""

import argparse
import importlib.util
import logging
import sys
import time
from dataclasses import dataclass
from importlib.machinery import SourceFileLoader
from typing import List, Optional

from binance.client import Client


def _load_xinbian():
    loader = SourceFileLoader("xinbian_bot", "新幣安")
    spec = importlib.util.spec_from_loader("xinbian_bot", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["xinbian_bot"] = mod
    loader.exec_module(mod)
    # 「新幣安」載入時會設定 logging.basicConfig() 寫入 新幣安.log(給正在跑的機器人用)。
    # 回測每根K棒都會呼叫一次策略,若不關掉這個 logger,幾千根K棒會瘋狂洗版終端機,
    # 而且還會把回測的雜訊寫進正式機器人在用的同一份 log 檔。直接關閉這個 logger 的輸出,
    # 不影響回測腳本自己用 print 印出的報告。
    mod.logger.setLevel(logging.CRITICAL + 10)
    return mod


_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "8h": 28_800_000, "12h": 43_200_000, "1d": 86_400_000,
}


def fetch_historical_klines(client: Client, symbol: str, interval: str, days: int) -> list:
    if interval not in _INTERVAL_MS:
        raise ValueError(f"不支援的 interval: {interval}(可用: {', '.join(_INTERVAL_MS)})")

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86_400_000
    step_ms = _INTERVAL_MS[interval] * 1500  # 每次最多拿 1500 根

    all_klines = []
    cursor = start_ms
    print(f"下載歷史K線中... {symbol} {interval} 最近 {days} 天", file=sys.stderr)
    while cursor < end_ms:
        batch = client.futures_klines(
            symbol=symbol, interval=interval,
            startTime=cursor, endTime=min(cursor + step_ms, end_ms), limit=1500,
        )
        if not batch:
            cursor += step_ms
            continue
        all_klines.extend(batch)
        cursor = batch[-1][0] + _INTERVAL_MS[interval]
        print(f"  已取得 {len(all_klines)} 根K棒...", file=sys.stderr)

    # 依開盤時間去重(分批下載邊界可能重疊)
    seen = set()
    deduped = []
    for k in all_klines:
        if k[0] in seen:
            continue
        seen.add(k[0])
        deduped.append(k)
    deduped.sort(key=lambda k: k[0])
    return deduped


@dataclass
class _Position:
    side: str = "NONE"
    quantity: float = 0.0
    entry_price: float = 0.0
    entry_time: int = 0
    best_price: float = 0.0  # 移動停利用:多單記錄進場以來最高價,空單記錄最低價


@dataclass
class Trade:
    entry_time: int
    exit_time: int
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    fee: float
    reason: str


def run_backtest(mod, klines: list, symbol: str, leverage: int, risk_pct: float,
                  max_margin: float, stop_loss_pct: float, trailing_stop_pct: float,
                  fee_pct: float, starting_balance: float, strategy):
    balance = starting_balance
    pos = _Position()
    trades: List[Trade] = []
    equity_curve = [starting_balance]

    # 通用地找出策略需要多少根K棒才有足夠資料 - 不同策略有不同的「週期」屬性名稱
    # (EmaRsiCrossStrategy 是 ema_slow/rsi_period/adx_period,BollingerRsiReversionStrategy
    # 是 bb_period/rsi_period),用屬性名稱裡有沒有 "period" 或 "slow" 通用抓出來,
    # 不用為了每個新策略類型都回來改這裡。
    period_like = [v for k, v in vars(strategy).items()
                   if isinstance(v, int) and ("period" in k or "slow" in k)]
    min_required = (max(period_like) if period_like else 20) + 4

    def calc_qty(price: float) -> float:
        margin = min(balance * risk_pct, max_margin)
        notional = margin * leverage
        return notional / price

    def close(exit_price: float, exit_time: int, reason: str):
        nonlocal balance, pos
        diff = exit_price - pos.entry_price
        if pos.side == "SHORT":
            diff = -diff
        pnl = diff * pos.quantity
        notional_exit = exit_price * pos.quantity
        fee = notional_exit * fee_pct
        balance += pnl - fee
        trades.append(Trade(
            entry_time=pos.entry_time, exit_time=exit_time, side=pos.side,
            entry_price=pos.entry_price, exit_price=exit_price, quantity=pos.quantity,
            pnl=pnl - fee, fee=fee, reason=reason,
        ))
        pos = _Position()
        equity_curve.append(balance)

    for i in range(min_required, len(klines)):
        window = klines[max(0, i - 98):i + 1]
        # 策略只會讀 -2 / -3,絕對不會讀 -1,所以把最後一根(candle i,真正剛收盤的那根)
        # 複製一份塞在 -1 當佔位,讓 -2 對齊到 candle i,跟正式環境「-1 是還沒收盤的
        # 最新K棒、-2 才是最後一根已收盤K棒」的語意完全一致。
        window_for_strategy = window + [window[-1]]

        close_price = float(klines[i][4])
        high_price = float(klines[i][2])
        low_price = float(klines[i][3])
        candle_time = int(klines[i][0])

        # 1. 若有倉位,先用這根K棒的高低點判斷有沒有觸及止損,再判斷移動停利。
        #    移動停利要先「啟動」(價格已經往有利方向跑過 TRAILING_STOP_PCT)才會生效,
        #    否則一筆進場就被套的交易,會在還沒到停損之前就被移動停利當成停損提早出場 -
        #    跟「新幣安」bot 裡 check_paper_trailing_stop() 用完全相同的邏輯,確保回測
        #    結果跟正式環境的行為一致。
        if pos.side != "NONE":
            if pos.side == "LONG":
                pos.best_price = max(pos.best_price, high_price)
            else:
                pos.best_price = min(pos.best_price, low_price)

            if pos.side == "LONG":
                sl_price = pos.entry_price * (1 - stop_loss_pct)
                if stop_loss_pct > 0 and low_price <= sl_price:
                    close(sl_price, candle_time, "STOP_LOSS")
                elif trailing_stop_pct > 0:
                    activation_price = pos.entry_price * (1 + trailing_stop_pct)
                    if pos.best_price >= activation_price:
                        trail_stop_price = pos.best_price * (1 - trailing_stop_pct)
                        if low_price <= trail_stop_price:
                            close(trail_stop_price, candle_time, "TRAILING_STOP")
            else:  # SHORT
                sl_price = pos.entry_price * (1 + stop_loss_pct)
                if stop_loss_pct > 0 and high_price >= sl_price:
                    close(sl_price, candle_time, "STOP_LOSS")
                elif trailing_stop_pct > 0:
                    activation_price = pos.entry_price * (1 - trailing_stop_pct)
                    if pos.best_price <= activation_price:
                        trail_stop_price = pos.best_price * (1 + trailing_stop_pct)
                        if high_price >= trail_stop_price:
                            close(trail_stop_price, candle_time, "TRAILING_STOP")

        # 2. 交給策略判斷(用重新整理過、is_open 反映最新狀態的 position)
        position_info = mod.PositionInfo(
            symbol=symbol, side=pos.side, quantity=pos.quantity,
            entry_price=pos.entry_price, unrealized_pnl=0.0,
        )
        market = mod.MarketSnapshot(symbol=symbol, price=close_price, klines=window_for_strategy)
        signal = strategy.on_tick(market, position_info)

        if signal == mod.Signal.CLOSE and pos.side != "NONE":
            close(close_price, candle_time, "策略訊號")
        elif signal in (mod.Signal.LONG, mod.Signal.SHORT) and pos.side == "NONE":
            qty = calc_qty(close_price)
            if qty > 0:
                notional_entry = close_price * qty
                fee = notional_entry * fee_pct
                balance -= fee
                pos = _Position(
                    side=signal.value, quantity=qty, entry_price=close_price, entry_time=candle_time,
                    best_price=close_price,
                )

    # 回測結束時若還有倉位,用最後一根K棒收盤價強制平倉,才能算出完整的最終權益
    if pos.side != "NONE":
        close(float(klines[-1][4]), int(klines[-1][0]), "回測結束強制平倉")

    return trades, balance, equity_curve


def print_report(trades: List[Trade], starting_balance: float, final_balance: float,
                  equity_curve: List[float], symbol: str, interval: str, days: int, strategy_name: str):
    print()
    print("=" * 60)
    print(f"回測報告 | {symbol} | {interval} | 近 {days} 天 | 策略: {strategy_name}")
    print("=" * 60)

    if not trades:
        print("這段期間內策略完全沒有觸發任何一筆交易(沒有出現符合進場條件的訊號),")
        print("無法計算績效統計。可以試著拉長 --days,或換一個 interval 看看。")
        return

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    total_pnl = sum(t.pnl for t in trades)
    total_fee = sum(t.fee for t in trades)
    win_rate = len(wins) / len(trades) * 100
    gross_win = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    peak = equity_curve[0]
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = (peak - e) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    total_return_pct = (final_balance / starting_balance - 1) * 100

    print(f"起始本金        : {starting_balance:,.2f} USDT")
    print(f"結束本金        : {final_balance:,.2f} USDT")
    print(f"總報酬率        : {total_return_pct:+.2f}%")
    print(f"總交易次數      : {len(trades)}")
    print(f"勝率            : {win_rate:.1f}% ({len(wins)} 勝 / {len(losses)} 敗)")
    print(f"獲利因子 (PF)   : {profit_factor:.2f}" if profit_factor != float("inf") else "獲利因子 (PF)   : inf(沒有任何虧損交易)")
    print(f"最大回撤        : {max_dd * 100:.2f}%")
    print(f"平均每筆損益    : {total_pnl / len(trades):+.4f} USDT")
    print(f"累積手續費      : {total_fee:.4f} USDT")
    print()

    reason_counts = {}
    for t in trades:
        reason_counts[t.reason] = reason_counts.get(t.reason, 0) + 1
    print("出場原因分布    :", ", ".join(f"{k} x{v}" for k, v in reason_counts.items()))

    print()
    shown = trades[-20:]
    if len(trades) > 20:
        print(f"最近 20 筆交易明細(共 {len(trades)} 筆):")
    else:
        print("交易明細:")
    for t in shown:
        import datetime
        et = datetime.datetime.fromtimestamp(t.entry_time / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        xt = datetime.datetime.fromtimestamp(t.exit_time / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"  [{et} -> {xt}] {t.side:<5} 進場 {t.entry_price:.2f} 出場 {t.exit_price:.2f} "
              f"數量 {t.quantity:.6f} | 損益 {t.pnl:+.4f} USDT ({t.reason})")

    print("=" * 60)
    print(f"提醒:以上是「{strategy_name}」策略在歷史資料上的表現,")
    print("不是未來績效的保證,行情環境改變策略可能完全失效。")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="回測「新幣安」目前套用的策略")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--leverage", type=int, default=5)
    parser.add_argument("--risk-pct", type=float, default=0.02)
    parser.add_argument("--max-margin", type=float, default=50.0)
    parser.add_argument("--stop-loss-pct", type=float, default=0.01)
    parser.add_argument("--trailing-stop-pct", type=float, default=0.0025,
                         help="移動停利回落幅度,0 代表不設。需要先真的獲利超過這個幅度才會啟動追蹤")
    parser.add_argument("--fee-pct", type=float, default=0.0004, help="單邊手續費率,預設 0.04%%(幣安合約 Taker 費率)")
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    parser.add_argument("--strategy", choices=["ema_rsi", "bb_reversion", "ma_turn", "ma_turn_volume"], default="ma_turn",
                         help="ema_rsi = EMA交叉+RSI+ADX趨勢濾網(追動能);bb_reversion = 布林通道+RSI均值回歸(逆勢);"
                              "ma_turn = MA轉折(谷底轉向上買入、高點轉向下賣出);"
                              "ma_turn_volume = MA轉折 + 量縮濾網(進場前那段走勢成交量要明顯萎縮)")
    # EmaRsiCrossStrategy 參數
    parser.add_argument("--ema-fast", type=int, default=9)
    parser.add_argument("--ema-slow", type=int, default=21)
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--rsi-buy", type=float, default=50.0)
    parser.add_argument("--rsi-sell", type=float, default=50.0)
    parser.add_argument("--adx-period", type=int, default=14)
    parser.add_argument("--adx-threshold", type=float, default=20.0,
                         help="ADX 趨勢濾網門檻,0 代表關閉濾網(等同沒有 ADX 過濾)")
    # BollingerRsiReversionStrategy 參數
    parser.add_argument("--bb-period", type=int, default=20)
    parser.add_argument("--bb-std", type=float, default=2.0)
    parser.add_argument("--rsi-oversold", type=float, default=30.0)
    parser.add_argument("--rsi-overbought", type=float, default=70.0)
    # MaTurnStrategy 參數
    parser.add_argument("--ma-period", type=int, default=7)
    parser.add_argument("--ma-entry-confirm-bars", type=int, default=1,
                         help="進場轉折需要連續幾根同方向K棒確認,預設 1(不額外確認,盡量減少進場延遲)")
    parser.add_argument("--ma-exit-confirm-bars", type=int, default=2,
                         help="出場/止盈轉折需要連續幾根同方向K棒確認,預設 2(比進場嚴格,避免雜訊提早出場)")
    # MaTurnVolumeStrategy 額外參數
    parser.add_argument("--volume-lookback-bars", type=int, default=16)
    parser.add_argument("--volume-max-ratio", type=float, default=0.7,
                         help="後半段平均量 <= 前半段平均量 * 這個比例才算量縮,預設 0.7")
    args = parser.parse_args()

    mod = _load_xinbian()
    client = Client("", "")  # 只用公開行情端點,不需要 API Key

    klines = fetch_historical_klines(client, args.symbol, args.interval, args.days)
    if not klines:
        print("沒有抓到任何K線資料,請確認 symbol/interval 是否正確。", file=sys.stderr)
        sys.exit(1)
    print(f"共取得 {len(klines)} 根K棒,開始回測...", file=sys.stderr)

    if args.strategy == "bb_reversion":
        strategy = mod.BollingerRsiReversionStrategy(
            bb_period=args.bb_period, bb_std=args.bb_std, rsi_period=args.rsi_period,
            rsi_oversold=args.rsi_oversold, rsi_overbought=args.rsi_overbought,
        )
    elif args.strategy == "ma_turn":
        strategy = mod.MaTurnStrategy(
            ma_period=args.ma_period,
            entry_confirm_bars=args.ma_entry_confirm_bars,
            exit_confirm_bars=args.ma_exit_confirm_bars,
        )
    elif args.strategy == "ma_turn_volume":
        strategy = mod.MaTurnVolumeStrategy(
            ma_period=args.ma_period,
            entry_confirm_bars=args.ma_entry_confirm_bars,
            exit_confirm_bars=args.ma_exit_confirm_bars,
            volume_lookback_bars=args.volume_lookback_bars,
            volume_max_ratio=args.volume_max_ratio,
        )
    else:
        strategy = mod.EmaRsiCrossStrategy(
            ema_fast=args.ema_fast, ema_slow=args.ema_slow, rsi_period=args.rsi_period,
            rsi_buy_threshold=args.rsi_buy, rsi_sell_threshold=args.rsi_sell,
            adx_period=args.adx_period, adx_threshold=args.adx_threshold,
        )

    trades, final_balance, equity_curve = run_backtest(
        mod, klines, args.symbol, args.leverage, args.risk_pct, args.max_margin,
        args.stop_loss_pct, args.trailing_stop_pct, args.fee_pct, args.starting_balance,
        strategy,
    )

    print_report(trades, args.starting_balance, final_balance, equity_curve,
                 args.symbol, args.interval, args.days, type(strategy).__name__)


if __name__ == "__main__":
    main()
