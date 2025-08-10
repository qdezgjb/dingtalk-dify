#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钉钉云盘服务

负责文件上传到钉钉云盘的核心逻辑
基于钉钉官方Storage 2.0 API实现
"""

import os
import tempfile
import logging
import requests
import json
import time
from typing import Optional, Dict, Any, List
from .auth import DingTalkAuth


class DingTalkDriveService:
    """钉钉云盘服务"""
    
    def __init__(self, client_id: str, client_secret: str, logger: logging.Logger = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth = DingTalkAuth(client_id, client_secret)
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = "https://api.dingtalk.com/v1.0"
    
    async def upload_file(self, file_name: str, file_size: int, union_id: str, file_content: bytes = None) -> Dict[str, Any]:
        """上传文件到钉钉云盘
        
        Args:
            file_name: 文件名
            file_size: 文件大小（字节）
            union_id: 用户unionId
            file_content: 文件内容（可选，如果不提供则创建占位文件）
            
        Returns:
            上传结果字典
        """
        try:
            self.logger.info(f"开始上传文件到钉钉云盘: {file_name}, 大小: {file_size}字节")
            
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
                file_content
            )
            
            if not upload_result['success']:
                return {'success': False, 'error': upload_result['error']}
            
            # 提交文件信息
            commit_result = await self._commit_file(
                union_id, space_id, upload_info['upload_key'], 
                file_name, file_size, access_token
            )
            
            if commit_result['success']:
                self.logger.info(f"文件上传成功: {file_name}")
                return {
                    'success': True, 
                    'doc_url': commit_result['doc_url'],
                    'file_id': commit_result['file_id'],
                    'space_id': space_id
                }
            else:
                return {'success': False, 'error': commit_result['error']}
                
        except Exception as e:
            self.logger.error(f"上传文件到钉钉云盘失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_file_info(self, file_id: str, space_id: str, union_id: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return {'success': False, 'error': '无法获取访问令牌'}
            
            url = f"{self.base_url}/storage/spaces/{space_id}/files/{file_id}"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            params = {"unionId": union_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200:
                return {'success': True, 'file_info': result}
            else:
                return {'success': False, 'error': f'获取文件信息失败: {result}'}
                
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def delete_file(self, file_id: str, space_id: str, union_id: str) -> Dict[str, Any]:
        """删除文件"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return {'success': False, 'error': '无法获取访问令牌'}
            
            url = f"{self.base_url}/storage/spaces/{space_id}/files/{file_id}"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {"unionId": union_id}
            
            response = requests.delete(url, headers=headers, json=data, timeout=10, verify=False)
            
            if response.status_code == 200:
                return {'success': True}
            else:
                result = response.json()
                return {'success': False, 'error': f'删除文件失败: {result}'}
                
        except Exception as e:
            self.logger.error(f"删除文件失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def list_files(self, space_id: str, union_id: str, parent_id: str = "0", max_results: int = 50) -> Dict[str, Any]:
        """列出文件"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return {'success': False, 'error': '无法获取访问令牌'}
            
            url = f"{self.base_url}/storage/spaces/{space_id}/files"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            params = {
                "unionId": union_id,
                "parentId": parent_id,
                "maxResults": max_results
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200:
                return {'success': True, 'files': result.get('dentries', [])}
            else:
                return {'success': False, 'error': f'列出文件失败: {result}'}
                
        except Exception as e:
            self.logger.error(f"列出文件失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def download_file_content(self, file_id: str, space_id: str, union_id: str) -> Optional[bytes]:
        """下载文件内容"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                self.logger.error("无法获取访问令牌")
                return None
            
            # 获取文件下载地址
            download_url = self.get_file_download_url(file_id, space_id, union_id, access_token)
            if not download_url:
                self.logger.error("无法获取文件下载地址")
                return None
            
            # 下载文件内容
            headers = {
                "x-acs-dingtalk-access-token": access_token
            }
            
            response = requests.get(download_url, headers=headers, timeout=60, verify=False)
            if response.status_code == 200:
                self.logger.info(f"文件内容下载成功: {file_id}")
                return response.content
            else:
                self.logger.error(f"文件下载失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"下载文件内容失败: {str(e)}")
            return None
    
    async def get_file_by_name(self, file_name: str, space_id: str, union_id: str) -> Optional[Dict[str, Any]]:
        """根据文件名查找文件"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return None
            
            # 列出文件
            files_result = await self.list_files(space_id, union_id)
            if not files_result['success']:
                return None
            
            # 查找匹配的文件
            for file_info in files_result['files']:
                if file_info.get('name') == file_name:
                    return file_info
            
            return None
            
        except Exception as e:
            self.logger.error(f"查找文件失败: {str(e)}")
            return None
    
    async def _get_access_token(self) -> Optional[str]:
        """获取钉钉访问令牌"""
        try:
            return self.auth.get_access_token()
        except Exception as e:
            self.logger.error(f"获取访问令牌失败: {str(e)}")
            return None
    
    async def _get_workspace(self, union_id: str, access_token: str) -> Optional[str]:
        """获取工作空间ID"""
        try:
            url = f"{self.base_url}/drive/spaces"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {
                "unionId": union_id,
                "spaceType": "org"
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
        """获取文件上传信息"""
        try:
            url = f"{self.base_url}/storage/spaces/{space_id}/files/uploadInfos"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {
                "unionId": union_id,
                "protocol": "HEADER_SIGNATURE",
                "option": {
                    "storageDriver": "DINGTALK",
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
    
    async def _upload_to_resource(self, resource_url: str, headers: Dict[str, str], file_name: str, file_content: bytes = None) -> Dict[str, Any]:
        """上传文件到资源服务器"""
        try:
            # 如果没有提供文件内容，创建一个占位文件
            if file_content is None:
                file_content = b"File content placeholder for " + file_name.encode('utf-8')
            
            # 使用PUT方法上传文件
            session = requests.Session()
            session.verify = False
            
            # 设置请求头
            for key, value in headers.items():
                session.headers[key] = value
            
            # 上传文件
            response = session.put(
                resource_url, 
                data=file_content, 
                timeout=60,
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
        """提交文件信息"""
        try:
            url = f"{self.base_url}/storage/spaces/{space_id}/files/commit"
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
                    "conflictStrategy": "OVERWRITE",
                    "convertToOnlineDoc": False
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200 and result.get('dentry'):
                dentry = result['dentry']
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
    
    def get_file_download_url(self, file_id: str, space_id: str, union_id: str, access_token: str) -> Optional[str]:
        """获取文件下载地址（同步方法）"""
        try:
            url = f"{self.base_url}/storage/spaces/{space_id}/files/{file_id}/downloadInfos"
            headers = {
                "x-acs-dingtalk-access-token": access_token,
                "Content-Type": "application/json"
            }
            data = {"unionId": union_id}
            
            response = requests.post(url, headers=headers, json=data, timeout=10, verify=False)
            result = response.json()
            
            if response.status_code == 200 and result.get('headerSignatureInfo'):
                info = result['headerSignatureInfo']
                download_url = info['resourceUrls'][0]
                self.logger.info(f"获取文件下载地址成功: {download_url}")
                return download_url
            else:
                self.logger.error(f"获取文件下载地址失败: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取文件下载地址异常: {str(e)}")
            return None 