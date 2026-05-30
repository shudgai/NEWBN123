import json
import os
import uuid
import time

PAPER_STATE_FILE = "paper_state.json"

def update_paper_state(symbol, side, price, qty, is_close=False, pnl=0.0):
    state = {
        "balance_usdt": 150.0,
        "positions": {},
        "trades": []
    }
    if os.path.exists(PAPER_STATE_FILE):
        try:
            with open(PAPER_STATE_FILE, "r") as f:
                state = json.load(f)
        except:
            pass
            
    pos = state["positions"].get(symbol, {"qty": 0.0, "avg_price": 0.0, "realized_pnl": 0.0})
    
    trade = {
        "id": str(uuid.uuid4())[:8],
        "order_id": str(uuid.uuid4())[:8],
        "symbol": symbol,
        "price": price,
        "qty": qty,
        "quote_qty": price * qty,
        "time": time.time(),
        "is_buyer": (side == 'buy'),
        "pnl": pnl if is_close else None
    }
    state["trades"].append(trade)
    
    # Update position
    current_qty = pos["qty"]
    current_avg = pos["avg_price"]
    
    if side == 'buy':
        signed_qty = qty
    else:
        signed_qty = -qty
        
    if not is_close:
        new_qty = current_qty + signed_qty
        if new_qty != 0:
            if (current_qty >= 0 and signed_qty > 0) or (current_qty <= 0 and signed_qty < 0):
                new_avg = (abs(current_qty) * current_avg + abs(signed_qty) * price) / abs(new_qty)
                pos["avg_price"] = new_avg
        pos["qty"] = new_qty
    else:
        new_qty = current_qty + signed_qty
        if abs(new_qty) < 0.000001:
            new_qty = 0.0
            pos["avg_price"] = 0.0
        pos["qty"] = new_qty
        pos["realized_pnl"] += pnl
        state["balance_usdt"] += pnl
        
    # 統一扣除手續費 (開平倉皆適用 Binance taker fee 0.05%)
    fee = (price * abs(qty)) * 0.0005
    state["balance_usdt"] -= fee

    state["positions"][symbol] = pos
    
    with open(PAPER_STATE_FILE, "w") as f:
        json.dump(state, f)
