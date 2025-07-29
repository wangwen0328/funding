import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "usdt-futures"
OUTPUT_DIR = "funding_rates"
MAX_SYMBOLS = 600  # 最多请求 20 个
MAX_WORKERS = 8   # 并发线程数，推荐 5~10

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_all_symbols():
    url = f"{BASE_URL}/api/v2/mix/market/contracts"
    params = {"productType": PRODUCT_TYPE}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "00000":
                return [item["symbol"] for item in data.get("data", [])]
    except Exception as e:
        print(f"❌ 获取合约列表失败: {e}")
    return []

def get_funding_rate(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/current-fund-rate"
    params = {"symbol": symbol, "productType": PRODUCT_TYPE}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "00000":
                return symbol, data.get("data")
    except Exception as e:
        print(f"❌ 获取 {symbol} 的资金费率失败: {e}")
    return symbol, None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    symbols = get_all_symbols()
    if not symbols:
        print("❌ 没有获取到任何交易对")
        return

    symbols = symbols[:MAX_SYMBOLS]
    results = {}

    print(f"🚀 正在并发请求 {len(symbols)} 个交易对...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(get_funding_rate, symbol) for symbol in symbols]

        for future in as_completed(futures):
            symbol, rate = future.result()
            if rate:
                results[symbol] = rate
                output_path = os.path.join(OUTPUT_DIR, f"{symbol}.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(rate, f, ensure_ascii=False, indent=2)
                print(f"✅ {symbol} → {output_path}")
            else:
                print(f"⚠️ {symbol} 没有获取到资金费率")

    with open("all_funding_rates.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n📦 所有资金费率合并结果已保存到 all_funding_rates.json")

if __name__ == "__main__":
    main()
