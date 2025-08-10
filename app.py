#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钉钉-Dify流式适配器 - 统一版

整合了重构版和完整版的所有功能
基于模块化架构，支持多类型消息处理和Dify工作流集成
"""

import os
import sys
import asyncio
import argparse
import logging
import threading
import time
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# SSL修复 - 在导入其他模块之前应用
from utils.ssl_utils import SSLUtils
SSLUtils.apply_ssl_fixes()

# 添加当前目录到Python模块搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

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
from dingtalk_stream import DingTalkStreamClient, Credential, AckMessage, ChatbotHandler, CallbackHandler

# 导入自定义模块
from dify.client import DifyClient
from utils.logger import app_logger

# 导入处理器模块
try:
    from handlers.message_handler import MessageHandler
    MODULAR_HANDLERS_AVAILABLE = True
except ImportError:
    MODULAR_HANDLERS_AVAILABLE = False
    app_logger.warning("模块化处理器不可用，将使用内置处理器")


def define_options():
    """定义命令行参数"""
    parser = argparse.ArgumentParser(description='钉钉-Dify流式适配器 - 统一版')
    
    # 钉钉配置
    parser.add_argument('--client_id', help='钉钉应用客户端ID')
    parser.add_argument('--client_secret', help='钉钉应用客户端密钥')
    parser.add_argument('--card_template_id', help='AI卡片模板ID')
    
    # Dify配置
    parser.add_argument('--dify_api_base', help='Dify API基础URL')
    parser.add_argument('--dify_api_key', help='Dify API密钥')
    parser.add_argument('--dify_app_type', choices=['chat', 'completion'], default='chat', help='Dify应用类型')
    
    # 服务器配置
    parser.add_argument('--port', type=int, default=9000, help='服务器端口')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机')
    
    # 功能开关
    parser.add_argument('--use-modular-handlers', action='store_true', help='使用模块化处理器')
    parser.add_argument('--use-builtin-handlers', action='store_true', help='使用内置处理器')
    
    return parser


def load_config_from_env() -> Dict[str, Any]:
    """从环境变量加载配置"""
    config = {
        'client_id': os.getenv('DINGTALK_CLIENT_ID'),
        'client_secret': os.getenv('DINGTALK_CLIENT_SECRET'),
        'card_template_id': os.getenv('DINGTALK_AI_CARD_TEMPLATE_ID'),
        'dify_api_base': os.getenv('DIFY_API_BASE', 'https://api.dify.ai/v1'),
        'dify_api_key': os.getenv('DIFY_API_KEY'),
        'dify_app_type': os.getenv('DIFY_APP_TYPE', 'chat'),
        'port': int(os.getenv('SERVER_PORT', '9000')),
        'host': os.getenv('SERVER_HOST', '0.0.0.0'),
        'use_workflow': os.environ.get('DIFY_USE_WORKFLOW', 'false').lower() == 'true'
    }
    
    # 验证必需配置
    required_fields = ['client_id', 'client_secret', 'dify_api_key']
    missing_fields = [field for field in required_fields if not config.get(field)]
    
    if missing_fields:
        raise ValueError(f"缺少必需的环境变量: {', '.join(missing_fields)}")
    
    return config


def test_dify_api_connection(api_base: str) -> bool:
    """测试Dify API连接"""
    try:
        import requests
        # 使用SSL工具确保SSL配置正确
        SSLUtils.apply_ssl_fixes()
        response = requests.get(f"{api_base}/health", timeout=10, verify=False)
        return response.status_code == 200
    except Exception as e:
        app_logger.error(f"Dify API连接测试失败: {str(e)}")
        return False


class UnifiedCardBotHandler(ChatbotHandler):
    """统一的卡片机器人处理器，支持模块化和内置处理器"""
    
    def __init__(self, dify_client: DifyClient, card_template_id: str, 
                 use_modular_handlers: bool = False, logger: logging.Logger = app_logger):
        super().__init__()
        self.dify_client = dify_client
        self.card_template_id = card_template_id
        self.use_modular_handlers = use_modular_handlers
        self.logger = logger
        
        # 初始化处理器
        if use_modular_handlers and MODULAR_HANDLERS_AVAILABLE:
            self.message_handler = MessageHandler(
                dify_client=dify_client,
                card_template_id=card_template_id,
                logger=logger
            )
            self.logger.info("使用模块化处理器")
        else:
            self.logger.info("使用内置处理器")
    
    async def process(self, callback):
        """处理消息"""
        try:
            # 正确解析钉钉流式SDK的消息格式
            self.logger.info(f"收到回调消息：{callback}")
            self.logger.info(f"消息类型：{type(callback)}")
            self.logger.info(f"消息属性：{dir(callback)}")
            
            # 从CallbackMessage中提取ChatbotMessage
            from dingtalk_stream import ChatbotMessage
            incoming_message = ChatbotMessage.from_dict(callback.data)
            self.logger.info(f"成功解析ChatbotMessage：{incoming_message}")

            # 使用模块化处理器或内置处理器
            if self.use_modular_handlers and MODULAR_HANDLERS_AVAILABLE:
                return await self._process_with_modular_handlers(incoming_message)
            else:
                return await self._process_with_builtin_handlers(incoming_message)
        except Exception as e:
            self.logger.error(f"消息处理异常: {str(e)}")
            return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)
    
    async def _process_with_modular_handlers(self, incoming_message):
        """使用模块化处理器处理消息"""
        try:
            # 使用消息处理器处理消息
            status, message = await self.message_handler.process_message(self, incoming_message)
            return status, message
        except Exception as e:
            self.logger.error(f"模块化处理器处理消息异常: {str(e)}")
            return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)
    
    async def _process_with_builtin_handlers(self, incoming_message):
        """使用内置处理器处理消息"""
        try:
            # 获取消息类型，支持多种格式
            message_type = None
            if hasattr(incoming_message, 'message_type'):
                message_type = incoming_message.message_type
            elif hasattr(incoming_message, 'type'):
                message_type = incoming_message.type
            elif hasattr(incoming_message, 'msg_type'):
                message_type = incoming_message.msg_type
            
            self.logger.info(f"消息类型: {message_type}")
            
            # 处理不同类型的消息
            if message_type == "text" or message_type == "TEXT":
                # 文本消息 - 使用AI卡片处理
                await self._handle_text_message(incoming_message)
            elif message_type == "image" or message_type == "IMAGE":
                # 图片消息
                await self._handle_image_message(incoming_message)
            elif message_type == "audio" or message_type == "AUDIO":
                # 语音消息
                await self._handle_audio_message(incoming_message)
            elif message_type == "file" or message_type == "FILE":
                # 文件消息
                await self._handle_file_message(incoming_message)
            else:
                # 默认按文本消息处理
                self.logger.warning(f"未知消息类型: {message_type}，按文本消息处理")
                await self._handle_text_message(incoming_message)
            
            return AckMessage.STATUS_OK, "OK"
        except Exception as e:
            self.logger.error(f"内置处理器处理消息异常: {str(e)}")
            return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)
    
    async def _handle_text_message(self, incoming_message):
        """处理文本消息 - 内置处理器"""
        try:
            # 直接使用官方的方式处理AI卡片
            await self._handle_ai_card(incoming_message)
        except Exception as e:
            self.logger.error(f"处理文本消息异常: {str(e)}")
            self.reply_text("处理消息时发生错误，请重试", incoming_message)
    
    async def _handle_ai_card(self, incoming_message):
        """处理AI卡片 - 使用官方方式"""
        try:
            # 获取用户ID
            user_id = incoming_message.sender_staff_id
            self.logger.info(f"处理用户 {user_id} 的消息")
            
            # 卡片数据键名
            content_key = "content"
            card_data = {content_key: ""}
            
            # 创建AI卡片回复器
            from dingtalk_stream import AICardReplier
            card_instance = AICardReplier(self.dingtalk_client, incoming_message)
            card_instance_id = None
            
            try:
                # 1. 先投放卡片 - 使用官方推荐的方式
                self.logger.info(f"开始创建AI卡片，模板ID: {self.card_template_id}")
                
                # 根据官方文档，使用async_create_and_deliver_card方法
                card_instance_id = await card_instance.async_create_and_deliver_card(
                    self.card_template_id, 
                    card_data,
                    callback_type="STREAM",  # 指定回调类型为流式
                    at_sender=False,  # 不@发送者
                    at_all=False,     # 不@所有人
                    support_forward=True  # 支持转发
                )
                
                if not card_instance_id:
                    self.logger.error("创建AI卡片失败")
                    # 如果卡片创建失败，回退到普通文本消息
                    self.reply_text("思考中...", incoming_message)
                    return False
                
                self.logger.info(f"成功创建AI卡片，实例ID: {card_instance_id}")
                
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
                            self.logger.error(f"更新卡片失败: {str(e)}")
                            # 如果卡片更新失败，回退到普通文本消息
                            self.reply_text(content_value, incoming_message)
                    else:
                        # 如果没有卡片ID，直接发送文本消息
                        self.reply_text(content_value, incoming_message)
                
                # 3. 调用Dify API并处理流式响应
                full_content = await self._call_dify_with_stream(
                    incoming_message.text.content, 
                    update_card_callback,
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
                        self.logger.info(f"完成流式响应，总长度: {len(full_content)}")
                    except Exception as e:
                        self.logger.error(f"最终更新卡片失败: {str(e)}")
                        # 回退到普通文本消息
                        self.reply_text(full_content, incoming_message)
                else:
                    # 如果没有卡片ID，发送最终文本消息
                    self.reply_text(full_content, incoming_message)
                
                return True
                
            except Exception as e:
                self.logger.exception(f"处理消息异常: {str(e)}")
                
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
                        self.logger.error(f"更新错误状态失败: {str(update_error)}")
                        # 回退到普通文本消息
                        self.reply_text(f"处理消息时发生错误: {str(e)}", incoming_message)
                else:
                    # 如果没有卡片ID，发送错误文本消息
                    self.reply_text(f"处理消息时发生错误: {str(e)}", incoming_message)
                
                return False
                
        except Exception as e:
            self.logger.error(f"AI卡片处理异常: {str(e)}")
            # 回退到普通文本消息
            await self._fallback_to_text(incoming_message)
    
    async def _call_dify_with_stream(self, request_content: str, callback, user_id: str):
        """调用Dify API并处理流式响应，基于钉钉官方文档"""
        try:
            # 调用Dify API，确保传递user参数
            response = self.dify_client.chat_completion(
                query=request_content,
                user=user_id,  # 确保传递用户ID
                stream=True
            )
            
            self.logger.info(f"Dify API响应格式: {type(response)}")
            self.logger.info(f"Dify API响应键: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            full_content = ""
            length = 0
            update_threshold = 20  # 每20个字符更新一次，符合官方文档建议
            
            # 处理流式响应 - 使用正确的Dify API响应格式
            event_stream = response.get("event_stream", [])
            self.logger.info(f"事件流长度: {len(event_stream)}")
            
            for i, chunk in enumerate(event_stream):
                self.logger.debug(f"处理第 {i+1} 个数据块: {chunk}")
                
                # 检查是否有answer字段
                if "answer" in chunk:
                    answer_chunk = chunk.get("answer", "")
                    full_content += answer_chunk
                    self.logger.debug(f"累积内容: {full_content}")
                    
                    # 当累积内容长度超过阈值时更新卡片
                    # 这实现了官方文档中提到的"打字机效果"
                    full_content_length = len(full_content)
                    if full_content_length - length > update_threshold:
                        await callback(full_content)
                        self.logger.info(
                            f"调用流式更新接口更新内容：current_length: {length}, next_length: {full_content_length}"
                        )
                        length = full_content_length
                else:
                    self.logger.debug(f"数据块中没有answer字段: {chunk}")
            
            # 最终回调 - 确保完整内容被发送
            if full_content:
                await callback(full_content)
                self.logger.info(
                    f"Request Content: {request_content}\nFull response: {full_content}\nFull response length: {len(full_content)}"
                )
            else:
                self.logger.warning("未获取到有效内容")
                await callback("抱歉，暂时无法生成回复，请稍后再试。")
            
            return full_content
            
        except Exception as e:
            self.logger.error(f"调用Dify API异常: {str(e)}")
            # 发生异常时，尝试发送错误信息
            try:
                await callback("抱歉，处理您的请求时出现了错误，请稍后再试。")
            except Exception as callback_error:
                self.logger.error(f"发送错误信息失败: {str(callback_error)}")
            raise
    
    async def _fallback_to_text(self, incoming_message):
        """回退到普通文本消息"""
        try:
            # 调用Dify API（非流式）
            response = self.dify_client.chat_completion(
                query=incoming_message.text.content,
                user="user",
                stream=False
            )
            
            # 获取回复内容
            answer = response.get("accumulated_data", {}).get("answer", "处理完成")
            
            # 发送文本回复
            self.reply_text(answer, incoming_message)
            self.logger.info("已回退到文本消息")
            
        except Exception as e:
            self.logger.error(f"回退处理失败: {str(e)}")
            self.reply_text("抱歉，处理您的消息时出现了问题，请重试。", incoming_message)
    
    async def _handle_image_message(self, incoming_message):
        """处理图片消息 - 内置处理器"""
        try:
            from handlers.reply_handler import ReplyHandler
            reply_handler = ReplyHandler(self.dify_client, self.logger)
            await reply_handler.handle_image_message(self, incoming_message)
        except Exception as e:
            self.logger.error(f"处理图片消息异常: {str(e)}")
            self.reply_text("图片处理时发生错误，请重试", incoming_message)
    
    async def _handle_audio_message(self, incoming_message):
        """处理语音消息 - 内置处理器"""
        try:
            from handlers.reply_handler import ReplyHandler
            reply_handler = ReplyHandler(self.dify_client, self.logger)
            await reply_handler.handle_audio_message(self, incoming_message)
        except Exception as e:
            self.logger.error(f"处理语音消息异常: {str(e)}")
            self.reply_text("语音处理时发生错误，请重试", incoming_message)
    
    async def _handle_file_message(self, incoming_message):
        """处理文件消息 - 内置处理器"""
        try:
            from handlers.file_handler import FileHandler
            file_handler = FileHandler(self.dify_client, self.logger)
            await file_handler.handle_file_message(self, incoming_message)
        except Exception as e:
            self.logger.error(f"处理文件消息异常: {str(e)}")
            self.reply_text("文件处理时发生错误，请重试", incoming_message)


def main():
    """主函数"""
    global start_time
    start_time = time.time()
    
    try:
        # 解析命令行参数
        parser = define_options()
        args = parser.parse_args()
        
        # 应用SSL修复
        app_logger.info("正在应用SSL修复...")
        ssl_results = SSLUtils.fix_ssl_issues()
        app_logger.info(f"SSL修复完成: {sum(ssl_results.values())}/{len(ssl_results)} 项成功")
        
        # 加载配置
        config = load_config_from_env()
        
        # 命令行参数覆盖环境变量
        if args.client_id:
            config['client_id'] = args.client_id
        if args.client_secret:
            config['client_secret'] = args.client_secret
        if args.card_template_id:
            config['card_template_id'] = args.card_template_id
        if args.dify_api_base:
            config['dify_api_base'] = args.dify_api_base
        if args.dify_api_key:
            config['dify_api_key'] = args.dify_api_key
        if args.dify_app_type:
            config['dify_app_type'] = args.dify_app_type
        if args.port:
            config['port'] = args.port
        if args.host:
            config['host'] = args.host
        
        # 确定处理器类型
        use_modular_handlers = args.use_modular_handlers or (not args.use_builtin_handlers and MODULAR_HANDLERS_AVAILABLE)
        
        # 测试Dify API连接
        if not test_dify_api_connection(config['dify_api_base']):
            app_logger.warning("Dify API连接测试失败，但继续启动...")
        
        # 创建Dify客户端
        dify_client = DifyClient(
            api_base=config['dify_api_base'],
            api_key=config['dify_api_key'],
            app_type=config['dify_app_type']
        )
        
        # 创建钉钉客户端凭证
        credential = Credential(
            client_id=config['client_id'],
            client_secret=config['client_secret']
        )
        
        # 创建钉钉流式客户端
        client = DingTalkStreamClient(credential)
        
        # 创建统一的机器人处理器
        handler = UnifiedCardBotHandler(
            dify_client=dify_client,
            card_template_id=config['card_template_id'],
            use_modular_handlers=use_modular_handlers,
            logger=app_logger
        )
        
        # 设置handler的dingtalk_client
        handler.dingtalk_client = client
        
        # 注册处理器 - 使用正确的TOPIC
        try:
            from dingtalk_stream import ChatbotMessage
            client.register_callback_handler(ChatbotMessage.TOPIC, handler)
            app_logger.info("使用ChatbotMessage.TOPIC注册处理器")
        except Exception as e:
            app_logger.error(f"注册处理器失败: {str(e)}")
            raise e
        
        # 启动客户端
        app_logger.info(f"启动钉钉-Dify流式适配器 - 统一版...")
        app_logger.info(f"服务器地址: {config['host']}:{config['port']}")
        app_logger.info(f"Dify API: {config['dify_api_base']}")
        app_logger.info(f"处理器类型: {'模块化' if use_modular_handlers else '内置'}")
        app_logger.info(f"支持的消息类型: 文本、图片、语音、文件")
        
        client.start_forever()
        
    except KeyboardInterrupt:
        app_logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        app_logger.error(f"启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # 运行主函数
    try:
        main()
    except Exception as e:
        print(f"启动失败: {str(e)}")
        sys.exit(1) 