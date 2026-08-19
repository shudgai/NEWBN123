import csv
import json
import secrets
import threading
from datetime import date
from io import StringIO
from urllib.parse import urlparse

from flask import Flask, Response, abort, jsonify, render_template, request

from src.config import (
    MAX_POSITION_VALUE_USDT,
    PAPER_BALANCE_USDT,
    PAPER_FEE_RATE,
    STATUS_FILE,
    TRADING_SYMBOL,
)
from src.main import TradingBot, save_status

app = Flask(__name__)
CONTROL_TOKEN = secrets.token_urlsafe(32)


def empty_position(side):
    return {
        "symbol": TRADING_SYMBOL,
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


def empty_status():
    return {
        "balance": PAPER_BALANCE_USDT,
        "current_price": None,
        "signal_timeframe": "1m",
        "max_position_value": MAX_POSITION_VALUE_USDT,
        "fee_rate": PAPER_FEE_RATE,
        "total_realized_pnl": 0.0,
        "symbol": TRADING_SYMBOL,
        "positions": {
            "long": empty_position("long"),
            "short": empty_position("short"),
        },
        "rsi": None,
        "low_volatility_protection": False,
        "mode": "paper",
        "running": False,
        "error": None,
    }


class BotManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.bot = TradingBot()
        self.thread = None
        self.stop_event = None
        self.bot.current_status["running"] = False
        save_status(self.bot.current_status)

    def start(self):
        with self.lock:
            already_running = bool(
                self.thread and self.thread.is_alive()
            )
            if not already_running:
                self.stop_event = threading.Event()
                self.bot.current_status["running"] = True
                self.bot.current_status["error"] = None
                save_status(self.bot.current_status)
                self.thread = threading.Thread(
                    target=self._run,
                    name="btc-paper-bot",
                    daemon=True,
                )
                self.thread.start()
        return self.status()

    def _run(self):
        try:
            self.bot.run(self.stop_event)
        except Exception as exc:
            self.bot.set_error(exc)

    def stop(self):
        with self.lock:
            thread = self.thread
            stop_event = self.stop_event
        if thread and thread.is_alive() and stop_event:
            stop_event.set()
            thread.join(timeout=10)
        return self.status()

    def close_position(self, position_side):
        if position_side not in {"long", "short"}:
            raise ValueError("position_side must be long or short")
        closed = self.bot.manual_close(position_side)
        return closed, self.status()

    def open_position(self, position_side):
        if position_side not in {"long", "short"}:
            raise ValueError("position_side must be long or short")
        opened = self.bot.manual_open(position_side)
        return opened, self.status()

    def status(self):
        with self.bot.lock:
            return dict(self.bot.current_status)

    def history(self, trade_date=None):
        with self.bot.lock:
            return self.bot.executor.get_trade_history(trade_date)


manager = BotManager()


def require_control_token():
    supplied_token = request.headers.get("X-Control-Token")
    if supplied_token == CONTROL_TOKEN:
        return

    referrer = request.referrer
    if (
        supplied_token
        and referrer
        and urlparse(referrer).netloc == request.host
    ):
        return
    abort(403)


def validate_date(value):
    if not value:
        return None
    date.fromisoformat(value)
    return value


@app.route("/")
def index():
    return render_template("index.html", control_token=CONTROL_TOKEN)


@app.get("/api/status")
def api_status():
    return jsonify(manager.status())


@app.get("/api/history")
def api_history():
    require_control_token()
    try:
        trade_date = validate_date(request.args.get("date"))
        return jsonify({"ok": True, "trades": manager.history(trade_date)})
    except ValueError:
        return jsonify({"ok": False, "error": "日期格式必須為 YYYY-MM-DD。"}), 400


@app.get("/api/history/download")
def api_history_download():
    require_control_token()
    try:
        trade_date = validate_date(request.args.get("date"))
    except ValueError:
        return jsonify({"ok": False, "error": "日期格式必須為 YYYY-MM-DD。"}), 400

    output = StringIO()
    fields = [
        "closed_at",
        "opened_at",
        "symbol",
        "side",
        "leverage",
        "exit_reason",
        "quantity",
        "entry_price",
        "exit_price",
        "trade_value",
        "gross_pnl",
        "entry_fee",
        "exit_fee",
        "total_fees",
        "net_realized_pnl",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(manager.history(trade_date))
    filename_date = trade_date or "all"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename=btc-paper-trades-{filename_date}.csv"
            )
        },
    )


@app.post("/api/bot")
def api_bot():
    require_control_token()
    action = (request.get_json(silent=True) or {}).get("action")
    try:
        if action == "start":
            status = manager.start()
        elif action == "stop":
            status = manager.stop()
        else:
            return jsonify({"ok": False, "error": "不支援的操作。"}), 400
        return jsonify({"ok": True, "status": status})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/position/close")
def api_close_position():
    require_control_token()
    position_side = (request.get_json(silent=True) or {}).get("side")
    try:
        closed, status = manager.close_position(position_side)
        side_name = "多單" if position_side == "long" else "空單"
        message = (
            f"{side_name}平倉完成。"
            if closed
            else f"目前沒有 BTC {side_name}。"
        )
        return jsonify({
            "ok": True,
            "closed": bool(closed),
            "message": message,
            "status": status,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/position/open")
def api_open_position():
    require_control_token()
    position_side = (request.get_json(silent=True) or {}).get("side")
    try:
        opened, status = manager.open_position(position_side)
        side_name = "多單" if position_side == "long" else "空單"
        message = (
            f"{side_name}開倉完成。"
            if opened
            else "已有 BTC 持倉，不重複開倉。"
        )
        return jsonify({
            "ok": True,
            "opened": bool(opened),
            "message": message,
            "status": status,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8005, debug=False, threaded=True)
