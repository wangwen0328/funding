import time
import hmac
import hashlib
import base64
import json
import requests
from decimal import Decimal, ROUND_DOWN

# === API 配置信息 ===
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'
product_type = 'usdt-futures'

def truncate_size(size, decimals=4):
    d = Decimal(str(size))
    return float(d.quantize(Decimal(f'1.{"0"*decimals}'), rounding=ROUND_DOWN))


# 获取服务器时间
def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    resp = requests.get(url)
    return str(resp.json()['data']['serverTime'])

# 获取合约当前价格
def get_contract_price(symbol: str):
    url = f'{base_url}/api/v2/mix/market/ticker'
    params = {"symbol": symbol, "productType": product_type}
    resp = requests.get(url, params=params)
    data = resp.json()
    try:
        return float(data['data'][0]['lastPr'])
    except Exception as e:
        print("❌ 获取合约价格失败:", e)
        return None

# 生成签名
def generate_signature(timestamp, method, endpoint, body=''):
    pre_sign = f"{timestamp}{method}{endpoint}{body}"
    sign = base64.b64encode(
        hmac.new(secret.encode(), pre_sign.encode(), hashlib.sha256).digest()
    ).decode()
    return sign

# 下限价卖空单，返回orderId
def place_limit_short_order(symbol, size, price, dry_run=True):
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/mix/order/place-order'
    method = 'POST'

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "side": "sell",            # 卖空
        "tradeSide": "open",       # 开仓
        "orderType": "limit",
        "size": str(size),
        "price": str(price),
        "timeInForceValue": "gtc",
        "productType": product_type, 
        "marginMode": "crossed",
        "posMode": "one_way",
        "force": "gtc"
    }
    print(body)
    body_str = json.dumps(body)

    sign = generate_signature(timestamp, method, endpoint, body_str)
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json'
    }

    if dry_run:
        print("🔁 [Dry Run] 模拟卖空限价单:", body)
        return None

    url = base_url + endpoint
    resp = requests.post(url, headers=headers, data=body_str)
    resp_json = resp.json()
    print("卖空限价单响应:", resp_json)

    if resp_json.get("code") == "00000":
        return resp_json['data']['orderId']
    else:
        print("❌ 下单失败:", resp_json)
        return None

# 查询订单状态
def get_order_status(symbol, order_id):
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/mix/order/detail'
    method = 'GET'
    params = f"?symbol={symbol}&orderId={order_id}&productType={product_type}"
    pre_sign = f"{timestamp}{method}{endpoint}{params}"
    sign = base64.b64encode(
        hmac.new(secret.encode(), pre_sign.encode(), hashlib.sha256).digest()
    ).decode()

    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
    }

    url = base_url + endpoint + params
    resp = requests.get(url, headers=headers)
    resp_json = resp.json()
    print("订单详情响应:", json.dumps(resp_json, indent=2, ensure_ascii=False))  # 打印完整返回数据，方便调试
    return resp_json


def wait_for_order_filled(symbol, order_id, check_interval=3):
    print(f"⏳ 等待订单 {order_id} 成交...")
    while True:
        order_status_resp = get_order_status(symbol, order_id)
        if order_status_resp.get('code') != '00000':
            print(f"❌ 查询订单失败: {order_status_resp}")
            time.sleep(check_interval)
            continue

        data = order_status_resp.get('data', {})
        state = data.get('state')
        filled_qty = float(data.get('baseVolume', 0))  # 已成交数量用 baseVolume
        size = float(data.get('size', 0))             # 委托总量

        print(f"订单状态: {state}, 已成交数量: {filled_qty} / {size}")

        if state == 'filled' or filled_qty >= size:
            print("✅ 订单已完全成交")
            return True

        time.sleep(check_interval)

def execute_short_trade(symbol, usdt_amount, max_slippage):
    try:
        print(symbol, usdt_amount, max_slippage)
        price = get_contract_price(symbol)
        if price is None:
            return False, "无法获取合约价格"

        limit_price = truncate_size(price * (1 - max_slippage), 4)
        size = truncate_size(usdt_amount / limit_price, 4)

        order_id = place_limit_short_order(symbol, size, limit_price, dry_run=False)
        if order_id is None:
            return False, "下单失败"

        wait_for_order_filled(symbol, order_id)
        return True, {"order_id": order_id, "symbol": symbol, "price": limit_price, "size": size}
    except Exception as e:
        return False, str(e)

def main():
    symbol = "APEUSDT"
    max_slippage = 0.001  # 最大滑点0.5%
    usdt_amount = 5.1      # 准备卖空的USDT金额

    price = get_contract_price(symbol)
    if price is None:
        print("❌ 无法获取价格，退出")
        return

    limit_price = round(price * (1 - max_slippage), 6)
    size = round(usdt_amount / limit_price, 3)
    size = truncate_size(size, 4)  # 截断到4位小数
    limit_price = truncate_size(limit_price, 4)  # 截断到4位小数

    print(f"当前价格: {price}")
    print(f"下限价卖空单，价格: {limit_price}, 数量: {size}")

    order_id = place_limit_short_order(symbol, size, limit_price, dry_run=False)
    if order_id is None:
        print("❌ 下单失败，退出")
        return

    # 等待订单成交，不成功不返回
    wait_for_order_filled(symbol, order_id)

if __name__ == '__main__':
    main()
