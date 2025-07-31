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


def truncate_size(size, decimals=8):
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


def get_headers(method: str, endpoint: str, body=''):
    timestamp = get_server_timestamp()
    sign = generate_signature(timestamp, method, endpoint, body)
    return {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json'
    }


def get_spot_balance(coin: str) -> float:
    endpoint = '/api/v2/spot/account/assets'
    method = 'GET'
    url = base_url + endpoint
    headers = get_headers(method, endpoint)
    resp = requests.get(url, headers=headers)
    data = resp.json()
    for item in data.get('data', []):
        if item['coin'] == coin:
            balance = float(item['available'])
            print(f"✅ 当前 {coin} 可用余额: {balance}")
            return balance
    print(f"❌ 没有找到 {coin} 的余额信息")
    return 0.0


def find_savings_product_id(coin):
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/earn/savings/product?filter=available_and_held'
    method = 'GET'
    body = ''

    sign = generate_signature(timestamp, method, endpoint, body)
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
    }

    url = base_url + endpoint
    resp = requests.get(url, headers=headers)

    result = resp.json()
    if result.get('code') != '00000':
        print("❌ 查询产品失败:", result)
        return None

    for item in result['data']:
        # ✅ 使用实际字段 coin
        if item.get('coin') == coin:
            product_id = item['productId']
            print(f"✅ 找到 {coin} 的活期理财产品ID: {product_id}")
            return product_id

    print(f"❌ 没有找到 {coin} 的理财产品")
    return None



def subscribe_to_savings(product_id: str, amount: float):
    endpoint = '/api/v2/earn/savings/subscribe'
    method = 'POST'
    body = {
        "periodType": "flexible",  # 活期
        "productId": product_id,
        "amount": str(truncate_size(amount, 8))
    }
    body_str = json.dumps(body)
    headers = get_headers(method, endpoint, body_str)
    url = base_url + endpoint
    resp = requests.post(url, headers=headers, data=body_str)
    print("📨 理财申购响应:", resp.status_code, resp.text)
    return resp.json()


def auto_subscribe_savings_for_coin(coin: str):
    balance = get_spot_balance(coin)
    if balance <= 0:
        msg = f"❌ 当前无 {coin} 余额，无法购买理财"
        print(msg)
        return False, msg

    product_id = find_savings_product_id(coin)
    if not product_id:
        msg = f"❌ 找不到 {coin} 对应的活期理财产品"
        print(msg)
        return False, msg

    print(f"🚀 尝试将 {balance} {coin} 申购活期理财")
    result = subscribe_to_savings(product_id, balance)
    print("✅ 最终结果:", result)

    if result.get("code") == "00000":
        return True, "申购成功"
    else:
        return False, result.get("msg", "申购失败")


if __name__ == '__main__':
    auto_subscribe_savings_for_coin('APE')
