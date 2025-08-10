# 钉钉云盘文件上传与Dify工作流分析功能指南

## 概述

本功能基于钉钉官方 Storage 2.0 API 实现，支持将用户发送的文件自动上传到钉钉云盘，并集成Dify工作流进行AI智能分析。

## 功能特性

- ✅ 支持多种文件格式（PDF、Word、Excel、图片、音频、视频等）
- ✅ 自动文件大小检查（默认最大100MB）
- ✅ 钉钉云盘存储，生成可访问的文档链接
- ✅ **Dify工作流AI分析集成**
- ✅ 智能错误处理和重试机制
- ✅ 支持工作空间管理
- ✅ 基于钉钉官方API规范实现

## 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 文件处理配置
MAX_FILE_SIZE_MB=100                    # 最大文件大小（MB）
UPLOAD_TO_DIFY=true                     # 启用Dify集成
ENABLE_DINGTALK_DRIVE=true              # 启用钉钉云盘功能

# Dify工作流配置
DIFY_USE_WORKFLOW=true                  # 启用Dify工作流
DIFY_WORKFLOW_ID=your_workflow_id      # Dify工作流ID（可选）

# 钉钉云盘配置
DINGTALK_DRIVE_SPACE_TYPE=org           # 工作空间类型（org/personal）
DINGTALK_DRIVE_STORAGE_DRIVER=DINGTALK  # 存储驱动
DINGTALK_DRIVE_CONFLICT_STRATEGY=OVERWRITE  # 冲突处理策略
DINGTALK_DRIVE_CONVERT_TO_ONLINE_DOC=false  # 是否转换为在线文档
```

### 必需权限

确保钉钉应用具有以下权限：

1. **通讯录权限**：获取用户 unionId
2. **云盘权限**：访问和上传文件
3. **机器人权限**：接收和处理消息

## 使用流程

### 1. 用户发送文件

用户在钉钉中向机器人发送文件，机器人会自动接收并处理。

### 2. 文件信息提取

机器人从消息中提取文件信息（基于钉钉官方规范）：
- 文件名
- 文件大小
- 文件类型
- 文件ID和空间ID

### 3. 钉钉云盘上传

机器人将文件上传到钉钉云盘（钉钉官方Storage 2.0 API流程）：
1. 获取访问令牌（OAuth2.0）
2. 获取工作空间ID
3. 获取文件上传信息
4. 上传文件到资源服务器
5. 提交文件信息

### 4. 生成文档链接

上传成功后，生成钉钉云盘文档链接，格式：
```
https://alidocs.dingtalk.com/i/nodes/{uuid}
```

### 5. Dify工作流AI分析

**新增功能**：机器人自动将文件信息发送给Dify工作流进行AI分析：

```python
# 工作流输入参数
workflow_inputs = {
    "file_info": {
        "name": "文件名",
        "size": "文件大小",
        "type": "文件类型",
        "dingtalk_file_id": "钉钉文件ID",
        "dingtalk_doc_url": "钉钉云盘链接",
        "upload_time": "上传时间戳",
        "user_union_id": "用户unionId"
    },
    "analysis_request": "分析请求描述"
}
```

## API 接口

### 钉钉云盘服务类

```python
from dingtalk.drive_service import DingTalkDriveService

# 创建服务实例
drive_service = DingTalkDriveService(client_id, client_secret)

# 上传文件
result = await drive_service.upload_file(
    file_name="document.pdf",
    file_size=1024000,
    union_id="user_union_id"
)

# 获取文件信息
file_info = await drive_service.get_file_info(
    file_id="file_id",
    space_id="space_id",
    union_id="user_union_id"
)
```

### Dify工作流集成

```python
from dify.client import DifyClient

# 创建Dify客户端
dify_client = DifyClient(api_base, api_key, app_type="chat")

# 执行工作流
response = dify_client.workflow_run(
    inputs=workflow_inputs,
    user=user_id,
    stream=False
)
```

## 钉钉官方API规范

### 认证机制
- 使用OAuth2.0获取访问令牌
- 所有API请求携带 `x-acs-dingtalk-access-token` 头

### 文件上传流程
1. **获取工作空间**: `/drive/spaces`
2. **获取上传信息**: `/storage/spaces/{spaceId}/files/uploadInfos`
3. **上传到资源服务器**: PUT方法到钉钉返回的resourceUrl
4. **提交文件信息**: `/storage/spaces/{spaceId}/files/commit`

### 请求头规范
```python
headers = {
    "x-acs-dingtalk-access-token": access_token,
    "Content-Type": "application/json"
}
```

### 超时设置
- 普通API请求：10秒
- 文件上传：60秒
- 认证请求：30秒

## 错误处理

### 重试机制
- 访问令牌获取：最多重试5次
- 文件上传：最多重试3次
- 网络请求：自动重试机制

### 错误日志
- 文件接收失败
- 上传过程异常
- Dify工作流执行错误
- 网络连接问题

## 使用场景

1. **企业文档管理**: 自动上传企业文档到钉钉云盘
2. **AI智能分析**: 通过Dify工作流进行文件内容分析
3. **文件共享**: 生成云盘链接供团队访问
4. **工作流集成**: 与钉钉工作流结合使用
5. **智能客服**: 自动分析用户上传的文件并提供智能回复

## 注意事项

1. **文件大小限制**: 默认最大100MB，可在配置中调整
2. **文件类型支持**: 支持钉钉应用配置的所有文件类型
3. **权限要求**: 确保钉钉应用具有必要的权限
4. **网络环境**: 建议在稳定的网络环境下使用
5. **Dify配置**: 确保Dify API密钥和工作流配置正确

## 故障排除

### 常见问题

1. **文件上传失败**
   - 检查钉钉应用权限
   - 验证网络连接
   - 查看错误日志

2. **Dify工作流执行失败**
   - 检查API密钥配置
   - 验证工作流ID
   - 查看Dify服务状态

3. **权限获取失败**
   - 检查钉钉应用配置
   - 验证client_id和client_secret
   - 确认应用权限设置

### 日志查看

查看应用日志以获取详细的错误信息：
```bash
tail -f logs/app.log
``` 