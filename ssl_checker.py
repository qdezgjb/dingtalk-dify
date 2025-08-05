#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ssl
import sys
import OpenSSL
import requests
import socket
import certifi

def check_ssl_configuration():
    """检查SSL配置和可用的SSL/TLS版本"""
    print("=== SSL 配置检查 ===")
    
    # Python SSL 库信息
    print(f"Python SSL 版本: {ssl.OPENSSL_VERSION}")
    print(f"Python SSL 库路径: {ssl.OPENSSL_VERSION_INFO}")
    
    # 系统支持的TLS版本
    print("\n支持的TLS版本:")
    try:
        print(f"  TLS 1.0: {hasattr(ssl, 'PROTOCOL_TLSv1')}")
        print(f"  TLS 1.1: {hasattr(ssl, 'PROTOCOL_TLSv1_1')}")
        print(f"  TLS 1.2: {hasattr(ssl, 'PROTOCOL_TLSv1_2')}")
        print(f"  TLS 1.3: {hasattr(ssl, 'PROTOCOL_TLSv1_3')}")
    except Exception as e:
        print(f"检查TLS版本出错: {e}")
    
    # 检查CA证书路径
    print(f"\nCA证书路径: {certifi.where()}")
    
    # 检查请求库设置
    print("\nRequests库设置:")
    print(f"  默认验证: {requests.Session().verify}")
    print(f"  默认适配器: {type(requests.Session().adapters.get('https://')).__name__}")
    
    # 尝试连接钉钉API
    print("\n测试连接钉钉API:")
    try:
        # 禁用警告
        import urllib3
        urllib3.disable_warnings()
        
        # 测试连接
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        response = requests.get(url, timeout=5, verify=False)
        print(f"  状态码: {response.status_code}")
        print(f"  返回头: {response.headers.get('server', 'Unknown')}")
    except Exception as e:
        print(f"  连接失败: {e}")
    
    # 显示网络配置
    print("\n网络配置:")
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        print(f"  主机名: {host_name}")
        print(f"  IP地址: {host_ip}")
    except Exception as e:
        print(f"  获取网络配置出错: {e}")
    
    print("\n=== 检查完成 ===")

if __name__ == "__main__":
    check_ssl_configuration()