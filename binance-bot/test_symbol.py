from binance.client import Client
client = Client(testnet=True)
info = client.get_exchange_info()
symbols = [s['symbol'] for s in info['symbols']]
print("PEPEUSDT in testnet:", "PEPEUSDT" in symbols)
print("BTCUSDT in testnet:", "BTCUSDT" in symbols)
