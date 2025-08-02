#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钉钉-Dify 流式适配器

本次更新主要增加了流式输出功能：
1. 优化了普通文本消息的流式输出逻辑，提高了更新频率
2. 新增了AI卡片流式输出方式，提供更好的用户体验
3. 增加了配置选项，允许用户选择流式输出方式
   - ai_card: 使用钉钉AI卡片实现流式输出(默认推荐模式)
   - text: 使用普通文本消息实现流式输出

使用AI卡片流式输出需要在钉钉卡片平台创建AI卡片模板，
并将模板ID填入配置文件的dingtalk.ai_card_template_id字段。
还需要申请权限点：Card.Streaming.Write

配置示例：
{
  "adapter": {
    "stream_mode": "ai_card"  # 流式输出模式：ai_card(AI卡片)或text(普通文本)
  }
}

钉钉卡片平台地址：https://card.dingtalk.com/card-builder
"""

import os
import sys

# 添加当前目录到Python模块搜索路径，确保可以导入本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import json
import time
import uuid
import asyncio
import requests
from typing import Dict, Any, Optional

# 导入增强版日志系统
from utils.logger import app_logger, dingtalk_logger, dify_logger

# 禁用所有SSL警告和验证
import urllib3
urllib3.disable_warnings()
# 彻底禁用SSL验证
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_SSL_VERIFY'] = '0'

# 替换requests库的默认SSL验证设置
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 设置requests库默认不验证SSL
requests.packages.urllib3.disable_warnings()
old_merge_environment_settings = requests.Session.merge_environment_settings

def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    if verify is True:
        verify = False
    return old_merge_environment_settings(self, url, proxies, stream, verify, cert)

requests.Session.merge_environment_settings = new_merge_environment_settings

from dingtalk_stream import DingTalkStreamClient
from dingtalk_stream import Credential
from dingtalk_stream import AckMessage
from dingtalk_stream import ChatbotMessage
from dingtalk_stream import AsyncChatbotHandler

# 修改导入路径，使用.dingtalk形式导入
try:
    # 本地开发环境
    from dingtalk.client import DingTalkClient
    from dingtalk.auth import DingTalkAuth
except ModuleNotFoundError:
    try:
        # Docker环境或其他环境
        from dingtalk.dingtalk.client import DingTalkClient
        from dingtalk.dingtalk.auth import DingTalkAuth
    except ModuleNotFoundError:
        # 最后尝试直接导入
        from dingtalk_client import DingTalkClient
        from dingtalk_auth import DingTalkAuth

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

# 配置文件路径
CONFIG_PATH = "config.json"

# 加载配置
def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        app_logger.info(f"成功加载配置文件: {config_path}")
        
        # 添加默认值
        if "stream_mode" not in config["adapter"]:
            config["adapter"]["stream_mode"] = "ai_card"  # 修改为默认使用AI卡片流式输出
        
        return config
    except Exception as e:
        app_logger.error(f"加载配置文件失败: {str(e)}")
        raise

CONFIG = load_config(CONFIG_PATH)

class DifyClient:
    """Dify API客户端，用于调用Dify API进行文本或聊天完成"""
    
    def __init__(self, api_base: str, api_key: str, app_type: str = "completion"):
        """
        初始化Dify客户端
        
        Args:
            api_base: Dify API基础URL，例如 https://api.dify.ai/v1
            api_key: Dify API密钥
            app_type: 应用类型，可选 'chat' 或 'completion'
        """
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.app_type = app_type
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def completion(self, query: str, user: Optional[str] = None, stream: bool = True) -> Dict[str, Any]:
        """
        调用Dify完成接口
        
        Args:
            query: 用户输入
            user: 用户标识
            stream: 是否使用流式响应
            
        Returns:
            响应数据或生成器
        """
        endpoint = f"{self.api_base}/completion"
        
        data = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming" if stream else "blocking",
            "user": user if user else "anonymous"
        }
        
        dify_logger.info(f"发送完成请求到 {endpoint}: 用户={user}, 流式输出={stream}")
        
        return self._send_request(endpoint, data, stream)
    
    def chat_completion(self, query: str, conversation_id: Optional[str] = None, 
                       user: Optional[str] = None, stream: bool = True) -> Dict[str, Any]:
        """
        调用Dify聊天完成接口
        
        Args:
            query: 用户输入
            conversation_id: 会话ID，用于维持上下文
            user: 用户标识
            stream: 是否使用流式响应
            
        Returns:
            响应数据或生成器
        """
        endpoint = f"{self.api_base}/chat-messages"
        
        data = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming" if stream else "blocking",
            "user": user if user else "anonymous"
        }
        
        if conversation_id:
            data["conversation_id"] = conversation_id
        
        dify_logger.info(f"发送聊天请求到 {endpoint}: 用户={user}, 会话ID={conversation_id}, 流式输出={stream}")
        
        return self._send_request(endpoint, data, stream)
    
    def _send_request(self, endpoint: str, data: Dict[str, Any], stream: bool = True) -> Dict[str, Any]:
        """
        发送请求到Dify API
        
        Args:
            endpoint: API端点URL
            data: 请求数据
            stream: 是否使用流式响应
            
        Returns:
            响应数据或生成器
        """
        try:
            response = requests.post(
                endpoint, 
                headers=self.headers, 
                json=data, 
                stream=stream, 
                verify=False, 
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = f"Dify API请求失败: 状态码={response.status_code}, 响应={response.text}"
                dify_logger.error(error_msg)
                raise Exception(error_msg)
            
            if stream:
                dify_logger.info("开始接收流式响应")
                return self._handle_stream_response(response)
            else:
                dify_logger.info("成功接收阻塞式响应")
                return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Dify API请求异常: {str(e)}"
            dify_logger.error(error_msg)
            raise Exception(error_msg)
    
    def _handle_stream_response(self, response) -> Dict[str, Any]:
        """
        处理流式响应
        
        Args:
            response: 流式响应对象
            
        Returns:
            累积的响应数据或生成器
        
        Yields:
            每个数据块
        """
        try:
            import sseclient
            
            client = sseclient.SSEClient(response)
            accumulated_data = {"answer": ""}  # 确保answer字段始终存在
            chunk_count = 0
            
            for event in client.events():
                if event.data.strip():  # 忽略空行
                    try:
                        chunk = json.loads(event.data)
                        # 合并数据
                        for key, value in chunk.items():
                            if key not in accumulated_data:
                                accumulated_data[key] = value
                            elif key == "answer":
                                accumulated_data[key] += value
                        
                        chunk_count += 1
                        
                        # 每10个块记录一次，避免日志过多
                        if chunk_count % 10 == 0:
                            dify_logger.debug(f"接收流式响应块 #{chunk_count}")
                        
                        yield chunk
                    except json.JSONDecodeError as e:
                        dify_logger.warning(f"解析JSON数据块失败: {str(e)}")
                        continue
                    except Exception as e:
                        dify_logger.warning(f"处理数据块时出错: {str(e)}")
                        continue
                        
            dify_logger.info(f"流式响应完成，共 {chunk_count} 个数据块")
            return accumulated_data
        except Exception as e:
            dify_logger.error(f"处理流式响应时出错: {str(e)}")
            raise

# 会话管理
class SessionManager:
    def __init__(self, timeout: int = 1800):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.timeout = timeout
    
    def get_session(self, user_id: str) -> Dict[str, Any]:
        """获取用户会话"""
        current_time = int(time.time())
        
        if user_id in self.sessions:
            session = self.sessions[user_id]
            if current_time - session.get("last_activity", 0) <= self.timeout:
                session["last_activity"] = current_time
                return session
        
        # 创建新会话
        session = {
            "conversation_id": None,  # 初始化为None，首次对话不传递conversation_id
            "last_activity": current_time,
            "card_instance_id": None
        }
        self.sessions[user_id] = session
        return session
    
    def clear_expired_sessions(self):
        """清理过期会话"""
        current_time = int(time.time())
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if current_time - session.get("last_activity", 0) > self.timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]

# 创建会话管理器
session_manager = SessionManager(CONFIG["adapter"].get("timeout", 1800))

class DifyHandler(AsyncChatbotHandler):
    """钉钉机器人回调处理"""
    
    def __init__(self, dingtalk_client_id, dingtalk_client_secret, ai_card_template_id,
                dify_api_base, dify_api_key, dify_app_type):
        super().__init__()
        self.dingtalk_client_id = dingtalk_client_id
        self.dingtalk_client_secret = dingtalk_client_secret
        self.ai_card_template_id = ai_card_template_id
        
        # 初始化Dify客户端
        self.dify_client = DifyClient(dify_api_base, dify_api_key, dify_app_type)
        
        # 记录访问令牌
        self.access_token = None
        self.token_expires_at = 0
    
    def get_access_token(self) -> str:
        """获取钉钉访问令牌"""
        current_time = int(time.time())
        
        # 如果令牌存在且未过期，则直接返回
        if self.access_token and self.token_expires_at > current_time:
            return self.access_token
        
        # 获取新的访问令牌
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        data = {
            "appKey": self.dingtalk_client_id,
            "appSecret": self.dingtalk_client_secret
        }
        
        response = requests.post(url, json=data, verify=False)  # 禁用SSL验证
        if response.status_code != 200:
            error_msg = f"获取钉钉访问令牌失败: {response.text}"
            dingtalk_logger.error(error_msg)
            raise Exception(error_msg)
        
        result = response.json()
        self.access_token = result["accessToken"]
        # 提前5分钟过期，避免边界问题
        self.token_expires_at = current_time + result["expireIn"] - 300
        
        return self.access_token
    
    def process(self, callback):
        """处理钉钉机器人消息"""
        try:
            # 解析消息
            incoming_message = ChatbotMessage.from_dict(callback.data)
            
            # 正确获取消息内容
            # 根据钉钉Stream SDK的定义，incoming_message.text是TextContent对象，需要获取其content属性
            if hasattr(incoming_message, 'text') and hasattr(incoming_message.text, 'content'):
                message_content = incoming_message.text.content
            else:
                message_content = str(incoming_message.text)  # 降级处理
                
            dingtalk_logger.info(f"收到消息: {message_content}")
            user_id = incoming_message.sender_staff_id
            
            # 获取会话
            session = session_manager.get_session(user_id)
            conversation_id = session.get("conversation_id")
            dingtalk_logger.debug(f"会话信息: user_id={user_id}, conversation_id={conversation_id}")
            
            try:
                # 发送初始消息 - 改用普通文本消息而非AI卡片
                self.reply_text("思考中...", incoming_message)
            except Exception as e:
                dingtalk_logger.warning(f"发送初始响应失败，可能是SSL错误: {str(e)}")
                # 继续处理，不中断流程
            
            # 处理Dify请求
            accumulated_text = ""
            
            # 根据应用类型调用不同的接口
            if CONFIG["dify"]["app_type"] == "chat":
                dingtalk_logger.debug("使用chat模式处理请求")
                params = {
                    "query": message_content,
                    "user": user_id,
                    "stream": True
                }
                # 只有在会话ID存在时才传递
                if conversation_id:
                    params["conversation_id"] = conversation_id
                    dingtalk_logger.info(f"使用现有会话ID: {conversation_id}")
                else:
                    dingtalk_logger.info("首次对话，不传递会话ID")
                    
                response_generator = self.dify_client.chat_completion(**params)
            else:  # completion, workflow或其他类型
                dingtalk_logger.debug("使用completion模式处理请求")
                response_generator = self.dify_client.completion(
                    query=message_content,
                    user=user_id,
                    stream=True
                )
            
            # 处理流式响应
            update_count = 0
            last_update_time = time.time()
            chunk = None
            update_interval = 0.5  # 更新间隔时间，单位秒，可根据需求调整
            min_token_count = 10   # 至少累积的字符数，避免过于频繁更新
            token_buffer = ""      # 字符缓冲区
            
            for chunk in response_generator:
                if "answer" in chunk:
                    answer_delta = chunk.get("answer", "")
                    accumulated_text += answer_delta
                    token_buffer += answer_delta
                    
                    # 控制更新频率
                    current_time = time.time()
                    update_condition = (current_time - last_update_time >= update_interval and 
                                       len(token_buffer) >= min_token_count)
                    
                    if update_condition:
                        try:
                            # 使用流式输出更新消息
                            update_count += 1
                            self.reply_text(accumulated_text, incoming_message)
                            last_update_time = current_time
                            token_buffer = ""  # 清空缓冲区
                            dingtalk_logger.debug(f"流式更新消息内容 #{update_count}, 长度: {len(accumulated_text)}")
                        except Exception as e:
                            dingtalk_logger.warning(f"更新消息失败: {str(e)}")
            
            try:
                # 最终发送完整响应，确保所有内容都已展示
                if token_buffer or update_count == 0:  # 如果有未发送的内容或者从未更新过
                    self.reply_text(accumulated_text, incoming_message)
                    dingtalk_logger.debug(f"发送最终消息, 长度: {len(accumulated_text)}")
                
                dingtalk_logger.info(f"完成处理用户 {user_id} 的Dify请求，最终响应长度: {len(accumulated_text)}")
            except Exception as e:
                dingtalk_logger.warning(f"发送最终响应失败: {str(e)}")
            
            # 如果是chat类型，保存conversation_id
            if CONFIG["dify"]["app_type"] == "chat" and chunk and "conversation_id" in chunk:
                new_conversation_id = chunk.get("conversation_id")
                dingtalk_logger.debug(f"更新会话ID: {conversation_id} -> {new_conversation_id}")
                session["conversation_id"] = new_conversation_id
                
            return AckMessage.STATUS_OK, 'OK'
                
        except Exception as e:
            dingtalk_logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            error_text = f"很抱歉，处理您的消息时出错: {str(e)}"
            try:
                self.reply_text(error_text, incoming_message)
            except Exception as reply_error:
                dingtalk_logger.error(f"发送错误回复失败: {str(reply_error)}")
            return AckMessage.STATUS_OK, 'Error'

    def process_with_ai_card(self, callback):
        """使用AI卡片处理钉钉机器人消息（流式输出）"""
        try:
            # 解析消息
            incoming_message = ChatbotMessage.from_dict(callback.data)
            
            # 正确获取消息内容
            if hasattr(incoming_message, 'text') and hasattr(incoming_message.text, 'content'):
                message_content = incoming_message.text.content
            else:
                message_content = str(incoming_message.text)  # 降级处理
                
            dingtalk_logger.info(f"收到消息: {message_content}")
            user_id = incoming_message.sender_staff_id
            
            # 获取会话
            session = session_manager.get_session(user_id)
            conversation_id = session.get("conversation_id")
            dingtalk_logger.debug(f"会话信息: user_id={user_id}, conversation_id={conversation_id}")
            
            # 创建AI卡片会话ID，使用会话ID以保持会话连贯性
            card_session_id = str(uuid.uuid4()) if not session.get("card_session_id") else session.get("card_session_id")
            session["card_session_id"] = card_session_id
            
            # 获取钉钉客户端
            dingtalk_client = DingTalkClient(
                DingTalkAuth(self.dingtalk_client_id, self.dingtalk_client_secret),
                self.ai_card_template_id
            )
            
            # 检查之前的卡片是否存在
            previous_card_id = session.get("card_instance_id")
            
            # 发送初始AI卡片（加载状态）
            try:
                # 如果已有之前的卡片，则更新它而不是创建新卡片
                if previous_card_id:
                    try:
                        dingtalk_client.update_ai_card(
                            card_instance_id=previous_card_id,
                            content="思考中...",
                            status="loading"
                        )
                        card_instance_id = previous_card_id
                        dingtalk_logger.info(f"更新已有AI卡片，实例ID: {card_instance_id}")
                    except Exception as update_error:
                        dingtalk_logger.warning(f"更新已有卡片失败，将创建新卡片: {str(update_error)}")
                        previous_card_id = None
                
                # 如果没有之前的卡片或更新失败，则创建新卡片
                if not previous_card_id:
                    card_response = dingtalk_client.send_ai_card(
                        user_id=user_id,
                        session_id=card_session_id,
                        content="思考中...",
                        status="loading"
                    )
                    # 记录卡片实例ID，用于后续更新
                    card_instance_id = card_response.get("cardInstanceId")
                    dingtalk_logger.info(f"成功创建AI卡片，实例ID: {card_instance_id}")
                
                # 保存卡片实例ID到会话
                session["card_instance_id"] = card_instance_id
            except Exception as e:
                dingtalk_logger.error(f"创建AI卡片失败: {str(e)}")
                # 如果AI卡片创建失败，回退到普通文本消息
                self.reply_text("思考中...", incoming_message)
                # 继续处理流程，但使用普通文本消息
                card_instance_id = None
            
            # 处理Dify请求
            accumulated_text = ""
            
            # 根据应用类型调用不同的接口
            if CONFIG["dify"]["app_type"] == "chat":
                dingtalk_logger.debug("使用chat模式处理请求")
                params = {
                    "query": message_content,
                    "user": user_id,
                    "stream": True
                }
                # 只有在会话ID存在时才传递
                if conversation_id:
                    params["conversation_id"] = conversation_id
                    dingtalk_logger.info(f"使用现有会话ID: {conversation_id}")
                else:
                    dingtalk_logger.info("首次对话，不传递会话ID")
                    
                response_generator = self.dify_client.chat_completion(**params)
            else:  # completion, workflow或其他类型
                dingtalk_logger.debug("使用completion模式处理请求")
                response_generator = self.dify_client.completion(
                    query=message_content,
                    user=user_id,
                    stream=True
                )
            
            # 处理流式响应
            update_count = 0
            last_update_time = time.time()
            chunk = None
            update_interval = 0.2  # 增加AI卡片更新频率，钉钉官方建议0.2秒一次更新
            
            for chunk in response_generator:
                if "answer" in chunk:
                    answer_delta = chunk.get("answer", "")
                    accumulated_text += answer_delta
                    
                    # 控制AI卡片更新频率
                    current_time = time.time()
                    if (current_time - last_update_time >= update_interval) and card_instance_id:
                        try:
                            # 流式更新AI卡片内容
                            dingtalk_client.update_ai_card(
                                card_instance_id=card_instance_id,
                                content=accumulated_text,
                                status="loading"  # 仍在加载中
                            )
                            update_count += 1
                            last_update_time = current_time
                            dingtalk_logger.debug(f"流式更新AI卡片内容 #{update_count}, 长度: {len(accumulated_text)}")
                        except Exception as e:
                            dingtalk_logger.warning(f"更新AI卡片失败: {str(e)}")
                            # 如果卡片更新失败5次以上，标记卡片实例ID为空，转为普通消息
                            if update_count > 5:
                                dingtalk_logger.error("多次更新AI卡片失败，转为普通消息模式")
                                card_instance_id = None
            
            try:
                # 最终更新AI卡片为成功状态，显示完整内容
                if card_instance_id:
                    dingtalk_client.update_ai_card(
                        card_instance_id=card_instance_id,
                        content=accumulated_text,
                        status="success"  # 完成状态
                    )
                    dingtalk_logger.info(f"完成AI卡片流式更新，最终长度: {len(accumulated_text)}")
                else:
                    # 如果之前的卡片处理失败，使用普通文本消息发送最终结果
                    self.reply_text(accumulated_text, incoming_message)
                    dingtalk_logger.info(f"使用普通消息发送最终结果，长度: {len(accumulated_text)}")
            except Exception as e:
                dingtalk_logger.warning(f"发送最终响应失败: {str(e)}")
                # 尝试使用普通消息作为备选方案
                try:
                    self.reply_text(accumulated_text, incoming_message)
                except Exception as text_error:
                    dingtalk_logger.error(f"发送普通文本消息也失败: {str(text_error)}")
            
            # 如果是chat类型，保存conversation_id
            if CONFIG["dify"]["app_type"] == "chat" and chunk and "conversation_id" in chunk:
                new_conversation_id = chunk.get("conversation_id")
                dingtalk_logger.debug(f"更新会话ID: {conversation_id} -> {new_conversation_id}")
                session["conversation_id"] = new_conversation_id
                
            return AckMessage.STATUS_OK, 'OK'
                
        except Exception as e:
            dingtalk_logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            error_text = f"很抱歉，处理您的消息时出错: {str(e)}"
            try:
                self.reply_text(error_text, incoming_message)
            except Exception as reply_error:
                dingtalk_logger.error(f"发送错误回复失败: {str(reply_error)}")
            return AckMessage.STATUS_OK, 'Error'

def test_dify_api_connection(api_base: str) -> bool:
    """测试Dify API连接"""
    try:
        dingtalk_logger.info(f"测试Dify API连接: {api_base}")
        # 尝试直接连接API基础URL
        response = requests.get(api_base, verify=False, timeout=10)
        dingtalk_logger.info(f"Dify API连接测试结果: 状态码={response.status_code}")
        return response.status_code < 400
    except Exception as e:
        dingtalk_logger.error(f"Dify API连接测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    app_logger.info("======================================")
    app_logger.info("    钉钉-Dify 消息适配器 (Stream版)    ")
    app_logger.info("======================================")
    app_logger.info(f"配置文件: {CONFIG_PATH}")
    app_logger.info(f"Dify API: {CONFIG['dify']['api_base']}")
    app_logger.info(f"Dify 应用类型: {CONFIG['dify']['app_type']}")
    
    # 获取流式输出模式
    stream_mode = CONFIG["adapter"].get("stream_mode", "ai_card")
    
    # 检查AI卡片模板ID是否存在
    ai_card_template_id = CONFIG["dingtalk"].get("ai_card_template_id")
    
    # 如果选择了AI卡片模式但模板ID不存在，回退到text模式
    if stream_mode == "ai_card" and (not ai_card_template_id or ai_card_template_id == "your_template_id"):
        app_logger.warning("选择了AI卡片模式但未配置有效的模板ID，回退到普通文本模式")
        stream_mode = "text"
        CONFIG["adapter"]["stream_mode"] = "text"
    
    app_logger.info(f"流式输出模式: {stream_mode}")
    
    # 测试Dify API连接
    api_available = test_dify_api_connection(CONFIG['dify']['api_base'])
    if not api_available:
        app_logger.warning("Dify API连接测试失败，请检查API地址和网络连接!")
    
    # 创建证书
    credential = Credential(
        CONFIG["dingtalk"]["client_id"],
        CONFIG["dingtalk"]["client_secret"]
    )
    
    # 创建客户端
    try:
        # 尝试设置环境变量来禁用SSL验证
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        # 创建Stream客户端，只使用SDK支持的参数
        client = DingTalkStreamClient(credential)
        app_logger.info("成功创建钉钉Stream客户端")
    except Exception as e:
        app_logger.error(f"创建钉钉Stream客户端失败: {str(e)}")
        raise
    
    # 创建处理器
    handler = DifyHandler(
        CONFIG["dingtalk"]["client_id"],
        CONFIG["dingtalk"]["client_secret"],
        CONFIG["dingtalk"]["ai_card_template_id"],
        CONFIG["dify"]["api_base"],
        CONFIG["dify"]["api_key"],
        CONFIG["dify"]["app_type"]
    )
    
    # 注册处理器
    # 根据配置选择处理方法
    if stream_mode == "ai_card":
        # 使用AI卡片流式输出
        app_logger.info("使用AI卡片流式输出模式")
        # 创建包装类而不是函数，确保pre_start方法存在
        class AICardHandlerWrapper(AsyncChatbotHandler):
            def __init__(self, handler):
                super().__init__()
                self.handler = handler
                
            def pre_start(self):
                if hasattr(self.handler, 'pre_start'):
                    self.handler.pre_start()
                    
            def process(self, callback):
                return self.handler.process_with_ai_card(callback)
        
        # 使用包装类而不是包装函数
        card_handler = AICardHandlerWrapper(handler)
        client.register_callback_handler(ChatbotMessage.TOPIC, card_handler)
        app_logger.info(f"成功注册AI卡片流式处理器，模板ID: {CONFIG['dingtalk']['ai_card_template_id']}")
    else:
        # 使用普通文本流式输出
        app_logger.info("使用普通文本流式输出模式")
        client.register_callback_handler(ChatbotMessage.TOPIC, handler)
        app_logger.info("成功注册普通文本流式处理器")
    
    # 启动客户端
    app_logger.info("启动Stream客户端...")
    client.start_forever()


if __name__ == '__main__':
    main() 