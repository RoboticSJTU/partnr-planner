from flask import Flask, send_from_directory, render_template
import os
import argparse

app = Flask(__name__)
app.config['HLS_FOLDER'] = 'outputs'  # 对应你的HLS输出目录

@app.route('/')
def index():
    return render_template('player.html')

@app.route('/hls/<path:filename>')
def hls_files(filename):
    return send_from_directory(
        app.config['HLS_FOLDER'],
        filename,
        mimetype='application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/MP2T'
    )

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='HLS Server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()

    # 创建输出目录（如果不存在）
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs'), exist_ok=True)
    # 启动服务器（端口可自定义）
    app.run(host='0.0.0.0', port=args.port, debug=True)