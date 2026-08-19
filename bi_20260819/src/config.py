import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
PAPER_ONLY = os.getenv("PAPER_ONLY", "true").lower() not in {"0", "false", "no"}
DRY_RUN = True if PAPER_ONLY else (
    os.getenv("DRY_RUN", "true").lower() not in {"0", "false", "no"}
)
HEDGE_MODE = True
PAPER_BALANCE_USDT = float(os.getenv("PAPER_BALANCE_USDT", "150"))
PAPER_LEVERAGE = float(os.getenv("PAPER_LEVERAGE", "5"))
PAPER_FEE_RATE = float(os.getenv("PAPER_FEE_RATE", "0.0005"))
TARGET_PERCENTAGE = float(os.getenv("TARGET_PERCENTAGE", "0.50"))
MAX_POSITION_VALUE_USDT = float(os.getenv("MAX_POSITION_VALUE_USDT", "75"))
MAX_CANDLE_RANGE_ATR = float(os.getenv("MAX_CANDLE_RANGE_ATR", "3.0"))
MAX_CLOSE_MOVE_ATR = float(os.getenv("MAX_CLOSE_MOVE_ATR", "3.0"))
MIN_ENTRY_ATR_PCT = float(os.getenv("MIN_ENTRY_ATR_PCT", "0.03"))
MIN_MA7_TURN_ATR_RATIO = float(
    os.getenv("MIN_MA7_TURN_ATR_RATIO", "0.05")
)
MAX_ENTRY_PRICE_DEVIATION_PCT = float(
    os.getenv("MAX_ENTRY_PRICE_DEVIATION_PCT", "0.5")
)
SIGNAL_TIMEFRAME = os.getenv("SIGNAL_TIMEFRAME", "1m").strip()
LOOP_INTERVAL_SECONDS = int(os.getenv("LOOP_INTERVAL_SECONDS", "10"))
TRAILING_TP_ACTIVATION_PCT = float(
    os.getenv("TRAILING_TP_ACTIVATION_PCT", "0.25")
)
TRAILING_TP_DISTANCE_PCT = float(
    os.getenv("TRAILING_TP_DISTANCE_PCT", "0.10")
)
TRADING_SYMBOL = "BTC/USDT:USDT"
STATUS_FILE = PROJECT_ROOT / "status.json"
PAPER_STATE_FILE = PROJECT_ROOT / "paper_state.json"

if not 0 < TARGET_PERCENTAGE <= 1:
    raise RuntimeError("TARGET_PERCENTAGE must be greater than 0 and at most 1.")
if MAX_POSITION_VALUE_USDT <= 0:
    raise RuntimeError("MAX_POSITION_VALUE_USDT must be greater than 0.")
if MAX_CANDLE_RANGE_ATR <= 0 or MAX_CLOSE_MOVE_ATR <= 0:
    raise RuntimeError("ATR spike thresholds must be greater than 0.")
if MIN_ENTRY_ATR_PCT <= 0 or MIN_MA7_TURN_ATR_RATIO <= 0:
    raise RuntimeError("Minimum entry volatility thresholds must be positive.")
if MAX_ENTRY_PRICE_DEVIATION_PCT <= 0:
    raise RuntimeError("MAX_ENTRY_PRICE_DEVIATION_PCT must be greater than 0.")
if not 0 <= PAPER_FEE_RATE < 1:
    raise RuntimeError("PAPER_FEE_RATE must be at least 0 and less than 1.")
if SIGNAL_TIMEFRAME not in {"1m", "3m", "5m", "15m", "30m", "1h"}:
    raise RuntimeError("SIGNAL_TIMEFRAME is not supported.")
if LOOP_INTERVAL_SECONDS < 1:
    raise RuntimeError("LOOP_INTERVAL_SECONDS must be at least 1.")
if PAPER_LEVERAGE <= 0:
    raise RuntimeError("PAPER_LEVERAGE must be greater than 0.")
if TRAILING_TP_ACTIVATION_PCT <= 0 or TRAILING_TP_DISTANCE_PCT <= 0:
    raise RuntimeError("Trailing take-profit thresholds must be positive.")
