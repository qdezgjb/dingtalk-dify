import requests
import json
import time
import ssl
import sys
import os
import urllib3
from typing import Dict, Any, List, Optional
from requests.adapters import HTTPAdapter
from .auth import DingTalkAuth, create_custom_ssl_context
# 修改导入路径，使用相对导入
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
            # 创建会话对象
            session = requests.Session()
            session.verify = False
            
            # 优化连接池设置
            adapter = HTTPAdapter(
                pool_connections=5,  # 连接池连接数
                pool_maxsize=5,      # 连接池最大连接数
                max_retries=5,        # 最大重试次数
                pool_block=False      # 连接池用尽时不阻塞
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # 增强请求头
            headers_extended = headers.copy()
            headers_extended.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
                "Accept": "*/*",
                "Connection": "close"
            })
            
            # 添加重试机制
            for retry in range(5):
                try:
                    response = session.post(url, headers=headers_extended, json=data, timeout=30)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    error = f"发送文本消息失败 (重试 {retry+1}/5): {str(e)}"
                    dingtalk_logger.warning(error)
                    if retry == 4:  # 最后一次重试
                        raise Exception(f"发送钉钉消息失败(所有重试失败): {str(e)}")
                    time.sleep(2)  # 等待1秒后重试
            
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
        url = f"{self.base_url}/v1.0/ai/interactions/send"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth.get_access_token()}"
        }
        
        # 构建符合新API的数据格式
        data = {
            "cardData": json.dumps({
                "content": content,
                "status": status,  # loading, success, error
                "sessionId": session_id
            }),
            "cardTemplateId": self.ai_card_template_id,
            "robotCode": self.auth.client_id,
            "userIds": [user_id],
            "conversationId": session_id,
            "coolAppCode": self.auth.client_id,  # 使用client_id作为coolAppCode
            "version": "1.0"  # 添加API版本参数
        }
        
        dingtalk_logger.info(f"向用户 {user_id} 发送AI卡片, 会话ID: {session_id}, 状态: {status}")
        log_request(dingtalk_logger, "POST", url, headers, data)
        
        start_time = time.time()
        try:
            # 创建会话对象
            session = requests.Session()
            session.verify = False
            
            # 优化连接池设置
            adapter = HTTPAdapter(
                pool_connections=5,  # 连接池连接数
                pool_maxsize=5,      # 连接池最大连接数
                max_retries=5,        # 最大重试次数
                pool_block=False      # 连接池用尽时不阻塞
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # 适配各种网络环境的请求头
            headers_extended = headers.copy()
            headers_extended.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
                "Accept": "*/*",
                "Connection": "close"
            })
            
            # 增加重试次数和间隔
            for retry in range(5):
                try:
                    response = session.post(url, headers=headers_extended, json=data, timeout=30)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    error = f"发送卡片失败 (重试 {retry+1}/5): {str(e)}"
                    dingtalk_logger.warning(error)
                    if retry == 4:  # 最后一次重试
                        raise Exception(f"发送钉钉AI卡片失败(所有重试失败): {str(e)}")
                    time.sleep(2)  # 增加重试间隔
            
            elapsed_time = time.time() - start_time
            log_response(dingtalk_logger, response, elapsed_time)
            
            if response.status_code != 200:
                error_msg = f"发送钉钉AI卡片失败: {response.text}"
                dingtalk_logger.error(error_msg)
                raise Exception(error_msg)
            
            resp_json = response.json()
            dingtalk_logger.info(f"成功向用户 {user_id} 发送AI卡片, 响应: {resp_json}")
            return resp_json
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"发送钉钉AI卡片异常: {str(e)}"
            dingtalk_logger.error(error_msg)
            raise Exception(error_msg)
    
    def update_ai_card(self, card_instance_id: str, content: str, is_finalize: bool = False, is_error: bool = False) -> Dict[str, Any]:
        """更新AI卡片内容
        
        Args:
            card_instance_id: 卡片实例ID
            content: 更新的内容
            is_finalize: 是否是最终更新，完成打字机效果
            is_error: 是否是错误状态
        """
        # 使用官方流式更新API
        url = f"{self.base_url}/v1.0/ai/interactions/streamUpdate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth.get_access_token()}"
        }
        
        data = {
            "cardInstanceId": card_instance_id,
            "cardData": json.dumps({
                "content": content
            }),
            "isFinalize": is_finalize,
            "isError": is_error,
            "version": "1.0"  # 添加API版本参数
        }
        
        status = "success" if is_finalize else "error" if is_error else "updating"
        dingtalk_logger.debug(f"更新AI卡片 {card_instance_id}, 状态: {status}, 内容长度: {len(content)}")
        log_request(dingtalk_logger, "POST", url, headers, data)
        
        start_time = time.time()
        try:
            # 创建会话对象
            session = requests.Session()
            session.verify = False
            
            # 优化连接池设置
            adapter = HTTPAdapter(
                pool_connections=5,  # 连接池连接数
                pool_maxsize=5,      # 连接池最大连接数
                max_retries=5,        # 最大重试次数
                pool_block=False      # 连接池用尽时不阻塞
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # 增强请求头
            headers_extended = headers.copy()
            headers_extended.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
                "Accept": "*/*",
                "Connection": "close"
            })
            
            # 添加重试机制
            for retry in range(5):
                try:
                    response = session.post(url, headers=headers_extended, json=data, timeout=30)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    error = f"更新卡片失败 (重试 {retry+1}/5): {str(e)}"
                    dingtalk_logger.warning(error)
                    if retry == 4:  # 最后一次重试
                        raise Exception(f"更新钉钉AI卡片失败(所有重试失败): {str(e)}")
                    time.sleep(2)  # 等待1秒后重试
            
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