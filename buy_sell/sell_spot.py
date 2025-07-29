import json
import requests
import time
import hmac
import hashlib
import base64
from decimal import Decimal, ROUND_DOWN

api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'


def truncate_size(size, decimals=4):
    d = Decimal(str(size))
    return float(d.quantize(Decimal(f'1.{"0"*decimals}'), rounding=ROUND_DOWN))

def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    resp = requests.get(url)
    return str(resp.json()['data']['serverTime'])

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

def get_spot_account_balance(coin):
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/spot/account/assets'
    method = 'GET'
    sign = generate_signature(timestamp, method, endpoint, '')

    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
    }
    url = base_url + endpoint
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("❌ 获取账户余额失败:", response.text)
        return 0
    data = response.json().get('data', [])
    print("📝 账户资产详细:", data)  # 打印所有资产，帮你看下APE情况
    for asset in data:
        if asset.get('coin') == coin:
            free = float(asset.get('available', 0))
            print(f"💰 账户可用 {coin} 数量: {free}")
            return free
    print(f"❌ 账户没有该币种 {coin} 余额")
    return 0


def place_spot_market_sell_order(symbol, size, dry_run=True):
    timestamp = get_server_timestamp()
    endpoint = '/api/v2/spot/trade/place-order'
    method = 'POST'
    size_truncated = truncate_size(size, 4)
    body = {
        "symbol": symbol,
        "side": "sell",
        "orderType": "market",
        "force": "gtc",
        "size": str(size_truncated)
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
        print("🔁 [Dry Run] 模拟卖单数据:", body)
        return

    url = base_url + endpoint
    response = requests.post(url, headers=headers, data=body_str)
    print("✅ 状态码:", response.status_code)
    print("📨 响应内容:", response.text)


if __name__ == '__main__':
    # 1. 读json文件
    with open('net_apy_sorted.json', 'r') as f:
        coins_data = json.load(f)

    first_coin = coins_data[0]['coin']
    symbol = first_coin + "USDT"
    print(f"准备卖出交易对: {symbol}")

    # 2. 获取该币持仓数量
    balance = get_spot_account_balance(first_coin)
    if balance <= 0:
        print("❌ 没有持仓或者余额不足，无法卖出")
    else:
        # 3. 下市价卖单，dry_run改False才真正卖
        place_spot_market_sell_order(symbol, size=balance, dry_run=False)
