# 钉钉-Dify流式适配器

基于官方 `dingtalk-stream` SDK 实现的钉钉-Dify流式适配器，使用 `AICardReplier` 进行AI卡片流式输出，支持多种消息类型和文件处理功能。

## 🚀 主要特性

- ✅ **基于官方SDK**: 使用官方 `dingtalk-stream` SDK
- ✅ **AI卡片流式输出**: 使用 `AICardReplier` 实现打字机效果
- ✅ **多类型消息支持**: 文本、图片、语音、文件、链接、OA消息
- ✅ **文件处理功能**: 自动上传文件到Dify进行分析
- ✅ **模块化架构**: 清晰的代码结构和职责分离
- ✅ **SSL自动修复**: 内置SSL工具模块，自动处理连接问题
- ✅ **完善的错误处理**: 重试机制和异常处理
- ✅ **详细日志记录**: 彩色控制台输出和文件日志
- ✅ **Docker支持**: 完整的容器化部署方案
- ✅ **双模式支持**: 模块化处理器和内置处理器

## 📋 支持的消息类型

### 📥 接收消息类型
1. **文本消息** - 支持AI卡片流式输出
2. **图片消息** - 自动识别并处理图片内容
3. **语音消息** - 支持语音消息处理
4. **文件消息** - 支持文件上传和处理，自动上传到Dify进行分析

### 📤 发送消息类型
1. **文本消息** (`reply_text`) - 基础文本回复
2. **Markdown消息** (`reply_markdown`) - 富文本格式
3. **AI卡片** (`AICardReplier`) - 流式输出卡片
4. **图片消息** (`reply_image`) - 发送图片
5. **链接消息** (`reply_link`) - 发送链接卡片
6. **OA消息** (`reply_oa`) - 发送OA格式消息
7. **交互卡片** (`reply_card`) - 发送交互式卡片

## 🏗️ 项目架构

```
dingtalk/
├── app.py                          # 主程序入口文件
├── requirements.txt                 # Python依赖包
├── env.example                     # 环境变量示例
├── docker-compose.yml              # Docker编排文件
├── Dockerfile                      # Docker镜像构建文件
├── CHANGELOG.md                    # 变更日志
├── .gitignore                      # Git忽略文件
├── .dockerignore                   # Docker忽略文件
│
├── handlers/                       # 模块化处理器
│   ├── __init__.py
│   ├── message_handler.py          # 消息分发处理器
│   ├── ai_card_handler.py         # AI卡片处理器
│   ├── file_handler.py            # 文件消息处理器
│   └── reply_handler.py           # 回复消息处理器
│
├── utils/                          # 工具模块
│   ├── __init__.py
│   ├── logger.py                   # 日志系统
│   ├── ssl_utils.py               # SSL配置工具
│   └── dingtalk_client.py         # 钉钉客户端工具
│
├── dify/                          # Dify集成模块
│   ├── __init__.py
│   └── client.py                  # Dify API客户端
│
├── config/                        # 配置管理
│   ├── __init__.py
│   └── settings.py                # 配置管理类
│
├── adapter/                       # 适配器模块
│   ├── __init__.py
│   └── session.py                 # 会话管理
│
├── logs/                          # 日志文件目录
├── wiki/                          # 文档目录
└── dingtalk/                      # 钉钉相关模块
    ├── __init__.py
    ├── auth.py                    # 钉钉认证
    ├── client.py                  # 钉钉客户端
    └── requirements.txt           # 钉钉模块依赖
```

## 🔧 核心模块功能

### 1. 主程序 (app.py)
- **功能**: 程序入口和配置管理
- **职责**: 
  - 配置加载和验证
  - SSL修复和服务器环境检测
  - 钉钉流式客户端初始化
  - 处理器注册和启动
  - 命令行参数处理
- **特性**: 支持模块化和内置处理器切换

### 2. 模块化处理器 (handlers/)

#### message_handler.py
- **功能**: 消息分发和主要处理逻辑
- **职责**: 根据消息类型分发到对应处理器

#### ai_card_handler.py
- **功能**: AI卡片创建和流式更新
- **职责**: 
  - 创建AI卡片实例
  - 流式调用Dify API
  - 实时更新卡片内容
  - 异常处理和回退机制

#### file_handler.py
- **功能**: 文件消息处理
- **职责**:
  - 文件信息提取
  - 文件下载和上传到Dify
  - 文件类型识别和MIME类型处理
  - 工作流和聊天API支持

#### reply_handler.py
- **功能**: 回复消息处理
- **职责**:
  - 图片和语音消息处理
  - Dify API集成
  - 各种回复类型支持
  - 错误回复处理

### 3. 工具模块 (utils/)

#### logger.py
- **功能**: 增强版日志系统
- **特性**: 彩色终端输出、JSON格式日志、文件轮转

#### ssl_utils.py
- **功能**: SSL配置工具
- **特性**: SSL证书验证修复、服务器环境SSL配置

#### dingtalk_client.py
- **功能**: 钉钉客户端工具
- **特性**: 用户信息获取、UnionId获取、钉钉API调用封装

### 4. Dify集成 (dify/)

#### client.py
- **功能**: Dify API客户端
- **特性**: 聊天完成API、文本完成API、工作流执行API、文件上传API

### 5. 配置管理 (config/)

#### settings.py
- **功能**: 配置管理类
- **特性**: 环境变量加载、配置验证、默认值设置、服务器环境检测

## 📁 文件处理功能

### 文件处理流程
1. **接收文件** - 用户发送文件消息
2. **提取信息** - 获取文件名、大小、downloadCode、fileId、spaceId
3. **构建下载URL** - 使用downloadCode构建钉钉文件下载URL
4. **下载文件** - 从钉钉服务器下载文件到临时目录
5. **上传到Dify** - 使用Dify文件上传API上传文件
6. **AI分析** - Dify分析文件内容并生成回复
7. **返回结果** - 将分析结果发送给用户

### 支持的文件类型
- 文档文件：PDF、DOC、DOCX、TXT等
- 图片文件：JPG、PNG、GIF等
- 表格文件：XLS、XLSX、CSV等
- 其他格式：根据Dify应用配置支持的类型

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- 钉钉应用配置
- Dify API密钥

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑环境变量
DINGTALK_CLIENT_ID=your_client_id
DINGTALK_CLIENT_SECRET=your_client_secret
DIFY_API_KEY=your_dify_api_key
```

### 4. 运行程序

#### 🚀 自动启动脚本 (推荐 - Windows用户)
```bash
# 双击运行启动脚本
start.bat

# 或在命令行中运行
start.bat
```

**自动启动脚本功能：**
- ✅ 自动检查Python环境和虚拟环境
- ✅ 自动安装依赖包
- ✅ 自动检查配置文件

- ✅ 完整的错误处理和用户提示

#### 📝 手动启动方式

##### 模块化处理器 (推荐)
```bash
python app.py --use-modular-handlers
```

##### 内置处理器
```bash
python app.py --use-builtin-handlers
```

##### 指定配置
```bash
python app.py --client_id your_id --client_secret your_secret
```



### 5. Docker部署
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 🚀 启动脚本使用说明

### start.bat 自动启动脚本

`start.bat` 是一个功能完整的Windows自动启动脚本，提供了以下特性：

#### ✨ 主要功能
- **🔍 环境检查**: 自动检查Python版本、虚拟环境、依赖包
- **📦 依赖管理**: 自动安装requirements.txt中的依赖包
- **⚙️ 配置验证**: 检查.env配置文件和logs目录

- **🛡️ 错误处理**: 完整的错误处理和用户友好的提示信息

#### 📋 使用方法
1. **双击启动**: 在Windows资源管理器中双击 `start.bat` 文件
2. **命令行启动**: 在命令提示符或PowerShell中运行 `start.bat`
3. **自动完成**: 脚本会自动完成所有启动步骤，无需用户干预

#### 🔧 启动流程
```
环境检查 → 虚拟环境激活 → 依赖安装 → 配置验证 → 服务启动
```



#### ⚠️ 注意事项
- 确保在项目根目录下运行脚本
- 首次运行可能需要较长时间安装依赖
- 需要网络连接以下载依赖包
- 建议使用Python 3.8+版本

## ⚙️ 配置说明

### 环境变量配置

#### 钉钉配置
```bash
DINGTALK_CLIENT_ID=your_client_id          # 钉钉应用客户端ID
DINGTALK_CLIENT_SECRET=your_client_secret  # 钉钉应用客户端密钥
DINGTALK_AI_CARD_TEMPLATE_ID=your_template_id  # AI卡片模板ID
```

#### Dify配置
```bash
DIFY_API_BASE=https://api.dify.ai/v1      # Dify API基础URL
DIFY_API_KEY=app-xxx                      # Dify API密钥
DIFY_APP_TYPE=chat                        # Dify应用类型 (chat/completion)
DIFY_USE_WORKFLOW=false                   # 是否使用工作流API
```

#### 服务器配置
```bash
SERVER_PORT=9000                          # 服务器端口
SERVER_HOST=0.0.0.0                      # 服务器主机
SESSION_TIMEOUT=1800                      # 会话超时时间
STREAM_MODE=ai_card                       # 流式输出模式
```

#### 日志配置
```bash
LOG_LEVEL=INFO                            # 日志级别
LOG_FORMAT=text                           # 日志格式 (text/json)
```

### 命令行参数

```bash
# 钉钉配置
--client_id          # 钉钉应用客户端ID
--client_secret      # 钉钉应用客户端密钥
--card_template_id   # AI卡片模板ID

# Dify配置
--dify_api_base      # Dify API基础URL
--dify_api_key       # Dify API密钥
--dify_app_type      # Dify应用类型

# 服务器配置
--port               # 服务器端口
--host               # 服务器主机

# 功能开关
--use-modular-handlers    # 使用模块化处理器
--use-builtin-handlers    # 使用内置处理器
```

## 🔍 故障排除

### 常见问题

#### 1. SSL证书问题
- 检查 `utils/ssl_utils.py` 配置
- 确保SSL修复已正确应用

#### 2. 配置问题
- 检查环境变量和 `config/settings.py`
- 验证钉钉和Dify配置是否正确

#### 3. 日志问题
- 检查 `utils/logger.py` 配置
- 查看 `logs/` 目录下的日志文件

#### 4. 网络问题
- 检查防火墙和代理设置
- 验证网络连接和API可访问性

### 调试模式
```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python app.py
```

## 📈 性能优化

### 1. 服务器环境配置
```bash
# 设置服务器环境
export SERVER_ENV=true

# 增加超时时间
export REQUESTS_TIMEOUT=60

# 增加文件大小限制
export MAX_FILE_SIZE=100MB
```

### 2. 日志优化
```bash
# 使用JSON格式日志
export LOG_FORMAT=json

# 设置日志级别
export LOG_LEVEL=INFO
```

### 3. Docker优化
```bash
# 使用多阶段构建
docker build --target production .

# 设置资源限制
docker run --memory=512m --cpus=1 your-image
```

## 🔧 开发指南

### 添加新的消息处理器
1. 在 `handlers/` 目录下创建新的处理器文件
2. 实现处理器接口
3. 在 `message_handler.py` 中注册新处理器

### 添加新的工具模块
1. 在 `utils/` 目录下创建新的工具文件
2. 实现工具功能
3. 在主程序中导入和使用

### 配置新功能
1. 在 `config/settings.py` 中添加配置项
2. 在环境变量中设置对应值
3. 在代码中使用配置

## 📝 变更日志

### [0.1.0] - 2025-08-02

#### 新增功能
- 初始版本发布
- 支持流式输出模式：AI卡片（推荐）和文本模式
- 集成Dify API实现AI对话功能
- 会话管理，支持多轮对话上下文维护
- 自定义日志系统，支持彩色控制台输出和文件日志

#### 技术特性
- 使用dingtalk-stream-sdk实现钉钉Stream模式接入
- AI卡片流式更新，提供更好的用户体验
- 支持本地和Docker环境部署
- 完善的错误处理和重试机制，增强稳定性
- 支持环境变量和配置文件配置

#### 依赖
- Python 3.8+
- dingtalk-stream 0.24.2
- requests
- sseclient-py 1.7.2

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 技术支持

如果在使用过程中遇到问题：

1. **检查配置**: 确保 `.env` 文件配置正确
2. **查看日志**: 检查 `logs/` 目录下的日志文件
3. **运行测试**: 使用 `python app.py --help` 查看帮助
4. **提交Issue**: 在GitHub上提交详细的问题描述

---

**钉钉-Dify流式适配器** - 让AI对话更智能，让文件处理更便捷！ 