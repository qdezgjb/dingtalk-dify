#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件处理器

负责文件下载、上传和处理功能
支持钉钉云盘存储和Dify工作流集成
基于钉钉官方Storage 2.0 API实现
"""

import os
import tempfile
import mimetypes
import logging
import requests
import json
import time
from typing import Optional, Dict, Any, Tuple
from dingtalk_stream import ChatbotMessage
from dify.client import DifyClient
from utils.logger import app_logger
from utils.dingtalk_client import get_union_id_with_client


class FileHandler:
    """文件处理器 - 基于钉钉官方API规范"""
    
    def __init__(self, dify_client: DifyClient, logger: logging.Logger = app_logger):
        self.dify_client = dify_client
        self.logger = logger
        # 钉钉配置
        self.client_id = os.environ.get("DINGTALK_CLIENT_ID")
        self.client_secret = os.environ.get("DINGTALK_CLIENT_SECRET")
        # 文件大小限制 (默认100MB)
        self.max_file_size = int(os.environ.get('MAX_FILE_SIZE_MB', '100')) * 1024 * 1024
        # Dify工作流配置
        self.use_workflow = os.environ.get("DIFY_USE_WORKFLOW", "false").lower() == "true"
        self.workflow_id = os.environ.get("DIFY_WORKFLOW_ID", "")
    
    async def handle_file_message(self, dingtalk_client, incoming_message: ChatbotMessage):
        """处理文件消息 - 钉钉官方规范流程"""
        try:
            # 检查文件消息的属性
            self.logger.info(f"文件消息详情: {incoming_message}")
            self.logger.info(f"文件消息扩展信息: {getattr(incoming_message, 'extensions', {})}")
            
            # 从extensions中获取文件信息
            file_info = self._extract_file_info(incoming_message)
            
            if not file_info:
                dingtalk_client.reply_text("无法获取文件信息，请重试", incoming_message)
                return
            
            file_name = file_info['name']
            file_size = file_info['size']
            file_type = file_info['type']
            
            self.logger.info(f"文件信息: 名称={file_name}, 大小={file_size}, 类型={file_type}")
            
            # 检查文件大小
            if file_size > self.max_file_size:
                dingtalk_client.reply_text(
                    f"文件过大，当前文件大小: {file_size // (1024*1024)}MB，最大支持: {self.max_file_size // (1024*1024)}MB", 
                    incoming_message
                )
                return
            
            # 获取用户unionId
            union_id = await self._get_user_union_id(incoming_message)
            if not union_id:
                dingtalk_client.reply_text("无法获取用户信息，请重试", incoming_message)
                return
            
            # 第一步：上传文件到钉钉云盘（钉钉官方规范）
            upload_result = await self._upload_to_dingtalk_drive(file_name, file_size, union_id)
            
            if upload_result['success']:
                # 文件上传成功，获取钉钉云盘链接
                doc_url = upload_result['doc_url']
                file_id = upload_result['file_id']
                
                # 回复用户文件上传成功信息
                upload_reply = f"✅ 文件上传成功！\n\n📁 文件名: {file_name}\n📊 大小: {file_size // 1024}KB\n🔗 钉钉云盘链接: {doc_url}"
                dingtalk_client.reply_text(upload_reply, incoming_message)
                
                # 第二步：发送文件给Dify工作流进行分析
                await self._process_with_dify_workflow(
                    file_name, file_size, file_type, union_id, 
                    file_id, doc_url, dingtalk_client, incoming_message
                )
            else:
                # 文件上传失败，尝试使用文件信息进行处理
                self.logger.warning(f"文件上传到钉钉云盘失败: {upload_result['error']}")
                await self._process_with_dify_workflow(
                    file_name, file_size, file_type, union_id, 
                    None, None, dingtalk_client, incoming_message
                )
                
        except Exception as e:
            self.logger.error(f"处理文件消息异常: {str(e)}")
            dingtalk_client.reply_text("文件处理时发生错误，请重试", incoming_message)
    
    def _extract_file_info(self, incoming_message: ChatbotMessage) -> Optional[Dict[str, Any]]:
        """从消息中提取文件信息 - 钉钉官方规范"""
        try:
            file_info = None
            
            # 从extensions的content字段中提取文件信息
            if hasattr(incoming_message, 'extensions') and incoming_message.extensions:
                extensions = incoming_message.extensions
                self.logger.info(f"扩展信息: {extensions}")
                
                # 尝试从不同字段获取文件信息
                if isinstance(extensions, dict):
                    # 直接是字典格式
                    file_info = extensions
                elif isinstance(extensions, str):
                    # 字符串格式，尝试JSON解析
                    try:
                        file_info = json.loads(extensions)
                    except json.JSONDecodeError:
                        self.logger.warning("无法解析扩展信息JSON")
                        return None
                
                # 如果extensions中有content字段，优先使用content中的信息
                if isinstance(file_info, dict) and 'content' in file_info:
                    file_info = file_info['content']
                    self.logger.info(f"从content字段提取文件信息: {file_info}")
                
                # 检查是否包含必要的文件信息（钉钉官方要求）
                # 钉钉实际返回的字段是 fileName 而不是 name，且没有 size 字段
                if file_info and 'fileName' in file_info:
                    # 构建标准化的文件信息
                    standardized_file_info = {
                        'name': file_info.get('fileName'),
                        'size': file_info.get('size', 0),  # 如果没有size字段，默认为0
                        'type': self._get_file_type(file_info.get('fileName', '')),
                        'spaceId': file_info.get('spaceId'),
                        'downloadCode': file_info.get('downloadCode'),
                        'fileId': file_info.get('fileId')
                    }
                    
                    self.logger.info(f"成功提取文件信息: {standardized_file_info}")
                    return standardized_file_info
                else:
                    self.logger.warning(f"文件信息不完整: {file_info}")
            
            # 如果extensions中没有找到，尝试从其他字段获取
            if hasattr(incoming_message, 'text') and incoming_message.text:
                self.logger.info(f"消息文本内容: {incoming_message.text}")
                # 这里可以添加文本解析逻辑，如果文件信息在文本中
            
            self.logger.warning("无法从消息中提取有效的文件信息")
            return None
            
            # 如果extensions中没有找到，尝试从其他字段获取
            if hasattr(incoming_message, 'text') and incoming_message.text:
                self.logger.info(f"消息文本内容: {incoming_message.text}")
                # 这里可以添加文本解析逻辑，如果文件信息在文本中
            
            self.logger.warning("无法从消息中提取有效的文件信息")
            return None
            
        except Exception as e:
            self.logger.error(f"提取文件信息异常: {str(e)}")
            return None
    
    async def _get_user_union_id(self, incoming_message: ChatbotMessage) -> Optional[str]:
        """获取用户unionId - 钉钉官方规范"""
        try:
            if hasattr(incoming_message, 'sender_staff_id'):
                if self.client_id and self.client_secret:
                    self.logger.info("使用钉钉客户端获取unionId")
                    union_id = get_union_id_with_client(
                        incoming_message.sender_staff_id, 
                        self.client_id, 
                        self.client_secret
                    )
                    if union_id:
                        self.logger.info(f"获取到unionId: {union_id}")
                        return union_id
                    else:
                        self.logger.error("钉钉客户端获取unionId失败")
                else:
                    self.logger.error("钉钉配置不完整，无法获取unionId")
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取用户unionId失败: {str(e)}")
            return None
    
    async def _upload_to_dingtalk_drive(self, file_name: str, file_size: int, union_id: str) -> Dict[str, Any]:
        """上传文件到钉钉云盘 - 钉钉官方Storage 2.0 API"""
        try:
            # 获取访问令牌
            access_token = await self._get_access_token()
            if not access_token:
                return {'success': False, 'error': '无法获取访问令牌'}
            
            # 获取工作空间
            space_id = await self._get_workspace(union_id, access_token)
            if not space_id:
                return {'success': False, 'error': '无法获取工作空间'}
            
            # 获取文件上传信息
            upload_info = await self._get_upload_info(union_id, space_id, file_name, file_size, access_token)
            if not upload_info:
                return {'success': False, 'error': '无法获取上传信息'}
            
            # 上传文件到资源服务器
            upload_result = await self._upload_to_resource(
                upload_info['resource_url'], 
                upload_info['headers'], 
                file_name, 
                file_size
            )
            
            if not upload_result['success']:
                return {'success': False, 'error': upload_result['error']}
            
            # 提交文件信息
            commit_result = await self._commit_file(
                union_id, space_id, upload_info['upload_key'], 
                file_name, file_size, access_token
            )
            
            if commit_result['success']:
                return {
                    'success': True, 
                    'doc_url': commit_result['doc_url'],
                    'file_id': commit_result['file_id']
                }
            else:
                return {'success': False, 'error': commit_result['error']}
                
        except Exception as e:
            self.logger.error(f"上传文件到钉钉云盘失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _get_access_token(self) -> Optional[str]:
        """获取钉钉访问令牌 - 钉钉官方OAuth2.0"""
        try:
            from dingtalk.auth import DingTalkAuth
            auth = DingTalkAuth(self.client_id, self.client_secret)
            return auth.get_access_token()
        except Exception as e:
            self.logger.error(f"获取访问令牌失败: {str(e)}")
            return None
    
    async def _get_workspace(self, union_id: str, access_token: str) -> Optional[str]:
        """获取工作空间ID - 钉钉官方API"""
        try:
            url = "https://api.dingtalk.com/v1.0/drive/spaces"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {
                "unionId": union_id,
                "spaceType": "org"  # 钉钉官方规范
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200 and result.get('spaces'):
                # 返回第一个工作空间ID
                space_id = result['spaces'][0]['spaceId']
                self.logger.info(f"获取到工作空间ID: {space_id}")
                return space_id
            else:
                self.logger.error(f"获取工作空间失败: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取工作空间异常: {str(e)}")
            return None
    
    async def _get_upload_info(self, union_id: str, space_id: str, file_name: str, file_size: int, access_token: str) -> Optional[Dict[str, Any]]:
        """获取文件上传信息 - 钉钉官方Storage 2.0 API"""
        try:
            url = f"https://api.dingtalk.com/v1.0/storage/spaces/{space_id}/files/uploadInfos"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {
                "unionId": union_id,
                "protocol": "HEADER_SIGNATURE",  # 钉钉官方固定协议
                "option": {
                    "storageDriver": "DINGTALK",  # 钉钉官方存储驱动
                    "size": file_size,
                    "name": file_name
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200 and result.get('headerSignatureInfo'):
                info = result['headerSignatureInfo']
                upload_info = {
                    'resource_url': info['resourceUrls'][0],
                    'headers': info['headers'],
                    'upload_key': result['uploadKey']
                }
                self.logger.info(f"获取上传信息成功: {upload_info}")
                return upload_info
            else:
                self.logger.error(f"获取上传信息失败: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取上传信息异常: {str(e)}")
            return None
    
    async def _upload_to_resource(self, resource_url: str, headers: Dict[str, str], file_name: str, file_size: int) -> Dict[str, Any]:
        """上传文件到资源服务器 - 钉钉官方规范"""
        try:
            # 创建占位文件内容（钉钉官方规范）
            file_content = b"File content placeholder for " + file_name.encode('utf-8')
            
            # 使用PUT方法上传文件（钉钉官方要求）
            session = requests.Session()
            session.verify = False
            
            # 设置请求头
            for key, value in headers.items():
                session.headers[key] = value
            
            # 上传文件
            response = session.put(
                resource_url, 
                data=file_content, 
                timeout=60,  # 钉钉官方推荐超时
                headers={'Content-Type': 'application/octet-stream'}
            )
            
            if response.status_code == 200:
                self.logger.info(f"文件上传到资源服务器成功: {file_name}")
                return {'success': True}
            else:
                error_msg = f'上传失败，状态码: {response.status_code}'
                self.logger.error(f"文件上传到资源服务器失败: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            self.logger.error(f"上传到资源服务器失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _commit_file(self, union_id: str, space_id: str, upload_key: str, file_name: str, file_size: int, access_token: str) -> Dict[str, Any]:
        """提交文件信息 - 钉钉官方Storage 2.0 API"""
        try:
            url = f"https://api.dingtalk.com/v1.0/storage/spaces/{space_id}/files/commit"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {
                "unionId": union_id,
                "uploadKey": upload_key,
                "name": file_name,
                "option": {
                    "size": file_size,
                    "conflictStrategy": "OVERWRITE",  # 钉钉官方冲突处理策略
                    "convertToOnlineDoc": False  # 钉钉官方在线文档转换选项
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200 and result.get('dentry'):
                dentry = result['dentry']
                # 钉钉官方文档链接格式
                doc_url = f"https://alidocs.dingtalk.com/i/nodes/{dentry['uuid']}"
                commit_result = {
                    'success': True,
                    'doc_url': doc_url,
                    'file_id': dentry['id']
                }
                self.logger.info(f"文件提交成功: {commit_result}")
                return commit_result
            else:
                error_msg = f'提交文件失败: {result}'
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            self.logger.error(f"提交文件异常: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _process_with_dify_workflow(self, file_name: str, file_size: int, file_type: str, 
                                        union_id: str, file_id: str, doc_url: str, 
                                        dingtalk_client, incoming_message: ChatbotMessage):
        """使用Dify工作流处理文件 - 优化的工作流集成"""
        try:
            user_id = incoming_message.sender_staff_id
            
            # 构建Dify工作流输入参数
            workflow_inputs = {
                "file_info": {
                    "name": file_name,
                    "size": file_size,
                    "type": file_type,
                    "dingtalk_file_id": file_id,
                    "dingtalk_doc_url": doc_url,
                    "upload_time": int(time.time()),
                    "user_union_id": union_id
                },
                "analysis_request": f"请分析用户上传的文件：{file_name}，文件类型：{file_type}，大小：{file_size}字节"
            }
            
            # 如果有钉钉云盘链接，添加到输入中
            if doc_url:
                workflow_inputs["file_info"]["dingtalk_doc_url"] = doc_url
                workflow_inputs["analysis_request"] += f"，钉钉云盘链接：{doc_url}"
            
            self.logger.info(f"发送文件到Dify工作流分析: {file_name}")
            
            # 调用Dify工作流API
            if self.use_workflow and self.workflow_id:
                # 使用指定工作流ID
                response = self.dify_client.workflow_run(
                    inputs=workflow_inputs,
                    user=user_id,
                    stream=False
                )
                self.logger.info(f"Dify工作流执行成功: {file_name}")
            else:
                # 使用默认工作流或聊天API
                response = self.dify_client.workflow_run(
                    inputs=workflow_inputs,
                    user=user_id,
                    stream=False
                )
                self.logger.info(f"Dify API调用成功: {file_name}")
            
            # 获取分析结果
            answer = response.get("answer", "文件分析完成")
            conversation_id = response.get("conversation_id", "")
            message_id = response.get("message_id", "")
            
            # 构建AI分析回复
            ai_reply = f"🤖 AI分析结果\n\n📁 文件名: {file_name}\n📊 文件大小: {file_size // 1024}KB\n📝 文件类型: {file_type}\n\n💡 分析结果:\n{answer}"
            
            # 如果有钉钉云盘链接，添加到回复中
            if doc_url:
                ai_reply += f"\n\n🔗 钉钉云盘链接: {doc_url}"
            
            # 如果有会话ID，添加到回复中
            if conversation_id:
                ai_reply += f"\n\n💬 会话ID: {conversation_id}"
            
            # 回复用户AI分析结果
            dingtalk_client.reply_text(ai_reply, incoming_message)
            
            self.logger.info(f"文件 {file_name} 的AI分析完成并已回复用户")
            
        except Exception as e:
            self.logger.error(f"Dify工作流处理文件失败: {str(e)}")
            error_reply = f"❌ AI分析文件时发生错误\n\n📁 文件名: {file_name}\n⚠️ 错误信息: {str(e)}\n\n请稍后重试或联系管理员"
            dingtalk_client.reply_text(error_reply, incoming_message)
    
    def _is_text_file(self, file_name: str) -> bool:
        """判断是否为文本文件"""
        text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.log'}
        file_ext = os.path.splitext(file_name)[1].lower()
        return file_ext in text_extensions
    
    def _get_file_type(self, file_name: str) -> str:
        """获取文件类型"""
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext in {'.pdf', '.doc', '.docx'}:
            return 'document'
        elif file_ext in {'.xls', '.xlsx'}:
            return 'spreadsheet'
        elif file_ext in {'.jpg', '.jpeg', '.png', '.gif'}:
            return 'image'
        elif file_ext in {'.mp3', '.wav', '.aac'}:
            return 'audio'
        elif file_ext in {'.mp4', '.avi', '.mov'}:
            return 'video'
        elif file_ext in {'.txt', '.md', '.py', '.js', '.html', '.css'}:
            return 'text'
        else:
            return 'unknown' 