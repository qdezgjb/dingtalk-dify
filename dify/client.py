import json
import requests
import sseclient
import time
import os
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
    
    def chat_completion(self, query: str, user: str, stream: bool = False, files: list = None) -> Dict[str, Any]:
        """聊天完成API"""
        try:
            # 构建请求数据
            data = {
                "inputs": {},
                "query": query,
                "user": user,
                "response_mode": "streaming" if stream else "blocking"
            }
            
            # 添加文件参数
            if files:
                data["files"] = files
            
            dify_logger.info(f"发送聊天请求到 {self.api_base}/chat-messages: 用户={user}, 流式输出={stream}, 文件数量={len(files) if files else 0}")
            
            if stream:
                return self._send_stream_request("/chat-messages", data)
            else:
                return self._send_request("/chat-messages", data)
                
        except Exception as e:
            dify_logger.error(f"Dify API请求失败: {str(e)}")
            raise

    def completion(self, prompt: str, user: str, stream: bool = False, files: list = None) -> Dict[str, Any]:
        """文本完成API"""
        try:
            # 构建请求数据
            data = {
                "inputs": {},
                "query": prompt,
                "user": user,
                "response_mode": "streaming" if stream else "blocking"
            }
            
            # 添加文件参数
            if files:
                data["files"] = files
            
            dify_logger.info(f"发送完成请求到 {self.api_base}/completion-messages: 用户={user}, 流式输出={stream}, 文件数量={len(files) if files else 0}")
            
            if stream:
                return self._send_stream_request("/completion-messages", data)
            else:
                return self._send_request("/completion-messages", data)
                
        except Exception as e:
            dify_logger.error(f"Dify API请求失败: {str(e)}")
            raise

    def workflow_run(self, inputs: dict, user: str, files: list = None, stream: bool = False) -> Dict[str, Any]:
        """工作流执行API"""
        try:
            # 构建请求数据
            data = {
                "inputs": inputs,
                "user": user,
                "response_mode": "streaming" if stream else "blocking"
            }
            
            # 添加文件参数
            if files:
                data["files"] = files
            
            dify_logger.info(f"发送工作流请求到 {self.api_base}/workflows/run: 用户={user}, 流式输出={stream}, 文件数量={len(files) if files else 0}")
            
            if stream:
                return self._send_stream_request("/workflows/run", data)
            else:
                return self._send_request("/workflows/run", data)
                
        except Exception as e:
            dify_logger.error(f"Dify工作流API请求失败: {str(e)}")
            raise

    def upload_file(self, file_path: str, file_name: str = None) -> str:
        """上传文件到Dify"""
        try:
            if not file_name:
                file_name = os.path.basename(file_path)
            
            upload_url = f"{self.api_base}/files/upload"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, 'application/octet-stream')}
                dify_logger.info(f"上传文件到Dify: {file_name}")
                response = requests.post(upload_url, headers=headers, files=files, verify=False, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                file_id = result.get('id')
                
                if file_id:
                    dify_logger.info(f"文件上传成功，ID: {file_id}")
                    return file_id
                else:
                    dify_logger.error(f"文件上传失败，响应: {result}")
                    return None
                    
        except Exception as e:
            dify_logger.error(f"上传文件到Dify失败: {str(e)}")
            return None

    def _send_request(self, endpoint: str, data: dict) -> Dict[str, Any]:
        """发送非流式请求"""
        try:
            url = f"{self.api_base}{endpoint}"
            dify_logger.info(f"发送请求到: {url}")
            
            start_time = time.time()
            response = requests.post(url, headers=self.headers, json=data, verify=False)
            elapsed_time = time.time() - start_time
            
            dify_logger.info(f"请求耗时: {elapsed_time:.3f}秒")
            
            if response.status_code != 200:
                error_msg = f"Dify API请求失败: {response.text}"
                dify_logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            dify_logger.info("成功接收响应")
            return result
            
        except Exception as e:
            dify_logger.error(f"发送请求失败: {str(e)}")
            raise

    def _send_stream_request(self, endpoint: str, data: dict) -> Dict[str, Any]:
        """发送流式请求"""
        try:
            url = f"{self.api_base}{endpoint}"
            dify_logger.info(f"发送流式请求到: {url}")
            
            start_time = time.time()
            response = requests.post(url, headers=self.headers, json=data, stream=True, verify=False)
            elapsed_time = time.time() - start_time
            
            dify_logger.info(f"请求耗时: {elapsed_time:.3f}秒")
            
            if response.status_code != 200:
                error_msg = f"Dify API请求失败: {response.text}"
                dify_logger.error(error_msg)
                raise Exception(error_msg)
            
            dify_logger.info("开始接收流式响应")
            return self._handle_stream_response(response)
            
        except Exception as e:
            dify_logger.error(f"发送流式请求失败: {str(e)}")
            raise

    def _handle_stream_response(self, response) -> Dict[str, Any]:
        """处理流式响应，返回字典格式，参考dingtalk-dify-master的实现"""
        try:
            import sseclient
            
            client = sseclient.SSEClient(response)
            accumulated_data = {"answer": ""}  # 确保answer字段始终存在
            event_stream = []
            chunk_count = 0
            
            for event in client.events():
                if event.data.strip():  # 忽略空行
                    try:
                        chunk = json.loads(event.data)
                        event_stream.append(chunk)
                        
                        # 合并数据
                        for key, value in chunk.items():
                            if key not in accumulated_data:
                                accumulated_data[key] = value
                            elif key == "answer":
                                accumulated_data[key] += value
                        
                        chunk_count += 1
                        
                        # 每10个块记录一次，避免日志过多
                        if chunk_count % 10 == 0:
                            dify_logger.debug(f"接收流式响应块 #{chunk_count}")
                        
                    except json.JSONDecodeError as e:
                        dify_logger.warning(f"解析JSON数据块失败: {str(e)}")
                        continue
                    except Exception as e:
                        dify_logger.warning(f"处理数据块时出错: {str(e)}")
                        continue
                        
            dify_logger.info(f"流式响应完成，共 {chunk_count} 个数据块")
            
            return {
                "event_stream": event_stream,
                "chunk_count": chunk_count,
                "accumulated_data": accumulated_data
            }
        except Exception as e:
            dify_logger.error(f"处理流式响应时出错: {str(e)}")
            raise 