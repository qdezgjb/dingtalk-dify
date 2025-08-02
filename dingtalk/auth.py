import time
import requests
from typing import Dict, Any
import urllib3

# 禁用SSL警告
urllib3.disable_warnings()

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
            # 添加重试机制和禁用SSL验证
            for retry in range(3):  # 最多重试3次
                try:
                    # 禁用SSL验证
                    response = requests.post(url, json=data, verify=False, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    if retry == 2:  # 最后一次重试
                        raise Exception(f"获取钉钉访问令牌失败(SSL/连接错误): {str(e)}")
                    time.sleep(1)  # 等待1秒后重试
            
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