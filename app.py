#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钉钉-Dify流式适配器
支持多类型消息处理和Dify工作流集成
"""

import os
import sys
import asyncio
import argparse
import logging
import json
import time
from typing import Dict, Any, Callable
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# SSL修复 - 在导入其他模块之前应用
import ssl
import urllib3
urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

# 设置环境变量
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_SSL_VERIFY'] = '0'

# 修改requests默认行为
import requests
old_merge_environment_settings = requests.Session.merge_environment_settings

def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    if verify is True:
        verify = False
    return old_merge_environment_settings(self, url, proxies, stream, verify, cert)

requests.Session.merge_environment_settings = new_merge_environment_settings

# 添加当前目录到Python模块搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'dingtalk-stream-sdk-python-main'))

# 服务器环境检测和配置
def is_server_environment():
    """检测是否为服务器环境"""
    return os.environ.get('SERVER_ENV', 'false').lower() == 'true'

def setup_server_environment():
    """设置服务器环境配置"""
    if is_server_environment():
        # 设置更长的超时时间
        os.environ.setdefault('REQUESTS_TIMEOUT', '60')
        # 设置更大的文件上传限制
        os.environ.setdefault('MAX_FILE_SIZE', '100MB')
        # 启用详细日志
        os.environ.setdefault('LOG_LEVEL', 'INFO')
        print("检测到服务器环境，已应用服务器配置")

# 初始化服务器环境
setup_server_environment()

# 导入钉钉流式SDK
import dingtalk_stream
from dingtalk_stream import DingTalkStreamClient, Credential, ChatbotMessage, AckMessage, AICardReplier

# 导入自定义模块
from dify.client import DifyClient
from utils.logger import app_logger

# 导入Dify客户端
from dify.client import DifyClient

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 禁用所有SSL警告和验证
import urllib3
urllib3.disable_warnings()
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
import requests
requests.packages.urllib3.disable_warnings()

def define_options():
    """定义命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client_id",
        dest="client_id",
        default=os.getenv("DINGTALK_CLIENT_ID"),
        help="app_key or suite_key from https://open-dev.dingtalk.com",
    )
    parser.add_argument(
        "--client_secret",
        dest="client_secret",
        default=os.getenv("DINGTALK_CLIENT_SECRET"),
        help="app_secret or suite_secret from https://open-dev.dingtalk.com",
    )
    parser.add_argument(
        "--card_template_id",
        dest="card_template_id",
        default=os.getenv("DINGTALK_AI_CARD_TEMPLATE_ID", "8aebdfb9-28f4-4a98-98f5-396c3dde41a0.schema"),
        help="AI card template ID",
    )
    parser.add_argument(
        "--dify_api_base",
        dest="dify_api_base",
        default=os.getenv("DIFY_API_BASE", "https://api.dify.ai/v1"),
        help="Dify API base URL",
    )
    parser.add_argument(
        "--dify_api_key",
        dest="dify_api_key",
        default=os.getenv("DIFY_API_KEY"),
        help="Dify API key",
    )
    parser.add_argument(
        "--dify_app_type",
        dest="dify_app_type",
        default=os.getenv("DIFY_APP_TYPE", "chat"),
        help="Dify app type (chat or completion)",
    )
    options = parser.parse_args()
    return options

def load_config_from_env() -> Dict[str, Any]:
    """从环境变量加载配置"""
    try:
        config = {
            "dingtalk": {
                "client_id": os.environ.get("DINGTALK_CLIENT_ID", ""),
                "client_secret": os.environ.get("DINGTALK_CLIENT_SECRET", ""),
                "ai_card_template_id": os.environ.get("DINGTALK_AI_CARD_TEMPLATE_ID", "")
            },
            "dify": {
                "api_base": os.environ.get("DIFY_API_BASE", "https://api.dify.ai/v1"),
                "api_key": os.environ.get("DIFY_API_KEY", ""),
                "app_type": os.environ.get("DIFY_APP_TYPE", "chat")
            },
            "adapter": {
                "stream_mode": os.environ.get("STREAM_MODE", "ai_card")
            }
        }
        
        app_logger.info("成功从环境变量加载配置")
        return config
    except Exception as e:
        app_logger.error(f"加载环境变量配置失败: {str(e)}")
        raise

def test_dify_api_connection(api_base: str) -> bool:
    """测试Dify API连接"""
    try:
        response = requests.get(f"{api_base}/health", timeout=5, verify=False)
        return response.status_code == 200
    except Exception as e:
        app_logger.error(f"测试Dify API连接失败: {str(e)}")
        return False

async def call_with_stream(request_content: str, callback: Callable[[str], None], dify_client: DifyClient, user_id: str):
    """调用Dify API并处理流式响应，基于钉钉官方文档"""
    try:
        # 调用Dify API，确保传递user参数
        response = dify_client.chat_completion(
            query=request_content,
            user=user_id,  # 确保传递用户ID
            stream=True
        )
        
        app_logger.info(f"Dify API响应格式: {type(response)}")
        app_logger.info(f"Dify API响应键: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        full_content = ""
        length = 0
        update_threshold = 20  # 每20个字符更新一次，符合官方文档建议
        
        # 处理流式响应 - 使用正确的Dify API响应格式
        event_stream = response.get("event_stream", [])
        app_logger.info(f"事件流长度: {len(event_stream)}")
        
        for i, chunk in enumerate(event_stream):
            app_logger.debug(f"处理第 {i+1} 个数据块: {chunk}")
            
            # 检查是否有answer字段
            if "answer" in chunk:
                answer_chunk = chunk.get("answer", "")
                full_content += answer_chunk
                app_logger.debug(f"累积内容: {full_content}")
                
                # 当累积内容长度超过阈值时更新卡片
                # 这实现了官方文档中提到的"打字机效果"
                full_content_length = len(full_content)
                if full_content_length - length > update_threshold:
                    await callback(full_content)
                    app_logger.info(
                        f"调用流式更新接口更新内容：current_length: {length}, next_length: {full_content_length}"
                    )
                    length = full_content_length
            else:
                app_logger.debug(f"数据块中没有answer字段: {chunk}")
        
        # 最终回调 - 确保完整内容被发送
        if full_content:
            await callback(full_content)
            app_logger.info(
                f"Request Content: {request_content}\nFull response: {full_content}\nFull response length: {len(full_content)}"
            )
        else:
            app_logger.warning("未获取到有效内容")
            await callback("抱歉，暂时无法生成回复，请稍后再试。")
        
        return full_content
        
    except Exception as e:
        app_logger.error(f"调用Dify API异常: {str(e)}")
        # 发生异常时，尝试发送错误信息
        try:
            await callback("抱歉，处理您的请求时出现了错误，请稍后再试。")
        except Exception as callback_error:
            app_logger.error(f"发送错误信息失败: {str(callback_error)}")
        raise

async def handle_reply_and_update_card(self, incoming_message: ChatbotMessage, dify_client: DifyClient, card_template_id: str):
    """处理消息并使用AI卡片进行流式输出，基于钉钉官方文档"""
    
    # 获取用户ID
    user_id = incoming_message.sender_staff_id
    app_logger.info(f"处理用户 {user_id} 的消息")
    
    # 卡片数据键名
    content_key = "content"
    card_data = {content_key: ""}
    
    # 创建AI卡片回复器
    card_instance = AICardReplier(self.dingtalk_client, incoming_message)
    card_instance_id = None
    
    try:
        # 1. 先投放卡片 - 使用官方推荐的方式
        app_logger.info(f"开始创建AI卡片，模板ID: {card_template_id}")
        
        # 根据官方文档，使用async_create_and_deliver_card方法
        card_instance_id = await card_instance.async_create_and_deliver_card(
            card_template_id, 
            card_data,
            callback_type="STREAM",  # 指定回调类型为流式
            at_sender=False,  # 不@发送者
            at_all=False,     # 不@所有人
            support_forward=True  # 支持转发
        )
        
        if not card_instance_id:
            app_logger.error("创建AI卡片失败")
            # 如果卡片创建失败，回退到普通文本消息
            self.reply_text("思考中...", incoming_message)
            return False
        
        app_logger.info(f"成功创建AI卡片，实例ID: {card_instance_id}")
        
        # 2. 定义回调函数，用于流式更新卡片
        async def update_card_callback(content_value: str):
            """更新卡片的回调函数，基于官方文档"""
            if card_instance_id:
                try:
                    # 使用官方推荐的async_streaming方法
                    return await card_instance.async_streaming(
                        card_instance_id,
                        content_key=content_key,
                        content_value=content_value,
                        append=False,  # 不追加，替换内容
                        finished=False,  # 未完成
                        failed=False,    # 未失败
                    )
                except Exception as e:
                    app_logger.error(f"更新卡片失败: {str(e)}")
                    # 如果卡片更新失败，回退到普通文本消息
                    self.reply_text(content_value, incoming_message)
            else:
                # 如果没有卡片ID，直接发送文本消息
                self.reply_text(content_value, incoming_message)
        
        # 3. 调用Dify API并处理流式响应
        full_content = await call_with_stream(
            incoming_message.text.content, 
            update_card_callback,
            dify_client,
            user_id  # 传递用户ID
        )
        
        # 4. 最终更新，标记完成 - 使用官方推荐的方式
        if card_instance_id:
            try:
                # 最终更新，标记为完成状态
                await card_instance.async_streaming(
                    card_instance_id,
                    content_key=content_key,
                    content_value=full_content,
                    append=False,  # 不追加，替换内容
                    finished=True,  # 已完成
                    failed=False,   # 未失败
                )
                app_logger.info(f"完成流式响应，总长度: {len(full_content)}")
            except Exception as e:
                app_logger.error(f"最终更新卡片失败: {str(e)}")
                # 回退到普通文本消息
                self.reply_text(full_content, incoming_message)
        else:
            # 如果没有卡片ID，发送最终文本消息
            self.reply_text(full_content, incoming_message)
        
        return True
        
    except Exception as e:
        app_logger.exception(f"处理消息异常: {str(e)}")
        
        # 如果出现异常，尝试更新卡片为错误状态
        if card_instance_id:
            try:
                # 使用官方推荐的方式标记失败状态
                await card_instance.async_streaming(
                    card_instance_id,
                    content_key=content_key,
                    content_value=f"处理消息时发生错误: {str(e)}",
                    append=False,  # 不追加，替换内容
                    finished=False,  # 未完成
                    failed=True,     # 标记为失败
                )
            except Exception as update_error:
                app_logger.error(f"更新错误状态失败: {str(update_error)}")
                # 回退到普通文本消息
                self.reply_text(f"处理消息时发生错误: {str(e)}", incoming_message)
        else:
            # 如果没有卡片ID，发送错误文本消息
            self.reply_text(f"处理消息时发生错误: {str(e)}", incoming_message)
        
        return False

class CardBotHandler(dingtalk_stream.ChatbotHandler):
    """基于官方代码的卡片机器人处理器，支持多类型消息"""
    
    def __init__(self, dify_client: DifyClient, card_template_id: str, logger: logging.Logger = app_logger):
        super(dingtalk_stream.ChatbotHandler, self).__init__()
        self.dify_client = dify_client
        self.card_template_id = card_template_id
        self.logger = logger
    
    async def process(self, callback: dingtalk_stream.CallbackMessage):
        """处理消息"""
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        self.logger.info(f"收到消息：{incoming_message}")

        # 处理不同类型的消息
        if incoming_message.message_type == "text":
            # 文本消息 - 使用AI卡片处理
            asyncio.create_task(
                handle_reply_and_update_card(self, incoming_message, self.dify_client, self.card_template_id)
            )
        elif incoming_message.message_type == "image":
            # 图片消息
            await self.handle_image_message(incoming_message)
        elif incoming_message.message_type == "audio":
            # 语音消息
            await self.handle_audio_message(incoming_message)
        elif incoming_message.message_type == "file":
            # 文件消息
            await self.handle_file_message(incoming_message)
        else:
            # 其他类型消息
            self.reply_text("目前只支持文本、图片、语音和文件消息，其他类型暂不支持~", incoming_message)
        
        return AckMessage.STATUS_OK, "OK"
    
    async def handle_image_message(self, incoming_message: ChatbotMessage):
        """处理图片消息"""
        try:
            # 提取图片信息
            image_list = incoming_message.get_image_list()
            if image_list:
                image_info = image_list[0]
                download_url = self.get_image_download_url(image_info.get('downloadCode', ''))
                
                # 发送给Dify处理
                user_id = incoming_message.sender_staff_id
                query = f"[图片消息] 用户发送了一张图片，下载地址: {download_url}"
                
                # 调用Dify API
                response = self.dify_client.chat_completion(
                    query=query,
                    user=user_id,
                    stream=False  # 图片处理使用非流式
                )
                
                # 获取回复内容
                answer = response.get("accumulated_data", {}).get("answer", "图片处理完成")
                
                # 回复用户
                self.reply_text(f"收到您的图片！\n\n{answer}", incoming_message)
            else:
                self.reply_text("图片处理失败，请重试", incoming_message)
                
        except Exception as e:
            self.logger.error(f"处理图片消息异常: {str(e)}")
            self.reply_text("图片处理时发生错误，请重试", incoming_message)
    
    async def handle_audio_message(self, incoming_message: ChatbotMessage):
        """处理语音消息"""
        try:
            # 提取语音信息
            audio_info = incoming_message.audio
            if audio_info:
                # 发送给Dify处理
                user_id = incoming_message.sender_staff_id
                query = f"[语音消息] 用户发送了一条语音消息，时长: {getattr(audio_info, 'duration', '未知')}秒"
                
                # 调用Dify API
                response = self.dify_client.chat_completion(
                    query=query,
                    user=user_id,
                    stream=False
                )
                
                # 获取回复内容
                answer = response.get("accumulated_data", {}).get("answer", "语音处理完成")
                
                # 回复用户
                self.reply_text(f"收到您的语音！\n\n{answer}", incoming_message)
            else:
                self.reply_text("语音处理失败，请重试", incoming_message)
                
        except Exception as e:
            self.logger.error(f"处理语音消息异常: {str(e)}")
            self.reply_text("语音处理时发生错误，请重试", incoming_message)
    
    async def handle_file_message(self, incoming_message: ChatbotMessage):
        """处理文件消息"""
        try:
            # 检查文件消息的属性
            self.logger.info(f"文件消息详情: {incoming_message}")
            self.logger.info(f"文件消息扩展信息: {getattr(incoming_message, 'extensions', {})}")
            
            # 从extensions中获取文件信息
            file_info = None
            if hasattr(incoming_message, 'extensions') and incoming_message.extensions:
                # 尝试从extensions中获取文件信息
                for key, value in incoming_message.extensions.items():
                    self.logger.debug(f"检查扩展字段: {key} = {value}")
                    if key == 'content' and isinstance(value, dict):
                        # 钉钉文件消息的content字段包含文件信息
                        file_info = value
                        break
                    elif 'file' in key.lower() or 'content' in key.lower():
                        file_info = value
                        break
            
            # 如果没有找到文件信息，尝试从其他属性获取
            if not file_info:
                # 检查是否有文件相关的属性
                file_attrs = ['file_content', 'file_info', 'content', 'file']
                for attr in file_attrs:
                    if hasattr(incoming_message, attr):
                        file_info = getattr(incoming_message, attr)
                        self.logger.debug(f"从属性 {attr} 获取文件信息: {file_info}")
                        break
            
            # 如果还是没有找到，尝试从原始数据中解析
            if not file_info:
                # 尝试从消息的原始数据中解析文件信息
                try:
                    # 检查是否有文件相关的字段
                    message_data = incoming_message.__dict__
                    self.logger.debug(f"消息数据: {message_data}")
                    
                    # 查找包含文件信息的字段
                    for key, value in message_data.items():
                        if isinstance(value, dict) and ('file' in key.lower() or 'content' in key.lower()):
                            file_info = value
                            self.logger.debug(f"从消息数据中找到文件信息: {key} = {value}")
                            break
                except Exception as e:
                    self.logger.warning(f"解析消息数据失败: {str(e)}")
            
            if file_info:
                # 提取文件信息 - 支持钉钉文件消息格式
                if isinstance(file_info, dict):
                    # 钉钉文件消息格式
                    file_name = file_info.get('fileName', file_info.get('name', '未知文件'))
                    file_size = file_info.get('fileSize', file_info.get('size', 0))
                    download_code = file_info.get('downloadCode', '')
                    file_id = file_info.get('fileId', '')
                    space_id = file_info.get('spaceId', '')
                    
                    file_type = self._get_file_type(file_name)
                else:
                    # 如果不是字典，尝试其他方式解析
                    file_name = str(file_info) if file_info else '未知文件'
                    file_size = 0
                    file_type = '未知类型'
                
                self.logger.info(f"文件信息: 名称={file_name}, 大小={file_size}, 类型={file_type}")
                
                # 直接使用Storage API获取文件下载地址
                self.logger.info("使用钉钉Storage API获取文件下载信息")
                file_url = self._get_file_download_url(incoming_message)
                
                if file_url:
                    # 尝试上传文件到Dify
                    uploaded_file_id = await self.upload_file_to_dify(file_url, file_name, file_type)
                    
                    if uploaded_file_id:
                        # 发送给Dify处理，包含文件ID
                        user_id = incoming_message.sender_staff_id
                        query = f"[文件消息] 用户发送了一个文件，文件名: {file_name}，大小: {file_size}字节，类型: {file_type}"
                        
                        # 检查是否使用工作流
                        use_workflow = os.environ.get("DIFY_USE_WORKFLOW", "false").lower() == "true"
                        
                        if use_workflow:
                            # 使用工作流API
                            inputs = {
                                "query": query,
                                "file_info": {
                                    "name": file_name,
                                    "size": file_size,
                                    "type": file_type
                                }
                            }
                            
                            response = self.dify_client.workflow_run(
                                inputs=inputs,
                                user=user_id,
                                files=[uploaded_file_id],
                                stream=False
                            )
                        else:
                            # 使用聊天API
                            response = self.dify_client.chat_completion(
                                query=query,
                                user=user_id,
                                stream=False,
                                files=[uploaded_file_id]  # 传递文件ID列表
                            )
                        
                        # 获取回复内容
                        answer = response.get("answer", "文件处理完成")
                        
                        # 回复用户
                        self.reply_text(f"收到您的文件！\n\n文件名: {file_name}\n大小: {file_size}字节\n\n{answer}", incoming_message)
                    else:
                        # 如果文件上传失败，提供文件信息给Dify处理
                        self.logger.info("文件上传失败，尝试使用文件信息进行处理")
                        user_id = incoming_message.sender_staff_id
                        query = f"[文件消息] 用户发送了一个文件，文件名: {file_name}，大小: {file_size}字节，类型: {file_type}。由于文件下载权限问题，无法直接上传文件内容，请根据文件信息进行分析。"
                        
                        # 检查是否使用工作流
                        use_workflow = os.environ.get("DIFY_USE_WORKFLOW", "false").lower() == "true"
                        
                        if use_workflow:
                            # 使用工作流API，不传递文件
                            inputs = {
                                "query": query,
                                "file_info": {
                                    "name": file_name,
                                    "size": file_size,
                                    "type": file_type
                                }
                            }
                            
                            response = self.dify_client.workflow_run(
                                inputs=inputs,
                                user=user_id,
                                stream=False
                            )
                        else:
                            # 使用聊天API，不传递文件
                            response = self.dify_client.chat_completion(
                                query=query,
                                user=user_id,
                                stream=False
                            )
                        
                        # 获取回复内容
                        answer = response.get("answer", "文件处理完成")
                        
                        # 回复用户
                        self.reply_text(f"收到您的文件！\n\n文件名: {file_name}\n大小: {file_size}字节\n\n{answer}\n\n注意：由于OSS权限限制，无法直接下载文件内容，但已根据文件信息进行了AI分析。如需完整分析，请联系管理员检查应用权限配置。", incoming_message)
                else:
                    self.reply_text(f"收到您的文件！\n\n文件名: {file_name}\n大小: {file_size}字节\n\n无法获取文件下载地址，请重试。", incoming_message)
            else:
                self.reply_text("文件处理失败，无法获取文件信息，请重试", incoming_message)
                
        except Exception as e:
            self.logger.error(f"处理文件消息异常: {str(e)}")
            self.reply_text("文件处理时发生错误，请重试", incoming_message)
    

    
    def _get_file_type(self, file_name: str) -> str:
        """根据文件名获取文件类型"""
        try:
            import mimetypes
            # 根据文件扩展名获取MIME类型
            mime_type, _ = mimetypes.guess_type(file_name)
            if mime_type:
                return mime_type
            else:
                # 如果无法获取MIME类型，根据扩展名判断
                ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
                type_map = {
                    'pdf': 'application/pdf',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'txt': 'text/plain',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'mp3': 'audio/mpeg',
                    'mp4': 'video/mp4'
                }
                return type_map.get(ext, 'application/octet-stream')
        except Exception as e:
            self.logger.error(f"获取文件类型失败: {str(e)}")
            return 'application/octet-stream'
    
    def _get_file_download_url(self, incoming_message: ChatbotMessage) -> str:
        """使用官方代码从钉钉API获取文件下载地址"""
        try:
            # 从消息中提取文件信息
            file_id = None
            space_id = None
            union_id = None
            
            # 从extensions的content字段中提取文件信息
            if hasattr(incoming_message, 'extensions') and incoming_message.extensions:
                self.logger.info(f"消息extensions内容: {incoming_message.extensions}")
                for key, value in incoming_message.extensions.items():
                    self.logger.info(f"检查扩展字段: {key} = {value}")
                    if key == 'content' and isinstance(value, dict):
                        # 从content字段中提取文件信息
                        file_id = value.get('fileId')
                        space_id = value.get('spaceId')
                        self.logger.info(f"从extensions.content中提取文件信息: fileId={file_id}, spaceId={space_id}")
                        break
                    elif isinstance(value, dict):
                        # 备用：从其他字典字段中提取
                        file_id = value.get('fileId') or value.get('id')
                        space_id = value.get('spaceId') or value.get('space_id')
                        if file_id and space_id:
                            self.logger.info(f"从extensions.{key}中提取文件信息: fileId={file_id}, spaceId={space_id}")
                            break
            
            # 只使用旧版SDK获取unionId
            union_id = None
            if hasattr(incoming_message, 'sender_staff_id'):
                try:
                    # 根据钉钉官方文档：https://open.dingtalk.com/document/orgapp/obtain-the-userid-of-a-user-by-using-the-log-free
                    # 使用旧版taobao SDK获取unionId
                    from old_sdk_client import get_union_id_with_old_sdk
                    client_id = os.environ.get("DINGTALK_CLIENT_ID")
                    client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
                    
                    if client_id and client_secret:
                        self.logger.info("使用旧版SDK获取unionId")
                        union_id = get_union_id_with_old_sdk(
                            incoming_message.sender_staff_id, 
                            client_id, 
                            client_secret
                        )
                        if union_id:
                            self.logger.info(f"使用旧版SDK获取到unionId: {union_id}")
                        else:
                            self.logger.error("旧版SDK获取unionId失败")
                    else:
                        self.logger.error("钉钉配置不完整，无法获取unionId")
                except Exception as e:
                    self.logger.error(f"获取用户unionId失败: {str(e)}")
            
            # 如果没有sender_staff_id或获取失败，则无法继续
            if not union_id:
                self.logger.error("无法获取unionId，无法调用Storage API")
                return ""
            
            self.logger.info(f"最终使用的unionId: {union_id}")
            
            if not file_id or not space_id:
                self.logger.error("未找到必要的文件信息: fileId 或 spaceId")
                return ""
            
            self.logger.info(f"找到文件信息: fileId={file_id}, spaceId={space_id}")
            
            # 使用官方代码实现Storage API调用
            try:
                # 导入官方SDK
                from alibabacloud_tea_openapi import models as open_api_models
                from alibabacloud_tea_util import models as util_models
                from alibabacloud_dingtalk.storage_1_0.client import Client as dingtalkstorage_1_0Client
                from alibabacloud_dingtalk.storage_1_0 import models as dingtalkstorage__1__0_models
                
                # 获取访问令牌
                from dingtalk.auth import DingTalkAuth
                client_id = os.environ.get("DINGTALK_CLIENT_ID")
                client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
                
                if not client_id or not client_secret:
                    self.logger.error("钉钉配置不完整")
                    return ""
                
                auth = DingTalkAuth(client_id, client_secret)
                access_token = auth.get_access_token()
                
                if not access_token:
                    self.logger.error("无法获取钉钉访问令牌")
                    return ""
                
                # 按照官方代码创建客户端
                config = open_api_models.Config()
                config.protocol = 'https'
                config.region_id = 'central'
                client = dingtalkstorage_1_0Client(config)
                
                # 按照官方代码设置请求头
                get_file_download_info_headers = dingtalkstorage__1__0_models.GetFileDownloadInfoHeaders()
                get_file_download_info_headers.x_acs_dingtalk_access_token = access_token
                
                # 按照官方代码设置请求选项
                option = dingtalkstorage__1__0_models.GetFileDownloadInfoRequestOption(
                    version=1,
                    prefer_intranet=False
                )
                
                # 按照官方代码创建请求对象
                get_file_download_info_request = dingtalkstorage__1__0_models.GetFileDownloadInfoRequest()
                get_file_download_info_request.union_id = union_id
                get_file_download_info_request.option = option
                
                # 按照官方代码调用API
                self.logger.info(f"调用Storage API: spaceId={space_id}, fileId={file_id}, unionId={union_id}")
                
                runtime_options = util_models.RuntimeOptions()
                
                # 严格按照官方代码调用API
                response = client.get_file_download_info_with_options(
                    space_id, 
                    file_id, 
                    get_file_download_info_request, 
                    get_file_download_info_headers, 
                    runtime_options
                )
                    
                # 处理官方API响应
                if response and hasattr(response, 'body') and response.body:
                    download_info = response.body
                    self.logger.info(f"Storage API响应: {download_info}")
                    
                    # 添加详细的调试信息
                    self.logger.info(f"响应类型: {type(download_info)}")
                    self.logger.info(f"响应属性: {dir(download_info)}")
                    
                    # 按照官方响应格式解析下载URL
                    download_url = None
                    
                    # 检查headerSignatureInfo格式（官方标准格式）
                    self.logger.info(f"检查hasattr(download_info, 'headerSignatureInfo'): {hasattr(download_info, 'headerSignatureInfo')}")
                    self.logger.info(f"检查hasattr(download_info, 'header_signature_info'): {hasattr(download_info, 'header_signature_info')}")
                    
                    # 尝试两种属性名格式
                    header_info = None
                    if hasattr(download_info, 'headerSignatureInfo'):
                        header_info = download_info.headerSignatureInfo
                        self.logger.info(f"找到headerSignatureInfo: {header_info}")
                    elif hasattr(download_info, 'header_signature_info'):
                        header_info = download_info.header_signature_info
                        self.logger.info(f"找到header_signature_info: {header_info}")
                    
                    if header_info:
                        self.logger.info(f"header_info类型: {type(header_info)}")
                        self.logger.info(f"header_info属性: {dir(header_info)}")
                        
                        # 优先使用resourceUrls（外部访问URL）
                        self.logger.info(f"检查hasattr(header_info, 'resourceUrls'): {hasattr(header_info, 'resourceUrls')}")
                        self.logger.info(f"检查hasattr(header_info, 'resource_urls'): {hasattr(header_info, 'resource_urls')}")
                        
                        # 尝试两种属性名格式
                        resource_urls = None
                        if hasattr(header_info, 'resourceUrls'):
                            resource_urls = header_info.resourceUrls
                            self.logger.info(f"从resourceUrls获取: {resource_urls}")
                        elif hasattr(header_info, 'resource_urls'):
                            resource_urls = header_info.resource_urls
                            self.logger.info(f"从resource_urls获取: {resource_urls}")
                        
                        if resource_urls:
                            self.logger.info(f"resourceUrls值: {resource_urls}")
                            self.logger.info(f"resourceUrls是否为真: {bool(resource_urls)}")
                            
                            if resource_urls:
                                download_url = resource_urls[0]
                                self.logger.info(f"从headerSignatureInfo.resourceUrls获取到下载URL: {download_url}")
                            else:
                                self.logger.warning("resourceUrls为空")
                        else:
                            self.logger.warning("header_info没有resourceUrls或resource_urls属性")
                        
                        # 备用使用internalResourceUrls（内部访问URL）
                        self.logger.info(f"检查hasattr(header_info, 'internalResourceUrls'): {hasattr(header_info, 'internalResourceUrls')}")
                        self.logger.info(f"检查hasattr(header_info, 'internal_resource_urls'): {hasattr(header_info, 'internal_resource_urls')}")
                        
                        # 尝试两种属性名格式
                        internal_resource_urls = None
                        if hasattr(header_info, 'internalResourceUrls'):
                            internal_resource_urls = header_info.internalResourceUrls
                            self.logger.info(f"从internalResourceUrls获取: {internal_resource_urls}")
                        elif hasattr(header_info, 'internal_resource_urls'):
                            internal_resource_urls = header_info.internal_resource_urls
                            self.logger.info(f"从internal_resource_urls获取: {internal_resource_urls}")
                        
                        if internal_resource_urls:
                            self.logger.info(f"internalResourceUrls值: {internal_resource_urls}")
                            self.logger.info(f"internalResourceUrls是否为真: {bool(internal_resource_urls)}")
                            
                            if not download_url and internal_resource_urls:
                                download_url = internal_resource_urls[0]
                                self.logger.info(f"从headerSignatureInfo.internalResourceUrls获取到下载URL: {download_url}")
                        else:
                            self.logger.warning("header_info没有internalResourceUrls或internal_resource_urls属性")
                    else:
                        self.logger.warning("download_info没有headerSignatureInfo或header_signature_info属性")
                    
                    # 如果还是没有找到，尝试从响应字典中查找
                    if not download_url and hasattr(download_info, '__dict__'):
                        response_dict = download_info.__dict__
                        self.logger.info(f"响应字典: {response_dict}")
                        
                        # 尝试两种字典键名格式
                        header_dict = None
                        if 'headerSignatureInfo' in response_dict:
                            header_dict = response_dict['headerSignatureInfo']
                            self.logger.info(f"headerSignatureInfo字典: {header_dict}")
                        elif 'header_signature_info' in response_dict:
                            header_dict = response_dict['header_signature_info']
                            self.logger.info(f"header_signature_info字典: {header_dict}")
                        
                        if header_dict:
                            if isinstance(header_dict, dict):
                                # 优先使用resourceUrls
                                if 'resourceUrls' in header_dict and header_dict['resourceUrls']:
                                    download_url = header_dict['resourceUrls'][0]
                                    self.logger.info(f"从字典headerSignatureInfo.resourceUrls获取到下载URL: {download_url}")
                                # 备用使用internalResourceUrls
                                elif 'internalResourceUrls' in header_dict and header_dict['internalResourceUrls']:
                                    download_url = header_dict['internalResourceUrls'][0]
                                    self.logger.info(f"从字典headerSignatureInfo.internalResourceUrls获取到下载URL: {download_url}")
                                # 尝试下划线格式
                                elif 'resource_urls' in header_dict and header_dict['resource_urls']:
                                    download_url = header_dict['resource_urls'][0]
                                    self.logger.info(f"从字典header_signature_info.resource_urls获取到下载URL: {download_url}")
                                elif 'internal_resource_urls' in header_dict and header_dict['internal_resource_urls']:
                                    download_url = header_dict['internal_resource_urls'][0]
                                    self.logger.info(f"从字典header_signature_info.internal_resource_urls获取到下载URL: {download_url}")
                            else:
                                self.logger.warning(f"header_dict不是字典类型: {type(header_dict)}")
                        else:
                            self.logger.warning("响应字典中没有headerSignatureInfo或header_signature_info")
                    else:
                        self.logger.warning("download_info没有__dict__属性")
                    
                    if download_url:
                        self.logger.info(f"成功获取文件下载URL: {download_url}")
                        return download_url
                    else:
                        self.logger.error("无法从Storage API响应中获取下载URL")
                        self.logger.debug(f"完整响应内容: {download_info}")
                        return ""
                else:
                    self.logger.warning("Storage API响应为空")
                    return ""
                        
            except Exception as api_err:
                # 按照官方代码的错误处理方式
                self.logger.error("=== Storage API调用失败 ===")
                
                if hasattr(api_err, 'code') and hasattr(api_err, 'message'):
                    self.logger.error(f"错误代码: {api_err.code}")
                    self.logger.error(f"错误消息: {api_err.message}")
                    
                    # 检查权限问题
                    if api_err.code == "Forbidden.AccessDenied.AccessTokenPermissionDenied":
                        self.logger.error("权限不足，请检查钉钉应用权限配置")
                        self.logger.error("需要权限: Contact.Org.Read, Storage.Read")
                    elif "403" in str(api_err.code) or "Forbidden" in str(api_err.code):
                        self.logger.error("权限不足，请检查钉钉应用权限配置")
                else:
                    self.logger.error(f"Storage API调用失败: {str(api_err)}")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"获取文件下载地址异常: {str(e)}")
            return ""
    
    async def upload_file_to_dify(self, file_url: str, file_name: str, file_type: str) -> str:
        """上传文件到Dify"""
        try:
            if not file_url:
                self.logger.warning("文件URL为空，跳过上传")
                return None
            
            # 从环境变量获取Dify配置
            dify_api_base = os.environ.get("DIFY_API_BASE", "https://api.dify.ai/v1")
            dify_api_key = os.environ.get("DIFY_API_KEY")
            
            if not dify_api_key:
                self.logger.error("Dify API密钥未配置")
                return None
            
            # 下载文件
            import tempfile
            import requests
            import shutil
            import time
            
            # 获取正确的文件扩展名
            file_extension = self._get_file_extension(file_name, file_type)
            self.logger.info(f"文件扩展名: {file_extension}")
            
            # 服务器环境下的超时设置
            timeout = int(os.environ.get('REQUESTS_TIMEOUT', '30'))
            if is_server_environment():
                timeout = max(timeout, 60)  # 服务器环境至少60秒超时
            
            # Docker环境检测
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_ENV', 'false').lower() == 'true'
            if is_docker:
                self.logger.info("检测到Docker环境，应用Docker优化配置")
                timeout = max(timeout, 120)  # Docker环境120秒超时
            
            # 创建临时文件，使用正确的扩展名
            temp_file = None
            temp_file_path = None
            
            # 下载文件 - 如果是钉钉文件，需要添加访问令牌
            headers = {}
            if "api.dingtalk.com" in file_url:
                # 获取钉钉访问令牌
                try:
                    from dingtalk.auth import DingTalkAuth
                    # 从环境变量获取钉钉配置
                    client_id = os.environ.get("DINGTALK_CLIENT_ID")
                    client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
                    
                    if client_id and client_secret:
                        auth = DingTalkAuth(client_id, client_secret)
                        access_token = auth.get_access_token()
                        if access_token:
                            headers['x-acs-dingtalk-access-token'] = access_token
                            self.logger.info("使用钉钉访问令牌下载文件")
                        else:
                            self.logger.warning("无法获取钉钉访问令牌")
                    else:
                        self.logger.warning("钉钉配置不完整，跳过访问令牌")
                except Exception as e:
                    self.logger.warning(f"获取钉钉访问令牌失败: {str(e)}")
            
            # 如果是新的Storage API返回的URL，可能需要特殊处理
            if "storage.dingtalk.com" in file_url or "download.dingtalk.com" in file_url or "zjk-dualstack.trans.dingtalk.com" in file_url:
                self.logger.info("检测到Storage API下载URL，使用特殊处理")
                # 根据钉钉官方文档，必须添加x-acs-dingtalk-access-token认证头
                if 'x-acs-dingtalk-access-token' not in headers:
                    try:
                        from dingtalk.auth import DingTalkAuth
                        client_id = os.environ.get("DINGTALK_CLIENT_ID")
                        client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
                        if client_id and client_secret:
                            auth = DingTalkAuth(client_id, client_secret)
                            access_token = auth.get_access_token()
                            if access_token:
                                # 根据官方文档添加认证头
                                headers['x-acs-dingtalk-access-token'] = access_token
                                # 添加OSS相关的认证头
                                headers['Authorization'] = f'Bearer {access_token}'
                                headers['x-oss-object-acl'] = 'public-read'
                                # 添加OSS签名相关的头
                                headers['x-oss-date'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
                                headers['x-oss-security-token'] = access_token
                                self.logger.info("为Storage API URL添加访问令牌和OSS认证头")
                            else:
                                self.logger.warning("无法获取钉钉访问令牌")
                        else:
                            self.logger.warning("钉钉配置不完整")
                    except Exception as e:
                        self.logger.warning(f"为Storage API URL获取访问令牌失败: {str(e)}")
            
            # 按照钉钉API标准下载文件
            download_success = False
            response_content = None
            
            try:
                self.logger.info(f"开始下载文件: {file_url}")
                
                # 创建请求会话，设置连接参数
                session = requests.Session()
                session.verify = False  # 禁用SSL验证
                
                # 设置请求头
                if headers:
                    session.headers.update(headers)
                
                # 设置连接参数 - 参考Java代码的设置
                session.headers.update({
                    'User-Agent': 'DingTalk-Bot/1.0',
                    'Accept': '*/*',
                    'Connection': 'keep-alive'
                })
                
                # 下载文件 - 使用GET方法（下载）但参考Java代码的连接设置
                response = session.get(
                    file_url, 
                    timeout=timeout,
                    stream=True  # 使用流式下载，参考Java的流式处理
                )
                
                if response.status_code == 200:
                    # 流式读取文件内容，参考Java的缓冲区处理
                    response_content = b''
                    chunk_size = 1024  # 参考Java的1024字节缓冲区
                    
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            response_content += chunk
                    
                    if len(response_content) > 0:
                        download_success = True
                        self.logger.info(f"文件下载成功: {file_name}, 大小: {len(response_content)}字节")
                    else:
                        self.logger.warning("文件下载成功但内容为空")
                elif response.status_code == 403:
                    # 处理403权限错误，根据官方文档建议
                    self.logger.error(f"文件下载失败，状态码: {response.status_code}, 响应: {response.text}")
                    self.logger.error("检测到OSS权限错误，尝试添加更多认证头")
                    
                    # 尝试添加更多认证头
                    try:
                        # 重新获取访问令牌
                        auth = DingTalkAuth(client_id, client_secret)
                        access_token = auth.get_access_token()
                        if access_token:
                            # 添加更多认证头，根据官方文档
                            session.headers.update({
                                'x-acs-dingtalk-access-token': access_token,
                                'Authorization': f'Bearer {access_token}',
                                'x-oss-object-acl': 'public-read',
                                'x-oss-security-token': access_token,  # 添加安全令牌
                                'x-oss-date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
                            })
                            
                            # 重试下载
                            self.logger.info("使用增强认证头重试下载")
                            response = session.get(file_url, timeout=timeout, stream=True)
                            
                            if response.status_code == 200:
                                response_content = b''
                                for chunk in response.iter_content(chunk_size=chunk_size):
                                    if chunk:
                                        response_content += chunk
                                
                                if len(response_content) > 0:
                                    download_success = True
                                    self.logger.info(f"重试后文件下载成功: {file_name}, 大小: {len(response_content)}字节")
                                else:
                                    self.logger.warning("重试后文件下载成功但内容为空")
                            else:
                                self.logger.error(f"重试后仍然失败，状态码: {response.status_code}, 响应: {response.text}")
                    except Exception as retry_e:
                        self.logger.error(f"重试下载失败: {str(retry_e)}")
                else:
                    self.logger.warning(f"文件下载失败，状态码: {response.status_code}, 响应: {response.text}")
                    
            except requests.exceptions.Timeout:
                self.logger.error("文件下载超时")
            except requests.exceptions.ConnectionError:
                self.logger.error("文件下载连接错误")
            except Exception as e:
                self.logger.warning(f"文件下载失败: {str(e)}")
            
            if not download_success:
                self.logger.error("Storage API文件下载失败")
                # 尝试使用钉钉官方SDK下载文件
                self.logger.info("尝试使用钉钉官方SDK下载文件")
                try:
                    from alibabacloud_tea_openapi import models as open_api_models
                    from alibabacloud_tea_util import models as util_models
                    from alibabacloud_dingtalk.storage_1_0.client import Client as dingtalkstorage_1_0Client
                    from alibabacloud_dingtalk.storage_1_0 import models as dingtalkstorage__1__0_models
                    
                    # 创建钉钉Storage客户端
                    config = open_api_models.Config()
                    config.protocol = 'https'
                    config.region_id = 'central'
                    client = dingtalkstorage_1_0Client(config)
                    
                    # 获取访问令牌
                    from dingtalk.auth import DingTalkAuth
                    client_id = os.environ.get("DINGTALK_CLIENT_ID")
                    client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
                    
                    if client_id and client_secret:
                        auth = DingTalkAuth(client_id, client_secret)
                        access_token = auth.get_access_token()
                        
                        if access_token:
                            # 设置请求头
                            headers = dingtalkstorage__1__0_models.GetFileDownloadInfoHeaders()
                            headers.x_acs_dingtalk_access_token = access_token
                            
                            # 设置请求选项
                            option = dingtalkstorage__1__0_models.GetFileDownloadInfoRequestOption(
                                version=1,
                                prefer_intranet=False
                            )
                            
                            # 这里无法使用SDK直接下载文件内容，因为需要spaceId和fileId
                            # 但我们已经有了下载URL，所以直接返回None，让上层处理
                            self.logger.info("跳过SDK直接下载，使用URL下载方式")
                            return None
                        else:
                            self.logger.error("无法获取访问令牌")
                            return None
                    else:
                        self.logger.error("钉钉配置不完整")
                        return None
                except Exception as sdk_e:
                    self.logger.error(f"使用钉钉官方SDK下载失败: {str(sdk_e)}")
                    return None
                
                # 添加权限问题指导和降级策略
                self.logger.error("=== OSS权限问题解决指导 ===")
                self.logger.error("您遇到的是钉钉OSS存储桶访问权限问题")
                self.logger.error("可能的解决方案：")
                self.logger.error("1. 检查钉钉应用权限：确保应用有Storage.Read权限")
                self.logger.error("2. 检查应用状态：确保应用已上线且状态正常")
                self.logger.error("3. 检查用户权限：确保用户有访问该文件的权限")
                self.logger.error("4. 联系钉钉技术支持：如果问题持续存在")
                self.logger.error("=== 权限问题解决指导结束 ===")
                
                # 尝试使用不同的认证方式
                self.logger.info("尝试使用不同的OSS认证方式...")
                
                # 方法1：使用OSS签名URL
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(file_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    # 如果URL包含签名参数，尝试直接使用
                    if 'Signature' in query_params or 'Expires' in query_params:
                        self.logger.info("检测到OSS签名URL，尝试直接下载")
                        response = requests.get(file_url, timeout=30, verify=False)
                        if response.status_code == 200:
                            self.logger.info("使用OSS签名URL下载成功")
                            return response.content
                except Exception as e:
                    self.logger.warning(f"OSS签名URL下载失败: {e}")
                
                # 方法2：使用内部URL
                try:
                    if hasattr(header_info, 'internal_resource_urls') and header_info.internal_resource_urls:
                        internal_url = header_info.internal_resource_urls[0]
                        self.logger.info(f"尝试使用内部URL: {internal_url}")
                        
                        # 为内部URL添加认证头
                        internal_headers = {
                            'Authorization': f'Bearer {access_token}',
                            'x-oss-object-acl': 'public-read',
                            'x-oss-date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
                            'x-oss-security-token': access_token
                        }
                        
                        response = requests.get(internal_url, headers=internal_headers, timeout=30, verify=False)
                        if response.status_code == 200:
                            self.logger.info("使用内部URL下载成功")
                            return response.content
                except Exception as e:
                    self.logger.warning(f"内部URL下载失败: {e}")
                
                # 方法3：使用不同的认证头组合
                try:
                    self.logger.info("尝试使用不同的认证头组合...")
                    
                    # 组合1：标准OSS头
                    headers1 = {
                        'Authorization': f'OSS {access_token}',
                        'x-oss-date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
                    }
                    
                    response = requests.get(file_url, headers=headers1, timeout=30, verify=False)
                    if response.status_code == 200:
                        self.logger.info("使用标准OSS头下载成功")
                        return response.content
                        
                    # 组合2：钉钉认证头
                    headers2 = {
                        'x-acs-dingtalk-access-token': access_token,
                        'Authorization': f'Bearer {access_token}'
                    }
                    
                    response = requests.get(file_url, headers=headers2, timeout=30, verify=False)
                    if response.status_code == 200:
                        self.logger.info("使用钉钉认证头下载成功")
                        return response.content
                        
                except Exception as e:
                    self.logger.warning(f"不同认证头组合下载失败: {e}")
                
                self.logger.error("所有下载方式都失败，返回None")
                
                # 记录详细的错误诊断信息
                self.logger.error("=== 文件下载失败诊断 ===")
                self.logger.error(f"文件URL: {file_url}")
                self.logger.error(f"访问令牌: {access_token[:20]}...")
                self.logger.error(f"文件名称: {file_name}")
                self.logger.error(f"文件类型: {file_type}")
                self.logger.error("可能的原因:")
                self.logger.error("1. 钉钉应用缺少Storage.Read权限")
                self.logger.error("2. 用户没有访问该文件的权限")
                self.logger.error("3. 文件所属空间权限配置问题")
                self.logger.error("4. OSS存储桶ACL配置限制")
                self.logger.error("建议解决方案:")
                self.logger.error("1. 检查钉钉应用权限配置")
                self.logger.error("2. 确认应用已上线且状态正常")
                self.logger.error("3. 联系钉钉技术支持")
                self.logger.error("=== 诊断结束 ===")
                
                return None
            
            # 创建临时文件并写入内容
            try:
                # Docker环境下的临时文件路径优化
                if is_docker:
                    temp_dir = '/tmp'
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir, exist_ok=True)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, dir=temp_dir)
                else:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                
                temp_file_path = temp_file.name
                temp_file.write(response_content)
                temp_file.close()
                temp_file = None  # 避免重复关闭
                
                self.logger.info(f"文件下载成功: {file_name}, 大小: {len(response_content)}字节, 临时文件: {temp_file_path}")
            except Exception as e:
                self.logger.error(f"创建临时文件失败: {str(e)}")
                if temp_file:
                    temp_file.close()
                return None
            
            # 检查临时文件是否存在
            if not os.path.exists(temp_file_path):
                self.logger.error(f"临时文件不存在: {temp_file_path}")
                return None
            
            # 检查文件大小
            file_size = os.path.getsize(temp_file_path)
            if file_size == 0:
                self.logger.error("临时文件大小为0")
                os.unlink(temp_file_path)
                return None
            
            self.logger.info(f"临时文件大小: {file_size}字节")
            
            # 上传到Dify - 参考Java代码的流式上传方式
            upload_url = f"{dify_api_base}/files/upload"
            headers = {
                'Authorization': f'Bearer {dify_api_key}',
                'Content-Type': 'multipart/form-data',
                'User-Agent': 'DingTalk-Bot/1.0'
            }
            
            try:
                # 创建上传会话，参考Java的连接设置
                session = requests.Session()
                session.verify = False  # 禁用SSL验证
                session.headers.update(headers)
                
                # 流式上传文件，参考Java的流式处理
                with open(temp_file_path, 'rb') as f:
                    files = {'file': (file_name, f, file_type)}
                    self.logger.info(f"开始上传文件到Dify: {upload_url}")
                    
                    # 设置上传超时，参考Java的10秒超时
                    upload_timeout = 60
                    response = session.post(
                        upload_url, 
                        files=files, 
                        timeout=upload_timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        file_id = result.get('id')
                        
                        if file_id:
                            self.logger.info(f"文件上传成功，ID: {file_id}")
                            return file_id
                        else:
                            self.logger.error(f"文件上传失败，响应: {result}")
                            return None
                    else:
                        self.logger.error(f"文件上传失败，状态码: {response.status_code}, 响应: {response.text}")
                        return None
                        
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        self.logger.info(f"清理临时文件: {temp_file_path}")
                except Exception as e:
                    self.logger.warning(f"清理临时文件失败: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"上传文件到Dify失败: {str(e)}")
            # 尝试清理临时文件
            try:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except:
                pass
            return None
    
    def _get_file_extension(self, file_name: str, mime_type: str) -> str:
        """根据文件名和MIME类型获取正确的文件扩展名"""
        try:
            # 首先尝试从文件名获取扩展名
            if '.' in file_name:
                ext = file_name.lower().split('.')[-1]
                return f".{ext}"
            
            # 如果文件名没有扩展名，根据MIME类型推断
            mime_to_ext = {
                'application/pdf': '.pdf',
                'application/msword': '.doc',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                'application/vnd.ms-excel': '.xls',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                'text/plain': '.txt',
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'audio/mpeg': '.mp3',
                'video/mp4': '.mp4'
            }
            
            return mime_to_ext.get(mime_type, '.bin')
            
        except Exception as e:
            self.logger.error(f"获取文件扩展名失败: {str(e)}")
            return '.bin'
    
    async def upload_file_to_dingtalk(self, file_path: str, file_name: str, union_id: str = None) -> str:
        """使用Storage 2.0 API上传文件到钉钉
        
        完整流程：
        1. 获取上传信息 (GetFileUploadInfo)
        2. 上传文件内容 (PUT请求)
        3. 提交文件 (CommitFile)
        """
        try:
            # 获取钉钉配置
            client_id = os.environ.get("DINGTALK_CLIENT_ID")
            client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                self.logger.error("钉钉配置不完整")
                return None
            
            # 获取访问令牌
            from dingtalk.auth import DingTalkAuth
            auth = DingTalkAuth(client_id, client_secret)
            access_token = auth.get_access_token()
            
            if not access_token:
                self.logger.error("无法获取钉钉访问令牌")
                return None
            
            # 尝试导入钉钉Storage 2.0 SDK
            try:
                from alibabacloud_dingtalk.storage_2_0.client import Client as dingtalkstorage_2_0Client
                from alibabacloud_dingtalk.storage_2_0 import models as dingtalkstorage__2__0_models
                from alibabacloud_tea_openapi import models as open_api_models
                from alibabacloud_tea_util import models as util_models
                from alibabacloud_tea_util.client import Client as UtilClient
                
                self.logger.info("钉钉Storage 2.0 SDK导入成功")
            except ImportError as e:
                self.logger.error(f"钉钉Storage 2.0 SDK导入失败: {str(e)}")
                return None
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 创建Storage 2.0客户端
            config = open_api_models.Config()
            config.protocol = 'https'
            config.region_id = 'central'
            client = dingtalkstorage_2_0Client(config)
            
            # 设置请求头
            get_file_upload_info_headers = dingtalkstorage__2__0_models.GetFileUploadInfoHeaders()
            get_file_upload_info_headers.x_acs_dingtalk_access_token = access_token
            
            # 设置预检查参数
            option_pre_check_param = dingtalkstorage__2__0_models.GetFileUploadInfoRequestOptionPreCheckParam(
                size=file_size,
                name=file_name
            )
            
            # 设置请求选项
            option = dingtalkstorage__2__0_models.GetFileUploadInfoRequestOption(
                storage_driver='DINGTALK',
                pre_check_param=option_pre_check_param,
                prefer_region='ZHANGJIAKOU',
                prefer_intranet=True
            )
            
            # 设置请求参数
            get_file_upload_info_request = dingtalkstorage__2__0_models.GetFileUploadInfoRequest(
                union_id=union_id or 'default',
                protocol='HEADER_SIGNATURE',
                option=option
            )
            
            # 调用API获取上传信息
            try:
                response = client.get_file_upload_info_with_options(
                    'uuid',  # 这里需要根据实际情况提供space_id
                    get_file_upload_info_request, 
                    get_file_upload_info_headers, 
                    util_models.RuntimeOptions()
                )
                
                if response and hasattr(response, 'body') and response.body:
                    upload_info = response.body
                    
                    # 获取上传URL和headers
                    resource_url = upload_info.get('resource_url')
                    headers = upload_info.get('headers', {})
                    
                    if resource_url and headers:
                        self.logger.info(f"获取到上传信息: URL={resource_url}")
                        
                        # 使用PUT方法上传文件
                        import requests
                        
                        # 创建上传会话
                        session = requests.Session()
                        session.verify = False
                        session.headers.update(headers)
                        
                        # 设置连接参数
                        session.headers.update({
                            'User-Agent': 'DingTalk-Bot/1.0',
                            'Accept': '*/*',
                            'Connection': 'keep-alive'
                        })
                        
                        # 流式上传文件
                        with open(file_path, 'rb') as f:
                            self.logger.info(f"开始上传文件: {file_name}")
                            response = session.put(
                                resource_url,
                                data=f,
                                timeout=60
                            )
                        
                        if response.status_code == 200:
                            self.logger.info(f"文件内容上传成功: {file_name}")
                            
                            # 第三步：提交文件 - 根据您提供的代码
                            try:
                                # 设置提交文件请求头
                                commit_file_headers = dingtalkstorage__2__0_models.CommitFileHeaders()
                                commit_file_headers.x_acs_dingtalk_access_token = access_token
                                
                                # 设置应用属性
                                option_app_properties_0 = dingtalkstorage__2__0_models.CommitFileRequestOptionAppProperties(
                                    name='source',
                                    value='dingtalk_bot',
                                    visibility='PRIVATE'
                                )
                                
                                # 设置提交选项
                                option = dingtalkstorage__2__0_models.CommitFileRequestOption(
                                    size=file_size,
                                    conflict_strategy='AUTO_RENAME',
                                    app_properties=[option_app_properties_0],
                                    convert_to_online_doc=False
                                )
                                
                                # 创建提交请求
                                commit_file_request = dingtalkstorage__2__0_models.CommitFileRequest(
                                    union_id=union_id or 'default',
                                    upload_key=upload_info.get('upload_key', ''),
                                    name=file_name,
                                    option=option
                                )
                                
                                # 提交文件
                                commit_response = client.commit_file_with_options(
                                    'uuid',  # 这里需要根据实际情况提供space_id
                                    commit_file_request, 
                                    commit_file_headers, 
                                    util_models.RuntimeOptions()
                                )
                                
                                if commit_response and hasattr(commit_response, 'body') and commit_response.body:
                                    self.logger.info(f"文件提交成功: {file_name}")
                                    return "success"
                                else:
                                    self.logger.error("文件提交失败")
                                    return None
                                    
                            except Exception as commit_err:
                                if hasattr(commit_err, 'code') and hasattr(commit_err, 'message'):
                                    self.logger.error(f"文件提交失败: code={commit_err.code}, message={commit_err.message}")
                                else:
                                    self.logger.error(f"文件提交失败: {str(commit_err)}")
                                return None
                        else:
                            self.logger.error(f"文件上传失败，状态码: {response.status_code}")
                            return None
                    else:
                        self.logger.error("上传信息不完整")
                        return None
                else:
                    self.logger.error("获取上传信息失败")
                    return None
                    
            except Exception as api_err:
                if hasattr(api_err, 'code') and hasattr(api_err, 'message'):
                    self.logger.error(f"Storage 2.0 API调用失败: code={api_err.code}, message={api_err.message}")
                else:
                    self.logger.error(f"Storage 2.0 API调用失败: {str(api_err)}")
                return None
                
        except Exception as e:
            self.logger.error(f"上传文件到钉钉失败: {str(e)}")
            return None
    
    def reply_image(self, image_url: str, incoming_message: ChatbotMessage):
        """回复图片消息"""
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
        }
        values = {
            'msgtype': 'image',
            'image': {
                'photoURL': image_url,
            },
            'at': {
                'atUserIds': [incoming_message.sender_staff_id],
            }
        }
        try:
            response = requests.post(incoming_message.session_webhook,
                                   headers=request_headers,
                                   data=json.dumps(values))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f'reply image failed, error={e}')
            return None
    
    def reply_link(self, title: str, text: str, pic_url: str, message_url: str, incoming_message: ChatbotMessage):
        """回复链接消息"""
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
        }
        values = {
            'msgtype': 'link',
            'link': {
                'title': title,
                'text': text,
                'picUrl': pic_url,
                'messageUrl': message_url,
            },
            'at': {
                'atUserIds': [incoming_message.sender_staff_id],
            }
        }
        try:
            response = requests.post(incoming_message.session_webhook,
                                   headers=request_headers,
                                   data=json.dumps(values))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f'reply link failed, error={e}')
            return None
    
    def reply_oa(self, title: str, content: str, incoming_message: ChatbotMessage, 
                 author: str = "", image_url: str = "", message_url: str = ""):
        """回复OA消息"""
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
        }
        values = {
            'msgtype': 'oa',
            'oa': {
                'title': title,
                'content': content,
                'author': author,
                'imageUrl': image_url,
                'messageUrl': message_url,
            },
            'at': {
                'atUserIds': [incoming_message.sender_staff_id],
            }
        }
        try:
            response = requests.post(incoming_message.session_webhook,
                                   headers=request_headers,
                                   data=json.dumps(values))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f'reply oa failed, error={e}')
            return None 

def main():
    """主函数"""
    try:
        # 解析命令行参数
        options = define_options()
        
        # 验证配置
        if not options.client_id or not options.client_secret:
            app_logger.error("钉钉应用配置不完整，请检查DINGTALK_CLIENT_ID和DINGTALK_CLIENT_SECRET环境变量")
            return
        
        if not options.dify_api_key:
            app_logger.error("Dify API配置不完整，请检查DIFY_API_KEY环境变量")
            return
        
        # 测试Dify API连接
        if not test_dify_api_connection(options.dify_api_base):
            app_logger.warning("无法连接到Dify API，请检查网络连接和API配置")
        
        # 初始化钉钉流式客户端
        credential = Credential(options.client_id, options.client_secret)
        stream_client = DingTalkStreamClient(credential)
        
        # 初始化Dify客户端
        dify_client = DifyClient(
            options.dify_api_base,
            options.dify_api_key,
            options.dify_app_type
        )
        
        # 创建卡片机器人处理器
        card_handler = CardBotHandler(
            dify_client=dify_client,
            card_template_id=options.card_template_id,
            logger=app_logger
        )
        
        # 注册处理程序
        stream_client.register_callback_handler(ChatbotMessage.TOPIC, card_handler)
        
        app_logger.info("钉钉-Dify流式适配器启动成功")
        app_logger.info(f"AI卡片模板ID: {options.card_template_id}")
        app_logger.info(f"Dify API: {options.dify_api_base}")
        app_logger.info(f"Dify应用类型: {options.dify_app_type}")
        app_logger.info("支持的消息类型: 文本、图片、语音、文件")
        
        # 启动流式客户端
        stream_client.start_forever()
        
    except KeyboardInterrupt:
        app_logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        app_logger.error(f"程序运行异常: {str(e)}")
        raise

if __name__ == "__main__":
    main() 