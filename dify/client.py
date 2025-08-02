import json
import requests
import sseclient
import time
from typing import Dict, Any, Generator, Optional
from utils.logger import dify_logger, log_request, log_response

class DifyClient:
    def __init__(self, api_base: str, api_key: str, app_type: str = "completion"):
        self.api_base = api_base
        self.api_key = api_key
        self.app_type = app_type
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, query: str, conversation_id: Optional[str] = None, 
                       user: Optional[str] = None, stream: bool = True) -> Dict[str, Any]:
        """聊天完成接口"""
        endpoint = f"{self.api_base}/chat-messages"
        
        data = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming" if stream else "blocking",
            "user": user
        }
        
        if conversation_id:
            data["conversation_id"] = conversation_id
        
        dify_logger.info(f"发送聊天请求: 用户={user}, 会话ID={conversation_id}, 流式输出={stream}")
        log_request(dify_logger, "POST", endpoint, self.headers, data)
        
        start_time = time.time()
        response = requests.post(endpoint, headers=self.headers, json=data, stream=stream)
        elapsed_time = time.time() - start_time
        
        if not stream:
            log_response(dify_logger, response, elapsed_time)
        
        if response.status_code != 200:
            error_msg = f"Dify API请求失败: {response.text}"
            dify_logger.error(error_msg)
            raise Exception(error_msg)
        
        if stream:
            dify_logger.info("开始接收流式响应")
            return self._handle_stream_response(response)
        else:
            dify_logger.info("成功接收阻塞式响应")
            return response.json()
    
    def completion(self, query: str, user: Optional[str] = None, stream: bool = True) -> Dict[str, Any]:
        """文本完成接口"""
        endpoint = f"{self.api_base}/completion"
        
        data = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming" if stream else "blocking",
            "user": user
        }
        
        dify_logger.info(f"发送完成请求: 用户={user}, 流式输出={stream}")
        log_request(dify_logger, "POST", endpoint, self.headers, data)
        
        start_time = time.time()
        response = requests.post(endpoint, headers=self.headers, json=data, stream=stream)
        elapsed_time = time.time() - start_time
        
        if not stream:
            log_response(dify_logger, response, elapsed_time)
        
        if response.status_code != 200:
            error_msg = f"Dify API请求失败: {response.text}"
            dify_logger.error(error_msg)
            raise Exception(error_msg)
        
        if stream:
            dify_logger.info("开始接收流式响应")
            return self._handle_stream_response(response)
        else:
            dify_logger.info("成功接收阻塞式响应")
            return response.json()
    
    def _handle_stream_response(self, response) -> Generator[Dict[str, Any], None, None]:
        """处理流式响应"""
        client = sseclient.SSEClient(response)
        chunk_count = 0
        try:
            for event in client.events():
                chunk_count += 1
                if event.data != "[DONE]":
                    data = json.loads(event.data)
                    if chunk_count % 10 == 0:  # 每10个块记录一次，避免日志过多
                        dify_logger.debug(f"接收流式响应块 #{chunk_count}")
                    yield data
                else:
                    dify_logger.info(f"流式响应完成，共 {chunk_count} 个数据块")
        except Exception as e:
            dify_logger.error(f"处理流式响应时出错: {str(e)}")
            raise 