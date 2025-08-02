# API文档

## 核心组件

### DifyHandler

处理钉钉消息并与Dify API交互。

```python
class DifyHandler:
    def __init__(self, config):
        # 初始化配置
        
    def process(self, ctx, data):
        # 处理文本流式输出
        
    def process_with_ai_card(self, ctx, data):
        # 处理AI卡片流式输出
```

### SessionManager

管理用户会话和对话历史。

```python
class SessionManager:
    def __init__(self, timeout=1800):
        # 初始化会话管理器
        
    def get_session(self, user_id):
        # 获取用户会话
        
    def update_session(self, user_id, messages):
        # 更新用户会话
        
    def clear_session(self, user_id):
        # 清除用户会话
```

### DifyClient

与Dify API交互的客户端。

```python
class DifyClient:
    def __init__(self, api_base, api_key):
        # 初始化客户端
        
    def chat_completion(self, messages, stream=False):
        # 聊天完成API
        
    def completion(self, inputs, query, stream=False):
        # 文本完成API
```

### DingTalkClient

与钉钉API交互的客户端。

```python
class DingTalkClient:
    def __init__(self, client_id, client_secret):
        # 初始化客户端
        
    def send_text_message(self, open_conversation_id, text, at_users=None):
        # 发送文本消息
        
    def send_ai_card(self, open_conversation_id, template_id, card_data, at_users=None):
        # 发送AI卡片
        
    def update_ai_card(self, open_conversation_id, card_instance_id, card_data, is_finalize=False, is_error=False):
        # 更新AI卡片
```

## 配置API

### Config类

管理应用配置。

```python
class Config:
    def __init__(self, config_path="config.json"):
        # 初始化配置
        
    def _load_config(self):
        # 加载配置文件
        
    def _override_from_env(self):
        # 从环境变量覆盖配置
```

## 日志API

### 日志工具

提供格式化和彩色日志输出。

```python
# 获取应用日志
app_logger = setup_logger("dingtalk_dify_adapter", "logs/dingtalk_dify_adapter.log")

# 获取钉钉API日志
dingtalk_logger = setup_logger("dingtalk_api", "logs/dingtalk_api.log")

# 获取Dify API日志
dify_logger = setup_logger("dify_api", "logs/dify_api.log")

# 记录API请求
log_request(logger, method, url, headers, data, params)

# 记录API响应
log_response(logger, response, elapsed_time)
``` 