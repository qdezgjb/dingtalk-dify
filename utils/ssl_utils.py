#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSL工具模块

整合了SSL问题修复和检查功能，包括：
1. SSL配置修复
2. SSL连接检查
3. 环境变量设置
4. 连接池优化
"""

import os
import sys
import ssl
import socket
import certifi
import urllib3
import requests
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)


class SSLUtils:
    """SSL工具类"""
    
    @staticmethod
    def fix_ssl_issues() -> Dict[str, Any]:
        """
        修复SSL相关问题
        
        Returns:
            Dict[str, Any]: 修复结果报告
        """
        results = {
            'warnings_disabled': False,
            'certifi_updated': False,
            'env_vars_set': False,
            'ssl_context_created': False,
            'requests_modified': False,
            'connection_pool_optimized': False,
            'connection_test_passed': False
        }
        
        try:
            # 1. 禁用SSL警告
            urllib3.disable_warnings()
            results['warnings_disabled'] = True
            logger.info("✅ 已禁用SSL警告")
            
            # 2. 检查并尝试更新证书
            try:
                logger.info("正在检查证书更新...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "certifi"], 
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    results['certifi_updated'] = True
                    logger.info("✅ 已更新certifi证书")
                else:
                    logger.warning(f"⚠️ 更新certifi失败: {result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️ 无法更新证书: {str(e)}")
            
            # 3. 设置环境变量
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            os.environ['CURL_SSL_VERIFY'] = '0'
            results['env_vars_set'] = True
            logger.info("✅ 已设置SSL相关环境变量")
            
            # 4. 创建自定义SSL上下文并设为默认
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                # 设置全局默认上下文
                ssl._create_default_https_context = ssl._create_unverified_context
                results['ssl_context_created'] = True
                logger.info("✅ 已创建并应用不验证的SSL上下文")
            except Exception as e:
                logger.warning(f"⚠️ 无法设置自定义SSL上下文: {str(e)}")
            
            # 5. 修改requests库的验证行为
            try:
                old_merge_environment_settings = requests.Session.merge_environment_settings
                
                def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
                    if verify is True:
                        verify = False
                    return old_merge_environment_settings(self, url, proxies, stream, verify, cert)
                
                requests.Session.merge_environment_settings = new_merge_environment_settings
                results['requests_modified'] = True
                logger.info("✅ 已修改requests库的默认SSL验证行为")
            except Exception as e:
                logger.warning(f"⚠️ 无法修改requests库设置: {str(e)}")
            
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
                results['connection_pool_optimized'] = True
                logger.info("✅ 已优化requests连接池设置")
            except Exception as e:
                logger.warning(f"⚠️ 无法修改requests连接池设置: {str(e)}")
            
            # 7. 测试连接
            logger.info("正在测试钉钉API连接...")
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
                    results['connection_test_passed'] = True
                    logger.info(f"✅ 连接测试成功! 状态码: {response.status_code}")
                else:
                    logger.warning(f"⚠️ 连接测试失败! 状态码: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ 连接测试出错: {str(e)}")
            
            logger.info("SSL问题修复完成。如果仍然遇到问题，请尝试重新启动应用。")
            
        except Exception as e:
            logger.error(f"SSL修复过程中出现错误: {str(e)}")
        
        return results
    
    @staticmethod
    def check_ssl_configuration() -> Dict[str, Any]:
        """
        检查SSL配置和可用的SSL/TLS版本
        
        Returns:
            Dict[str, Any]: SSL配置检查结果
        """
        results = {
            'python_ssl_version': None,
            'python_ssl_library_path': None,
            'tls_versions': {},
            'ca_cert_path': None,
            'requests_settings': {},
            'dingtalk_connection': {},
            'network_config': {}
        }
        
        try:
            logger.info("=== SSL 配置检查 ===")
            
            # Python SSL 库信息
            results['python_ssl_version'] = ssl.OPENSSL_VERSION
            results['python_ssl_library_path'] = ssl.OPENSSL_VERSION_INFO
            logger.info(f"Python SSL 版本: {ssl.OPENSSL_VERSION}")
            logger.info(f"Python SSL 库路径: {ssl.OPENSSL_VERSION_INFO}")
            
            # 系统支持的TLS版本
            logger.info("\n支持的TLS版本:")
            try:
                results['tls_versions'] = {
                    'TLS 1.0': hasattr(ssl, 'PROTOCOL_TLSv1'),
                    'TLS 1.1': hasattr(ssl, 'PROTOCOL_TLSv1_1'),
                    'TLS 1.2': hasattr(ssl, 'PROTOCOL_TLSv1_2'),
                    'TLS 1.3': hasattr(ssl, 'PROTOCOL_TLSv1_3')
                }
                for version, supported in results['tls_versions'].items():
                    logger.info(f"  {version}: {supported}")
            except Exception as e:
                logger.error(f"检查TLS版本出错: {e}")
            
            # 检查CA证书路径
            results['ca_cert_path'] = certifi.where()
            logger.info(f"\nCA证书路径: {certifi.where()}")
            
            # 检查请求库设置
            logger.info("\nRequests库设置:")
            session = requests.Session()
            results['requests_settings'] = {
                'default_verify': session.verify,
                'default_adapter': type(session.adapters.get('https://')).__name__
            }
            logger.info(f"  默认验证: {session.verify}")
            logger.info(f"  默认适配器: {type(session.adapters.get('https://')).__name__}")
            
            # 尝试连接钉钉API
            logger.info("\n测试连接钉钉API:")
            try:
                # 禁用警告
                urllib3.disable_warnings()
                
                # 测试连接
                url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
                response = requests.get(url, timeout=5, verify=False)
                results['dingtalk_connection'] = {
                    'status_code': response.status_code,
                    'server': response.headers.get('server', 'Unknown'),
                    'success': True
                }
                logger.info(f"  状态码: {response.status_code}")
                logger.info(f"  返回头: {response.headers.get('server', 'Unknown')}")
            except Exception as e:
                results['dingtalk_connection'] = {
                    'error': str(e),
                    'success': False
                }
                logger.error(f"  连接失败: {e}")
            
            # 显示网络配置
            logger.info("\n网络配置:")
            try:
                host_name = socket.gethostname()
                host_ip = socket.gethostbyname(host_name)
                results['network_config'] = {
                    'host_name': host_name,
                    'host_ip': host_ip
                }
                logger.info(f"  主机名: {host_name}")
                logger.info(f"  IP地址: {host_ip}")
            except Exception as e:
                results['network_config'] = {'error': str(e)}
                logger.error(f"  获取网络配置出错: {e}")
            
            logger.info("\n=== 检查完成 ===")
            
        except Exception as e:
            logger.error(f"SSL配置检查过程中出现错误: {str(e)}")
        
        return results
    
    @staticmethod
    def apply_ssl_fixes():
        """
        应用SSL修复（简化版本，用于程序启动时）
        """
        try:
            # 禁用SSL警告
            urllib3.disable_warnings()
            
            # 设置环境变量
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            os.environ['CURL_SSL_VERIFY'] = '0'
            
            # 设置全局默认上下文
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # 修改requests默认行为（仅在第一次调用时）
            if not hasattr(requests.Session, '_ssl_fixed'):
                try:
                    old_merge_environment_settings = requests.Session.merge_environment_settings
                    
                    def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
                        if verify is True:
                            verify = False
                        return old_merge_environment_settings(self, url, proxies, stream, verify, cert)
                    
                    requests.Session.merge_environment_settings = new_merge_environment_settings
                    requests.Session._ssl_fixed = True
                except Exception as e:
                    logger.warning(f"无法修改requests库设置: {str(e)}")
            
            logger.info("SSL修复已应用")
            
        except Exception as e:
            logger.error(f"应用SSL修复时出错: {str(e)}")


def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL工具')
    parser.add_argument('--check', action='store_true', help='检查SSL配置')
    parser.add_argument('--fix', action='store_true', help='修复SSL问题')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    
    if args.check:
        SSLUtils.check_ssl_configuration()
    elif args.fix:
        SSLUtils.fix_ssl_issues()
    else:
        # 默认执行修复
        SSLUtils.fix_ssl_issues()


if __name__ == "__main__":
    main() 