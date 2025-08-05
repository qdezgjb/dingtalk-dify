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

# 使用pip安装的alibabacloud-dingtalk SDK
# 根据钉钉官方文档：https://open.dingtalk.com/document/resourcedownload/download-server-sdk
# 不需要手动添加路径，直接导入即可

# 尝试导入SDK
OLD_SDK_AVAILABLE = False
try:
    # 使用新版的alibabacloud-dingtalk SDK
    from alibabacloud_dingtalk.contact_1_0.client import Client as ContactClient
    from alibabacloud_dingtalk.contact_1_0.models import GetUserRequest
    from alibabacloud_tea_openapi.models import Config
    from alibabacloud_tea_util.models import RuntimeOptions
    OLD_SDK_AVAILABLE = True
    print("新版alibabacloud-dingtalk SDK导入成功")
except ImportError as e:
    print(f"新版SDK导入失败: {e}")
    OLD_SDK_AVAILABLE = False

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
            
            # 使用新版alibabacloud-dingtalk SDK获取用户信息
            config = Config()
            config.protocol = "https"
            config.region_id = "central"
            
            client = ContactClient(config)
            request = GetUserRequest()
            request.userid = user_id
            
            runtime = RuntimeOptions()
            
            # 设置访问令牌
            response = client.get_user_with_options(request, runtime)
            print(f"获取用户信息响应: {response}")
            
            if response and hasattr(response.body, 'unionid'):
                return response.body.unionid
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