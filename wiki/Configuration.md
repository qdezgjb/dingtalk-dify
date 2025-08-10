# 配置说明

适配器支持通过配置文件和环境变量进行配置。环境变量优先级高于配置文件。

## 配置文件 (config.json)

```json
{
  "dingtalk": {
    "client_id": "钉钉应用的ClientID",
    "client_secret": "钉钉应用的ClientSecret",
    "ai_card_template_id": "AI卡片模板ID"
  },
  "dify": {
    "api_base": "https://api.dify.ai/v1",
    "api_key": "Dify应用的API密钥",
    "app_type": "chat"
  },
  "adapter": {
    "port": 9000,
    "timeout": 60,
    "stream_mode": "ai_card"
  }
}
```

## 环境变量

| 环境变量 | 描述 | 默认值 |
| --- | --- | --- |
| `DINGTALK_CLIENT_ID` | 钉钉应用的ClientID | - |
| `DINGTALK_CLIENT_SECRET` | 钉钉应用的ClientSecret | - |
| `DINGTALK_AI_CARD_TEMPLATE_ID` | AI卡片模板ID | - |
| `DIFY_API_BASE` | Dify API基础URL | https://api.dify.ai/v1 |
| `DIFY_API_KEY` | Dify应用的API密钥 | - |
| `DIFY_APP_TYPE` | Dify应用类型 (chat或completion) | chat |
| `SERVER_PORT` | 服务端口 | 9000 |
| `SESSION_TIMEOUT` | 会话超时时间(秒) | 60 |
| `STREAM_MODE` | 流式输出模式 (ai_card或text) | ai_card |

## 流式输出模式

适配器支持两种流式输出模式：

1. **AI卡片模式** (`stream_mode: "ai_card"`): 使用钉钉AI卡片实现更好的流式输出体验，支持Markdown格式。需要配置`ai_card_template_id`。

2. **文本模式** (`stream_mode: "text"`): 使用普通文本消息实现流式输出，多次发送更新消息。

推荐使用AI卡片模式，提供更好的用户体验。 