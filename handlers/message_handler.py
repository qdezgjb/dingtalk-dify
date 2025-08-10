#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
消息处理器

负责消息分发和主要处理逻辑
"""

import asyncio
import logging
from dingtalk_stream import ChatbotMessage, AckMessage
from dify.client import DifyClient
from utils.logger import app_logger
from .ai_card_handler import AICardHandler
from .file_handler import FileHandler
from .reply_handler import ReplyHandler


class MessageHandler:
    """消息处理器"""
    
    def __init__(self, dify_client: DifyClient, card_template_id: str, logger: logging.Logger = app_logger):
        self.dify_client = dify_client
        self.card_template_id = card_template_id
        self.logger = logger
        
        # 初始化各个处理器
        self.ai_card_handler = AICardHandler(dify_client, card_template_id, logger)
        self.file_handler = FileHandler(dify_client, logger)
        self.reply_handler = ReplyHandler(dify_client, logger)
    
    async def process_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理消息"""
        try:
            self.logger.info(f"收到消息：{incoming_message}")
            
            # 根据消息类型分发处理
            if incoming_message.message_type == "text":
                # 文本消息 - 使用AI卡片处理
                await self.ai_card_handler.handle_reply_and_update_card(
                    dingtalk_client, incoming_message
                )
            elif incoming_message.message_type == "image":
                # 图片消息
                await self.reply_handler.handle_image_message(dingtalk_client, incoming_message)
            elif incoming_message.message_type == "audio":
                # 语音消息
                await self.reply_handler.handle_audio_message(dingtalk_client, incoming_message)
            elif incoming_message.message_type == "file":
                # 文件消息
                await self.file_handler.handle_file_message(dingtalk_client, incoming_message)
            else:
                # 其他类型消息
                self.reply_handler.reply_unsupported_message(
                    dingtalk_client, incoming_message.message_type, incoming_message
                )
            
            return AckMessage.STATUS_OK, "OK"
            
        except Exception as e:
            self.logger.error(f"处理消息异常: {str(e)}")
            self.reply_handler.reply_error(
                dingtalk_client, f"处理消息时发生错误: {str(e)}", incoming_message
            )
            return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)
    
    def get_supported_message_types(self):
        """获取支持的消息类型"""
        return ["text", "image", "audio", "file"]
    
    def is_supported_message_type(self, message_type: str) -> bool:
        """检查消息类型是否支持"""
        return message_type in self.get_supported_message_types()
    
    async def handle_text_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理文本消息"""
        return await self.ai_card_handler.handle_reply_and_update_card(
            dingtalk_client, incoming_message
        )
    
    async def handle_image_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理图片消息"""
        return await self.reply_handler.handle_image_message(dingtalk_client, incoming_message)
    
    async def handle_audio_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理语音消息"""
        return await self.reply_handler.handle_audio_message(dingtalk_client, incoming_message)
    
    async def handle_file_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理文件消息"""
        return await self.file_handler.handle_file_message(dingtalk_client, incoming_message)
    
    def get_message_info(self, incoming_message: ChatbotMessage) -> dict:
        """获取消息信息"""
        return {
            "message_type": incoming_message.message_type,
            "sender_id": incoming_message.sender_staff_id,
            "conversation_id": incoming_message.conversation_id,
            "message_id": incoming_message.message_id,
            "timestamp": incoming_message.create_at,
            "content": getattr(incoming_message.text, 'content', '') if hasattr(incoming_message, 'text') else ''
        } 