from flask import Flask, jsonify, render_template
import subprocess
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/top5')
def api_top5():
    try:
        # 执行你的3个脚本（每个都确保有 main 入口或能直接运行）
        #subprocess.run(['python', 'project/get_funding_rate.py'], check=True)
        #subprocess.run(['python', 'project/get_earn.py'], check=True)
        subprocess.run(['python', 'project/net_apy_calc.py'], check=True)

        # 然后读取最终的 JSON 文件
        with open('net_apy_sorted.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 只返回前 5 个
        return jsonify(data[:5])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
