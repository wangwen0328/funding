import time
import hmac
import hashlib
import base64
import requests
import json

# === 替换为你的 API 凭证 ===
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'

base_url = "https://api.bitget.com"
endpoint = "/api/margin/v1/cross/interestRateAndLimit"

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(timestamp, method, endpoint, body=''):
    message = timestamp + method + endpoint + body
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

def fetch_lending_rates():
    method = "GET"
    timestamp = get_timestamp()
    sign = sign_request(timestamp, method, endpoint)

    headers = {
        "ACCESS-KEY": api_key,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": api_passphrase,
        "Content-Type": "application/json"
    }

    url = base_url + endpoint
    response = requests.get(url, headers=headers)
    data = response.json()

    lending_rates = {}
    if data.get("code") == "00000":
        for item in data.get("data", []):
            coin = item["coin"].upper()
            yearly_rate = float(item["yearlyRate"])
            lending_rates[coin] = yearly_rate
        with open("spot_lending_rates.json", "w", encoding="utf-8") as f:
            json.dump(lending_rates, f, ensure_ascii=False, indent=2)
        print("✅ spot_lending_rates.json 已保存")
    else:
        print("❌ 请求失败：", data)

if __name__ == "__main__":
    fetch_lending_rates()
