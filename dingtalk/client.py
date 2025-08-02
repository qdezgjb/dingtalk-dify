import requests
import json
import time
from typing import Dict, Any, List, Optional
from .auth import DingTalkAuth
# 修改导入路径，使用相对导入
import sys
import os
import urllib3
# 将项目根目录添加到模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import dingtalk_logger, log_request, log_response

# 禁用SSL警告
urllib3.disable_warnings()

class DingTalkClient:
    def __init__(self, auth: DingTalkAuth, ai_card_template_id: str):
        self.auth = auth
        self.ai_card_template_id = ai_card_template_id
        self.base_url = "https://api.dingtalk.com"
    
    def send_text_message(self, user_id: str, content: str) -> Dict[str, Any]:
        """发送文本消息"""
        url = f"{self.base_url}/v1.0/robot/sendMessage"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth.get_access_token()}"
        }
        
        data = {
            "robotCode": self.auth.client_id,
            "userIds": [user_id],
            "msgParam": json.dumps({"content": content}),
            "msgKey": "sampleText"
        }
        
        dingtalk_logger.info(f"向用户 {user_id} 发送文本消息")
        log_request(dingtalk_logger, "POST", url, headers, data)
        
        start_time = time.time()
        try:
            # 添加重试机制
            for retry in range(3):
                try:
                    # 禁用SSL验证
                    response = requests.post(url, headers=headers, json=data, verify=False, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    if retry == 2:  # 最后一次重试
                        raise Exception(f"发送钉钉消息失败(SSL/连接错误): {str(e)}")
                    time.sleep(1)  # 等待1秒后重试
            
            elapsed_time = time.time() - start_time
            log_response(dingtalk_logger, response, elapsed_time)
            
            if response.status_code != 200:
                error_msg = f"发送钉钉消息失败: {response.text}"
                dingtalk_logger.error(error_msg)
                raise Exception(error_msg)
            
            dingtalk_logger.info(f"成功向用户 {user_id} 发送文本消息")
            return response.json()
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"发送钉钉消息异常: {str(e)}"
            dingtalk_logger.error(error_msg)
            raise Exception(error_msg)
    
    def send_ai_card(self, user_id: str, session_id: str, content: str = "", status: str = "loading") -> Dict[str, Any]:
        """发送AI卡片"""
        # 修改为正确的API接口URL
        url = f"{self.base_url}/v1.0/robot/aiInteractions/send"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth.get_access_token()}"
        }
        
        data = {
            "cardData": json.dumps({
                "content": content,
                "status": status,  # loading, success, error
                "sessionId": session_id
            }),
            "cardTemplateId": self.ai_card_template_id,
            "robotCode": self.auth.client_id,
            "userIds": [user_id],
            "conversationId": session_id
        }
        
        dingtalk_logger.info(f"向用户 {user_id} 发送AI卡片, 会话ID: {session_id}, 状态: {status}")
        log_request(dingtalk_logger, "POST", url, headers, data)
        
        start_time = time.time()
        try:
            # 添加重试机制
            for retry in range(3):
                try:
                    # 禁用SSL验证
                    response = requests.post(url, headers=headers, json=data, verify=False, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    if retry == 2:  # 最后一次重试
                        raise Exception(f"发送钉钉AI卡片失败(SSL/连接错误): {str(e)}")
                    time.sleep(1)  # 等待1秒后重试
            
            elapsed_time = time.time() - start_time
            log_response(dingtalk_logger, response, elapsed_time)
            
            if response.status_code != 200:
                error_msg = f"发送钉钉AI卡片失败: {response.text}"
                dingtalk_logger.error(error_msg)
                raise Exception(error_msg)
            
            dingtalk_logger.info(f"成功向用户 {user_id} 发送AI卡片")
            return response.json()
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"发送钉钉AI卡片异常: {str(e)}"
            dingtalk_logger.error(error_msg)
            raise Exception(error_msg)
    
    def update_ai_card(self, card_instance_id: str, content: str, status: str = "success") -> Dict[str, Any]:
        """更新AI卡片内容"""
        # 修改为正确的API接口URL
        url = f"{self.base_url}/v1.0/robot/aiInteractions/streamUpdate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth.get_access_token()}"
        }
        
        # 根据状态确定是否是最终更新
        is_finalize = status == "success"
        is_error = status == "error"
        
        data = {
            "cardInstanceId": card_instance_id,
            "cardData": json.dumps({
                "content": content
            }),
            "isFinalize": is_finalize,
            "isError": is_error
        }
        
        dingtalk_logger.debug(f"更新AI卡片 {card_instance_id}, 状态: {status}, 内容长度: {len(content)}")
        log_request(dingtalk_logger, "POST", url, headers, data)
        
        start_time = time.time()
        try:
            # 添加重试机制
            for retry in range(3):
                try:
                    # 禁用SSL验证
                    response = requests.post(url, headers=headers, json=data, verify=False, timeout=30)
                    if response.status_code == 200:
                        break
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    if retry == 2:  # 最后一次重试
                        raise Exception(f"更新钉钉AI卡片失败(SSL/连接错误): {str(e)}")
                    time.sleep(1)  # 等待1秒后重试
            
            elapsed_time = time.time() - start_time
            log_response(dingtalk_logger, response, elapsed_time)
            
            if response.status_code != 200:
                error_msg = f"更新钉钉AI卡片失败: {response.text}"
                dingtalk_logger.error(error_msg)
                raise Exception(error_msg)
            
            return response.json()
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"更新钉钉AI卡片异常: {str(e)}"
            dingtalk_logger.error(error_msg)
            raise Exception(error_msg) 