from flask import Flask, jsonify, render_template
import subprocess
import json
import os
import threading
import time

app = Flask(__name__)

# 获取当前文件的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 设置脚本路径
script_path = os.path.join(BASE_DIR, 'net_apy_calc.py')
json_path = os.path.join(BASE_DIR, 'net_apy_sorted.json')

# 定时任务线程函数
def run_calc_every_10_min():
    def job():
        while True:
            time.sleep(60)  # 每 10 分钟执行一次
            try:
                print("定时执行 net_apy_calc.py ...")
                subprocess.run(['python', script_path], check=True, cwd=os.path.dirname(script_path))
                print("✅ 定时执行成功")
            except Exception as e:
                print("❌ 定时执行失败:", e)

    # 启动后台线程
    threading.Thread(target=job, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/top5')
def api_top5():
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data[:5])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 启动 Flask 前，启动定时后台任务
    run_calc_every_10_min()

    port = int(os.environ.get('PORT', 5000))    
    app.run(host='0.0.0.0', port=port)

