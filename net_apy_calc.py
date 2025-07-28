import json
print("net_apy_calc")
with open("earn_products.json", "r", encoding="utf-8") as f:
    earn_data = json.load(f)

with open("all_funding_rates.json", "r", encoding="utf-8") as f:
    funding_data = json.load(f)

# 提取 earn 年化收益
earn_apys = {}
for item in earn_data.get("data", []):
    coin = item["coin"].upper()
    apy_list = item.get("apyList", [])
    if apy_list:
        try:
            apy = float(apy_list[0]["currentApy"])
            earn_apys[coin] = apy
        except:
            pass

# 检查是否存在负资金费率
has_negative_funding = False
for rates in funding_data.values():
    if rates:
        funding_rate = float(rates[0]["fundingRate"])
        if funding_rate < 0:
            has_negative_funding = True
            break

print(f"是否存在负资金费率？ {'是' if has_negative_funding else '否'}")

# 计算净年化收益
results = []
for symbol, rates in funding_data.items():
    if not rates:
        continue
    funding_rate = float(rates[0]["fundingRate"])
    base_coin = symbol.replace("USDT", "").upper()
    earn_apy = earn_apys.get(base_coin)
    if earn_apy is None:
        continue

    funding_annual = funding_rate * 3 * 365  # 资金费率换算成年化（小数）

    net_apy = earn_apy + funding_annual * 100  # 资金费率转%加减

    results.append({
        "coin": base_coin,
        "earn_apy": earn_apy,
        "funding_rate_annual_%": round(funding_annual * 100, 6),
        "net_apy": round(net_apy, 6)
    })

# 按净收益降序排序
results.sort(key=lambda x: x["net_apy"], reverse=True)

# 保存文件
with open("net_apy_sorted.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
