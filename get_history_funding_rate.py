import requests
import json
import time
import os

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "usdt-futures"
INPUT_FILE = "net_apy_sorted.json"
MAX_COINS = 10  # 处理前10个币
OUTPUT_DIR = "funding_data"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 删除目录下所有旧文件
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
    net_apy = coin_info.get("net_apy")  # 新增这一行

    print(f"🔍 处理 {symbol}...")

    current_rate = get_current_funding_rate(symbol)
    history = get_funding_rate_history(symbol, page_size=50)

    return {
        "coin": coin,
        "earn_apy": earn_apy,
        "net_apy": net_apy,              # 把 net_apy 也放进去
        "symbol": symbol,
        "funding_rate_annual_%": funding_rate_annual_percent,
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

        top_coins = coin_list[:MAX_COINS]

        for coin_info in top_coins:
            try:
                result = get_funding_data_for_symbol(coin_info)
                symbol = result['symbol']
                output_path = os.path.join(OUTPUT_DIR, f"{symbol}.json")

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump([result], f, ensure_ascii=False, indent=2)

                print(f"✅ 已保存 {symbol} 到 {output_path}")
                #time.sleep(0.5)  # 避免触发接口频率限制

            except Exception as e:
                print(f"❌ 处理币种 {coin_info.get('coin', '未知')} 时出错: {e}")

    except Exception as e:
        print(f"❌ 脚本运行出错: {e}")
