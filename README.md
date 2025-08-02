# 钉钉-Dify 流式适配器

钉钉Stream模式的Dify适配器，支持流式输出。

## 功能特点

- 支持钉钉Stream模式下的机器人消息处理
- 支持接收普通文本消息
- 支持接收和发送多种消息格式
- 支持会话保持，记录用户上下文
- **支持流式输出**，实现打字机效果
  - 支持普通文本流式输出
  - 支持AI卡片流式输出 (推荐)

## 使用说明

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

复制 `config.json.example` 为 `config.json`，并填入相应配置：

```json
{
  "dingtalk": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "ai_card_template_id": "your_template_id"  # 使用AI卡片流式输出必须填写
  },
  "dify": {
    "api_base": "https://api.dify.ai/v1",
    "api_key": "your_api_key",
    "app_type": "chat"  # 可选值：chat, completion
  },
  "adapter": {
    "port": 8080,
    "timeout": 1800,  # 会话超时时间，单位秒
    "stream_mode": "ai_card"  # 流式输出模式：text(普通文本)或ai_card(AI卡片)
  }
}
```

### 流式输出模式

适配器支持两种流式输出模式：

1. **AI卡片流式输出（ai_card）** - 默认推荐模式：
   - 使用钉钉的AI卡片实现流式更新
   - 需要配置 `ai_card_template_id`
   - 提供更好的用户体验和更高的更新频率
   - 设置 `stream_mode` 为 `ai_card`

2. **普通文本流式输出（text）**：
   - 使用普通文本消息实现流式更新
   - 不需要特殊配置，适用于所有类型的机器人
   - 设置 `stream_mode` 为 `text`

### 创建AI卡片模板

使用AI卡片流式输出需要在钉钉卡片平台创建一个卡片模板：

1. **进入钉钉卡片平台**
   - 访问 [钉钉卡片平台](https://card.dingtalk.com/card-builder)
   - 或在钉钉开发者后台，点击顶部导航**开放能力** > **卡片平台**

2. **创建新卡片模板**
   - 点击**新建模板**
   - 填写模板基本信息：
     - **模板名称**：如"AI流式回复卡片"
     - **卡片类型**：选择"消息卡片"
     - **卡片模板场景**：选择"AI卡片"
     - **关联应用**：选择您的机器人所属应用

3. **配置卡片内容**
   - 添加一个**Markdown**组件
   - 在Markdown组件设置中：
     - 开启**流式组件开关**
     - 绑定变量：在变量面板中添加`content`变量，并关联到Markdown组件
   - 可以添加标题、图标等其他组件（可选）

4. **保存并获取模板ID**
   - 点击**保存**按钮
   - 在模板列表中找到创建的模板
   - 复制模板ID（格式类似：`34f5g67h-ab12-3c4d-5e6f-789012gh34ij.schema`）
   - 将ID填入配置文件的`ai_card_template_id`字段

5. **申请权限**
   - 在钉钉开发者后台 > 应用开发 > 应用权限管理中
   - 搜索并申请权限点：`Card.Streaming.Write`（流式卡片修改权限）

### 运行

```bash
python app.py
```

## 依赖

- Python 3.7+
- dingtalk-stream
- requests
- sseclient

## 注意事项

- 使用AI卡片流式输出需要创建并配置钉钉AI卡片模板
- 需要确保应用已申请并获得了`Card.Streaming.Write`权限
- 普通文本流式输出可能受到钉钉API频率限制 