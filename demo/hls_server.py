from flask import Flask, send_from_directory, render_template, request
import os
import argparse
from datetime import datetime


app = Flask(__name__)
app.config['HLS_FOLDER'] = 'outputs'  # 对应你的HLS输出目录

@app.route('/')
def index():
    return render_template('player.html')

@app.route('/upload/<path:filename>', methods=['POST'])
def upload_file(filename):
    """接收推流请求并保存文件"""
    file_path = os.path.join(app.config['HLS_FOLDER'], filename)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # 保存文件内容
    with open(file_path, 'wb') as f:
        f.write(request.get_data())
    
    return f"File {filename} uploaded successfully", 200

@app.route('/hls/<path:filename>')
def hls_files(filename):
    return send_from_directory(
        app.config['HLS_FOLDER'],
        filename,
        mimetype='application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/MP2T'
    )
    
@app.route('/stream/<path:stream_name>', methods=['POST'])
def receive_stream(stream_name):
    # 根据Content-Type判断文件类型
    if request.headers['Content-Type'] == 'application/vnd.apple.mpegurl':
        filename = "playlist.m3u8"
    else:
        filename = f"segment{datetime.now().timestamp()}.ts"
    
    # 保存到对应目录
    save_path = os.path.join(app.config['HLS_FOLDER'], stream_name, filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, 'ab') as f:  # 追加模式允许分块上传
        f.write(request.get_data())
    
    return "Chunk received", 200

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='HLS Server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()

    # 创建输出目录（如果不存在）
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs'), exist_ok=True)
    # 启动服务器（端口可自定义）
    app.run(host='0.0.0.0', port=args.port, debug=True)