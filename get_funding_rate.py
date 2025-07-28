import requests
import json
import time

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "usdt-futures"

def get_all_symbols():
    url = f"{BASE_URL}/api/v2/mix/market/contracts"
    params = {"productType": PRODUCT_TYPE}
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == "00000":
            return [item["symbol"] for item in data.get("data", [])]
    return []

def get_funding_rate(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/current-fund-rate"
    params = {"symbol": symbol, "productType": PRODUCT_TYPE}
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == "00000":
            return data.get("data")
    return None

if __name__ == "__main__":
    print("get_funding_rate")
    symbols = get_all_symbols()
    results = {}
    for symbol in symbols:
        rate = get_funding_rate(symbol)
        if rate:
            results[symbol] = rate
        time.sleep(0.1)  # 控制速率，避免被封 IP
    with open("all_funding_rates.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
