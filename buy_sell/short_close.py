import time
import hmac
import hashlib
import base64
import json
import requests
from decimal import Decimal, ROUND_DOWN

# === API 配置 ===
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'
product_type = 'usdt-futures'


def truncate_size(size, decimals=4):
    d = Decimal(str(size))
    return float(d.quantize(Decimal(f'1.{"0"*decimals}'), rounding=ROUND_DOWN))


def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    return str(requests.get(url).json()['data']['serverTime'])


def generate_signature(timestamp, method, endpoint, body=''):
    pre_sign = f"{timestamp}{method}{endpoint}{body}"
    return base64.b64encode(
        hmac.new(secret.encode(), pre_sign.encode(), hashlib.sha256).digest()
    ).decode()


def get_contract_price(symbol):
    url = f'{base_url}/api/v2/mix/market/ticker'
    params = {"symbol": symbol, "productType": product_type}
    resp = requests.get(url, params=params)
    try:
        return float(resp.json()['data'][0]['lastPr'])
    except Exception as e:
        print("❌ 获取合约价格失败:", e)
        return None


def get_position_size_and_mode(symbol):
    """获取当前空头持仓数量和持仓模式"""
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/mix/position/single-position'
    method = 'GET'
    params = f"?symbol={symbol}&marginCoin=USDT&productType={product_type}"
    sign = generate_signature(timestamp, method, endpoint, params)

    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase
    }

    url = base_url + endpoint + params
    resp = requests.get(url, headers=headers)
    data = resp.json()

    print("持仓接口返回:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get('code') != '00000':
        print("❌ 获取持仓失败:", data)
        return 0, None

    positions = data.get('data', [])
    if not positions:
        print("ℹ️ 当前没有任何持仓")
        return 0, None

    for pos in positions:
        if pos.get('holdSide') == 'short':
            size = float(pos.get('total', 0))
            pos_mode = pos.get('posMode', 'one_way')
            print(f"📊 当前空头持仓数量: {size}, 持仓模式: {pos_mode}")
            return size, pos_mode

    print("ℹ️ 当前没有空头持仓")
    return 0, None


def place_close_short_order(symbol, size, price, dry_run=False, pos_mode='one_way'):
    """提交限价平仓单（买入平空仓）"""
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/mix/order/place-order'
    method = 'POST'
    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "side": "sell",             
        "tradeSide": "close",      
        "orderType": "limit",
        "size": str(size),
        "price": str(price),
        "timeInForceValue": "gtc",
        "productType": 'USDT-FUTURES',
        "marginMode": "crossed",
        "posMode": "hedge_mode",         
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
        print("🔁 [Dry Run] 模拟平仓单:", body)
        return

    url = base_url + endpoint
    resp = requests.post(url, headers=headers, data=body_str)
    print("✅ 状态码:", resp.status_code)
    print("📨 响应内容:", resp.text)


def close_short_position(symbol, max_slippage=0.001, dry_run=False):
    price = get_contract_price(symbol)
    if price is None:
        print("❌ 获取价格失败，终止操作")
        return

    size, pos_mode = get_position_size_and_mode(symbol)
    if size <= 0 or pos_mode is None:
        print("❌ 当前无空头持仓")
        return

    limit_price = price * (1 + max_slippage)
    size = truncate_size(size, 4)
    limit_price = truncate_size(limit_price, 4)

    print(f"📉 当前合约价格: {price}")
    print(f"🎯 限价平仓价格: {limit_price}，数量: {size}")
    place_close_short_order(symbol, size, limit_price, dry_run=dry_run, pos_mode=pos_mode)


if __name__ == '__main__':
    coin = 'APE'
    symbol = coin + 'USDT'
    close_short_position(symbol, max_slippage=0.001, dry_run=False)
