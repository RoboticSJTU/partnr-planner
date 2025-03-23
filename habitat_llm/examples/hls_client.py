import requests
import os
from io import BytesIO

class HLSClient:
    def __init__(self, server_url):
        self.server_url = server_url.rstrip('/')
    def push_stream(self, stream_name: str):
        """开启一个流式上传会话"""
        self.session = requests.Session()
        self.stream_url = f"{self.server_url}/stream/{stream_name}"
    
    def send_chunk(self, chunk: bytes, is_video: bool = True):
        """发送数据块"""
        headers = {
            "Content-Type": "video/MP2T" if is_video else "application/vnd.apple.mpegurl"
        }
        self.session.post(
            self.stream_url,
            data=chunk,
            headers=headers
        )
        
    def push_file(self, content: bytes, target_path: str):
        """
        推送内存数据到服务器
        :param content: 二进制内容（空字节表示创建目录）
        :param target_path: 目标路径
        """
        try:
            # 创建父目录
            dir_path = os.path.dirname(target_path)
            if dir_path:
                self._ensure_directory(dir_path)
            
            # 上传文件内容
            if content:
                response = requests.post(
                    f"{self.server_url}/upload/{target_path}",
                    data=content
                )
                return response.status_code == 200
            return True
        except Exception as e:
            print(f"推送失败: {str(e)}")
            return False

    def _ensure_directory(self, dir_path: str):
        """确保服务器目录存在"""
        dirs = dir_path.split('/')
        current_path = ""
        for dir_name in dirs:
            current_path = f"{current_path}/{dir_name}" if current_path else dir_name
            if not self._check_path_exists(current_path):
                requests.post(
                    f"{self.server_url}/upload/{current_path}",
                    data=b''  # 空内容表示创建目录
                )

    def _check_path_exists(self, path: str) -> bool:
        """检查路径是否存在"""
        try:
            response = requests.head(f"{self.server_url}/hls/{path}")
            return response.status_code == 200
        except:
            return False