import time
import hmac
import hashlib
import base64
import json
import requests
from decimal import Decimal

# ✅ API 配置
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'


def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    return str(requests.get(url).json()['data']['serverTime'])


def generate_signature(timestamp, method, endpoint, body=''):
    pre_sign = f"{timestamp}{method}{endpoint}{body}"
    return base64.b64encode(
        hmac.new(secret.encode(), pre_sign.encode(), hashlib.sha256).digest()
    ).decode()


def find_savings_product_id(coin: str):
    """查找理财产品ID"""
    timestamp = get_server_timestamp()
    endpoint = "/api/v2/earn/savings/product"
    method = "GET"
    params = "?filter=available_and_held"
    sign = generate_signature(timestamp, method, endpoint, params)

    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase
    }

    url = base_url + endpoint + params
    resp = requests.get(url, headers=headers)
    result = resp.json()

    if result.get("code") != "00000":
        print("❌ 查询产品失败:", result)
        return None

    for item in result.get("data", []):
        if item.get('coin') == coin and item.get('periodType') == 'flexible':
            print(f"✅ 找到 {coin} 活期理财产品ID: {item.get('productId')}")
            return item.get('productId')
    
    print(f"❌ 没有找到 {coin} 的理财产品")
    return None


def get_held_savings_amount(coin: str):
    """获取用户在活期理财中某币的持仓和产品ID"""
    timestamp = get_server_timestamp()
    endpoint = "/api/v2/earn/savings/assets"
    method = "GET"
    params = "?periodType=flexible&pageSize=20"
    sign = generate_signature(timestamp, method, endpoint, params)

    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
        'locale': 'en-US',
        'Content-Type': 'application/json'
    }

    url = base_url + endpoint + params
    resp = requests.get(url, headers=headers)
    result = resp.json()

    print("💡 理财资产接口返回:", json.dumps(result, indent=2))

    if result.get("code") != "00000":
        print("❌ 查询理财资产失败:", result)
        return None, 0

    assets = result.get("data", {}).get("resultList", [])
    for asset in assets:
        if asset.get("productCoin") == coin:
            product_id = asset.get("productId")
            amount = float(asset.get("holdAmount", 0))
            print(f"✅ 当前 {coin} 活期理财持仓: {amount}, 产品ID: {product_id}")
            return product_id, amount

    print(f"ℹ️ 当前没有 {coin} 的活期理财持仓")
    return None, 0



def redeem_savings(product_id: str, amount: float):
    """提交赎回请求"""
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/earn/savings/redeem'
    method = 'POST'

    body = {
        "periodType": "flexible",
        "productId": product_id,
        "amount": str(amount)
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
    print("📨 响应内容:", resp.text)

    result = resp.json()
    if result.get("code") == "00000":
        print(f"✅ 成功赎回 {amount}")
        return True
    else:
        print("❌ 赎回失败:", result)
        return False


def auto_redeem_savings_for_coin(coin: str):
    """自动赎回某币全部活期理财余额"""
    product_id, amount = get_held_savings_amount(coin)
    if not product_id or amount <= 0:
        msg = "ℹ️ 无可赎回余额或产品ID"
        print(msg)
        return False, msg

    success = redeem_savings(product_id, amount)
    if success:
        return True, f"成功赎回 {amount} {coin}"
    else:
        return False, f"赎回失败: {coin}"



if __name__ == '__main__':
    auto_redeem_savings_for_coin('APE')
