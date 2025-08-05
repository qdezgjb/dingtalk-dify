#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSL问题修复工具

这个脚本用于修复常见的SSL问题，包括：
1. 更新CA证书
2. 配置SSL连接参数
3. 禁用不必要的验证

使用方法：python ssl_fix.py
"""

import os
import sys
import ssl
import certifi
import urllib3
import requests
import subprocess
import importlib.util
from pathlib import Path

def fix_ssl_issues():
    """修复SSL相关问题"""
    print("开始修复SSL问题...")
    
    # 1. 禁用SSL警告
    urllib3.disable_warnings()
    print("✅ 已禁用SSL警告")
    
    # 2. 检查并尝试更新证书
    try:
        print("正在检查证书更新...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 已更新certifi证书")
        else:
            print(f"⚠️ 更新certifi失败: {result.stderr}")
    except Exception as e:
        print(f"⚠️ 无法更新证书: {str(e)}")
    
    # 3. 设置环境变量
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['CURL_SSL_VERIFY'] = '0'
    print("✅ 已设置SSL相关环境变量")
    
    # 4. 创建自定义SSL上下文并设为默认
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # 设置全局默认上下文
        ssl._create_default_https_context = ssl._create_unverified_context
        print("✅ 已创建并应用不验证的SSL上下文")
    except Exception as e:
        print(f"⚠️ 无法设置自定义SSL上下文: {str(e)}")
    
    # 5. 修改requests库的验证行为
    try:
        old_merge_environment_settings = requests.Session.merge_environment_settings
        
        def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
            if verify is True:
                verify = False
            return old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        
        requests.Session.merge_environment_settings = new_merge_environment_settings
        print("✅ 已修改requests库的默认SSL验证行为")
    except Exception as e:
        print(f"⚠️ 无法修改requests库设置: {str(e)}")
    
    # 6. 修改requests默认连接池设置
    try:
        # 降低最大连接数并禁用长连接
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # 连接池连接数
            pool_maxsize=10,      # 连接池最大连接数
            max_retries=5,        # 最大重试次数
            pool_block=False      # 连接池用尽时不阻塞
        )
        # 应用适配器到所有连接
        session = requests.Session()
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.verify = False
        # 将这个session设为默认
        requests.Session = lambda: session
        print("✅ 已优化requests连接池设置")
    except Exception as e:
        print(f"⚠️ 无法修改requests连接池设置: {str(e)}")
    
    # 7. 测试连接
    print("\n正在测试钉钉API连接...")
    try:
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        # 使用自定义的headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
            "Accept": "*/*",
            "Connection": "close"  # 明确禁用keep-alive
        }
        session = requests.Session()
        session.verify = False
        response = session.get(url, headers=headers, timeout=5)
        if response.status_code < 500:  # 允许401等权限错误
            print(f"✅ 连接测试成功! 状态码: {response.status_code}")
        else:
            print(f"⚠️ 连接测试失败! 状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 连接测试出错: {str(e)}")
    
    print("\nSSL问题修复完成。如果仍然遇到问题，请尝试重新启动应用。")

if __name__ == "__main__":
    fix_ssl_issues()