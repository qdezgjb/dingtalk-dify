#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
钉钉客户端工具模块

整合了钉钉API调用功能，包括：
1. 访问令牌获取
2. 用户信息获取
3. UnionId获取
"""

import os
import requests
from typing import Optional, Dict, Any
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)


class DingTalkClient:
    """钉钉客户端类"""
    
    def __init__(self, app_key: str, app_secret: str):
        """
        初始化钉钉客户端
        
        Args:
            app_key: 钉钉应用Key
            app_secret: 钉钉应用Secret
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = None
        self._token_expires_at = 0
        
    def get_access_token(self) -> Optional[str]:
        """
        获取访问令牌
        
        Returns:
            Optional[str]: 访问令牌，失败时返回None
        """
        try:
            # 使用钉钉API获取访问令牌
            url = "https://oapi.dingtalk.com/gettoken"
            params = {
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            response = requests.get(url, params=params, timeout=10, verify=False)
            result = response.json()
            logger.debug(f"获取访问令牌响应: {result}")
            
            if result.get("errcode") == 0 and 'access_token' in result:
                self.access_token = result['access_token']
                # 设置令牌过期时间（钉钉令牌有效期为2小时）
                import time
                self._token_expires_at = time.time() + 7200  # 2小时
                logger.info("✅ 成功获取钉钉访问令牌")
                return self.access_token
            else:
                logger.error(f"获取访问令牌失败: {result}")
                return None
        except Exception as e:
            logger.error(f"获取访问令牌异常: {e}")
            return None
    
    def _is_token_valid(self) -> bool:
        """检查访问令牌是否有效"""
        import time
        return (self.access_token is not None and 
                time.time() < self._token_expires_at)
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息，失败时返回None
        """
        try:
            # 检查并获取访问令牌
            if not self._is_token_valid():
                self.access_token = self.get_access_token()
                if not self.access_token:
                    return None
            
            # 使用钉钉API获取用户信息
            url = "https://oapi.dingtalk.com/user/get"
            params = {
                "access_token": self.access_token,
                "userid": user_id
            }
            
            response = requests.get(url, params=params, timeout=10, verify=False)
            result = response.json()
            logger.debug(f"获取用户信息响应: {result}")
            
            if result.get("errcode") == 0:
                logger.info(f"✅ 成功获取用户信息: {user_id}")
                return result
            else:
                logger.error(f"获取用户信息失败: {result}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None
    
    def get_user_union_id(self, user_id: str) -> Optional[str]:
        """
        获取用户的unionId
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[str]: 用户unionId，失败时返回None
        """
        try:
            user_info = self.get_user_info(user_id)
            if user_info and 'unionid' in user_info:
                union_id = user_info['unionid']
                logger.info(f"✅ 成功获取用户unionId: {user_id} -> {union_id}")
                return union_id
            else:
                logger.warning(f"用户信息中未找到unionId: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户unionId异常: {e}")
            return None
    
    def get_user_by_union_id(self, union_id: str) -> Optional[Dict[str, Any]]:
        """
        根据unionId获取用户信息
        
        Args:
            union_id: 用户unionId
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息，失败时返回None
        """
        try:
            # 检查并获取访问令牌
            if not self._is_token_valid():
                self.access_token = self.get_access_token()
                if not self.access_token:
                    return None
            
            # 使用钉钉API根据unionId获取用户信息
            url = "https://oapi.dingtalk.com/user/getbyunionid"
            params = {
                "access_token": self.access_token,
                "unionid": union_id
            }
            
            response = requests.get(url, params=params, timeout=10, verify=False)
            result = response.json()
            logger.debug(f"根据unionId获取用户信息响应: {result}")
            
            if result.get("errcode") == 0:
                logger.info(f"✅ 成功根据unionId获取用户信息: {union_id}")
                return result
            else:
                logger.error(f"根据unionId获取用户信息失败: {result}")
                return None
                
        except Exception as e:
            logger.error(f"根据unionId获取用户信息异常: {e}")
            return None


def get_union_id_with_client(user_id: str, app_key: str, app_secret: str) -> Optional[str]:
    """
    使用钉钉客户端获取unionId的便捷函数
    
    Args:
        user_id: 用户ID
        app_key: 钉钉应用Key
        app_secret: 钉钉应用Secret
        
    Returns:
        Optional[str]: 用户unionId，失败时返回None
    """
    try:
        client = DingTalkClient(app_key, app_secret)
        return client.get_user_union_id(user_id)
    except Exception as e:
        logger.error(f"使用钉钉客户端获取unionId失败: {e}")
        return None


def get_user_info_with_client(user_id: str, app_key: str, app_secret: str) -> Optional[Dict[str, Any]]:
    """
    使用钉钉客户端获取用户信息的便捷函数
    
    Args:
        user_id: 用户ID
        app_key: 钉钉应用Key
        app_secret: 钉钉应用Secret
        
    Returns:
        Optional[Dict[str, Any]]: 用户信息，失败时返回None
    """
    try:
        client = DingTalkClient(app_key, app_secret)
        return client.get_user_info(user_id)
    except Exception as e:
        logger.error(f"使用钉钉客户端获取用户信息失败: {e}")
        return None


# 兼容性函数（保持向后兼容）
def get_union_id_with_old_sdk(user_id: str, app_key: str, app_secret: str) -> Optional[str]:
    """
    兼容旧版SDK的函数名
    
    Args:
        user_id: 用户ID
        app_key: 钉钉应用Key
        app_secret: 钉钉应用Secret
        
    Returns:
        Optional[str]: 用户unionId，失败时返回None
    """
    logger.warning("get_union_id_with_old_sdk 函数已弃用，请使用 get_union_id_with_client")
    return get_union_id_with_client(user_id, app_key, app_secret)


class OldSDKClient:
    """旧版SDK客户端类（保持向后兼容）"""
    
    def __init__(self, app_key: str, app_secret: str):
        """
        初始化旧版SDK客户端
        
        Args:
            app_key: 钉钉应用Key
            app_secret: 钉钉应用Secret
        """
        logger.warning("OldSDKClient 类已弃用，请使用 DingTalkClient")
        self._client = DingTalkClient(app_key, app_secret)
        
    def get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        return self._client.get_access_token()
    
    def get_user_union_id(self, user_id: str) -> Optional[str]:
        """获取用户的unionId"""
        return self._client.get_user_union_id(user_id)


# 常量定义
OLD_SDK_AVAILABLE = True  # 保持向后兼容 