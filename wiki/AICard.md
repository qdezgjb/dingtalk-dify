# AI卡片使用指南

钉钉AI卡片是实现流式输出的最佳方式，本指南将帮助您设置和使用AI卡片功能。

## 前提条件

1. 钉钉开发者账号
2. 企业内部应用
3. 开通机器人功能
4. 申请`Card.Streaming.Write`权限

## 创建AI卡片模板

1. 登录[钉钉开发者后台](https://open-dev.dingtalk.com/)
2. 进入您的应用 > 开发管理 > 交互设计 > AI互动卡片
3. 点击"新建AI互动卡片"
4. 选择"空白卡片"模板
5. 配置卡片内容：
   ```json
   {
     "cardTemplateId": "钉钉自动生成的模板ID",
     "cardParams": {
       "title": "AI回复",
       "content": "",
       "status": "loading"
     }
   }
   ```
6. 保存模板并获取模板ID

## 配置适配器

在`config.json`或环境变量中设置：

```json
{
  "dingtalk": {
    "ai_card_template_id": "您的模板ID，例如：9dfa95b6-7c55-4a11-8666-b7cc5577f5a8.schema"
  },
  "adapter": {
    "stream_mode": "ai_card"
  }
}
```

## 卡片状态

AI卡片在不同阶段会展示不同状态：

1. **加载中** (`loading`): 初始发送卡片时的状态
2. **处理中** (`updating`): 流式更新内容时的状态
3. **已完成** (`success`): 流式输出完成后的状态
4. **错误** (`error`): 处理过程中发生错误时的状态

## 故障排查

如果AI卡片无法正常显示：

1. 检查模板ID是否正确
2. 确认应用已申请`Card.Streaming.Write`权限
3. 查看应用日志中的错误信息
4. 确认钉钉应用已正确配置回调URL

## 参考资料

- [钉钉开放平台文档](https://open.dingtalk.com/document/)
- [AI互动卡片开发指南](https://open.dingtalk.com/document/orgapp/ai-cards-design-guide) 