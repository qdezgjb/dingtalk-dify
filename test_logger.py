#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志系统测试脚本 - 展示优化后的日志功能
"""

import time
from utils.logger import app_logger, dingtalk_logger, dify_logger
import logging

def test_log_levels():
    """测试不同级别的日志输出"""
    app_logger.debug("这是一条调试信息")
    app_logger.info("这是一条普通信息")
    app_logger.warning("这是一条警告信息，包含源代码位置")
    app_logger.error("这是一条错误信息，带有源代码位置")
    
    try:
        result = 10 / 0
    except Exception as e:
        app_logger.exception("这是一条带有异常堆栈的错误信息")
    
    app_logger.critical("这是一条严重错误信息，带有高亮背景")

def test_api_logs():
    """测试API请求和响应日志"""
    # 模拟一个API请求
    class MockResponse:
        def __init__(self, status_code, json_data=None, text=None, headers=None):
            self.status_code = status_code
            self._json_data = json_data
            self.text = text or ""
            self.headers = headers or {"Content-Type": "application/json"}
        
        def json(self):
            return self._json_data
    
    # 模拟正常响应
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret-token-123"
    }
    
    data = {
        "query": "测试消息",
        "stream": True
    }
    
    dingtalk_logger.info("开始测试钉钉API日志")
    
    # 记录正常请求
    from utils.logger import log_request, log_response
    log_request(dingtalk_logger, "POST", "https://api.dingtalk.com/v1.0/robot/sendMessage", 
               headers=headers, data=data)
    
    # 模拟正常响应
    response = MockResponse(200, json_data={"success": True, "messageId": "abc123"})
    log_response(dingtalk_logger, response, elapsed_time=0.345)
    
    # 模拟错误响应
    dify_logger.info("开始测试Dify API日志")
    error_response = MockResponse(
        400, 
        json_data={
            "code": "invalid_request_error",
            "message": "无效的请求参数"
        }
    )
    log_response(dify_logger, error_response, elapsed_time=1.234)
    
    # 模拟服务器错误
    server_error = MockResponse(
        500, 
        json_data={
            "code": "internal_server_error",
            "message": "服务器内部错误"
        }
    )
    log_response(dify_logger, server_error, elapsed_time=2.345)

if __name__ == "__main__":
    print("测试优化后的日志系统...\n")
    
    # 设置日志级别
    logging.getLogger("dingtalk_dify_adapter").setLevel(logging.DEBUG)
    
    # 测试不同日志级别
    test_log_levels()
    print("\n" + "-" * 50 + "\n")
    
    # 测试API日志
    test_api_logs() 