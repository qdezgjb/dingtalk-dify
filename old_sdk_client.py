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

# 添加taobao SDK路径 - 按照官方文档方式
taobao_sdk_paths = [
    '/app/dingtalk_sdk',  # Docker容器中的SDK路径
    '/app/top',  # Docker容器中的top模块路径
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                 'taobao-sdk-PYTHON-auto_1479188381469-20250717', 'dingtalk'),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                 'taobao-sdk-PYTHON-auto_1479188381469-20250717', 'dingtalk'),
    os.path.join(os.getcwd(), 'dingtalk_sdk'),  # 当前工作目录下的SDK
]

# 尝试添加SDK路径
OLD_SDK_AVAILABLE = False
sdk_found = False

# 添加所有存在的SDK路径
for sdk_path in taobao_sdk_paths:
    if os.path.exists(sdk_path):
        sys.path.insert(0, sdk_path)
        print(f"找到taobao SDK路径: {sdk_path}")
        sdk_found = True

if not sdk_found:
    print("未找到taobao SDK，尝试的路径:")
    for path in taobao_sdk_paths:
        print(f"  - {path}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"当前Python路径: {sys.path}")

try:
    import dingtalk.api
    from dingtalk.api.rest.OapiUserGetRequest import OapiUserGetRequest
    from dingtalk.api.rest.OapiGettokenRequest import OapiGettokenRequest
    OLD_SDK_AVAILABLE = True
    print("旧版SDK导入成功")
except ImportError as e:
    OLD_SDK_AVAILABLE = False
    print(f"旧版SDK导入失败: {e}")
    print(f"当前Python路径: {sys.path}")

class OldSDKClient:
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = None
        
    def get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        try:
            # 使用旧版SDK获取访问令牌
            request = OapiGettokenRequest("https://oapi.dingtalk.com/gettoken")
            request.appkey = self.app_key
            request.appsecret = self.app_secret
            
            response = request.getResponse()
            print(f"获取访问令牌响应: {response}")
            
            if response and 'access_token' in response:
                self.access_token = response['access_token']
                return self.access_token
            else:
                print(f"获取访问令牌失败: {response}")
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
            
            # 使用旧版SDK获取用户信息
            request = OapiUserGetRequest()
            request.userid = user_id
            
            # 设置访问令牌
            response = request.getResponse(self.access_token)
            print(f"获取用户信息响应: {response}")
            
            if response and 'unionid' in response:
                return response['unionid']
            else:
                print(f"获取用户unionId失败: {response}")
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