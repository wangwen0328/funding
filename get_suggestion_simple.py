import json
import os
from datetime import datetime, timedelta

# === 配置参数 ===
days = 10
principal = 1000
hedge_fee_rate = 0.0032  # 0.32%

INPUT_DIR = "funding_data"
OUTPUT_DIR = "sim_results"
SPOT_LENDING_FILE = "spot_lending_rates_v2.json"
NET_APY_FILE = "net_apy_sorted.json"

# === 工具函数 ===
def weighted_moving_average(values):
    n = len(values)
    if n == 0:
        return 0.0
    weights = list(range(1, n + 1))
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / sum(weights)

def simulate(funding_data, spot_sell_lend_rate=0):
    earn_apy_raw = funding_data.get('earn_apy')
    earn_apy = earn_apy_raw / 100 if earn_apy_raw is not None else 0

    funding_interval_hours = int(funding_data['current_funding_rate'][0]['fundingRateInterval'])
    fundings_per_day = 24 // funding_interval_hours

    funding_rates = [float(entry['fundingRate']) for entry in funding_data['history']]
    predicted_rate = weighted_moving_average(funding_rates)

    predicted_annual_rate = predicted_rate * fundings_per_day * 365 * 100
    predicted_daily_rate = predicted_rate * fundings_per_day

    daily_lend_rate = spot_sell_lend_rate / 100 / 365
    single_lend_rate = daily_lend_rate / fundings_per_day if fundings_per_day > 0 else 0

    initial_balance = principal * (1 - hedge_fee_rate)
    balance = initial_balance
    daily_earn_rate = earn_apy / 365

    funding_fee_total = 0
    earn_total = 0
    result_per_day = []
    today = datetime.now()

    for i in range(1, days + 1):
        date_str = (today + timedelta(days=i)).strftime('%Y-%m-%d')

        # earn 只在预测资金费率为正时才计算
        earn_gain = balance * daily_earn_rate if predicted_rate >= 0 else 0
        balance += earn_gain
        earn_total += earn_gain

        # funding 收益或支出
        if predicted_rate >= 0:
            funding_gain = balance * predicted_daily_rate
        else:
            adjusted_rate = abs(predicted_rate) - single_lend_rate
            funding_gain = -balance * adjusted_rate * fundings_per_day

        balance += funding_gain
        funding_fee_total += funding_gain

        result_per_day.append({
            "date": date_str,
            "earn_interest": round(earn_gain, 6),
            "funding_income": round(funding_gain, 6),
            "daily_total": round(balance, 6),
            "total_earn": round(earn_total, 6),
            "total_funding": round(funding_fee_total, 6)
        })

    return {
        "predicted_funding_rate": round(predicted_rate, 8),
        "predicted_funding_rate_annual_%": round(predicted_annual_rate, 4),
        "initial_balance": round(initial_balance, 6),
        "daily_results": result_per_day
    }

def clear_output_dir():
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"\u26a0\ufe0f 删除文件失败 {file_path}: {e}")

# === 主程序 ===
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clear_output_dir()

    if os.path.exists(SPOT_LENDING_FILE):
        with open(SPOT_LENDING_FILE, 'r', encoding='utf-8') as f:
            spot_lending_rates = json.load(f)
    else:
        spot_lending_rates = {}

    with open(NET_APY_FILE, 'r', encoding='utf-8') as f:
        coins = json.load(f)

    filtered_coins = [coin for coin in coins if abs(coin.get("net_apy", 0)) > 40]

    if len(filtered_coins) < 10:
        print(f"\u26a0\ufe0f 满足 abs(net_apy) > 40 的币只有 {len(filtered_coins)} 个，补齐前 10 个")
        coin_selection = coins[:10]
    else:
        coin_selection = filtered_coins

    for coin_info in coin_selection:
        coin = coin_info['coin']
        symbol = f"{coin}USDT"
        funding_filename = os.path.join(INPUT_DIR, f"{symbol}.json")

        try:
            with open(funding_filename, 'r', encoding='utf-8') as f:
                funding_data_raw = json.load(f)

            if isinstance(funding_data_raw, list):
                if not funding_data_raw:
                    print(f"\u274c {funding_filename} 文件为空，跳过 {coin}")
                    continue
                funding_data = funding_data_raw[0]
            else:
                funding_data = funding_data_raw

            if funding_data.get("earn_apy") is None:
                print(f"\u26a0\ufe0f {symbol} 缺少 earn_apy，将不计入 earn 收益")

            lend_rate = spot_lending_rates.get(coin.upper(), 0)
            result = simulate(funding_data, spot_sell_lend_rate=lend_rate)

            initial_balance = result['initial_balance']
            tenth_day_total = result['daily_results'][-1]['daily_total'] if len(result['daily_results']) >= days else None

            if initial_balance and tenth_day_total:
                annualized_apy = ((tenth_day_total / initial_balance) ** (365 / days)) - 1
                annualized_apy_percent = round(annualized_apy * 100, 4)
            else:
                annualized_apy_percent = None

            output_data = {
                "annualized_apy_percent": annualized_apy_percent,
                "daily_total": tenth_day_total,
                "earn_apy": funding_data.get('earn_apy'),
                "net_apy": funding_data.get('net_apy'),
                "funding_rate_annual_%": funding_data.get('funding_rate_annual_%'),
                "predicted_funding_rate_annual_%": result['predicted_funding_rate_annual_%'],
                "spot_sell_lend_rate": lend_rate,
                "symbol": symbol,
                "simulation": result
            }

            output_path = os.path.join(OUTPUT_DIR, f"{symbol}_sim.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\u2705 {symbol} 模拟结果已保存到 {output_path}")

        except FileNotFoundError:
            print(f"\u274c 文件未找到: {funding_filename}，跳过 {coin}")
        except ValueError as ve:
            print(f"\u26a0\ufe0f {symbol} 模拟失败: {ve}")
        except Exception as e:
            print(f"\u274c {symbol} 模拟过程出错: {e}")

if __name__ == "__main__":
    main()
