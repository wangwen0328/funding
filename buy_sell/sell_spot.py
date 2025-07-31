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
        hmac.new(secret.encode('utf-8'), pre_sign.encode('utf-8'), hashlib.sha256).digest()
    ).decode()
    return sign

def get_spot_price(symbol: str):
    url = f'{base_url}/api/v2/spot/market/tickers'
    resp = requests.get(url)
    try:
        data = resp.json()
        for item in data.get("data", []):
            if item.get('symbol') == symbol:
                return float(item['lastPr'])
        return None
    except Exception as e:
        print("❌ 获取现货价格失败:", e)
        return None

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
    for asset in data:
        if asset.get('coin') == coin:
            return float(asset.get('available', 0))
    return 0

def place_spot_limit_sell_order(symbol, size, max_slippage=0.005, dry_run=True):
    # 获取当前市价
    price = get_spot_price(symbol)
    if price is None:
        print("❌ 无法获取现货价格")
        return

    # 计算限价
    limit_price = truncate_size(price * (1 - max_slippage), 4)
    size_truncated = truncate_size(size, 4)

    print(f"📉 当前市价: {price}")
    print(f"🎯 限价卖出: {limit_price}，数量: {size_truncated}")

    timestamp = get_server_timestamp()
    endpoint = '/api/v2/spot/trade/place-order'
    method = 'POST'
    body = {
        "symbol": symbol,
        "side": "sell",
        "orderType": "limit",
        "force": "fok",  # 一次成交全部，否则取消
        "price": str(limit_price),
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

def debug_print_all_balances():
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
        print("❌ 获取余额失败:", response.text)
        return
    data = response.json().get('data', [])
    print("📋 所有币种现货余额:")
    for asset in data:
        print(f"  {asset['coin']}: {asset['available']}")


def sell_spot_entry_from_app(symbol: str, slippage: float) -> tuple[bool, str]:
    try:
        debug_print_all_balances()  # 打印全部余额信息（可选）

        first_coin = symbol.replace('USDT', '')
        print(f"准备卖出交易对: {symbol}")

        balance = get_spot_account_balance(first_coin)
        if balance <= 0:
            msg = "❌ 没有持仓或者余额不足，无法卖出"
            print(msg)
            return False, msg

        print(f"持仓余额: {balance}")
        place_spot_limit_sell_order(symbol, size=balance, max_slippage=slippage, dry_run=False)
        return True, f"✅ 卖出提交成功，数量: {balance}"

    except Exception as e:
        return False, f"❌ 执行异常: {str(e)}"


if __name__ == '__main__':
    max_slippage = 0.001  # 允许滑点 0.1%
    debug_print_all_balances()
    first_coin = 'APE'
    symbol = first_coin + 'USDT'
    print(f"准备卖出交易对: {symbol}")

    balance = get_spot_account_balance(first_coin)
    if balance <= 0:
        print("❌ 没有持仓或者余额不足，无法卖出")
    else:
        print(balance)
        place_spot_limit_sell_order(symbol, size=balance, max_slippage=max_slippage, dry_run=False)
