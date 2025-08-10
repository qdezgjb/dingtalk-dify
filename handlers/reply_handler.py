#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回复处理器

负责各种类型的消息回复功能
"""

import logging
from typing import Optional
from dingtalk_stream import ChatbotMessage
from dify.client import DifyClient
from utils.logger import app_logger


class ReplyHandler:
    """回复处理器"""
    
    def __init__(self, dify_client: DifyClient = None, logger: logging.Logger = app_logger):
        self.dify_client = dify_client
        self.logger = logger
    
    def reply_text(self, dingtalk_client, text: str, incoming_message: ChatbotMessage):
        """发送文本回复"""
        try:
            dingtalk_client.reply_text(text, incoming_message)
            self.logger.info(f"发送文本回复: {text[:50]}...")
        except Exception as e:
            self.logger.error(f"发送文本回复失败: {str(e)}")
    
    def reply_markdown(self, dingtalk_client, markdown: str, incoming_message: ChatbotMessage):
        """发送Markdown回复"""
        try:
            dingtalk_client.reply_markdown(markdown, incoming_message)
            self.logger.info(f"发送Markdown回复: {markdown[:50]}...")
        except Exception as e:
            self.logger.error(f"发送Markdown回复失败: {str(e)}")
    
    def reply_image(self, dingtalk_client, image_url: str, incoming_message: ChatbotMessage):
        """发送图片回复"""
        try:
            dingtalk_client.reply_image(image_url, incoming_message)
            self.logger.info(f"发送图片回复: {image_url}")
        except Exception as e:
            self.logger.error(f"发送图片回复失败: {str(e)}")
    
    def reply_link(self, dingtalk_client, title: str, text: str, pic_url: str, 
                   message_url: str, incoming_message: ChatbotMessage):
        """发送链接回复"""
        try:
            dingtalk_client.reply_link(title, text, pic_url, message_url, incoming_message)
            self.logger.info(f"发送链接回复: {title}")
        except Exception as e:
            self.logger.error(f"发送链接回复失败: {str(e)}")
    
    def reply_oa(self, dingtalk_client, title: str, content: str, incoming_message: ChatbotMessage,
                 author: str = "", image_url: str = "", message_url: str = ""):
        """发送OA消息回复"""
        try:
            dingtalk_client.reply_oa(title, content, incoming_message, author, image_url, message_url)
            self.logger.info(f"发送OA消息回复: {title}")
        except Exception as e:
            self.logger.error(f"发送OA消息回复失败: {str(e)}")
    
    def reply_card(self, dingtalk_client, card_data: dict, incoming_message: ChatbotMessage):
        """发送卡片回复"""
        try:
            dingtalk_client.reply_card(card_data, incoming_message)
            self.logger.info("发送卡片回复")
        except Exception as e:
            self.logger.error(f"发送卡片回复失败: {str(e)}")
    
    async def handle_image_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理图片消息"""
        try:
            # 提取图片信息
            image_list = incoming_message.get_image_list()
            if image_list:
                image_info = image_list[0]
                download_url = self._get_image_download_url(image_info.get('downloadCode', ''))
                
                # 发送给Dify处理
                user_id = incoming_message.sender_staff_id
                query = f"[图片消息] 用户发送了一张图片，下载地址: {download_url}"
                
                # 调用Dify API
                if self.dify_client:
                    response = self.dify_client.chat_completion(
                        query=query,
                        user=user_id,
                        stream=False
                    )
                    
                    # 获取回复内容
                    answer = response.get("accumulated_data", {}).get("answer", "图片处理完成")
                    
                    # 回复用户
                    self.reply_text(dingtalk_client, f"收到您的图片！\n\n{answer}", incoming_message)
                else:
                    self.reply_text(dingtalk_client, f"收到您的图片！\n\n图片下载地址: {download_url}", incoming_message)
            else:
                self.reply_text(dingtalk_client, "图片处理失败，请重试", incoming_message)
                
        except Exception as e:
            self.logger.error(f"处理图片消息异常: {str(e)}")
            self.reply_text(dingtalk_client, "图片处理时发生错误，请重试", incoming_message)
    
    async def handle_audio_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理语音消息"""
        try:
            # 提取语音信息
            audio_info = incoming_message.audio
            if audio_info:
                # 发送给Dify处理
                user_id = incoming_message.sender_staff_id
                query = f"[语音消息] 用户发送了一条语音消息，时长: {getattr(audio_info, 'duration', '未知')}秒"
                
                # 调用Dify API
                if self.dify_client:
                    response = self.dify_client.chat_completion(
                        query=query,
                        user=user_id,
                        stream=False
                    )
                    
                    # 获取回复内容
                    answer = response.get("accumulated_data", {}).get("answer", "语音处理完成")
                    
                    # 回复用户
                    self.reply_text(dingtalk_client, f"收到您的语音！\n\n{answer}", incoming_message)
                else:
                    duration = getattr(audio_info, 'duration', '未知')
                    self.reply_text(dingtalk_client, f"收到您的语音！\n\n语音时长: {duration}秒", incoming_message)
            else:
                self.reply_text(dingtalk_client, "语音处理失败，请重试", incoming_message)
                
        except Exception as e:
            self.logger.error(f"处理语音消息异常: {str(e)}")
            self.reply_text(dingtalk_client, "语音处理时发生错误，请重试", incoming_message)
    
    def _get_image_download_url(self, download_code: str) -> str:
        """获取图片下载URL"""
        if download_code:
            return f"https://api.dingtalk.com/v1.0/robot/media/download?downloadCode={download_code}"
        return ""
    
    def reply_error(self, dingtalk_client, error_message: str, incoming_message: ChatbotMessage):
        """发送错误回复"""
        try:
            error_text = f"❌ 处理失败\n\n{error_message}\n\n请重试或联系管理员。"
            dingtalk_client.reply_text(error_text, incoming_message)
            self.logger.error(f"发送错误回复: {error_message}")
        except Exception as e:
            self.logger.error(f"发送错误回复失败: {str(e)}")
    
    def reply_unsupported_message(self, dingtalk_client, message_type: str, incoming_message: ChatbotMessage):
        """发送不支持的消息类型回复"""
        try:
            unsupported_text = f"目前只支持文本、图片、语音和文件消息，您发送的 {message_type} 类型暂不支持~"
            dingtalk_client.reply_text(unsupported_text, incoming_message)
            self.logger.info(f"发送不支持消息类型回复: {message_type}")
        except Exception as e:
            self.logger.error(f"发送不支持消息类型回复失败: {str(e)}") 