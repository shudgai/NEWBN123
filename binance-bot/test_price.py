import asyncio
import ccxt.pro as ccxtpro
from binance.client import Client
import os
from dotenv import load_dotenv

load_dotenv()
async def main():
    exchange = ccxtpro.binance({
        'apiKey': os.getenv('BINANCE_API_KEY') or None,
        'secret': os.getenv('BINANCE_API_SECRET') or None,
        'options': {'defaultType': 'future'}
    })
    ticker = await exchange.fetch_ticker('SUI/USDT')
    print("CCXT Price:", ticker['last'])
    await exchange.close()

    client = Client(os.getenv('BINANCE_API_KEY') or None, os.getenv('BINANCE_API_SECRET') or None)
    ticker_f = client.futures_symbol_ticker(symbol='SUIUSDT')
    print("Binance-Python Price:", ticker_f['price'])

asyncio.run(main())
