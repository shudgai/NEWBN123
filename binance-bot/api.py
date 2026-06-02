import os
import sys
import collections
import datetime
import asyncio
import time
import subprocess
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
import uvicorn
from functools import wraps

# 載入環境變數
load_dotenv()


app = FastAPI(title="Binance Bot API Backend")

# 快取合約精度
_contract_precisions = {}

def get_contract_step(symbol):
    """取得 Binance 合約 LOT_SIZE stepSize"""
    if symbol in _contract_precisions:
        return _contract_precisions[symbol]
    try:
        info = client.futures_exchange_info()
        for s in info.get('symbols', []):
            if s['symbol'] == symbol:
                for f in s.get('filters', []):
                    if f['filterType'] == 'LOT_SIZE':
                        step = float(f['stepSize'])
                        _contract_precisions[symbol] = step
                        return step
    except Exception as e:
        print(f"⚠️ 讀取 {symbol} LOT_SIZE 失敗: {e}")
    return 0.001  # 預設

def round_step(qty, step):
    precision = int(round(-__import__('math').log10(step)))
    return round(round(qty / step) * step, precision)

# 設定 CORS，允許 Vue 前端跨網域存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中，應指定具體的前端網址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Binance Client
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
use_testnet = os.getenv("USE_TESTNET", "True").lower() in ("true", "1", "yes")

if api_key and api_key != "your_api_key_here":
    print(f"🔑 API 金鑰已載入: {api_key[:6]}...{api_key[-6:]} (使用測試網: {use_testnet})")
    client = Client(api_key, api_secret, testnet=use_testnet)
else:
    print("⚠️ 未偵測到有效的 API 金鑰，將以唯讀模式啟動。")
    client = Client(testnet=use_testnet)


# 系統日誌儲存
system_logs = collections.deque(maxlen=100)

# Binance API 速率限制 (每分鐘最多 1200 次 request weight)
last_api_call = 0
API_RATE_LIMIT = 1.0  # 每次呼叫至少間隔 1 秒

def rate_limited_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global last_api_call
        elapsed = time.time() - last_api_call
        if elapsed < API_RATE_LIMIT:
            time.sleep(API_RATE_LIMIT - elapsed)
        last_api_call = time.time()
        return func(*args, **kwargs)
    return wrapper

# 雷達掃描冷卻 (手動掃描至少間隔 10 秒)
last_radar_scan = 0
RADAR_SCAN_COOLDOWN = 10.0
radar_lock = threading.Lock()

KNOWN_QUOTES = ["USDT", "BUSD", "BNB", "BTC", "ETH", "USDC"]

def parse_symbol(symbol: str):
    s = symbol.upper()
    for q in KNOWN_QUOTES:
        if s.endswith(q):
            return s[:-len(q)], q
    return s[:-4] if len(s) > 4 else s, s[-4:] if len(s) > 4 else s

def paper_key(symbol: str) -> str:
    """將交易所格式 (BNBUSDT) 轉換為 paper_state 的 key (BNB:USDT)"""
    base, quote = parse_symbol(symbol.upper())
    return f"{base}:{quote}"

def add_system_log(text: str, level: str = "info"):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    system_logs.append({"time": now, "text": text, "level": level})

# 模擬交易機器人狀態
bot_status = {
    "is_running": False,
    "strategy": "Sniper Mode",
    "balance_quote": 150.0,
    "active_orders": 0,
    "active_symbol": "SOLUSDT",
    "regime": "猴市 (區間震盪)",
    "trade_amount": 150.0,
}

bot_process = None

def read_bot_output(proc):
    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if line:
            if line.startswith("@@REGIME@@"):
                bot_status["regime"] = line.replace("@@REGIME@@", "").strip()
            elif line.startswith("@@AMOUNT@@"):
                try:
                    bot_status["trade_amount"] = float(line.replace("@@AMOUNT@@", "").strip())
                except:
                    pass
            else:
                add_system_log(f"[{bot_status.get('active_symbol', '')}] {line}", "info")
    proc.stdout.close()
    proc.wait()
    if proc.returncode == 2:
        # 觸發全自動雷達換倉機制
        threading.Thread(target=auto_radar_switch, daemon=True).start()
    elif bot_status["is_running"]:
        # 非預期停止（使用者未手動關閉），啟動守護重啟機制
        add_system_log("⚠️ [系統守護] 偵測到機器人意外停止，將在 5 秒後自動重啟...", "danger")
        def daemon_restart():
            time.sleep(5)
            if bot_status["is_running"]:
                global bot_process
                symbol = bot_status.get("active_symbol", "SOLUSDT")
                trade_amt = bot_status.get("trade_amount", 10.0)
                sym = symbol.replace("USDT", "/USDT")
                if "/USDT" not in sym:
                    sym = symbol + "/USDT"
                cmd = [sys.executable, "-u", "futures_bot.py", "--symbol", sym, "--amount", str(trade_amt)]
                bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
                add_system_log(f"🔄 [系統守護] 已成功自動重啟機器人 ({sym})", "success")
        threading.Thread(target=daemon_restart, daemon=True).start()

def auto_radar_switch(force_start=False):
    global bot_process, last_api_call
    if not radar_lock.acquire(blocking=False):
        add_system_log("⚠️ [雷達掃描] 前一次掃描尚未完成，跳過", "warning")
        return bot_status.get("active_symbol")
    try:
        add_system_log("🔥 [雷達切換] 當前幣種已冷卻，啟動全自動尋標機制...", "warning")
        targets = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'SUIUSDT', 'XRPUSDT', 
            '1000PEPEUSDT', 'DOGEUSDT', 'WIFUSDT', '1000SHIBUSDT', 'ORDIUSDT', 
            'AVAXUSDT', 'OPUSDT', 'HYPEUSDT', 'LABUSDT', 'ZECUSDT',
            'MRVLUSDT', 'NVDAUSDT', 'HOMEUSDT', 'WLDUSDT', 'HUSDT', 'NEARUSDT', 'XLMUSDT'
        ]
        elapsed = time.time() - last_api_call
        if elapsed < API_RATE_LIMIT:
            time.sleep(API_RATE_LIMIT - elapsed)
        last_api_call = time.time()
        import concurrent.futures

        def get_1h_volatility(sym):
            try:
                # 抓取最近 1 小時 (4根15分K)
                klines = client.futures_klines(symbol=sym, interval='15m', limit=4)
                if not klines:
                    return sym, 0
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                vols = [float(k[7]) for k in klines] # 1小時的總 USDT 交易量
                
                h = max(highs)
                l = min(lows)
                q_vol = sum(vols)
                
                # 至少要有 100 萬美金的 1 小時交易量，才算有熱度
                if l > 0 and q_vol > 1_000_000:
                    volatility = ((h - l) / l) * 100
                    return sym, volatility
            except:
                pass
            return sym, 0

        best_symbol = None
        max_vol = -1.0
        current_sym = bot_status.get("active_symbol")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(get_1h_volatility, targets)
            
        for sym, vol in results:
            if vol > max_vol:
                max_vol = vol
                best_symbol = sym

        if not best_symbol:
            add_system_log("⚠️ [雷達掃描] 所有目標幣種皆無數據", "warning")
            return current_sym

        # 如果最佳幣種就是當前幣種
        if best_symbol == current_sym:
            add_system_log(f"✅ [雷達掃描] 當前 {best_symbol} 仍是最熱門 (24h震幅: {max_vol}%)，維持不變", "success")
            # force_start 但已在正確幣種 → 若 bot 沒在跑則啟動
            if force_start and not bot_status.get("is_running"):
                sym_for_bot = best_symbol.replace("USDT", "/USDT")
                if "/USDT" not in sym_for_bot:
                    sym_for_bot = best_symbol + "/USDT"
                trade_amt = bot_status.get("trade_amount", 10.0)
                cmd = [sys.executable, "-u", "futures_bot.py", "--symbol", sym_for_bot, "--amount", str(trade_amt)]
                bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
                bot_status["is_running"] = True
                add_system_log(f"🚀 已啟動獨立機器人 ({sym_for_bot}, 金額: {trade_amt})", "success")
            return best_symbol

        # 找到更優幣種，切換過去
        add_system_log(f"🎯 [雷達鎖定] 發現最熱門目標: {best_symbol} (24h震幅: {max_vol}%)", "success")
        bot_status["active_symbol"] = best_symbol
        
        if bot_status.get("is_running") or force_start:
            if bot_process:
                try:
                    bot_process.terminate()
                    bot_process.wait(timeout=2)
                except:
                    bot_process.kill()
            sym_for_bot = best_symbol.replace("USDT", "/USDT")
            if "/USDT" not in sym_for_bot:
                sym_for_bot = best_symbol + "/USDT"
            trade_amt = bot_status.get("trade_amount", 10.0)
            cmd = [sys.executable, "-u", "futures_bot.py", "--symbol", sym_for_bot, "--amount", str(trade_amt)]
            bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
            bot_status["is_running"] = True
            add_system_log(f"🚀 已啟動獨立機器人 ({sym_for_bot}, 金額: {trade_amt})", "success")
        return best_symbol
    except Exception as e:
        add_system_log(f"🚨 [雷達掃描] 掃描失敗: {e}", "danger")
        if not bot_status.get("is_running") and not force_start:
            bot_status["is_running"] = False
        return bot_status.get("active_symbol")
    finally:
        radar_lock.release()

@app.get("/api/radar/scan")
def api_radar_scan():
    """手動觸發雷達掃描，找出當前波動最大的幣種並自動切換過去"""
    global last_radar_scan
    elapsed = time.time() - last_radar_scan
    if elapsed < RADAR_SCAN_COOLDOWN:
        return {"status": "success", "best_symbol": bot_status.get("active_symbol"), "cooldown": round(RADAR_SCAN_COOLDOWN - elapsed, 1)}
    last_radar_scan = time.time()
    try:
        best = auto_radar_switch(force_start=True)
        return {"status": "success", "best_symbol": best}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

MAX_TOTAL_INVEST_USDT = 80.0  # 總投資金額上限 (約 2500 TWD)
FEE_RATE = 0.001  # Binance 現貨手續費 0.1%

# 交易歷史快取與冷卻時間設定
KLINE_INTERVAL = '1m'
KLINE_LIMIT = 30
price_histories = {}
total_invested = {}
COOLDOWN_SECONDS = 30
last_trade_time = {}
initial_bought = set()

@app.on_event("startup")
async def startup_event():
    pass

@app.get("/")
def read_root():
    response = FileResponse("index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/api/bot-status")
def get_bot_status():
    """獲取機器人運行狀態"""
    is_paper_trading = not api_key or api_key == "your_api_key_here"
    if not is_paper_trading:
        try:
            symbol = bot_status.get("active_symbol", "SOLUSDT")
            _, quote_asset = parse_symbol(symbol)
            account = client.futures_account()
            balances = account["balances"]
            for b in balances:
                if b["asset"] == quote_asset:
                    bot_status["balance_quote"] = float(b["free"])
                    break
        except Exception as e:
            print(f"讀取實際餘額失敗: {e}")
    else:
        import os, json
        if os.path.exists("paper_state.json"):
            try:
                with open("paper_state.json", "r") as f:
                    state = json.load(f)
                    bot_status["balance_quote"] = float(state.get("balance_usdt", 150.0))
            except:
                pass
    return bot_status


@app.post("/api/bot-status/toggle")
def toggle_bot():
    global bot_process
    bot_status["is_running"] = not bot_status["is_running"]
    status_str = "啟動" if bot_status["is_running"] else "停止"
    add_system_log(f"手動{status_str}機器人", "info")
    
    if bot_status["is_running"]:
        symbol = bot_status.get("active_symbol", "SOLUSDT")
        trade_amt = bot_status.get("trade_amount", 10.0)
        # 轉換為 CCXT 格式, 例如 SOLUSDT -> SOL/USDT, BTCUSDT -> BTC/USDT
        sym = symbol.replace("USDT", "/USDT")
        if "/USDT" not in sym:
            sym = symbol + "/USDT" # fallback
            
        cmd = [sys.executable, "-u", "futures_bot.py", "--symbol", sym, "--amount", str(trade_amt)]
        bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
        add_system_log(f"🚀 已在背景啟動獨立機器人 ({sym}, 金額: {trade_amt})", "success")
    else:
        if bot_process:
            bot_process.terminate()
            bot_process = None
            add_system_log("🛑 已終止背景機器人", "warning")

    return {"status": "success", "is_running": bot_status["is_running"]}

@app.get("/api/logs")
def get_logs():
    """獲取系統日誌"""
    return list(system_logs)

@app.post("/api/bot-status/set-symbol/{symbol}")
def set_bot_symbol(symbol: str):
    """設定當前機器人自動交易的幣種"""
    global bot_process
    old_symbol = bot_status.get("active_symbol", "")
    bot_status["active_symbol"] = symbol.upper()
    
    # 防止重複觸發 (雷達已切換過)
    if old_symbol == symbol.upper():
        return {"status": "success", "active_symbol": bot_status["active_symbol"]}
    _, quote_asset = parse_symbol(symbol)
    amt = bot_status.get("trade_amount", 0.02)
    bot_status["strategy"] = f"MA Deviation ({amt} {quote_asset})"
    add_system_log(f"🎯 自動交易監聽目標切換為: {symbol.upper()}", "info")
    
    # 如果機器人正在執行，則重新啟動機器人以套用新幣種
    if bot_status.get("is_running"):
        if bot_process:
            try:
                bot_process.terminate()
                bot_process.wait(timeout=2)
            except:
                bot_process.kill()
        
        trade_amt = bot_status.get("trade_amount", 10.0)
        sym_for_bot = symbol.upper().replace("USDT", "/USDT")
        if "/USDT" not in sym_for_bot:
            sym_for_bot = symbol.upper() + "/USDT"
            
        import sys
        import threading
        cmd = [sys.executable, "-u", "futures_bot.py", "--symbol", sym_for_bot, "--amount", str(trade_amt)]
        bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
        add_system_log(f"♻️ 已自動重啟機器人切換至 ({sym_for_bot}, 金額: {trade_amt})", "success")
        
    return {"status": "success", "active_symbol": bot_status["active_symbol"]}

@app.post("/api/bot-status/set-amount/{amount}")
def set_bot_amount(amount: float):
    """設定當前機器人自動交易的單筆數量"""
    if amount < 0 or amount > 1000:
        raise HTTPException(status_code=400, detail="單次交易數量必須限制在 0 至 50 之間")
    bot_status["trade_amount"] = amount
    symbol = bot_status.get("active_symbol", "SOLUSDT")
    base_asset, _ = parse_symbol(symbol)
    bot_status["strategy"] = f"MA Deviation ({amount} {base_asset})"
    add_system_log(f"⚙️ 自動交易單次數量設定為: {amount} {base_asset}", "info")
    return {"status": "success", "trade_amount": bot_status["trade_amount"]}

@app.post("/api/order/market-buy/{symbol}")
def market_buy(symbol: str, amount: float = 150.0):
    """執行市價買入訂單"""
    is_paper_trading = not api_key or api_key == "your_api_key_here"
    if is_paper_trading:
        try:
            from update_paper_state import update_paper_state
            ticker = client.futures_symbol_ticker(symbol=symbol.upper())
            price = float(ticker['price'])
            qty = amount / price
            
            # 使用 update_paper_state 更新虛擬帳本
            active_sym = f"{symbol.upper().replace('USDT', '')}:USDT"
            if ":USDT:USDT" in active_sym:
                active_sym = active_sym.replace(":USDT:USDT", ":USDT")
            update_paper_state(active_sym, "buy", price, qty)
            
            # 重啟機器人以清除記憶體中的孤兒倉位
            global bot_process
            if bot_process:
                bot_process.terminate()
                bot_process = None
                add_system_log("♻️ 已手動加倉並自動重啟機器人...", "warning")
                import subprocess, sys
                sym = symbol.replace("USDT", "/USDT")
                bot_process = subprocess.Popen([
                    sys.executable, "-u", "futures_bot.py",
                    "--symbol", sym,
                    "--amount", str(bot_status.get("trade_amount", 30.0))
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
                
            order = {"orderId": "manual_paper", "executedQty": str(qty)}
            return {"status": "success", "order": order}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"模擬買入失敗: {str(e)}")
            
    if not api_key or api_key == "your_api_key_here":
        raise HTTPException(status_code=400, detail="請先在 .env 設定 API 金鑰才能下單")
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol_upper)
        price = float(ticker['price'])
        qty = amount / price
        step = get_contract_step(symbol_upper)
        qty_str = str(round_step(qty, step))

        if symbol_upper == 'USDCUSDT':
            order = client.futures_create_order(
                symbol=symbol_upper,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce='GTC',
                price='0.9999',
                quantity=qty_str
            )
        else:
            order = client.futures_create_order(
                symbol=symbol_upper,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quantity=qty_str
            )
        return {"status": "success", "order": order}
    except BinanceAPIException as e:
        raise HTTPException(status_code=400, detail=f"幣安下單失敗: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")

@app.post("/api/order/market-short/{symbol}")
def market_short(symbol: str, amount: float = 150.0):
    """執行市價做空訂單"""
    is_paper_trading = not api_key or api_key == "your_api_key_here"
    if is_paper_trading:
        try:
            from update_paper_state import update_paper_state
            ticker = client.futures_symbol_ticker(symbol=symbol.upper())
            price = float(ticker['price'])
            qty = amount / price
            
            # 使用 update_paper_state 更新虛擬帳本
            active_sym = f"{symbol.upper().replace('USDT', '')}:USDT"
            if ":USDT:USDT" in active_sym:
                active_sym = active_sym.replace(":USDT:USDT", ":USDT")
            update_paper_state(active_sym, "sell", price, qty)
            
            # 重啟機器人以清除記憶體中的孤兒倉位
            global bot_process
            if bot_process:
                bot_process.terminate()
                bot_process = None
                add_system_log("♻️ 已手動加倉並自動重啟機器人...", "warning")
                import subprocess, sys
                sym = symbol.replace("USDT", "/USDT")
                bot_process = subprocess.Popen([
                    sys.executable, "-u", "futures_bot.py",
                    "--symbol", sym,
                    "--amount", str(bot_status.get("trade_amount", 30.0))
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
                
            order = {"orderId": "manual_paper", "executedQty": str(qty)}
            return {"status": "success", "order": order}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"模擬做空失敗: {str(e)}")
            
    if not api_key or api_key == "your_api_key_here":
        raise HTTPException(status_code=400, detail="請先在 .env 設定 API 金鑰才能手動開倉")
    try:
        symbol_upper = symbol.upper()
        ticker = client.futures_symbol_ticker(symbol=symbol_upper)
        price = float(ticker['price'])
        qty = amount / price
        
        step = get_contract_step(symbol_upper)
        qty_str = str(round_step(qty, step))

        order = client.futures_create_order(
            symbol=symbol_upper,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=qty_str
        )
        return {"status": "success", "order": order}
    except BinanceAPIException as e:
        raise HTTPException(status_code=400, detail=f"幣安做空失敗: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")

@app.post("/api/order/market-sell/{symbol}")
def market_sell(symbol: str):
    """執行市價平倉 (平掉所有多單或空單)"""
    is_paper_trading = not api_key or api_key == "your_api_key_here"
    if is_paper_trading:
        # Paper Trading 手動平倉邏輯
        try:
            import json, os
            from update_paper_state import update_paper_state
            paper_state_file = "paper_state.json"
            if os.path.exists(paper_state_file):
                with open(paper_state_file, "r") as f:
                    state = json.load(f)
                
                sym = symbol.upper()
                positions = state.get("positions", {})
                
                pk = paper_key(sym)
                active_sym = pk
                pos = positions.get(pk)
                if pos is None:
                    pos = positions.get(f"{sym}:USDT") or positions.get(sym) or {}
                    if pos:
                        active_sym = f"{sym}:USDT" if positions.get(f"{sym}:USDT") else sym
                    
                qty = float(pos.get("qty", 0.0))
                
                if abs(qty) > 0:
                    # 取得目前價格
                    ticker = client.futures_symbol_ticker(symbol=symbol.upper())
                    current_price = float(ticker["price"])
                    avg_price = float(pos.get("avg_price", 0.0))
                    
                    # 計算 PnL
                    pnl = (current_price - avg_price) * qty
                    close_side = "sell" if qty > 0 else "buy"
                    
                    # 更新虛擬帳本
                    update_paper_state(active_sym, close_side, current_price, abs(qty), is_close=True, pnl=pnl)
                    
                    # 重啟機器人以清除記憶體中的孤兒倉位
                    global bot_process
                    if bot_process:
                        bot_process.terminate()
                        bot_process = None
                        add_system_log("♻️ 已重置虛擬倉位並自動重啟機器人...", "warning")
                        # 重新啟動
                        import subprocess, sys
                        sym = symbol.replace("USDT", "/USDT")
                        bot_process = subprocess.Popen([
                            sys.executable, "-u", "futures_bot.py",
                            "--symbol", sym,
                            "--amount", str(bot_status.get("trade_amount", 30.0))
                        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        threading.Thread(target=read_bot_output, args=(bot_process,), daemon=True).start()
                        
                    return {"status": "success", "detail": f"模擬平倉成功！獲利 {pnl:.2f} USDT"}
            return {"status": "error", "detail": "找不到虛擬倉位"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"模擬平倉失敗: {str(e)}")
            
    if not api_key or api_key == "your_api_key_here":
        raise HTTPException(status_code=400, detail="請先在 .env 設定 API 金鑰才能下單")
    try:
        symbol_upper = symbol.upper()
        account = client.futures_account()
        pos_list = [b for b in account["balances"] if b["asset"] == symbol_upper.replace("USDT","")]
        if not pos_list:
            raise HTTPException(status_code=400, detail="找不到合約倉位資訊")
            
        qty = float(pos_list[0]['free'])
        if qty == 0:
            raise HTTPException(status_code=400, detail="當前無合約倉位可平倉")

        side = Client.SIDE_SELL if qty > 0 else Client.SIDE_BUY
        step = get_contract_step(symbol_upper)
        qty_str = str(round_step(abs(qty), step))
        
        if symbol_upper == 'USDCUSDT':
            order = client.futures_create_order(
                symbol=symbol_upper,
                side=side,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce='GTC',
                price='1.0000',
                quantity=qty_str
            )
        else:
            order = client.futures_create_order(
                symbol=symbol_upper,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=abs(qty)
            )
        return {"status": "success", "order": order}
    except BinanceAPIException as e:
        raise HTTPException(status_code=400, detail=f"幣安下單失敗: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")


@app.get("/api/price/{symbol}")
def get_price(symbol: str):
    """獲取指定交易對的即時價格"""
    try:
        symbol_upper = symbol.upper()
        ticker = client.futures_symbol_ticker(symbol=symbol_upper)
        return {
            "symbol": symbol_upper,
            "price": float(ticker["price"]),
            "timestamp": ticker.get("time")  # 毫秒時間戳
        }
    except BinanceAPIException as e:
        raise HTTPException(status_code=400, detail=f"幣安 API 錯誤: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")

@app.get("/api/prices")
def get_all_prices():
    """一次獲取所有合約交易對的即時價格"""
    try:
        tickers = client.futures_ticker()
        prices = {}
        for t in tickers:
            prices[t['symbol']] = float(t.get('lastPrice', 0))
        return {"status": "success", "data": prices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/exchangerate/usdtwd")
def get_usd_twd():
    """獲取最新的 USD 到 TWD 匯率"""
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates", {})
        twd_rate = rates.get("TWD")
        if not twd_rate:
            raise HTTPException(status_code=502, detail="未能獲取到 TWD 匯率")
        return {"base": "USD", "target": "TWD", "rate": twd_rate}
    except Exception as e:
        return {"base": "USD", "target": "TWD", "rate": 32.50, "warning": f"API 獲取失敗，使用預設值。錯誤: {str(e)}"}

@app.get("/api/position/{symbol}")
def get_position(symbol: str):
    """獲取指定幣種的持倉數量、平均成本與未實現/已實現盈虧"""
    if not api_key or api_key == "your_api_key_here":
        import os
        import json
        paper_state_file = "paper_state.json"
        qty = 0.0
        avg_price = 0.0
        realized_pnl = 0.0
        
        if os.path.exists(paper_state_file):
            try:
                with open(paper_state_file, "r") as f:
                    state = json.load(f)
                
                sym = symbol.upper()
                positions = state.get("positions", {})
                
                # 用統一格式查 paper_state key (BNBUSDT → BNB:USDT)
                pk = paper_key(sym)
                pos = positions.get(pk)
                if pos is None:
                    pos = positions.get(f"{sym}:USDT") or positions.get(sym) or {}
                
                qty = float(pos.get("qty", 0.0))
                avg_price = float(pos.get("avg_price", 0.0))
                realized_pnl = float(pos.get("realized_pnl", 0.0))
            except:
                pass

        current_price = 0.0
        try:
            ticker = client.futures_symbol_ticker(symbol=symbol.upper())
            current_price = float(ticker["price"])
        except:
            pass

        unrealized_pnl = 0.0
        if qty > 0:
            unrealized_pnl = (current_price - avg_price) * abs(qty)
        elif qty < 0:
            unrealized_pnl = (avg_price - current_price) * abs(qty)

        total_cost = abs(qty) * avg_price
        current_value = abs(qty) * current_price
        pnl_percent = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

        base_asset, quote_asset = parse_symbol(symbol.upper())
        return {
            "asset": base_asset,
            "quote_asset": quote_asset,
            "qty": qty,
            "avg_price": avg_price,
            "total_cost": total_cost,
            "current_price": current_price,
            "current_value": current_value,
            "pnl": unrealized_pnl,
            "pnl_percent": pnl_percent,
            "realized_pnl": realized_pnl
        }
    try:
        symbol_upper = symbol.upper()
        base_asset, quote_asset = parse_symbol(symbol_upper)
        
        account = client.futures_account()
        pos_list = [b for b in account["balances"] if b["asset"] == symbol_upper.replace("USDT","")]
        if not pos_list:
            raise Exception("No position data returned")
            
        pos = pos_list[0]
        qty = float(pos['positionAmt'])
        unrealized_pnl = float(pos['unRealizedProfit'])
        entry_price = float(pos['entryPrice'])
        mark_price = float(pos['markPrice'])
        
        abs_qty = abs(qty)
        total_cost = abs_qty * entry_price
        current_value = abs_qty * mark_price
        pnl_percent = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
        
        return {
            "asset": base_asset,
            "quote_asset": quote_asset,
            "qty": qty,  # 保留正負號以辨識多空
            "avg_price": entry_price,
            "total_cost": total_cost,
            "current_price": mark_price,
            "current_value": current_value,
            "pnl": unrealized_pnl,
            "pnl_percent": pnl_percent,
            "realized_pnl": 0.0 # 合約前端暫不依賴此欄位
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取持倉狀態失敗: {str(e)}")

@app.get("/api/trades/{symbol}")
def get_trades(symbol: str):
    """獲取指定幣種的最新交易成交歷史並計算盈虧"""
    if not api_key or api_key == "your_api_key_here":
        import os
        import json
        paper_state_file = "paper_state.json"
        if os.path.exists(paper_state_file):
            try:
                with open(paper_state_file, "r") as f:
                    state = json.load(f)
                    trades = state.get("trades", [])
                    symbol_trades = [t for t in trades if t.get("symbol") in (symbol.upper(), paper_key(symbol))]
                    return list(reversed(symbol_trades))[:15]
            except:
                return []
        return []
    try:
        symbol_upper = symbol.upper()
        trades = client.futures_account_trades(symbol=symbol_upper, limit=15)
        
        formatted_trades = []
        for t in reversed(trades):
            price = float(t["price"])
            qty = float(t["qty"])
            is_buyer = (t["side"] == "BUY")
            realized_pnl = float(t.get("realizedPnl", 0.0))
            
            timestamp = t.get("time") / 1000.0
            formatted_trades.append({
                "id": t.get("id"),
                "order_id": t.get("orderId"),
                "price": price,
                "qty": qty,
                "quote_qty": float(t.get("quoteQty", price * qty)),
                "time": timestamp,
                "is_buyer": is_buyer,
                "pnl": realized_pnl if realized_pnl != 0 else None
            })
            
        return formatted_trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取交易紀錄失敗: {str(e)}")

@app.get("/api/klines/{symbol}")
def get_klines(symbol: str, interval: str = "1m", limit: int = 60):
    """獲取 K 線數據 (OHLCV)"""
    try:
        symbol_upper = symbol.upper()
        klines = client.futures_klines(symbol=symbol_upper, interval=interval, limit=limit)
        result = []
        for k in klines:
            result.append({
                "time": k[0] / 1000,        # 開盤時間 (秒)
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),       # 成交量
                "quote_volume": float(k[7]), # 計價貨幣成交量 (USDT)
                "trades": int(k[8]),         # 成交筆數
            })
        return result
    except BinanceAPIException as e:
        raise HTTPException(status_code=400, detail=f"幣安 API 錯誤: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")

if __name__ == "__main__":
    # 啟動 Uvicorn 伺服器，直接在 8081 埠口執行（同時提供靜態網頁與 API，省去多個埠口的防火牆問題）
    uvicorn.run(app, host="0.0.0.0", port=8081)

@app.post("/api/order/cancel-all/{symbol}")
def cancel_all_orders(symbol: str):
    try:
        if PAPER_TRADING:
            return {"status": "success", "msg": "模擬交易不支援撤單"}
        symbol_upper = symbol.upper()
        res = client.futures_cancel_all_open_orders(symbol=symbol_upper)
        add_system_log(f"🗑️ 已手動撤銷 {symbol_upper} 所有掛單", "warning")
        return {"status": "success", "msg": "所有掛單已撤銷", "data": res}
    except Exception as e:
        add_system_log(f"撤單失敗: {str(e)}", "danger")
        raise HTTPException(status_code=400, detail=str(e))
