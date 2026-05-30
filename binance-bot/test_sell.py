import requests
res = requests.post('http://127.0.0.1:8081/api/order/market-sell/XRPUSDT')
print(res.status_code)
print(res.text)
