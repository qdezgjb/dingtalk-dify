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
                    
                    # 根据钉钉文档，使用downloadCode构建下载URL
                    if download_code:
                        file_url = self._build_download_url(download_code, file_id, space_id)
                    else:
                        file_url = ''
                    
                    file_type = self._get_file_type(file_name)
                else:
                    # 如果不是字典，尝试其他方式解析
                    file_name = str(file_info) if file_info else '未知文件'
                    file_size = 0
                    file_url = ''
                    file_type = '未知类型'
                
                self.logger.info(f"文件信息: 名称={file_name}, 大小={file_size}, 类型={file_type}, URL={file_url}")
                
                # 如果文件URL为空，尝试从钉钉API获取文件下载地址
                if not file_url:
                    self.logger.warning("文件URL为空，尝试从钉钉API获取文件信息")
                    # 这里可以调用钉钉API获取文件信息
                    # 暂时使用默认处理
                    file_url = self._get_file_download_url(incoming_message)
                
                if file_url:
                    # 上传文件到Dify
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
                        self.reply_text(f"收到您的文件！\n\n文件名: {file_name}\n大小: {file_size}字节\n\n文件上传失败，但我会尝试处理文件内容。", incoming_message)
                else:
                    self.reply_text(f"收到您的文件！\n\n文件名: {file_name}\n大小: {file_size}字节\n\n无法获取文件下载地址，请重试。", incoming_message)
            else:
                self.reply_text("文件处理失败，无法获取文件信息，请重试", incoming_message)
                
        except Exception as e:
            self.logger.error(f"处理文件消息异常: {str(e)}")
            self.reply_text("文件处理时发生错误，请重试", incoming_message)
    
    def _build_download_url(self, download_code: str, file_id: str, space_id: str) -> str:
        """根据钉钉文件信息构建下载URL"""
        try:
            # 根据钉钉文档，尝试不同的API路径
            # 钉钉文件下载可能有多种方式，我们需要尝试不同的API
            
            # 方法1：使用文件ID下载
            if file_id:
                download_url = f"https://api.dingtalk.com/v1.0/robot/media/download?fileId={file_id}"
                self.logger.info(f"尝试使用fileId下载: {download_url}")
                return download_url
            
            # 方法2：使用downloadCode下载（原始方法）
            elif download_code:
                download_url = f"https://api.dingtalk.com/v1.0/robot/media/download?downloadCode={download_code}"
                self.logger.info(f"尝试使用downloadCode下载: {download_url}")
                return download_url
            
            # 方法3：使用spaceId和fileId组合
            elif space_id and file_id:
                download_url = f"https://api.dingtalk.com/v1.0/robot/media/download?spaceId={space_id}&fileId={file_id}"
                self.logger.info(f"尝试使用spaceId和fileId下载: {download_url}")
                return download_url
            
            else:
                self.logger.error("无法构建下载URL，缺少必要参数")
                return ""
                
        except Exception as e:
            self.logger.error(f"构建下载URL失败: {str(e)}")
            return ""
    
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
        """从钉钉API获取文件下载地址"""
        try:
            # 根据钉钉文档：https://open.dingtalk.com/document/isvapp/upload-media-files
            # 需要先获取文件的mediaId，然后调用下载API
            
            # 从消息中提取mediaId
            media_id = None
            
            # 检查extensions中是否有mediaId
            if hasattr(incoming_message, 'extensions') and incoming_message.extensions:
                for key, value in incoming_message.extensions.items():
                    if 'media' in key.lower() or 'id' in key.lower():
                        if isinstance(value, dict) and 'id' in value:
                            media_id = value.get('id')
                        elif isinstance(value, str):
                            media_id = value
                        break
            
            # 如果没有找到mediaId，尝试从其他字段获取
            if not media_id:
                # 检查消息的其他属性
                message_data = incoming_message.__dict__
                for key, value in message_data.items():
                    if 'media' in key.lower() and value:
                        media_id = value
                        break
            
            if media_id:
                self.logger.info(f"找到文件mediaId: {media_id}")
                # 构建下载URL
                # 根据钉钉API文档，下载URL格式为：/v1.0/robot/media/download?mediaId={mediaId}
                download_url = f"https://api.dingtalk.com/v1.0/robot/media/download?mediaId={media_id}"
                return download_url
            else:
                self.logger.warning("未找到文件mediaId")
                return ""
            
        except Exception as e:
            self.logger.error(f"获取文件下载地址失败: {str(e)}")
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
            
            # 获取正确的文件扩展名
            file_extension = self._get_file_extension(file_name, file_type)
            self.logger.info(f"文件扩展名: {file_extension}")
            
            # 创建临时文件，使用正确的扩展名
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
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
                
                # 尝试下载文件，如果失败则尝试其他方法
                download_success = False
                response_content = None
                
                # 方法1：直接下载
                try:
                    self.logger.info(f"开始下载文件: {file_url}")
                    response = requests.get(file_url, headers=headers, verify=False, timeout=30)
                    if response.status_code == 200 and len(response.content) > 0:
                        response_content = response.content
                        download_success = True
                        self.logger.info(f"文件下载成功: {file_name}, 大小: {len(response.content)}字节")
                    else:
                        self.logger.warning(f"文件下载失败，状态码: {response.status_code}, 内容长度: {len(response.content)}")
                except Exception as e:
                    self.logger.warning(f"文件下载失败: {str(e)}")
                
                # 如果下载失败，尝试其他方法
                if not download_success:
                    self.logger.warning("直接下载失败，尝试其他方法...")
                    
                    # 尝试不同的API路径
                    alternative_urls = [
                        # 方法1：使用fileId
                        file_url.replace("downloadCode=", "fileId=") if "downloadCode=" in file_url else None,
                        # 方法2：使用不同的API路径
                        file_url.replace("/robot/media/download", "/robot/file/download") if "/robot/media/download" in file_url else None,
                        # 方法3：使用不同的参数格式
                        file_url.replace("downloadCode=", "code=") if "downloadCode=" in file_url else None,
                    ]
                    
                    for alt_url in alternative_urls:
                        if alt_url and alt_url != file_url:
                            try:
                                self.logger.info(f"尝试备用下载URL: {alt_url}")
                                response = requests.get(alt_url, headers=headers, verify=False, timeout=30)
                                if response.status_code == 200 and len(response.content) > 0:
                                    response_content = response.content
                                    download_success = True
                                    self.logger.info(f"备用下载成功: {file_name}, 大小: {len(response.content)}字节")
                                    break
                                else:
                                    self.logger.warning(f"备用下载失败，状态码: {response.status_code}")
                            except Exception as e:
                                self.logger.warning(f"备用下载失败: {str(e)}")
                                continue
                
                if not response_content:
                    self.logger.error("所有下载方法都失败了")
                    return None
                
                # 写入临时文件
                temp_file.write(response_content)
                temp_file_path = temp_file.name
                
                self.logger.info(f"文件下载成功: {file_name}, 大小: {len(response_content)}字节, 临时文件: {temp_file_path}")
            
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
            
            # 上传到Dify
            upload_url = f"{dify_api_base}/files/upload"
            headers = {
                'Authorization': f'Bearer {dify_api_key}',
            }
            
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {'file': (file_name, f, file_type)}
                    self.logger.info(f"开始上传文件到Dify: {upload_url}")
                    response = requests.post(upload_url, headers=headers, files=files, verify=False, timeout=60)
                    response.raise_for_status()
                    
                    result = response.json()
                    file_id = result.get('id')
                    
                    if file_id:
                        self.logger.info(f"文件上传成功，ID: {file_id}")
                        return file_id
                    else:
                        self.logger.error(f"文件上传失败，响应: {result}")
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