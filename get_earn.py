import json
import requests
import time
import hmac
import hashlib
import base64

api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'
base_url = 'https://api.bitget.com'

def get_server_timestamp():
    url = f'{base_url}/api/v2/public/time'
    resp = requests.get(url)
    data = resp.json()
    print("🕒 服务器时间响应:", data)
    return str(data['data']['serverTime'])

def get_earn_savings_products():
    method = 'GET'
    endpoint = '/api/v2/earn/savings/product?filter=all'
    request_body = ''

    timestamp = get_server_timestamp()
    pre_sign = f"{timestamp}{method}{endpoint}"
    print("📦 pre_sign:", pre_sign)

    sign = base64.b64encode(
        hmac.new(secret.encode(), pre_sign.encode(), hashlib.sha256).digest()
    ).decode()
    print("🔐 签名:", sign)

    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
    }

    url = base_url + endpoint
    print("🌐 请求 URL:", url)
    print("📨 请求头 headers:", headers)

    response = requests.get(url, headers=headers)
    print("📬 响应状态码:", response.status_code)
    try:
        json_data = response.json()
        print("🧩 返回完整数据（调试）:", json_data)

        # 只在 json_data 有内容且 code 为 '00000' 时写文件
        if json_data and json_data.get('code') == '00000':
            with open('earn_products.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print("✅ JSON数据已保存到 earn_products.json")
        else:
            print("⚠️ 接口返回错误或数据为空:", json_data.get('msg'))

    except Exception as e:
        print("⚠️ 解析JSON失败:", e)
        print("响应文本:", response.text)

if __name__ == "__main__":
    get_earn_savings_products()
