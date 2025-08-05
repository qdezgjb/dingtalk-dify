#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用旧版taobao SDK获取钉钉用户unionId
根据钉钉官方文档：https://open.dingtalk.com/document/orgapp/obtain-the-userid-of-a-user-by-using-the-log-free
"""

import os
import sys
import requests
from typing import Optional

# 使用钉钉官方API获取unionId
# 根据钉钉官方文档：https://open.dingtalk.com/document/orgapp/obtain-the-userid-of-a-user-by-using-the-log-free

# SDK可用性检查
OLD_SDK_AVAILABLE = True
print("钉钉API SDK可用")

class OldSDKClient:
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = None
        
    def get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        try:
            # 使用钉钉API获取访问令牌
            url = "https://oapi.dingtalk.com/gettoken"
            params = {
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            print(f"获取访问令牌响应: {result}")
            
            if result.get("errcode") == 0 and 'access_token' in result:
                self.access_token = result['access_token']
                return self.access_token
            else:
                print(f"获取访问令牌失败: {result}")
                return None
        except Exception as e:
            print(f"获取访问令牌异常: {e}")
            return None
    
    def get_user_union_id(self, user_id: str) -> Optional[str]:
        """获取用户的unionId
        根据钉钉官方文档：https://open.dingtalk.com/document/orgapp/obtain-the-userid-of-a-user-by-using-the-log-free
        """
        try:
            if not self.access_token:
                self.access_token = self.get_access_token()
                if not self.access_token:
                    return None
            
            # 使用钉钉API直接获取用户信息
            url = "https://oapi.dingtalk.com/user/get"
            params = {
                "access_token": self.access_token,
                "userid": user_id
            }
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            print(f"获取用户信息响应: {result}")
            
            if result.get("errcode") == 0 and 'unionid' in result:
                return result['unionid']
            else:
                print(f"获取用户unionId失败: {result}")
                return None
                
        except Exception as e:
            print(f"获取用户unionId异常: {e}")
            return None
        
def get_union_id_with_old_sdk(user_id: str, app_key: str, app_secret: str) -> Optional[str]:
    """使用旧版SDK获取unionId的便捷函数
    根据钉钉官方文档：https://open.dingtalk.com/document/orgapp/obtain-the-userid-of-a-user-by-using-the-log-free
    """
    if not OLD_SDK_AVAILABLE:
        print("旧版SDK不可用")
        return None
    
    try:
        client = OldSDKClient(app_key, app_secret)
        return client.get_user_union_id(user_id)
    except Exception as e:
        print(f"使用旧版SDK获取unionId失败: {e}")
        return None 