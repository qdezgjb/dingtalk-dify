#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块

集中管理所有配置项，包括环境变量、默认值和验证规则
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """配置管理类"""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 钉钉配置
        self.DINGTALK_CLIENT_ID = os.getenv('DINGTALK_CLIENT_ID')
        self.DINGTALK_CLIENT_SECRET = os.getenv('DINGTALK_CLIENT_SECRET')
        self.DINGTALK_AI_CARD_TEMPLATE_ID = os.getenv('DINGTALK_AI_CARD_TEMPLATE_ID')
        
        # Dify配置
        self.DIFY_API_BASE = os.getenv('DIFY_API_BASE', 'https://api.dify.ai/v1')
        self.DIFY_API_KEY = os.getenv('DIFY_API_KEY')
        self.DIFY_APP_TYPE = os.getenv('DIFY_APP_TYPE', 'chat')
        self.DIFY_USE_WORKFLOW = os.getenv('DIFY_USE_WORKFLOW', 'false').lower() == 'true'
        self.DIFY_WORKFLOW_ID = os.getenv('DIFY_WORKFLOW_ID', '')
        
        # 服务器配置
        self.SERVER_PORT = int(os.getenv('SERVER_PORT', '9000'))
        self.SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
        self.SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '1800'))
        self.STREAM_MODE = os.getenv('STREAM_MODE', 'ai_card')
        
        # 日志配置
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FORMAT = os.getenv('LOG_FORMAT', 'text')  # text 或 json
        
        # 文件处理配置
        self.MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
        self.MAX_DOWNLOAD_SIZE_MB = int(os.getenv('MAX_DOWNLOAD_SIZE_MB', '10'))
        self.TEMP_FILE_DIR = os.getenv('TEMP_FILE_DIR', '/tmp')
        self.UPLOAD_TO_DIFY = os.getenv('UPLOAD_TO_DIFY', 'false').lower() == 'true'
        self.ENABLE_DINGTALK_DRIVE = os.getenv('ENABLE_DINGTALK_DRIVE', 'true').lower() == 'true'
        
        # 钉钉云盘配置
        self.DINGTALK_DRIVE_SPACE_TYPE = os.getenv('DINGTALK_DRIVE_SPACE_TYPE', 'org')
        self.DINGTALK_DRIVE_STORAGE_DRIVER = os.getenv('DINGTALK_DRIVE_STORAGE_DRIVER', 'DINGTALK')
        self.DINGTALK_DRIVE_CONFLICT_STRATEGY = os.getenv('DINGTALK_DRIVE_CONFLICT_STRATEGY', 'OVERWRITE')
        self.DINGTALK_DRIVE_CONVERT_TO_ONLINE_DOC = os.getenv('DINGTALK_DRIVE_CONVERT_TO_ONLINE_DOC', 'false').lower() == 'true'
        
        # 网络配置
        self.REQUESTS_TIMEOUT = int(os.getenv('REQUESTS_TIMEOUT', '30'))
        self.MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
        
        # SSL配置
        self.SSL_VERIFY = os.getenv('SSL_VERIFY', 'false').lower() == 'true'
        self.SSL_DISABLE_WARNINGS = os.getenv('SSL_DISABLE_WARNINGS', 'true').lower() == 'true'
        
        # 服务器环境检测
        self.SERVER_ENV = os.getenv('SERVER_ENV', 'false').lower() == 'true'
        
        # 如果检测到服务器环境，应用服务器配置
        if self.SERVER_ENV:
            self._apply_server_config()
    
    def _apply_server_config(self):
        """应用服务器环境配置"""
        self.REQUESTS_TIMEOUT = 60
        self.MAX_FILE_SIZE_MB = 100
        self.LOG_LEVEL = 'INFO'
        print("检测到服务器环境，已应用服务器配置")
    
    def validate(self) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []
        
        # 验证必需配置
        required_fields = {
            'DINGTALK_CLIENT_ID': self.DINGTALK_CLIENT_ID,
            'DINGTALK_CLIENT_SECRET': self.DINGTALK_CLIENT_SECRET,
            'DIFY_API_KEY': self.DIFY_API_KEY
        }
        
        for field, value in required_fields.items():
            if not value:
                errors.append(f"缺少必需的配置项: {field}")
        
        # 验证可选配置
        if not self.DINGTALK_AI_CARD_TEMPLATE_ID:
            warnings.append("未设置AI卡片模板ID，AI卡片功能可能不可用")
        
        if self.DIFY_APP_TYPE not in ['chat', 'completion']:
            errors.append("DIFY_APP_TYPE必须是 'chat' 或 'completion'")
        
        if self.STREAM_MODE not in ['ai_card', 'text']:
            errors.append("STREAM_MODE必须是 'ai_card' 或 'text'")
        
        # 验证端口范围
        if not (1 <= self.SERVER_PORT <= 65535):
            errors.append("SERVER_PORT必须在1-65535范围内")
        
        # 验证日志级别
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL必须是以下之一: {', '.join(valid_log_levels)}")
        
        # 验证文件大小限制
        if self.MAX_FILE_SIZE_MB <= 0 or self.MAX_FILE_SIZE_MB > 1000:
            errors.append("MAX_FILE_SIZE_MB必须在1-1000MB范围内")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return {
            'dingtalk': {
                'client_id': self.DINGTALK_CLIENT_ID,
                'client_secret': self.DINGTALK_CLIENT_SECRET,
                'ai_card_template_id': self.DINGTALK_AI_CARD_TEMPLATE_ID
            },
            'dify': {
                'api_base': self.DIFY_API_BASE,
                'api_key': self.DIFY_API_KEY,
                'app_type': self.DIFY_APP_TYPE,
                'use_workflow': self.DIFY_USE_WORKFLOW,
                'workflow_id': self.DIFY_WORKFLOW_ID
            },
            'server': {
                'port': self.SERVER_PORT,
                'host': self.SERVER_HOST,
                'session_timeout': self.SESSION_TIMEOUT,
                'stream_mode': self.STREAM_MODE
            },
            'logging': {
                'level': self.LOG_LEVEL,
                'format': self.LOG_FORMAT
            },
            'file_handling': {
                'max_file_size_mb': self.MAX_FILE_SIZE_MB,
                'max_download_size_mb': self.MAX_DOWNLOAD_SIZE_MB,
                'temp_file_dir': self.TEMP_FILE_DIR,
                'upload_to_dify': self.UPLOAD_TO_DIFY,
                'enable_dingtalk_drive': self.ENABLE_DINGTALK_DRIVE
            },
            'dingtalk_drive': {
                'space_type': self.DINGTALK_DRIVE_SPACE_TYPE,
                'storage_driver': self.DINGTALK_DRIVE_STORAGE_DRIVER,
                'conflict_strategy': self.DINGTALK_DRIVE_CONFLICT_STRATEGY,
                'convert_to_online_doc': self.DINGTALK_DRIVE_CONVERT_TO_ONLINE_DOC
            },
            'network': {
                'requests_timeout': self.REQUESTS_TIMEOUT,
                'max_retries': self.MAX_RETRIES
            },
            'ssl': {
                'verify': self.SSL_VERIFY,
                'disable_warnings': self.SSL_DISABLE_WARNINGS
            },
            'environment': {
                'server_env': self.SERVER_ENV
            }
        }
    
    def update_from_args(self, args: Dict[str, Any]):
        """从命令行参数更新配置"""
        if args.get('client_id'):
            self.DINGTALK_CLIENT_ID = args['client_id']
        if args.get('client_secret'):
            self.DINGTALK_CLIENT_SECRET = args['client_secret']
        if args.get('card_template_id'):
            self.DINGTALK_AI_CARD_TEMPLATE_ID = args['card_template_id']
        if args.get('dify_api_base'):
            self.DIFY_API_BASE = args['dify_api_base']
        if args.get('dify_api_key'):
            self.DIFY_API_KEY = args['dify_api_key']
        if args.get('dify_app_type'):
            self.DIFY_APP_TYPE = args['dify_app_type']
        if args.get('dify_workflow_id'):
            self.DIFY_WORKFLOW_ID = args['dify_workflow_id']
        if args.get('port'):
            self.SERVER_PORT = args['port']
        if args.get('host'):
            self.SERVER_HOST = args['host']


# 创建全局配置实例
settings = Settings() 