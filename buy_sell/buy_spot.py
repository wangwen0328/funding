import time
import hmac
import hashlib
import base64
import json
import requests
from decimal import Decimal, ROUND_DOWN

# === ✅ API 配置信息 ===
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'

# === 截断函数，向下保留指定位小数 ===
def truncate_size(size, decimals=4):
    d = Decimal(str(size))
    return float(d.quantize(Decimal(f'1.{"0"*decimals}'), rounding=ROUND_DOWN))

# === ✅ 获取服务器时间 ===
def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    resp = requests.get(url)
    return str(resp.json()['data']['serverTime'])

# === ✅ 获取现货市价 ===
def get_spot_price(symbol: str):
    url = f'{base_url}/api/v2/spot/market/tickers'
    resp = requests.get(url)
    try:
        data = resp.json()
        tickers = data.get("data", [])
        for item in tickers:
            if item.get('symbol') == symbol:
                print(f"✅ 找到 {symbol} 行情: {item}")
                return float(item['lastPr'])  # ✅ 注意是 lastPr
        print(f"❌ 没有找到 {symbol} 的市价")
        return None
    except Exception as e:
        print("❌ 解析行情失败:", e)
        return None

# === ✅ 创建签名 ===
def generate_signature(timestamp, method, endpoint, body=''):
    pre_sign = f"{timestamp}{method}{endpoint}{body}"
    sign = base64.b64encode(
        hmac.new(
            secret.encode('utf-8'),
            pre_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode()
    return sign

# === ✅ 下限价买单，含滑点控制 ===
def place_spot_limit_buy_order(symbol, usdt_amount=1, max_slippage=0.005, dry_run=True):
    price = get_spot_price(symbol)
    if price is None:
        print("❌ 获取市价失败，终止下单")
        return

    # 计算最大可接受价格
    limit_price = round(price * (1 + max_slippage), 6)
    size = round(usdt_amount / limit_price, 6)
    size = truncate_size(size, 4)  # 截断到4位小数
    limit_price = truncate_size(limit_price, 4)  # 截断到4位小数

    print(f"📊 当前价格: {price}")
    print(f"🎯 限价买入价格: {limit_price}，买入数量: {size} {symbol.replace('USDT', '')}")

    timestamp = get_server_timestamp()
    endpoint = '/api/v2/spot/trade/place-order'
    method = 'POST'

    body = {
        "symbol": symbol,
        "side": "buy",
        "orderType": "limit",      # ✅ 限价单
        "force": "fok",            # ✅ 一次成交全部，否则取消
        "price": str(limit_price),
        "size": str(size)
    }
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
        print("🔁 [Dry Run] 模拟下单数据:", body)
        return

    url = base_url + endpoint
    response = requests.post(url, headers=headers, data=body_str)
    print("✅ 状态码:", response.status_code)
    print("📨 响应内容:", response.text)

def execute_spot_buy_trade(symbol: str, usdt_amount: float, max_slippage: float):
    try:
        price = get_spot_price(symbol)
        if price is None:
            return False, "无法获取现货价格"

        limit_price = truncate_size(price * (1 + max_slippage), 4)
        size = truncate_size(usdt_amount / limit_price, 4)

        print(f"✅ 当前市价: {price}")
        print(f"🎯 买入限价: {limit_price}，数量: {size}")

        timestamp = get_server_timestamp()
        endpoint = '/api/v2/spot/trade/place-order'
        method = 'POST'

        body = {
            "symbol": symbol,
            "side": "buy",
            "orderType": "limit",
            "force": "fok",
            "price": str(limit_price),
            "size": str(size)
        }
        body_str = json.dumps(body)

        sign = generate_signature(timestamp, method, endpoint, body_str)
        headers = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sign,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }

        url = base_url + endpoint
        resp = requests.post(url, headers=headers, data=body_str)

        result = resp.json()
        print("📨 买单响应:", result)

        if result.get("code") == "00000":
            return True, {
                "order_id": result['data']['orderId'],
                "symbol": symbol,
                "price": limit_price,
                "size": size
            }
        else:
            return False, result.get("msg", "下单失败")

    except Exception as e:
        return False, str(e)

if __name__ == '__main__':
    symbol = "APEUSDT"
    result = execute_spot_buy_trade(symbol, usdt_amount=1.1, max_slippage=0.001)
    print(result)
