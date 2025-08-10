#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI卡片处理器

负责AI卡片的创建、更新和流式输出功能
"""

import asyncio
import logging
from typing import Callable, Optional
from dingtalk_stream import ChatbotMessage, AICardReplier
from dify.client import DifyClient
from utils.logger import app_logger


class AICardHandler:
    """AI卡片处理器"""
    
    def __init__(self, dify_client: DifyClient, card_template_id: str, logger: logging.Logger = app_logger):
        self.dify_client = dify_client
        self.card_template_id = card_template_id
        self.logger = logger
    
    async def handle_reply_and_update_card(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理回复并更新AI卡片"""
        try:
            # 获取用户ID和消息内容 - 使用ChatbotMessage的标准属性
            user_id = incoming_message.sender_staff_id
            request_content = ""
            
            # 获取消息内容 - 使用ChatbotMessage的标准方法
            if hasattr(incoming_message, 'text') and incoming_message.text:
                request_content = incoming_message.text.content.strip()
            else:
                # 如果没有text属性，尝试其他方式
                self.logger.warning("消息没有text属性，尝试其他方式获取内容")
                request_content = str(incoming_message).strip()
            
            self.logger.info(f"处理AI卡片消息: 用户={user_id}, 内容={request_content}")
            self.logger.info(f"消息对象属性: {dir(incoming_message)}")
            
            # 创建AI卡片回复器
            # 检查dingtalk_client的类型，如果是ChatbotHandler，需要获取其dingtalk_client属性
            if hasattr(dingtalk_client, 'dingtalk_client'):
                actual_client = dingtalk_client.dingtalk_client
            else:
                actual_client = dingtalk_client
            
            card_instance = AICardReplier(actual_client, incoming_message)
            
            # 创建卡片数据
            card_data = {
                "content": "正在思考中...",
                "status": "processing"
            }
            
            # 创建AI卡片
            try:
                card_instance_id = await card_instance.async_create_and_deliver_card(
                    self.card_template_id,
                    card_data,
                    callback_type="STREAM",
                    at_sender=False,
                    at_all=False,
                    support_forward=True
                )
                self.logger.info(f"AI卡片创建成功: {card_instance_id}")
            except Exception as e:
                self.logger.error(f"AI卡片创建失败: {str(e)}")
                # 回退到普通文本消息
                return await self._fallback_to_text(dingtalk_client, incoming_message, request_content)
            
            # 定义卡片更新回调函数
            async def update_card_callback(content_value: str):
                try:
                    await card_instance.async_streaming(
                        card_instance_id,
                        content_key="content",
                        content_value=content_value,
                        append=False,
                        finished=False,
                        failed=False
                    )
                except Exception as e:
                    self.logger.error(f"AI卡片更新失败: {str(e)}")
            
            # 调用Dify API进行流式处理
            full_content = await self._call_dify_with_stream(
                request_content, 
                update_card_callback, 
                user_id
            )
            
            # 标记卡片完成
            try:
                await card_instance.async_streaming(
                    card_instance_id,
                    content_key="content",
                    content_value=full_content,  # 使用完整的最终内容
                    append=False,
                    finished=True,
                    failed=False
                )
                self.logger.info("AI卡片处理完成")
            except Exception as e:
                self.logger.error(f"标记AI卡片完成失败: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"AI卡片处理异常: {str(e)}")
            # 回退到普通文本消息
            await self._fallback_to_text(dingtalk_client, incoming_message, request_content)
    
    async def _call_dify_with_stream(self, request_content: str, callback: Callable[[str], None], user_id: str):
        """调用Dify API进行流式处理"""
        try:
            # 调用Dify API
            response = self.dify_client.chat_completion(
                query=request_content,
                user=user_id,
                stream=True
            )
            
            self.logger.info(f"Dify API响应格式: {type(response)}")
            self.logger.info(f"Dify API响应键: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            full_content = ""
            length = 0
            update_threshold = 20  # 每20个字符更新一次
            
            # 处理流式响应
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
                full_content = "抱歉，暂时无法生成回复，请稍后再试。"
            
            return full_content
                
        except Exception as e:
            self.logger.error(f"Dify流式调用失败: {str(e)}")
            await callback("抱歉，处理您的消息时出现了问题，请重试。")
            return "抱歉，处理您的消息时出现了问题，请重试。"
    
    async def _fallback_to_text(self, dingtalk_client, incoming_message: ChatbotMessage, request_content: str):
        """回退到普通文本消息"""
        try:
            user_id = incoming_message.sender_staff_id
            
            # 调用Dify API（非流式）
            response = self.dify_client.chat_completion(
                query=request_content,
                user=user_id,
                stream=False
            )
            
            # 获取回复内容
            answer = response.get("accumulated_data", {}).get("answer", "处理完成")
            
            # 发送文本回复 - 使用ChatbotHandler的方法
            dingtalk_client.reply_text(answer, incoming_message)
            self.logger.info("已回退到文本消息")
            
        except Exception as e:
            self.logger.error(f"回退处理失败: {str(e)}")
            dingtalk_client.reply_text("抱歉，处理您的消息时出现了问题，请重试。", incoming_message) 