import os
import json
import requests
import time

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "usdt-futures"
INPUT_FILE = "net_apy_sorted.json"
OUTPUT_DIR = "funding_data"
SPOT_LENDING_FILE = "spot_lending_rates_v2.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 读借贷利率缓存文件
if os.path.exists(SPOT_LENDING_FILE):
    with open(SPOT_LENDING_FILE, "r", encoding="utf-8") as f:
        spot_lending_rates = json.load(f)
else:
    spot_lending_rates = {}

def clear_output_dir():
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"⚠️ 删除文件失败 {file_path}: {e}")

def get_funding_data_for_symbol(coin_info):
    coin = coin_info["coin"].upper()
    symbol = f"{coin}USDT"
    earn_apy = coin_info.get("earn_apy")
    funding_rate_annual_percent = coin_info.get("funding_rate_annual_%")
    net_apy = coin_info.get("net_apy")

    spot_sell_lend_rate = spot_lending_rates.get(coin)

    print(f"🔍 处理 {symbol}...")

    current_rate = get_current_funding_rate(symbol)
    history = get_funding_rate_history(symbol, page_size=50)

    return {
        "coin": coin,
        "earn_apy": earn_apy,
        "net_apy": net_apy,
        "symbol": symbol,
        "funding_rate_annual_%": funding_rate_annual_percent,
        "spot_sell_lend_rate": spot_sell_lend_rate,
        "current_funding_rate": current_rate,
        "history": history
    }

def get_current_funding_rate(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/current-fund-rate"
    params = {"symbol": symbol, "productType": PRODUCT_TYPE}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "00000":
                return data.get("data")
    except Exception as e:
        print(f"❌ 获取当前资金费率失败 ({symbol}): {e}")
    return None

def get_funding_rate_history(symbol, page_size=50):
    url = f"{BASE_URL}/api/v2/mix/market/history-fund-rate"
    params = {"symbol": symbol, "productType": PRODUCT_TYPE, "pageSize": page_size, "pageNo": 1}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code != 200:
            print(f"❌ {symbol} 请求失败，状态码：{response.status_code}")
            return []

        data = response.json()
        if data.get("code") != "00000":
            print(f"❌ {symbol} API返回错误: {data}")
            return []

        return data.get("data", [])
    except Exception as e:
        print(f"❌ 获取历史费率失败 ({symbol}): {e}")
        return []

if __name__ == "__main__":
    try:
        clear_output_dir()

        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            coin_list = json.load(f)

        if not coin_list:
            raise ValueError("❌ JSON 文件为空")

        filtered_coins = [c for c in coin_list if abs(c.get("net_apy", 0)) > 40]

        if len(filtered_coins) < 10:
            print(f"⚠️ 筛选出的币不足10个({len(filtered_coins)})，改为处理前10个币")
            coins_to_process = coin_list[:10]
        else:
            coins_to_process = filtered_coins

        for coin_info in coins_to_process:
            try:
                result = get_funding_data_for_symbol(coin_info)
                symbol = result['symbol']
                output_path = os.path.join(OUTPUT_DIR, f"{symbol}.json")

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump([result], f, ensure_ascii=False, indent=2)

                print(f"✅ 已保存 {symbol} 到 {output_path}")
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ 处理币种 {coin_info.get('coin', '未知')} 时出错: {e}")

    except Exception as e:
        print(f"❌ 脚本运行出错: {e}")
