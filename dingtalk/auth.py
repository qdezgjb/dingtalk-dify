import time
import requests
import ssl
from typing import Dict, Any
import urllib3
import certifi
from requests.adapters import HTTPAdapter

# 禁用SSL警告
urllib3.disable_warnings()

# 创建一个完全不验证的SSL上下文
def create_custom_ssl_context():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

class DingTalkAuth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.expires_at = 0
    
    def get_access_token(self) -> str:
        """获取钉钉访问令牌"""
        current_time = int(time.time())
        
        # 如果令牌存在且未过期，则直接返回
        if self.access_token and self.expires_at > current_time:
            return self.access_token
        
        # 获取新的访问令牌
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        data = {
            "appKey": self.client_id,
            "appSecret": self.client_secret
        }
        
        try:
            # 创建一个会话对象并设置自定义SSL上下文
            session = requests.Session()
            # 完全关闭验证
            session.verify = False
            # 设置超时时间
            timeout = 30
            
            # 优化连接设置
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=5,  # 连接池连接数
                pool_maxsize=5,      # 连接池最大连接数
                max_retries=5,        # 最大重试次数
                pool_block=False      # 连接池用尽时不阻塞
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # 适配各种网络环境的请求头
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
                "Accept": "*/*",
                "Connection": "close"
            }
            
            # 添加重试机制
            for retry in range(5):  # 增加重试次数到5次
                try:
                    # 使用会话对象进行请求
                    response = session.post(url, json=data, headers=headers, timeout=timeout)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    error = f"获取访问令牌失败 (重试 {retry+1}/5): {str(e)}"
                    print(error)
                    if retry == 4:  # 最后一次重试
                        raise Exception(f"获取钉钉访问令牌失败(所有重试失败): {str(e)}")
                    time.sleep(2)  # 增加重试间隔
            
            if response.status_code != 200:
                raise Exception(f"获取钉钉访问令牌失败: {response.text}")
            
            result = response.json()
            self.access_token = result["accessToken"]
            # 提前5分钟过期，避免边界问题
            self.expires_at = current_time + result["expireIn"] - 300
            
            return self.access_token
        except Exception as e:
            # 捕获并记录详细错误
            error_msg = f"获取钉钉访问令牌异常: {str(e)}"
            print(error_msg)  # 直接打印错误，确保在Docker日志中可见
            raise Exception(error_msg) 