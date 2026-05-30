import asyncio
import os
import ccxt.pro as ccxtpro  # 使用 CCXT 的 WebSocket 版本
import numpy as np
import sys                  # 用於觸發風控時關閉程式
import argparse             # 用於接收命令列參數
from update_paper_state import update_paper_state
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# =====================================================================
# 帳號與參數設定區（方案 A：直接交易 BNB 合約）
# =====================================================================
exchange = ccxtpro.binance({
    'apiKey': os.getenv('BINANCE_API_KEY') or None,     # 從 .env 讀取 API Key
    'secret': os.getenv('BINANCE_API_SECRET') or None,   # 從 .env 讀取 Secret Key
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',             # 操作合約 (Futures)
    }
})
USE_TESTNET = os.getenv("USE_TESTNET", "True").lower() in ("true", "1", "yes")
PAPER_TRADING = not bool(os.getenv('BINANCE_API_KEY')) or not USE_TESTNET

if USE_TESTNET:
    # 繞過 CCXT 的 set_sandbox_mode 棄用限制，手動覆寫合約測試網 URL
    exchange.urls['api']['fapiPublic'] = 'https://testnet.binancefuture.com/fapi/v1'
    exchange.urls['api']['fapiPrivate'] = 'https://testnet.binancefuture.com/fapi/v1'

if PAPER_TRADING:
    print(f"⚠️ [模式設定] 啟動純數據模擬模式 (Paper Trading) | 連線主網: {not USE_TESTNET}")
else:
    print(f"⚠️ [模式設定] 啟動真實交易模式 | 連線主網: {not USE_TESTNET}")

# 接收命令列參數
parser = argparse.ArgumentParser()
parser.add_argument('--symbol', type=str, default='SOL/USDT', help='Trading symbol (e.g. SOL/USDT)')
parser.add_argument('--amount', type=float, default=10.0, help='Trade amount in quote currency (USDT)')
args = parser.parse_args()

# 交易設定
symbol = args.symbol                      # 透過參數決定的交易對
if not symbol.endswith(':USDT') and '/USDT' in symbol:
    symbol = symbol + ':USDT'             # 確保使用合約幣對格式 (e.g. SUI/USDT:USDT)
timeframe = '1m'                          # 1分鐘K線
quote_amount = args.amount                # 下單金額 (USDT)

# --- 交易與風控參數 ---
ATR_PERIOD = 14                       # ATR 計算週期
ORDER_BOOK_THRESHOLD_USD = 100000.0   # 盤口大單追蹤門檻 (10萬美金)
ATR_TP_MULTIPLIER = 0.0       # 取消動態放大，只求最快平倉
ATR_SL_MULTIPLIER = 1.5       # 止損距離 (ATR 倍數)
MIN_TP_PCT = 0.003       # 最小止盈 0.3%
MIN_SL_PCT = 0.008         # 最小止損 0.8%
current_atr = 0.0                         # 當前 ATR 值（由 K線模組更新）
RSI_PERIOD = 14                           # RSI 計算週期
RSI_OVERBOUGHT = 70                       # RSI 超買門檻（高於此不買入）
current_rsi = 50.0                        # 當前 RSI 值

# 🎯 物理防火牆：每日最大虧損限額設定
INITIAL_BALANCE = 80.0                    # 你的總本金 80 USDT
MAX_DAILY_LOSS_PCT = 0.05                 # 每日最大容忍虧損 5%
BALANCE_STOP_LINE = INITIAL_BALANCE * (1 - MAX_DAILY_LOSS_PCT)  # 80 * 0.95 = 76 USDT


# =====================================================================
# 安全防護模組：動態檢查當前持倉與帳戶總資產
# =====================================================================
async def check_account_safety():
    """ 檢查帳戶總餘額，若跌破防禦線則立刻終止程式 """
    if PAPER_TRADING:
        return
    try:
        # 獲取帳戶全資產資訊
        balance_info = await exchange.fetch_balance()
        # 取得當前 U本位合約帳戶的總權益 (Total Wallet Balance + Unreallized PnL)
        current_wallet_balance = float(balance_info['total'].get('USDT', 0))
        
        # 判斷是否跌破防禦線
        if current_wallet_balance <= BALANCE_STOP_LINE:
            print(f"\n🚨🚨 [風控斷路器觸發] 🚨🚨")
            print(f"⚠️ 當前帳戶總資產為: {current_wallet_balance:.2f} USDT")
            print(f"⚠️ 已跌破每日防禦底線: {BALANCE_STOP_LINE:.2f} USDT (虧損達 5%)")
            print(f"🛑 為了保護剩餘的 95% 本金，程式現在執行「物理斷電」強制關機！")
            sys.exit(0)  # 徹底關閉 Python 程式
            
    except SystemExit:
        sys.exit(0)
    except Exception as e:
        print(f"⚠️ [風控模組] 讀取資產線失敗: {e}，暫時放行檢查。")

async def get_current_price():
    ticker = await exchange.fetch_ticker(symbol)
    return float(ticker['last'])

async def get_base_amount():
    price = await get_current_price()
    return quote_amount / price

simulated_base_amt = 0.0

MAX_POSITION_USD = 150.0

async def has_reached_position_limit():
    """ 檢查當前帳戶持倉是否已達 150 USD 上限 """
    if PAPER_TRADING:
        price = await get_current_price()
        return (abs(simulated_base_amt) * price) >= (MAX_POSITION_USD * 0.95)
    try:
        positions = await exchange.fetch_positions([symbol])
        if positions:
            pos = positions[0]
            notional = abs(float(pos.get('notional', 0)))
            if notional == 0:
                price = await get_current_price()
                notional = abs(float(pos.get('contracts', 0))) * price
            if notional >= (MAX_POSITION_USD * 0.95):
                return True
        return False
    except Exception as e:
        print(f"⚠️ [防護模組] 檢查持倉上限失敗，預設視為已達上限: {e}")
        return True


# =====================================================================
# ③ 下單與風控模組 (Execution & Risk Control)
# =====================================================================
async def execute_order_and_risk(side, price):
    global simulated_base_amt
    global simulated_avg_price
    global current_atr
    
    # 1. 每次準備下單前，先檢查今天是不是虧太多了
    await check_account_safety()
    
    # 2. 安全防護：檢查是否有持倉上限
    current_p = await get_current_price()
    current_balance = 150.0
    if PAPER_TRADING:
        try:
            import json
            with open("paper_state.json", "r") as f:
                state = json.load(f)
                current_balance = float(state.get("balance_usdt", 150.0))
        except:
            pass
    
    # 動態持倉上限 = 當前總資金 (實現複利滾存)
    dynamic_max_position = current_balance

    # 計算如果再加倉，是否會超過上限
    if (abs(simulated_base_amt) * current_p) + quote_amount > dynamic_max_position:
        print(f"⚠️ [風控攔截] 模擬倉位已達上限 {dynamic_max_position:.2f} USDT，暫停加倉！")
        return

    try:
        base_amt = await get_base_amount()
        direction_str = "做多(Long)" if side == 'buy' else "做空(Short)"
        print(f"\n🛒 [下單模組] 💡 訊號觸發！發送【市價單】{direction_str} {quote_amount} USDT -> 數量: {base_amt:.6f}")
        
        if PAPER_TRADING:
            avg_price = price
            actual_received_amt = base_amt
            if side == 'buy':
                simulated_base_amt += actual_received_amt
            else:
                simulated_base_amt -= actual_received_amt
            simulated_avg_price = avg_price
            print(f"✅ [模擬開倉成功] {direction_str} | 成交均價: {avg_price} | 總倉位: {simulated_base_amt:.6f}")
            update_paper_state(symbol.replace('/', ''), side, avg_price, actual_received_amt)
        else:
            # 3. 執行市價開倉單
            open_order = await exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=base_amt
            )
            avg_price = open_order.get('average') or price
            print(f"✅ [下單模組] {direction_str} 開倉成功！實際成交均價: {avg_price} | 單號: {open_order['id']}")
        
        # 4. 動態計算止盈與止損點位
        atr_pct = (current_atr / avg_price) if current_atr > 0 else MIN_TP_PCT
        tp_pct = max(MIN_TP_PCT, ATR_TP_MULTIPLIER * atr_pct)
        sl_pct = max(MIN_SL_PCT, ATR_SL_MULTIPLIER * atr_pct)
        
        if side == 'buy':
            tp_price = avg_price * (1 + tp_pct)
            sl_price = avg_price * (1 - sl_pct)
        else:
            tp_price = avg_price * (1 - tp_pct)
            sl_price = avg_price * (1 + sl_pct)
        
        print(f"🛡️ [風控模組] 當前 ATR: {current_atr:.6f} ({atr_pct*100:.2f}%) | RSI: {current_rsi:.1f}")
        print(f"   📈 動態止盈目標價: {tp_price:.2f} ({tp_pct*100:.2f}%)")
        print(f"   📉 動態止損觸發價: {sl_price:.2f} ({sl_pct*100:.2f}%)")
        
        # 5. 在本地進行迴圈監控
        while True:
            await asyncio.sleep(2)
            ticker = await exchange.fetch_ticker(symbol)
            current_p = ticker['last']
            if side == 'buy':
                if current_p >= tp_price:
                    print(f"🎯 [止盈觸發] 多單獲利！目前價格 {current_p} >= {tp_price}")
                    break
                elif current_p <= sl_price:
                    print(f"🛑 [止損觸發] 多單停損！目前價格 {current_p} <= {sl_price}")
                    break
            else:
                if current_p <= tp_price:
                    print(f"🎯 [止盈觸發] 空單獲利！目前價格 {current_p} <= {tp_price}")
                    break
                elif current_p >= sl_price:
                    print(f"🛑 [止損觸發] 空單停損！目前價格 {current_p} >= {sl_price}")
                    break
                
        # 6. 執行平倉 (只平掉這顆子彈的份額)
        if PAPER_TRADING:
            close_side = 'sell' if simulated_base_amt > 0 else 'buy'
            actual_close_amt = abs(simulated_base_amt)
            
            # 計算原始盈虧 (手續費統一由 update_paper_state 扣除)
            if simulated_base_amt > 0: # Long close
                close_pnl = (current_p - simulated_avg_price) * actual_close_amt
            else: # Short close
                close_pnl = (simulated_avg_price - current_p) * actual_close_amt
                
            simulated_base_amt = 0.0
            print(f"✅ [模擬平倉成功] 已成功平倉！剩餘模擬總倉位: {simulated_base_amt:.6f} | 盈虧(手續費由底層扣除): {close_pnl:.4f} USDT")
            update_paper_state(symbol.replace('/', ''), close_side, current_p, actual_close_amt, is_close=True, pnl=close_pnl)
        else:
            close_side = 'sell' if side == 'buy' else 'buy'
            close_action = "賣出平多" if close_side == 'sell' else "買入平空"
            print(f"🛒 [下單模組] 發送【市價單】{close_action}對應倉位...")
            target_close_amount = base_amt * 0.999
            try:
                close_order = await exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=close_side,
                    amount=target_close_amount,
                    params={'reduceOnly': True}
                )
                print(f"✅ [平倉成功] 已成功{close_action}！數量: {target_close_amount:.6f} | 單號: {close_order['id']}\n")
            except Exception as e:
                print(f"⚠️ [平倉失敗] 餘額不足或倉位已被其他網格平掉: {e}")
            
    except Exception as e:
        print(f"🚨 [下單/風控模組嚴重致命錯誤]: {e}")
        if PAPER_TRADING:
            simulated_base_amt = 0.0


# =====================================================================
# ① 行情接收模組 & ② 策略邏輯模組
# =====================================================================
async def watch_kline_and_strategy():
    """ 透過 WebSocket 監聽 1分K，並用 NumPy 計算布林插針策略 """
    print("🚀 [行情模組一] 開始監聽 WebSocket K線數據 (正在預載歷史數據...)")
    global current_atr, current_rsi
    prev_close = None
    tr_list = []
    import time
    last_buy_time = 0
    
    # 預載歷史 K 線以防啟動時需空等 20 分鐘
    try:
        historical_ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=30)
        closes_history = [x[4] for x in historical_ohlcv]
    except Exception as e:
        print(f"⚠️ 無法預載歷史 K 線: {e}")
        closes_history = []
        
    while True:
        try:
            ohlcv = await exchange.watch_ohlcv(symbol, timeframe)
            
            # 合併歷史數據與 WebSocket 即時數據
            # 注意：watch_ohlcv 回傳的是自帶緩存的 list，我們把歷史的補在前面，並去重疊
            combined_closes = closes_history + [x[4] for x in ohlcv]
            # 只取最後 30 筆即可
            closes = np.array(combined_closes[-30:])
            highs = np.array([x[2] for x in ohlcv])
            opens = np.array([x[1] for x in ohlcv])
            
            if len(closes) < 20:
                continue

            # 計算 ATR
            for i in range(len(ohlcv)):
                h, l, c = ohlcv[i][2], ohlcv[i][3], ohlcv[i][4]
                if i == 0 and prev_close is not None:
                    tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
                elif i > 0:
                    tr = max(h - l, abs(h - ohlcv[i-1][4]), abs(l - ohlcv[i-1][4]))
                else:
                    tr = h - l
                tr_list.append(tr)
            prev_close = ohlcv[-1][4]
            if len(tr_list) > ATR_PERIOD * 3:
                tr_list = tr_list[-(ATR_PERIOD * 3):]
            if len(tr_list) >= ATR_PERIOD:
                current_atr = float(np.mean(tr_list[-ATR_PERIOD:]))

            # 計算 RSI
            if len(closes) > RSI_PERIOD:
                deltas = np.diff(closes[-RSI_PERIOD-1:])
                gains = deltas[deltas > 0].mean() if np.any(deltas > 0) else 1e-10
                losses = -deltas[deltas < 0].mean() if np.any(deltas < 0) else 1e-10
                rs = gains / losses
                current_rsi = 100.0 - (100.0 / (1.0 + rs))
                
            middle_band = np.mean(closes[-20:])
            close_price = closes[-1]
            deviation = (close_price - middle_band) / middle_band
            
            # 雙向策略：跌破買入(做多)，漲破賣出(做空)
            # 增強精準度：要求偏離大於 0.1% (0.001) 且搭配 RSI 超買超賣指標
            if deviation <= -0.001 and current_rsi < 35.0:
                current_time = time.time()
                if current_time - last_buy_time > 30: # 30 秒冷卻時間
                    last_buy_time = current_time
                    print(f"⚠️ [策略訊號] RSI 超賣({current_rsi:.1f}) 且低於均線！偏離: {deviation*100:.3f}%，精準觸發做多(Long)")
                    asyncio.create_task(execute_order_and_risk(side='buy', price=close_price))
            elif deviation >= 0.001 and current_rsi > 65.0:
                current_time = time.time()
                if current_time - last_buy_time > 30: # 共用冷卻時間
                    last_buy_time = current_time
                    print(f"⚠️ [策略訊號] RSI 超買({current_rsi:.1f}) 且高於均線！偏離: {deviation*100:.3f}%，精準觸發做空(Short)")
                    asyncio.create_task(execute_order_and_risk(side='sell', price=close_price))
                
        except Exception as e:
            print(f"❌ [K線模組發生波動]: {e}，1秒後自動重連...")
            await asyncio.sleep(1)


async def watch_trades_and_order_book():
    """ 透過 WebSocket 監聽逐筆成交，執行「盤口大單追蹤」 """
    print("🚀 [行情模組二] 開始監聽 WebSocket 逐筆成交數據...")
    while True:
        try:
            trades = await exchange.watch_trades(symbol)
            price = await get_current_price()
            threshold_qty = ORDER_BOOK_THRESHOLD_USD / price
            for trade in trades:
                trade_volume = trade['amount']
                trade_price = trade['price']
                trade_side = trade['side']
                
                if trade_volume >= threshold_qty:
                    print(f"🔥 [策略訊號] 盤口湧入特大單！方向: {trade_side}, 數量: {trade_volume:.2f}, USD約: ${trade_volume*price:.0f}, 價格: {trade_price}")
                    
                    if trade_side == 'buy':
                        print("👉 [策略動態] 主力強勢吃單，程式啟動順勢追多！")
                        asyncio.create_task(execute_order_and_risk(side='buy', price=trade_price))
                        
        except Exception as e:
            print(f"❌ [逐筆成交模組發生波動]: {e}，1秒後自動重連...")
            await asyncio.sleep(1)


# =====================================================================
# 主程式入口
# =====================================================================
async def main():
    if not PAPER_TRADING:
        try:
            await exchange.set_margin_mode('isolated', symbol)
            await exchange.set_leverage(1, symbol)
            print(f"🔒 [安全保護] 已成功強制設定合約為【逐倉模式】與【1倍槓桿】！")
        except Exception as e:
            print(f"⚠️ [安全保護警告] 設定逐倉/槓桿失敗，可能該幣種不支援或已有持倉: {e}")
            
    # 啟動時先做第一次帳戶安全檢查
    await check_account_safety()
    # 同時併發運行兩大行情模組
    await asyncio.gather(
        watch_kline_and_strategy(),
        watch_trades_and_order_book()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 機器人已被手動關閉，安全退出。")
