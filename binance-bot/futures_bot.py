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
MIN_TP_PCT = 0.0015     # 全局最低停利標準：0.15%
MIN_SL_PCT = 0.008         # 最小止損 0.8%
current_atr = 0.0                         # 當前 ATR 值（由 K線模組更新）
RSI_PERIOD = 14                           # RSI 計算週期
RSI_OVERBOUGHT = 70                       # RSI 超買門檻（高於此不買入）
current_rsi = 50.0                        # 當前 RSI 值
macro_regime = "猴市 (區間震盪)"          # 全局大趨勢狀態

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

async def get_base_amount(amt_usd):
    price = await get_current_price()
    return amt_usd / price

simulated_base_amt = 0.0
latest_ws_price = 0.0
current_pos_qty = 0.0
current_pos_avg = 0.0

async def initialize_simulated_position():
    global simulated_base_amt
    if PAPER_TRADING:
        try:
            import json
            import os
            if os.path.exists("paper_state.json"):
                with open("paper_state.json", "r") as f:
                    state = json.load(f)
                    pos = state.get("positions", {}).get(symbol.replace('/', ''), {})
                    simulated_base_amt = float(pos.get("qty", 0.0))
                    print(f"📦 [系統初始化] 從歷史紀錄恢復模擬倉位: {simulated_base_amt} 顆")
        except Exception as e:
            print(f"⚠️ [系統初始化] 無法讀取歷史倉位，預設為 0: {e}")

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

    # 計算剩餘可下單額度
    current_position_usd = abs(simulated_base_amt) * current_p
    available_margin = dynamic_max_position - current_position_usd

    if available_margin <= 0:
        print(f"⚠️ [風控攔截] 模擬倉位已達上限 {dynamic_max_position:.2f} USDT，暫停加倉！")
        return

    # 🐒🐂🐻 依據市場狀態自動切換下單金額
    if "猴市" in macro_regime:
        actual_quote_amount = 75.0
        print(f"💰 [金額切換] 猴市(盤整)模式 → 固定下單 75 USDT")
        print(f"@@AMOUNT@@{actual_quote_amount}")
    else:
        actual_quote_amount = 30.0
        print(f"💰 [金額切換] 牛/熊市(趨勢)模式 → 固定下單 30 USDT")
        print(f"@@AMOUNT@@{actual_quote_amount}")
    if available_margin < actual_quote_amount:
        actual_quote_amount = available_margin
        print(f"⚠️ [額度調整] 剩餘額度不足，將剩餘 {actual_quote_amount:.2f} USDT 梭哈！")

    try:
        base_amt = await get_base_amount(actual_quote_amount)
        direction_str = "做多(Long)" if side == 'buy' else "做空(Short)"
        print(f"\n🛒 [下單模組] 💡 訊號觸發！發送【市價單】{direction_str} {actual_quote_amount:.2f} USDT -> 數量: {base_amt:.6f}")
        
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
        
        # 4. 只負責執行開倉，TP/SL 由 monitor_position_tp_sl 全局監控負責
        # print(f"🛡️ [風控模組] 已開倉！等待全局風控引擎接手監控。")
            
    except Exception as e:
        print(f"🚨 [下單/風控模組嚴重致命錯誤]: {e}")
        if PAPER_TRADING:
            simulated_base_amt = 0.0

async def update_position_info():
    global current_pos_qty, current_pos_avg
    while True:
        try:
            if PAPER_TRADING:
                import json
                try:
                    with open("paper_state.json", "r") as f:
                        state = json.load(f)
                        pos = state.get("positions", {}).get(symbol.replace('/', ''), {})
                        current_pos_qty = float(pos.get("qty", 0.0))
                        current_pos_avg = float(pos.get("avg_price", 0.0))
                except:
                    pass
            else:
                positions = await exchange.fetch_positions([symbol])
                if positions:
                    p = positions[0]
                    current_pos_qty = float(p.get('info', {}).get('positionAmt', 0.0))
                    current_pos_avg = float(p.get('entryPrice', 0.0))
            await asyncio.sleep(1.0)
        except Exception as e:
            await asyncio.sleep(1.0)

async def close_entire_position(close_side, actual_close_amt, current_p, pos_avg):
    global simulated_base_amt
    if PAPER_TRADING:
        close_pnl = (current_p - pos_avg) * actual_close_amt if close_side == 'sell' else (pos_avg - current_p) * actual_close_amt
        simulated_base_amt = 0.0
        print(f"✅ [模擬平倉成功] 全倉已平！盈虧: {close_pnl:.4f} USDT")
        update_paper_state(symbol.replace('/', ''), close_side, current_p, actual_close_amt, is_close=True, pnl=close_pnl)
    else:
        close_action = "賣出平多" if close_side == 'sell' else "買入平空"
        try:
            close_order = await exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=actual_close_amt,
                params={'reduceOnly': True}
            )
            print(f"✅ [全局平倉成功] 已成功{close_action}！數量: {actual_close_amt:.6f}")
        except Exception as e:
            print(f"⚠️ [全局平倉失敗]: {e}")

async def monitor_position_tp_sl():
    """ 獨立的全局倉位監控任務，根據整體持倉均價進行市價平倉 """
    while True:
        try:
            await asyncio.sleep(0.5)
            
            # 1. 抓取全局倉位
            pos_qty = 0.0
            pos_avg = 0.0
            if PAPER_TRADING:
                import json
                try:
                    with open("paper_state.json", "r") as f:
                        state = json.load(f)
                        pos = state.get("positions", {}).get(symbol.replace('/', ''), {})
                        pos_qty = float(pos.get("qty", 0.0))
                        pos_avg = float(pos.get("avg_price", 0.0))
                except:
                    pass
            else:
                positions = await exchange.fetch_positions([symbol])
                if positions:
                    p = positions[0]
                    pos_qty = float(p.get('info', {}).get('positionAmt', 0.0))
                    pos_avg = float(p.get('entryPrice', 0.0))
            
            if abs(pos_qty) <= 0.000001 or pos_avg <= 0:
                continue
                
            # 2. 獲取現價
            ticker = await exchange.fetch_ticker(symbol)
            current_p = ticker['last']
            
            # 3. 判斷全局 TP/SL
            tp_pct = MIN_TP_PCT
            sl_pct = MIN_SL_PCT
            
            if current_pos_qty > 0: # 多單
                tp_price = current_pos_avg * (1 + tp_pct)
                sl_price = current_pos_avg * (1 - sl_pct)
                if current_p >= tp_price:
                    print(f"🎯 [全局止盈] 多單均價 {current_pos_avg:.4f}，現價 {current_p} >= 目標 {tp_price:.4f}，市價全平！")
                    await close_entire_position('sell', abs(current_pos_qty), current_p, current_pos_avg)
                    current_pos_qty = 0.0 # 避免重複觸發
                elif current_p <= sl_price:
                    print(f"🛑 [全局止損] 多單均價 {current_pos_avg:.4f}，現價 {current_p} <= 觸發 {sl_price:.4f}，市價全平！")
                    await close_entire_position('sell', abs(current_pos_qty), current_p, current_pos_avg)
                    current_pos_qty = 0.0 # 避免重複觸發
            else: # 空單
                tp_price = current_pos_avg * (1 - tp_pct)
                sl_price = current_pos_avg * (1 + sl_pct)
                if current_p <= tp_price:
                    print(f"🎯 [全局止盈] 空單均價 {current_pos_avg:.4f}，現價 {current_p} <= 目標 {tp_price:.4f}，市價全平！")
                    await close_entire_position('buy', abs(current_pos_qty), current_p, current_pos_avg)
                    current_pos_qty = 0.0 # 避免重複觸發
                elif current_p >= sl_price:
                    print(f"🛑 [全局止損] 空單均價 {current_pos_avg:.4f}，現價 {current_p} >= 觸發 {sl_price:.4f}，市價全平！")
                    await close_entire_position('buy', abs(current_pos_qty), current_p, current_pos_avg)
                    current_pos_qty = 0.0 # 避免重複觸發
                    
        except Exception as e:
            pass # 忽略異常並重試

# =====================================================================
# ① 行情接收模組 & ② 策略邏輯模組
# =====================================================================
async def monitor_macro_trend():
    """ 週期性檢查 1H 級別的 20T 均線，判斷大趨勢 (牛/熊/猴) """
    global macro_regime
    while True:
        try:
            # 先抓取 BTC 大盤 1 小時 K 線
            btc_ohlcv = await exchange.fetch_ohlcv('BTCUSDT', timeframe='1h', limit=30)
            if len(btc_ohlcv) >= 20:
                btc_closes = np.array([x[4] for x in btc_ohlcv])
                btc_sma = np.mean(btc_closes[-20:])
                btc_deviation = (btc_closes[-1] - btc_sma) / btc_sma
            else:
                btc_deviation = 0.0

            # 抓取當前交易幣種 1 小時 K 線
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1h', limit=30)
            if len(ohlcv) >= 20:
                closes = np.array([x[4] for x in ohlcv])
                current_price = closes[-1]
                sma_20 = np.mean(closes[-20:])
                
                # 計算幣種偏離度
                coin_deviation = (current_price - sma_20) / sma_20
                
                old_regime = macro_regime
                
                # 邏輯：BTC 大盤擁有最高決策權
                if btc_deviation > 0.005:
                    macro_regime = "牛市 (大盤BTC帶飛)"
                    print_dev = btc_deviation
                elif btc_deviation < -0.005:
                    macro_regime = "熊市 (大盤BTC帶崩)"
                    print_dev = btc_deviation
                else:
                    # 大盤震盪時，才看個別幣種
                    if coin_deviation > 0.005:
                        macro_regime = "牛市 (獨立走強)"
                    elif coin_deviation < -0.005:
                        macro_regime = "熊市 (獨立走弱)"
                    else:
                        macro_regime = "猴市 (區間震盪)"
                    print_dev = coin_deviation
                
                if old_regime != macro_regime:
                    amount = 75.0 if "猴市" in macro_regime else 30.0
                    print(f"@@REGIME@@{macro_regime}")
                    print(f"@@AMOUNT@@{amount}")
                    print(f"🌍 [環境感知] 大趨勢已切換為: {macro_regime} | 下單金額: {amount} USDT (偏離: {print_dev*100:.2f}%)")
        except Exception as e:
            print(f"⚠️ [環境感知] 無法獲取 1H 趨勢: {e}")
        
        # 每 5 分鐘檢查一次
        await asyncio.sleep(300)

async def watch_kline_and_strategy():
    """ 透過 WebSocket 監聽 1分K，並用 NumPy 計算布林插針策略 """
    print("🚀 [行情模組一] 開始監聽 WebSocket K線數據 (正在預載歷史數據...)")
    global current_atr, current_rsi, current_pos_qty
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
            
            # 🔥 新增：高溫煞車系統 (RSI Overheat Protection)
            # 如果 RSI 進入極端瘋狂區域，禁止開倉，直到降溫
            if current_rsi > 75.0:
                # 記錄一次警告，避免洗版，這裡不印出，只做防護攔截
                continue
            if current_rsi < 25.0:
                continue

            # 🚀 [動態轉折平倉邏輯]
            if abs(current_pos_qty) > 0.000001:
                is_long = current_pos_qty > 0
                recent_highs = [x[2] for x in ohlcv[-30:-1]]
                recent_lows = [x[3] for x in ohlcv[-30:-1]]
                resistance = max(recent_highs) if recent_highs else 999999
                support = min(recent_lows) if recent_lows else 0
                range_height = resistance - support
                current_open = opens[-1]
                
                close_signal = False
                close_reason = ""
                
                if is_long:
                    if close_price < middle_band and opens[-1] > middle_band:
                        close_signal = True
                        close_reason = "跌破 20T 均線 (動能轉弱)"
                    elif close_price >= resistance - (range_height * 0.1) and close_price < current_open:
                        close_signal = True
                        close_reason = "壓力區出現紅K (遇壓回檔)"
                    elif current_rsi > 70 and close_price < current_open:
                        close_signal = True
                        close_reason = "RSI 超買且反轉收黑"
                else:
                    if close_price > middle_band and opens[-1] < middle_band:
                        close_signal = True
                        close_reason = "突破 20T 均線 (動能轉強)"
                    elif close_price <= support + (range_height * 0.1) and close_price > current_open:
                        close_signal = True
                        close_reason = "支撐區出現綠K (遇撐反彈)"
                    elif current_rsi < 30 and close_price > current_open:
                        close_signal = True
                        close_reason = "RSI 超賣且反轉收紅"

                if close_signal:
                    print(f"⚠️ [動態平倉] 偵測到趨勢轉折！原因: {close_reason}，觸發提早市價平倉！")
                    close_side = 'sell' if is_long else 'buy'
                    asyncio.create_task(close_entire_position(close_side, abs(current_pos_qty), close_price, current_pos_avg))
                    current_pos_qty = 0.0
                    continue # 平倉後本回合不再開新倉

            # 動態大腦：根據大環境切換雙刀流策略 (Regime-Switching)
            current_time = time.time()
            if current_time - last_buy_time > 30: # 全局共用 30 秒冷卻
                if "猴市" in macro_regime:
                    # 🐒 猴市 (盤整)：【區間操作 Range Trading】抓天花板與地板
                    recent_highs = [x[2] for x in ohlcv[-30:-1]] # 過去 29 根 K 線的高點 (不含當前未走完的)
                    recent_lows = [x[3] for x in ohlcv[-30:-1]]  # 過去 29 根 K 線的低點
                    
                    if recent_highs and recent_lows:
                        resistance = max(recent_highs)
                        support = min(recent_lows)
                        range_height = resistance - support
                        
                        # 確保箱子夠大 (至少 0.2% 震幅)，否則死魚盤不操作
                        if support > 0 and (range_height / support) >= 0.002:
                            current_open = opens[-1]
                            
                            # 接近壓力位 (頂部 10% 區域)，且出現紅K (走勢反轉向下)
                            if close_price >= resistance - (range_height * 0.1):
                                if close_price < current_open:
                                    last_buy_time = current_time
                                    print(f"⚠️ [雙刀流: 區間] 碰壓力區見跌(紅K)！箱頂:{resistance:.4f}，觸發做空(Short)")
                                    asyncio.create_task(execute_order_and_risk(side='sell', price=close_price))
                            
                            # 接近支撐位 (底部 10% 區域)，且出現綠K (走勢反轉向上)
                            elif close_price <= support + (range_height * 0.1):
                                if close_price > current_open:
                                    last_buy_time = current_time
                                    print(f"⚠️ [雙刀流: 區間] 碰支撐區見漲(綠K)！箱底:{support:.4f}，觸發做多(Long)")
                                    asyncio.create_task(execute_order_and_risk(side='buy', price=close_price))
                else:
                    # 🐂🐻 牛/熊市 (趨勢)：使用【順勢突破】(追漲殺跌)
                    if deviation >= 0.002 and current_rsi > 55.0:
                        if "熊市" not in macro_regime: # 熊市不逆勢追多
                            last_buy_time = current_time
                            print(f"⚠️ [雙刀流: 順勢] 強勢突破！RSI({current_rsi:.1f}) 偏離: {deviation*100:.3f}%，觸發追多(Long)")
                            asyncio.create_task(execute_order_and_risk(side='buy', price=close_price))
                    elif deviation <= -0.002 and current_rsi < 45.0:
                        if "牛市" not in macro_regime: # 牛市不逆勢追空
                            last_buy_time = current_time
                            print(f"⚠️ [雙刀流: 順勢] 弱勢跌破！RSI({current_rsi:.1f}) 偏離: {deviation*100:.3f}%，觸發追空(Short)")
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
    try:
        if not PAPER_TRADING:
            await exchange.set_margin_mode('isolated', symbol)
            await exchange.set_leverage(10, symbol)
            print(f"🔧 [系統初始化] 實盤模式: 已設定為逐倉模式與 10 倍槓桿")
    except Exception as e:
        print(f"⚠️ [安全保護警告] 設定逐倉/槓桿失敗，可能該幣種不支援或已有持倉: {e}")
            
    # 啟動時先做第一次帳戶安全檢查與歷史倉位載入
    await check_account_safety()
    await initialize_simulated_position()
    print("🚀 啟動防爆倉模組 & WebSocket 即時監聽...")
    print(f"@@REGIME@@{macro_regime}") # 初始化發送狀態
    # 同時併發運行兩大行情模組與全局監控
    await asyncio.gather(
        check_account_safety(),
        update_position_info(),
        watch_kline_and_strategy(),
        watch_trades_and_order_book(),
        monitor_macro_trend(),
        monitor_position_tp_sl()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 機器人已被手動關閉，安全退出。")
