import json
import os
from datetime import datetime, timedelta

days = 10
principal = 1000
hedge_fee_rate = 0.0032  # 0.32%手续费

INPUT_DIR = "funding_data"
OUTPUT_DIR = "sim_results"

def weighted_moving_average(values):
    n = len(values)
    if n == 0:
        return 0.0
    weights = list(range(1, n + 1))
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / sum(weights)

def simulate(funding_data):
    earn_apy = funding_data['earn_apy'] / 100
    funding_interval_hours = int(funding_data['current_funding_rate'][0]['fundingRateInterval'])
    fundings_per_day = 24 // funding_interval_hours

    funding_rates = [float(entry['fundingRate']) for entry in funding_data['history']]
    predicted_rate = weighted_moving_average(funding_rates)

    initial_balance = principal * (1 - hedge_fee_rate)
    balance = initial_balance
    daily_earn_rate = earn_apy / 365
    funding_fee_total = 0
    earn_total = 0
    result_per_day = []

    today = datetime.now()

    for i in range(1, days + 1):
        date_str = (today + timedelta(days=i)).strftime('%Y-%m-%d')

        earn_gain = balance * daily_earn_rate
        balance += earn_gain
        earn_total += earn_gain

        funding_gain = balance * predicted_rate * fundings_per_day
        balance += funding_gain
        funding_fee_total += funding_gain

        result_per_day.append({
            "date": date_str,
            "earn_interest": round(earn_gain, 4),
            "funding_income": round(funding_gain, 4),
            "daily_total": round(balance, 4),
            "total_earn": round(earn_total, 4),
            "total_funding": round(funding_fee_total, 4)
        })

    return {
        "predicted_funding_rate": round(predicted_rate, 6),
        "initial_balance": round(initial_balance, 4),
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
                    print(f"⚠️ 删除文件失败 {file_path}: {e}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clear_output_dir()  # 先删除旧文件

    with open('net_apy_sorted.json', 'r', encoding='utf-8') as f:
        coins = json.load(f)

    for coin_info in coins[:10]:  # 只处理前10个币
        coin = coin_info['coin']
        symbol = f"{coin}USDT"
        funding_filename = os.path.join(INPUT_DIR, f"{symbol}.json")

        try:
            with open(funding_filename, 'r', encoding='utf-8') as f:
                funding_data_raw = json.load(f)

            # 若文件内容为数组（兼容旧格式）
            if isinstance(funding_data_raw, list):
                if not funding_data_raw:
                    print(f"❌ {funding_filename} 文件为空，跳过 {coin}")
                    continue
                funding_data = funding_data_raw[0]
            else:
                funding_data = funding_data_raw

        except FileNotFoundError:
            print(f"❌ 文件未找到: {funding_filename}，跳过 {coin}")
            continue

        result = simulate(funding_data)
        # 取出初始余额和第10天总额
        initial_balance = result['initial_balance']
        tenth_day_total = result['daily_results'][-1]['daily_total'] if len(result['daily_results']) >= 10 else None

        # 计算实际年化收益率
        if initial_balance and tenth_day_total:
            annualized_apy = ((tenth_day_total / initial_balance) ** (365 / days)) - 1
            annualized_apy_percent = round(annualized_apy * 100, 4)
        else:
            annualized_apy_percent = None

        output_data = {
            "annualized_apy_percent": annualized_apy_percent, 
            "daily_total": tenth_day_total, 
            "earn_apy": funding_data['earn_apy'],
            "net_apy": funding_data.get('net_apy'),  # 加上net_apy
            "funding_rate_annual_%": funding_data['funding_rate_annual_%'],
            "symbol": symbol,
            "simulation": result
        }

        output_path = os.path.join(OUTPUT_DIR, f"{symbol}_sim.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"✅ {symbol} 模拟结果已保存到 {output_path}")

if __name__ == "__main__":
    main()
