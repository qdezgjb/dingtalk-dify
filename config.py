import os
import json
from typing import Dict, Any, Optional
from utils.logger import app_logger

class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self._override_from_env()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            app_logger.warning(f"配置文件 {self.config_path} 不存在，将使用默认配置和环境变量")
            return {
                "dingtalk": {
                    "client_id": "",
                    "client_secret": "",
                    "ai_card_template_id": ""
                },
                "dify": {
                    "api_base": "https://api.dify.ai/v1",
                    "api_key": "",
                    "app_type": "chat"
                },
                "adapter": {
                    "port": 8080,
                    "timeout": 60
                }
            }
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                app_logger.info(f"成功加载配置文件 {self.config_path}")
                return config
        except Exception as e:
            app_logger.error(f"加载配置文件时出错: {str(e)}")
            raise
    
    def _override_from_env(self):
        """从环境变量覆盖配置"""
        # 钉钉配置
        if os.environ.get("DINGTALK_CLIENT_ID"):
            self.config["dingtalk"]["client_id"] = os.environ.get("DINGTALK_CLIENT_ID")
            app_logger.info("从环境变量加载 DINGTALK_CLIENT_ID")
        
        if os.environ.get("DINGTALK_CLIENT_SECRET"):
            self.config["dingtalk"]["client_secret"] = os.environ.get("DINGTALK_CLIENT_SECRET")
            app_logger.info("从环境变量加载 DINGTALK_CLIENT_SECRET")
        
        if os.environ.get("DINGTALK_AI_CARD_TEMPLATE_ID"):
            self.config["dingtalk"]["ai_card_template_id"] = os.environ.get("DINGTALK_AI_CARD_TEMPLATE_ID")
            app_logger.info("从环境变量加载 DINGTALK_AI_CARD_TEMPLATE_ID")
        
        # Dify配置
        if os.environ.get("DIFY_API_BASE"):
            self.config["dify"]["api_base"] = os.environ.get("DIFY_API_BASE")
            app_logger.info("从环境变量加载 DIFY_API_BASE")
        
        if os.environ.get("DIFY_API_KEY"):
            self.config["dify"]["api_key"] = os.environ.get("DIFY_API_KEY")
            app_logger.info("从环境变量加载 DIFY_API_KEY")
        
        if os.environ.get("DIFY_APP_TYPE"):
            self.config["dify"]["app_type"] = os.environ.get("DIFY_APP_TYPE")
            app_logger.info("从环境变量加载 DIFY_APP_TYPE")
        
        # 适配器配置
        if os.environ.get("SERVER_PORT"):
            try:
                self.config["adapter"]["port"] = int(os.environ.get("SERVER_PORT"))
                app_logger.info("从环境变量加载 SERVER_PORT")
            except ValueError:
                app_logger.warning("环境变量 SERVER_PORT 不是有效的整数，使用配置文件中的值")
        
        if os.environ.get("SESSION_TIMEOUT"):
            try:
                self.config["adapter"]["timeout"] = int(os.environ.get("SESSION_TIMEOUT"))
                app_logger.info("从环境变量加载 SESSION_TIMEOUT")
            except ValueError:
                app_logger.warning("环境变量 SESSION_TIMEOUT 不是有效的整数，使用配置文件中的值")
    
    @property
    def dingtalk_client_id(self) -> str:
        return self.config["dingtalk"]["client_id"]
    
    @property
    def dingtalk_client_secret(self) -> str:
        return self.config["dingtalk"]["client_secret"]
    
    @property
    def dingtalk_ai_card_template_id(self) -> str:
        return self.config["dingtalk"]["ai_card_template_id"]
    
    @property
    def dify_api_base(self) -> str:
        return self.config["dify"]["api_base"]
    
    @property
    def dify_api_key(self) -> str:
        return self.config["dify"]["api_key"]
    
    @property
    def dify_app_type(self) -> str:
        return self.config["dify"]["app_type"]
    
    @property
    def server_port(self) -> int:
        return self.config["adapter"]["port"]
    
    @property
    def session_timeout(self) -> int:
        return self.config["adapter"].get("timeout", 1800)  # 默认30分钟 