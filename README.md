# 钉钉-Dify流式适配器

基于官方代码示例实现的钉钉-Dify流式适配器，使用AICardReplier进行AI卡片流式输出，支持多种消息类型。

## 主要特性

- ✅ 基于官方 `dingtalk-stream` SDK
- ✅ 使用官方 `AICardReplier` 实现AI卡片流式输出
- ✅ 支持打字机效果的流式更新
- ✅ **多类型消息支持**：文本、图片、语音、文件、链接、OA消息
- ✅ 环境变量配置
- ✅ 完善的错误处理和重试机制
- ✅ 详细的日志记录

## 支持的消息类型

### 📝 **接收消息类型**
1. **文本消息** - 支持AI卡片流式输出
2. **图片消息** - 自动识别并处理图片内容
3. **语音消息** - 支持语音消息处理
4. **文件消息** - 支持文件上传和处理，自动上传到Dify进行分析

### 📤 **发送消息类型**
1. **文本消息** (`reply_text`) - 基础文本回复
2. **Markdown消息** (`reply_markdown`) - 富文本格式
3. **AI卡片** (`AICardReplier`) - 流式输出卡片
4. **图片消息** (`reply_image`) - 发送图片
5. **链接消息** (`reply_link`) - 发送链接卡片
6. **OA消息** (`reply_oa`) - 发送OA格式消息
7. **交互卡片** (`reply_card`) - 发送交互式卡片

## 文件处理功能

### 🔧 **文件处理流程**
1. **接收文件** - 用户发送文件消息
2. **提取信息** - 获取文件名、大小、downloadCode、fileId、spaceId
3. **构建下载URL** - 使用downloadCode构建钉钉文件下载URL
4. **下载文件** - 从钉钉服务器下载文件到临时目录（使用钉钉访问令牌）
5. **上传到Dify** - 使用[Dify文件上传API](https://docs.dify.ai/api-reference/%E6%96%87%E4%BB%B6%E6%93%8D%E4%BD%9C/%E4%B8%8A%E4%BC%A0%E6%96%87%E4%BB%B6)上传文件
6. **AI分析** - Dify分析文件内容并生成回复
7. **返回结果** - 将分析结果发送给用户

### 📁 **支持的文件类型**
- 文档文件：PDF、DOC、DOCX、TXT等
- 图片文件：JPG、PNG、GIF等
- 表格文件：XLS、XLSX、CSV等
- 其他格式：根据Dify应用配置支持的类型

### 🛠️ **技术实现**
- **文件下载**：使用临时文件处理，自动清理
- **钉钉集成**：支持钉钉文件API，使用访问令牌下载文件
- **文件上传**：支持multipart/form-data格式上传到Dify
- **错误处理**：完善的异常处理和重试机制
- **日志记录**：详细的操作日志和错误日志
- **文件扩展名**：智能推断正确的文件扩展名
- **临时文件管理**：安全的临时文件创建和清理

### 🔍 **文件消息解析**
系统支持钉钉文件消息格式：
```json
{
  "content": {
    "spaceId": "27000524016",
    "fileName": "八大思维导图(4).docx",
    "downloadCode": "2QAztKWQQ2zR0OwP9or88hEi95b0yCvy79JOI9NVuhWWcuay3LrhKX9s5/M7/uR4DlUJaBCNwrzZq9Aiz2W0SI1yfu1Ly0/qXKhId9zbBeywTvGk+6gMVOm1+jgBo7L9fiqyHzqhmiGhWJ31VsM1i+zbLE4y9Um2JSoBu4y9c0lMuK3RErCPwrzCzsbPDUz+wQQRCXBHUwP4HwASPxSuKJVCLzU5yu109QNflE6Atuk=",
    "fileId": "188916199339"
  }
}
```

### 📋 **钉钉文件API集成**
根据[钉钉文件上传API文档](https://open.dingtalk.com/document/isvapp/upload-media-files)：
- **文件下载**：支持多种下载方式，自动重试
- **API路径**：`/v1.0/robot/media/download` 或 `/v1.0/robot/file/download`
- **参数支持**：`downloadCode`、`fileId`、`code`等多种参数格式
- **访问令牌**：自动获取钉钉访问令牌用于文件下载
- **认证方式**：使用`DingTalkAuth`类获取访问令牌
- **支持格式**：图片、语音、视频、文件（最大100MB）
- **错误处理**：完善的API调用错误处理机制
- **重试机制**：下载失败时自动尝试不同的API路径和参数

### 🔧 **Dify文件上传集成**
根据[Dify文件上传API文档](https://docs.dify.ai/api-reference/%E6%96%87%E4%BB%B6%E6%93%8D%E4%BD%9C/%E4%B8%8A%E4%BC%A0%E6%96%87%E4%BB%B6)：
- **上传接口**：`POST /files/upload`
- **请求格式**：`multipart/form-data`
- **认证方式**：`Authorization: Bearer {API_KEY}`
- **返回格式**：包含文件ID的JSON响应
- **文件限制**：支持应用程序支持的所有格式
- **超时设置**：60秒上传超时
- **错误处理**：详细的错误响应处理

### 🔄 **Dify工作流支持**
根据[Dify工作流API文档](https://docs.dify.ai/api-reference/%E5%B7%A5%E4%BD%9C%E6%B5%81/%E6%89%A7%E8%A1%8C%E5%B7%A5%E4%BD%9C%E6%B5%81)：
- **工作流接口**：`POST /workflows/run`
- **支持模式**：聊天API和工作流API两种模式
- **文件处理**：支持将文件上传到工作流进行处理
- **输入参数**：支持自定义输入参数
- **流式输出**：支持流式和非流式两种输出模式
- **配置选项**：通过`DIFY_USE_WORKFLOW`环境变量控制

### 🎯 **AI卡片打字机输出**
系统支持AI卡片的打字机效果流式输出，基于[钉钉官方文档](https://open.dingtalk.com/document/isvapp/example-of-card-api-call)：

#### **实现原理**
1. **卡片创建**：使用`AICardReplier.async_create_and_deliver_card`创建AI卡片
2. **流式更新**：通过`async_streaming`方法实时更新卡片内容
3. **打字机效果**：每20个字符更新一次，实现打字机效果
4. **状态管理**：支持处理中、完成、失败等状态

#### **核心组件**
```python
# 创建AI卡片回复器
card_instance = AICardReplier(self.dingtalk_client, incoming_message)

# 创建卡片 - 基于官方文档
card_instance_id = await card_instance.async_create_and_deliver_card(
    card_template_id, 
    card_data,
    callback_type="STREAM",  # 指定回调类型为流式
    at_sender=False,  # 不@发送者
    at_all=False,     # 不@所有人
    support_forward=True  # 支持转发
)

# 流式更新 - 基于官方文档
await card_instance.async_streaming(
    card_instance_id,
    content_key=content_key,
    content_value=content_value,
    append=False,  # 不追加，替换内容
    finished=False,  # 未完成
    failed=False,    # 未失败
)
```

#### **官方文档规范**
- **API调用**：使用官方推荐的`async_create_and_deliver_card`方法
- **回调类型**：指定`callback_type="STREAM"`支持流式更新
- **参数设置**：按照官方文档设置`at_sender`、`at_all`、`support_forward`等参数
- **状态管理**：使用`finished`和`failed`参数正确管理卡片状态
- **错误处理**：遵循官方文档的错误处理机制

#### **打字机效果实现**
- **更新阈值**：每20个字符更新一次，符合官方建议
- **累积内容**：逐步累积Dify返回的内容
- **实时更新**：通过回调函数实时更新卡片
- **最终状态**：完成后标记`finished=True`

#### **错误处理**
- **卡片创建失败**：回退到普通文本消息
- **更新失败**：记录错误并继续处理
- **SSL问题**：自动重试和SSL修复
- **网络异常**：多次重试机制
- **API异常**：发送友好的错误信息

### 🔐 **SSL问题修复**
系统已集成SSL问题修复机制：
- **SSL验证禁用**：自动禁用SSL证书验证
- **连接池优化**：优化HTTP连接池设置
- **重试机制**：添加网络请求重试机制
- **环境变量**：设置SSL相关环境变量
- **requests配置**：修改requests库默认行为

### 🔐 **钉钉认证配置**
文件下载需要钉钉访问令牌，系统会自动：
1. **获取配置**：从环境变量读取`DINGTALK_CLIENT_ID`和`DINGTALK_CLIENT_SECRET`
2. **创建认证对象**：使用`DingTalkAuth`类
3. **获取访问令牌**：调用`get_access_token()`方法
4. **添加认证头**：在文件下载请求中添加`x-acs-dingtalk-access-token`头部
5. **错误处理**：如果认证失败，会记录警告但继续处理

### 🔄 **文件下载重试机制**
系统支持多种文件下载方式，按优先级尝试：
1. **主要方法**：使用`downloadCode`参数下载
2. **备用方法1**：使用`fileId`参数下载
3. **备用方法2**：使用不同的API路径（`/robot/file/download`）
4. **备用方法3**：使用`code`参数格式
5. **错误处理**：所有方法失败时记录详细错误信息

### ⚙️ **配置选项**
系统支持多种配置模式：

#### **Dify API模式**
```env
# 聊天API模式（默认）
DIFY_USE_WORKFLOW=false
DIFY_APP_TYPE=chat

# 工作流模式
DIFY_USE_WORKFLOW=true
DIFY_APP_TYPE=workflow
```

#### **文件处理流程**
1. **聊天API模式**：文件 → 聊天API → 回复
2. **工作流模式**：文件 → 工作流API → 处理结果

### 🔧 **故障排除**

#### **AI卡片问题**
如果AI卡片创建或更新失败：
1. **检查导入**：确保`AICardReplier`正确导入
2. **SSL修复**：确保SSL连接正常
3. **模板ID**：确认卡片模板ID正确
4. **权限检查**：确认钉钉应用权限配置正确
5. **回退机制**：系统会自动回退到文本消息

#### **SSL连接问题**
如果遇到SSL连接错误：
1. **自动修复**：系统已集成SSL修复机制
2. **手动修复**：运行`python ssl_fix.py`
3. **环境变量**：确保设置了SSL相关环境变量
4. **网络检查**：检查网络连接和防火墙设置

#### **流式输出问题**
如果AI卡片流式输出失败：
1. **检查配置**：确认钉钉应用配置正确
2. **SSL修复**：确保SSL连接正常
3. **重试机制**：系统会自动重试获取访问令牌
4. **日志查看**：查看详细错误日志

## 架构说明

### 核心组件

1. **CardBotHandler**: 多类型消息处理器，继承自官方 `ChatbotHandler`
2. **DifyClient**: Dify API客户端，处理与Dify的通信
3. **AICardReplier**: 官方AI卡片回复器，用于创建和更新AI卡片
4. **Storage API**: 钉钉Storage 1.0/2.0 API，处理文件下载和上传

### 消息处理流程

1. **接收消息** - 根据消息类型分发处理
2. **内容提取** - 提取文本、图片、语音、文件信息
3. **文件处理** - 使用Storage API下载文件并上传到Dify
4. **发送给Dify** - 将消息内容发送给Dify API
5. **接收响应** - 处理Dify的回复内容
6. **发送回复** - 根据内容类型选择合适的回复方式

### 文件处理功能

- **文件下载**: 使用Storage 1.0 API从钉钉下载文件
- **文件上传**: 使用Storage 2.0 API上传文件到钉钉（新增功能）
- **流式处理**: 支持大文件的流式下载和上传
- **错误处理**: 完善的错误处理和重试机制

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**：项目使用钉钉官方SDK `alibabacloud-dingtalk`，无需手动下载taobao SDK文件。所有依赖都会通过pip自动安装。

### 2. 配置环境变量

复制 `env.example` 到 `.env` 并填写配置：

```bash
# 复制环境变量模板文件
cp env.example .env
```

编辑 `.env` 文件，填入您的实际配置：

```env
# 钉钉应用配置
DINGTALK_CLIENT_ID=dingvso4q8mkqfphqvvd
DINGTALK_CLIENT_SECRET=ukj_XEvVToTyYHIxkyK0t29gfd5162xnDAL3V1M071d8mbWPI2dE15uULXEI0DGV
DINGTALK_AI_CARD_TEMPLATE_ID=d8c997f0-6d82-4e55-b7ec-b92657f438e5.schema

# Dify配置
DIFY_API_BASE=http://1.92.133.173/v1
DIFY_API_KEY=app-bFcvDV9K3p02ha72oHs7WluY
DIFY_APP_TYPE=chat

# 服务器配置
SERVER_PORT=9090
SESSION_TIMEOUT=1800
STREAM_MODE=ai_card

# 日志配置
LOG_LEVEL=INFO
```

**注意**：`.env` 文件包含敏感信息，请确保：
- 不要将 `.env` 文件提交到版本控制系统
- 在生产环境中使用环境变量或安全的配置管理
- 定期更新访问令牌和密钥

### 3. 创建AI卡片模板

1. 访问 [钉钉卡片平台](https://card.dingtalk.com/card-builder)
2. 创建AI卡片模板
3. 获取模板ID并填入 `DINGTALK_AI_CARD_TEMPLATE_ID`

### 4. 申请权限

确保钉钉应用已申请以下权限：

#### 基础权限
- `Card.Streaming.Write`: AI卡片流式更新权限
- `Robot.Message.Send`: 机器人消息发送权限
- `Robot.Message.Receive`: 机器人消息接收权限

#### 文件处理权限（必需）
- `Contact.Org.Read`: 通讯录权限（Storage API必需）
- `Storage.Read`: 存储权限（文件下载必需）
- `Storage.Write`: 存储权限（文件上传必需，新增功能）

**重要**：如果遇到 `Forbidden.AccessDenied.AccessTokenPermissionDenied` 错误，请参考 [权限申请指导](PERMISSION_GUIDE.md) 进行权限申请。

## 使用方法

### 本地开发环境

```bash
python app.py
```

### 服务器部署

#### 方法一：使用服务器启动脚本（推荐）

```bash
python start_server.py
```

服务器启动脚本会自动：
- 检测服务器环境
- 检查并安装依赖
- 设置优化的服务器配置
- 启动应用程序

#### 方法二：手动设置环境变量

```bash
# 设置服务器环境变量
export SERVER_ENV=true
export LOG_LEVEL=INFO
export REQUESTS_TIMEOUT=60
export MAX_FILE_SIZE=100MB

# 启动应用程序
python app.py
```

#### 服务器环境优化

服务器环境下会自动应用以下优化：
- 更长的网络超时时间（60秒）
- 更大的文件上传限制（100MB）
- 详细的日志记录
- 增强的错误处理

### 命令行参数

```bash
python app.py --help
```

支持的参数：
- `--client_id`: 钉钉应用客户端ID
- `--client_secret`: 钉钉应用客户端密钥
- `--card_template_id`: AI卡片模板ID
- `--dify_api_base`: Dify API基础URL
- `--dify_api_key`: Dify API密钥
- `--dify_app_type`: Dify应用类型 (chat或completion)

### 示例

```bash
# 使用环境变量
python app.py

# 使用命令行参数
python app.py \
  --client_id your_client_id \
  --client_secret your_client_secret \
  --card_template_id your_template_id \
  --dify_api_key your_dify_api_key
```

## 代码结构

```
dingtalk/
├── app.py                  # 主程序 (支持多类型消息)
├── dify/
│   └── client.py          # Dify API客户端
├── utils/
│   └── logger.py          # 日志系统
├── .env                   # 环境变量配置
└── requirements.txt       # 依赖列表
```

## 消息类型详解

### 📝 文本消息处理
- **接收**: 用户发送文本消息
- **处理**: 使用AI卡片流式输出
- **回复**: 流式更新AI卡片内容

### 🖼️ 图片消息处理
- **接收**: 用户发送图片
- **处理**: 提取图片下载地址，发送给Dify
- **回复**: 文本回复图片处理结果

### 🎵 语音消息处理
- **接收**: 用户发送语音
- **处理**: 提取语音信息，发送给Dify
- **回复**: 文本回复语音处理结果

### 📁 文件消息处理
- **接收**: 用户发送文件
- **处理**: 使用钉钉Storage API获取文件下载信息，提取文件内容发送给Dify
- **回复**: 文本回复文件处理结果
- **支持**: 基于官方Storage API，支持更稳定的文件下载

## 关键改进

### 1. 使用官方API

- 使用 `AICardReplier` 替代自定义实现
- 使用正确的流式更新API路径
- 遵循官方参数规范

### 2. 多类型消息支持

- 支持文本、图片、语音、文件等多种消息类型
- 自动识别消息类型并分发处理
- 提供多种回复方式

### 3. 改进的错误处理

- 更详细的错误日志
- 优雅的异常处理
- 自动重试机制

### 4. 更好的流式输出

- 正确的打字机效果
- 可配置的更新频率
- 支持错误状态显示

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DINGTALK_CLIENT_ID` | 钉钉应用客户端ID | - |
| `DINGTALK_CLIENT_SECRET` | 钉钉应用客户端密钥 | - |
| `DINGTALK_AI_CARD_TEMPLATE_ID` | AI卡片模板ID | `8aebdfb9-28f4-4a98-98f5-396c3dde41a0.schema` |
| `DIFY_API_BASE` | Dify API基础URL | `https://api.dify.ai/v1` |
| `DIFY_API_KEY` | Dify API密钥 | - |
| `DIFY_APP_TYPE` | Dify应用类型 | `chat` |

## 故障排除

### 常见问题

1. **SSL连接错误**
   - 检查网络连接
   - 确认防火墙设置
   - 运行 `python ssl_fix.py` 修复SSL问题

2. **API权限错误**
   - 确认钉钉应用权限配置
   - 检查AI卡片模板ID是否正确
   - 验证应用是否已上线

3. **消息类型不支持**
   - 检查消息类型是否在支持列表中
   - 查看日志中的错误信息

4. **流式输出不工作**
   - 检查AI卡片模板配置正确
   - 查看日志中的错误信息

### 日志文件

- `logs/dingtalk_dify_adapter.log`: 主程序日志
- `logs/dingtalk_api.log`: 钉钉API调用日志
- `logs/dify_api.log`: Dify API调用日志

## 开发说明

### 添加新消息类型

1. 在 `CardBotHandler.process` 中添加新的消息类型判断
2. 创建对应的处理方法（如 `handle_video_message`）
3. 添加对应的回复方法（如 `reply_video`）

### 调试模式

设置环境变量启用详细日志：

```env
LOG_LEVEL=DEBUG
```

## 版本历史

- **v2.2**: 升级文件下载功能，使用钉钉Storage API，提高文件处理稳定性
- **v2.1**: 增加多类型消息支持（图片、语音、文件、链接、OA）
- **v2.0**: 基于官方代码重构，使用 `AICardReplier`
- **v1.0**: 初始版本，自定义AI卡片实现

## 新功能说明

### 文件下载升级 (v2.2)

- **官方Storage API**: 使用钉钉官方Storage API获取文件下载信息
- **稳定的下载**: 基于官方SDK，支持多种文件类型
- **详细日志**: 提供完整的下载过程日志和错误信息

### 新增依赖

项目新增了以下依赖包：
- `alibabacloud-tea-openapi`: 阿里云OpenAPI SDK
- `alibabacloud-tea-util`: 阿里云工具包

**钉钉Storage SDK**: 已包含在requirements.txt中
- 安装命令: `pip install alibabacloud-dingtalk alibabacloud-tea-openapi alibabacloud-tea-util`
- 或者直接运行: `pip install -r requirements.txt`

## 许可证

MIT License 