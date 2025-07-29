import time
import hmac
import hashlib
import base64
import json
import requests

# === ✅ API 配置信息 ===
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'

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

# === ✅ 下市价买单 ===
def place_spot_market_buy_order(symbol, usdt_amount=1, dry_run=True):
    price = get_spot_price(symbol)
    if price is None:
        print("❌ 获取市价失败，终止下单")
        return

    size = round(usdt_amount / price, 6)
    print(f"📊 当前价格: {price}, 拟买入数量: {size} {symbol.replace('USDT','')}")

    timestamp = get_server_timestamp()
    endpoint = '/api/v2/spot/trade/place-order'
    method = 'POST'

    body = {
        "symbol": symbol,
        "side": "buy",
        "orderType": "market",
        "force": "gtc",
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

# === ✅ 程序入口 ===
if __name__ == '__main__':
    symbol = "APEUSDT"
    place_spot_market_buy_order(symbol, usdt_amount=1, dry_run=False)
