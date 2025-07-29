import json
import time
import hmac
import hashlib
import base64
import requests
from decimal import Decimal, ROUND_DOWN

# === API 信息 ===
api_key = '你的API_KEY'
secret = '你的SECRET'
passphrase = '你的PASSPHRASE'
base_url = 'https://api.bitget.com'

# === 参数设置 ===
symbol = 'APEUSDT'
coin = 'APE'
slippage = 0.005  # 0.5% 滑点
poll_interval = 3  # 查询间隔（秒）
dry_run = False  # 测试模式

# === 工具函数 ===
def truncate(value, decimals=4):
    d = Decimal(str(value))
    return float(d.quantize(Decimal(f'1.{"0"*decimals}'), rounding=ROUND_DOWN))

def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    return str(requests.get(url).json()['data']['serverTime'])

def generate_signature(timestamp, method, endpoint, body=''):
    pre_sign = f"{timestamp}{method}{endpoint}{body}"
    return base64.b64encode(
        hmac.new(secret.encode(), pre_sign.encode(), hashlib.sha256).digest()
    ).decode()

def get_spot_price(symbol):
    url = f'{base_url}/api/v2/spot/market/tickers'
    resp = requests.get(url)
    for item in resp.json().get("data", []):
        if item.get("symbol") == symbol:
            return float(item.get("lastPr"))
    return None

def get_balance(coin):
    ts = get_server_timestamp()
    endpoint = '/api/v2/spot/account/assets'
    sign = generate_signature(ts, 'GET', endpoint)
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
    }
    resp = requests.get(base_url + endpoint, headers=headers)
    for item in resp.json().get("data", []):
        if item.get('coin') == coin:
            return float(item.get('available', 0))
    return 0

def place_limit_sell(symbol, price, size):
    ts = get_server_timestamp()
    endpoint = '/api/v2/spot/trade/place-order'
    body = {
        "symbol": symbol,
        "side": "sell",
        "orderType": "limit",
        "force": "gtc",
        "price": str(truncate(price, 4)),
        "size": str(truncate(size, 4))
    }
    body_str = json.dumps(body)
    sign = generate_signature(ts, 'POST', endpoint, body_str)
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json'
    }
    if dry_run:
        print("🧪 [Dry Run] 模拟限价单:", body)
        return "test-order-id"
    resp = requests.post(base_url + endpoint, headers=headers, data=body_str)
    print("📨 下单响应:", resp.text)
    return resp.json().get("data", {}).get("orderId")

def check_order_status(symbol, order_id):
    ts = get_server_timestamp()
    endpoint = f"/api/v2/spot/trade/order-info"
    params = f"?symbol={symbol}&orderId={order_id}"
    sign = generate_signature(ts, 'GET', endpoint + params)
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
    }
    resp = requests.get(base_url + endpoint + params, headers=headers)
    data = resp.json().get("data", {})
    return data.get("status")  # 'new', 'partial_fill', 'full_fill', 'cancelled'

# === 主逻辑 ===
if __name__ == '__main__':
    balance = get_balance(coin)
    if balance <= 0:
        print(f"❌ 没有可用余额 {coin}")
        exit(1)

    market_price = get_spot_price(symbol)
    if market_price is None:
        print("❌ 获取市场价格失败")
        exit(1)

    sell_price = market_price * (1 - slippage)
    print(f"📈 当前市价: {market_price}, 设置限价: {sell_price:.6f}")

    order_id = place_limit_sell(symbol, sell_price, balance)
    if not order_id:
        print("❌ 下单失败")
        exit(1)

    print(f"⏳ 等待订单成交... (orderId: {order_id})")

    while True:
        status = check_order_status(symbol, order_id)
        print(f"🌀 当前订单状态: {status}")
        if status == 'full_fill':
            print("✅ 订单已完全成交")
            break
        elif status in ['cancelled', 'failure']:
            print("❌ 订单已取消或失败")
            break
        time.sleep(poll_interval)
