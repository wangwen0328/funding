from flask import Flask, jsonify, render_template
import subprocess
import json
import os
import threading
import time

# Flask 实例，模板目录默认 templates，静态目录不暴露项目根目录（默认static即可）
app = Flask(__name__, template_folder='templates')

# 当前脚本所在目录（绝对路径）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 脚本文件路径（根据你的项目结构调整）
get_earn_path = os.path.join(BASE_DIR, 'get_earn.py')
get_funding_rate_path = os.path.join(BASE_DIR, 'get_funding_rate.py')
net_apy_calc_path = os.path.join(BASE_DIR, 'net_apy_calc.py')
history_funding_rate_path = os.path.join(BASE_DIR, 'get_history_funding_rate.py')
get_suggestion_path = os.path.join(BASE_DIR, 'get_suggestion_simple.py')

# 数据文件路径
json_path = os.path.join(BASE_DIR, 'net_apy_sorted.json')
sim_result_dir = os.path.join(BASE_DIR, 'sim_results')

def run_calc_every_8_hours():
    """
    后台线程函数：首次运行相关脚本，然后每8小时自动执行一次
    """
    def job():
        print("当前工作目录:", os.getcwd())
        # 首次运行
        try:
            print("首次执行相关脚本...")
            # 根据需要取消注释，执行相关脚本
            subprocess.run(['python', get_earn_path], check=True, cwd=BASE_DIR)
            subprocess.run(['python', get_funding_rate_path], check=True, cwd=BASE_DIR)
            subprocess.run(['python', net_apy_calc_path], check=True, cwd=BASE_DIR)
            subprocess.run(['python', history_funding_rate_path], check=True, cwd=BASE_DIR)
            subprocess.run(['python', get_suggestion_path], check=True, cwd=BASE_DIR)
            print("✅ 首次执行成功")
        except Exception as e:
            print("❌ 首次执行失败:", e)

        while True:
            time.sleep(60 * 60 * 8)  # 每8小时执行一次
            try:
                print("定时执行相关脚本...")
                subprocess.run(['python', get_earn_path], check=True, cwd=BASE_DIR)
                subprocess.run(['python', get_funding_rate_path], check=True, cwd=BASE_DIR)
                subprocess.run(['python', net_apy_calc_path], check=True, cwd=BASE_DIR)
                subprocess.run(['python', history_funding_rate_path], check=True, cwd=BASE_DIR)
                subprocess.run(['python', get_suggestion_path], check=True, cwd=BASE_DIR)
                print("✅ 定时执行成功")
            except Exception as e:
                print("❌ 定时执行失败:", e)

    threading.Thread(target=job, daemon=True).start()


@app.route('/')
def index():
    """
    渲染主页模板
    """
    return render_template('index.html')


@app.route('/api/top10')
def api_top10():
    """
    返回净APY前10个币种的详细数据（包含对应模拟数据）
    """
    try:
        # 读取净APY排序JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            coin_data = json.load(f)

        top_10 = coin_data[:10]
        enriched_data = []

        for coin in top_10:
            # 确保 symbol 存在且有效
            symbol = coin.get('coin')
            if not symbol:
                coin['simulation'] = {"error": "symbol 字段缺失"}
                enriched_data.append(coin)
                continue

            sim_file = os.path.join(sim_result_dir, f"{symbol}USDT_sim.json")
            print(sim_file)
            if os.path.exists(sim_file):
                try:
                    with open(sim_file, 'r', encoding='utf-8') as sim_f:
                        sim_data = json.load(sim_f)
                    # 把模拟部分放入coin['simulation']
                    coin['simulation'] = sim_data.get('simulation', {})
                    coin['annualized_apy_percent'] = sim_data.get('annualized_apy_percent')  # ✅ 添加这一行
                except Exception as e:
                    coin['simulation'] = {"error": f"模拟文件解析错误: {e}"}
            else:
                coin['simulation'] = {"error": "模拟数据文件不存在"}

            enriched_data.append(coin)

        return jsonify(enriched_data)

    except Exception as e:
        return jsonify({'error': f"读取数据失败: {e}"}), 500


if __name__ == '__main__':
    print("启动 Flask 服务器，当前工作目录:", os.getcwd())
    run_calc_every_8_hours()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
