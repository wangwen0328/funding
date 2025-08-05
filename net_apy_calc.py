import os
import time
import json
import hmac
import hashlib
import base64
import requests

# === API 凭证 ===
api_key = 'bg_fa5e35d776ba3f9699737693b039b180'
secret = '6c9a49290d69c75417890b3626ab3ff8d44a7ecefc9ba899af876857a8db62eb'
passphrase = 'Ii000000'

base_url = "https://api.bitget.com"
v2_interest_rate_endpoint = "/api/v2/margin/interest-rate-record?coin={coin}"

# === 工具函数 ===

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(timestamp, method, endpoint, body=''):
    message = timestamp + method + endpoint + body
    signature = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

def fetch_latest_interest_rate(coin):
    endpoint = v2_interest_rate_endpoint.format(coin=coin)
    method = "GET"
    timestamp = get_timestamp()
    sign = sign_request(timestamp, method, endpoint)

    headers = {
        "ACCESS-KEY": api_key,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json"
    }

    url = base_url + endpoint
    resp = requests.get(url, headers=headers)
    data = resp.json()

    if data.get("code") == "00000" and isinstance(data.get("data"), dict):
        try:
            annual_rate = float(data["data"]["annualInterestRate"])
            return round(annual_rate * 100, 6)
        except Exception as e:
            print(f"⚠️  {coin} 的年化利率提取失败: {e}")
    else:
        print(f"❌ 获取 {coin} 借币利率失败: {data.get('msg', data)}")
    return None  # 返回 None 就不会加入字段


# === 主逻辑 ===

with open("earn_products.json", "r", encoding="utf-8") as f:
    earn_data = json.load(f)

with open("all_funding_rates.json", "r", encoding="utf-8") as f:
    funding_data = json.load(f)

# 加载 spot_lending_rates_v2.json（如果存在）
spot_lending_rates = {}
spot_lending_path = "spot_lending_rates_v2.json"
if os.path.exists(spot_lending_path):
    with open(spot_lending_path, "r", encoding="utf-8") as f:
        spot_lending_rates = json.load(f)

# 提取 earn apy 数据
earn_apys = {}
for item in earn_data.get("data", []):
    coin = item["coin"].upper()
    apy_list = item.get("apyList", [])
    if apy_list:
        try:
            earn_apys[coin] = float(apy_list[0]["currentApy"])
        except:
            pass

# 构建净收益列表
results = []
for symbol, rates in funding_data.items():
    if not rates:
        continue
    funding_rate = float(rates[0]["fundingRate"])
    base_coin = symbol.replace("USDT", "").upper()

    earn_apy = earn_apys.get(base_coin, None)
    funding_annual = funding_rate * 3 * 365
    net_apy = funding_annual * 100  # 带正负号

    item = {
        "coin": base_coin,
        "funding_rate_annual_%": round(funding_annual * 100, 6),
        "net_apy": round(net_apy, 6),
    }

    if earn_apy is not None:
        item["earn_apy"] = earn_apy

    # 如满足 abs(net_apy) > 40，获取现货卖出借币年化利率
    if abs(net_apy) > 40:
        rate = fetch_latest_interest_rate(base_coin)
        if rate is not None:
            spot_lending_rates[base_coin] = rate
            item["spot_sell_lend_rate"] = rate

    results.append(item)

# 更新本地缓存
with open(spot_lending_path, "w", encoding="utf-8") as f:
    json.dump(spot_lending_rates, f, ensure_ascii=False, indent=2)

# 排序（按 abs(net_apy) 降序）
results.sort(key=lambda x: abs(x["net_apy"]), reverse=True)

# 保存最终结果
with open("net_apy_sorted.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

"✅ 计算完成，结果已保存为 net_apy_sorted.json"
