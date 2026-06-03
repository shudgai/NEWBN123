import sys
import time
import threading
import subprocess
from services.system_log_service import add_system_log

# 模擬交易機器人狀態 (支援多幣種多進程)
bot_status = {
    "is_running": False,
    "strategy": "Top 5 Sniper Mode",
    "balance_quote": 150.0,
    "active_orders": 0,
    "active_symbols": [],  # 現在改為陣列存放多個幣種 (主攻幣, 其實現在只支援單一運行)
    "watch_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "PEPEUSDT"], # 使用者自訂的 5 個關注幣種
    "regime": "多幣種監控中",
    "coin_regimes": {},    # { symbol: regime }
    "trade_amount": 150.0,
}

bot_processes = {}  # {symbol: subprocess.Popen}

def get_bot_status():
    from services.paper_trade_service import get_paper_balance
    import subprocess
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    if os.getenv("TRADING_MODE", "paper") == "paper":
        bot_status["balance_quote"] = get_paper_balance()
        
    # Check if any futures_bot.py is running
    try:
        res = subprocess.run(["pgrep", "-f", "futures_bot.py"], capture_output=True)
        bot_status["is_running"] = res.returncode == 0
    except:
        pass
        
    return bot_status

def set_bot_balance_quote(balance: float):
    bot_status["balance_quote"] = balance

def update_bot_status(key, value):
    bot_status[key] = value

def read_bot_output(proc, sym):
    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if line:
            if line.startswith("@@REGIME@@"):
                bot_status["regime"] = line.replace("@@REGIME@@", "").strip()
            elif line.startswith("@@COIN_REGIME@@"):
                parts = line.replace("@@COIN_REGIME@@", "").strip().split("@@")
                if len(parts) >= 2:
                    coin_sym = parts[0]
                    coin_reg = parts[1]
                    bot_status["coin_regimes"][coin_sym] = coin_reg
            elif line.startswith("@@AMOUNT@@"):
                try:
                    bot_status["trade_amount"] = float(line.replace("@@AMOUNT@@", "").strip())
                except:
                    pass
            else:
                add_system_log(f"[{sym}] {line}", "info")
    proc.stdout.close()
    proc.wait()
    
    if proc.returncode == 4:
        # 單幣熔斷停牌 (Exit Code 4)
        from services.radar_service import replace_dead_coin, blacklist_coin
        blacklist_coin(sym, duration_sec=24*3600)
        threading.Thread(target=replace_dead_coin, args=(sym,), daemon=True).start()
    elif proc.returncode == 3:
        # 死水幣觸發淘汰 (Exit Code 3)
        from services.radar_service import replace_dead_coin
        threading.Thread(target=replace_dead_coin, args=(sym,), daemon=True).start()
    elif proc.returncode == 2:
        # 觸發全自動雷達換倉機制 (保留)
        from services.radar_service import auto_radar_switch
        threading.Thread(target=auto_radar_switch, daemon=True).start()
    elif bot_status["is_running"] and sym in bot_processes and bot_processes[sym] == proc:
        # 非預期停止（使用者未手動關閉），啟動守護重啟機制
        add_system_log(f"⚠️ [系統守護] 偵測到機器人({sym})意外停止，將在 5 秒後自動重啟...", "danger")
        def daemon_restart():
            time.sleep(5)
            if bot_status["is_running"] and sym in bot_status.get("active_symbols", []):
                _start_single_bot(sym, bot_status["trade_amount"])
        threading.Thread(target=daemon_restart, daemon=True).start()

def _start_single_bot(symbol: str, trade_amt: float):
    global bot_processes
    sym = symbol.replace("USDT", "/USDT")
    if "/USDT" not in sym:
        sym = symbol + "/USDT"
        
    cmd = [sys.executable, "-u", "futures_bot.py", "--symbol", sym, "--amount", str(trade_amt)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    bot_processes[symbol] = proc
    threading.Thread(target=read_bot_output, args=(proc, symbol), daemon=True).start()
    add_system_log(f"🚀 已啟動獨立機器人 ({sym}, 金額: {trade_amt})", "success")

def start_bot(symbols=None, trade_amt: float = None):
    global bot_processes
    if symbols is None:
        symbols = bot_status.get("active_symbols", [])
    if isinstance(symbols, str):
        symbols = [symbols] # 向後相容單一字串
    if not symbols:
        symbols = ["SOLUSDT"]
        
    if trade_amt is None:
        trade_amt = bot_status.get("trade_amount", 150.0)
        
    bot_status["is_running"] = True
    bot_status["active_symbols"] = symbols
    bot_status["trade_amount"] = trade_amt
    
    # 關閉不在名單內的
    current_running = list(bot_processes.keys())
    for s in current_running:
        if s not in symbols:
            _kill_single_bot(s)
            
    # 啟動名單內的
    for s in symbols:
        if s not in bot_processes or bot_processes[s] is None or bot_processes[s].poll() is not None:
            _start_single_bot(s, trade_amt)

def _kill_single_bot(symbol: str):
    global bot_processes
    if symbol in bot_processes and bot_processes[symbol]:
        proc = bot_processes[symbol]
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()
        bot_processes[symbol] = None
        del bot_processes[symbol]
        add_system_log(f"🛑 已終止背景機器人 ({symbol})", "warning")

def kill_bot():
    global bot_processes
    bot_status["is_running"] = False
    symbols = list(bot_processes.keys())
    for s in symbols:
        _kill_single_bot(s)

def restart_bot():
    kill_bot()
    start_bot()

def toggle_bot():
    is_running = not bot_status["is_running"]
    status_str = "啟動" if is_running else "停止"
    add_system_log(f"手動{status_str}機器人群組", "info")
    
    if is_running:
        start_bot()
    else:
        kill_bot()
    return bot_status["is_running"]

def set_bot_symbol(symbols):
    if isinstance(symbols, str):
        symbols = [symbols.upper()]
    else:
        symbols = [s.upper() for s in symbols]
        
    bot_status["active_symbols"] = symbols
    
    amt = bot_status.get("trade_amount", 150.0)
    bot_status["strategy"] = f"Top 5 Sniper ({amt})"
    add_system_log(f"🎯 自動交易監聽目標切換為: {', '.join(symbols)}", "info")
    
    if bot_status.get("is_running"):
        add_system_log("♻️ 已自動重啟機器人以套用新幣種", "success")
        start_bot(symbols, amt) # start_bot 內會做 diff 啟動/關閉
        
    # 相容舊版回傳
    return symbols[0] if symbols else ""

def set_bot_watch_symbols(symbols):
    if not isinstance(symbols, list):
        symbols = [symbols]
    # 限定 5 隻
    symbols = [s.upper() for s in symbols][:5]
    bot_status["watch_symbols"] = symbols
    add_system_log(f"📋 使用者更新自選關注清單: {', '.join(symbols)}", "info")
    return symbols

def set_bot_amount(amount: float):
    if amount < 0 or amount > 1000:
        raise ValueError("單次交易數量必須限制在 0 至 1000 之間")
    bot_status["trade_amount"] = amount
    bot_status["strategy"] = f"Top 5 Sniper ({amount})"
    add_system_log(f"⚙️ 自動交易單次數量設定為: {amount}", "info")
    return bot_status["trade_amount"]
