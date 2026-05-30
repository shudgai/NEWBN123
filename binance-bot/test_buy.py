import os
from dotenv import load_dotenv
load_dotenv()
from binance.client import Client
from binance.exceptions import BinanceAPIException
client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'), testnet=True)
try:
    order = client.create_order(
        symbol='XRPUSDT',
        side=Client.SIDE_BUY,
        type=Client.ORDER_TYPE_MARKET,
        quoteOrderQty=10.0
    )
    print("Success:", order)
except BinanceAPIException as e:
    print("Error:", e)
