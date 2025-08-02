# 安装指南

## 环境要求

- Python 3.8+
- pip 包管理工具
- 钉钉企业账号和应用
- Dify API密钥

## 本地安装

1. 克隆仓库
```bash
git clone https://github.com/qdezgjb/dingtalk-dify.git
cd dingtalk-dify
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置
复制环境变量示例文件并编辑：
```bash
cp env.example .env
```

编辑`.env`文件或`config.json`，填入您的钉钉和Dify配置信息。

4. 运行
```bash
python app.py
```

## Docker安装

1. 使用docker-compose运行
```bash
docker-compose up -d
```

2. 查看日志
```bash
docker-compose logs -f
```

## 获取必要配置

### 钉钉配置

1. 创建钉钉企业内部应用
2. 开通机器人功能
3. 从应用信息页面获取ClientID和ClientSecret
4. 开启Stream模式

### Dify配置

1. 在Dify平台创建应用
2. 获取API密钥
3. 选择应用类型（chat或completion）

## 验证安装

发送消息到您的钉钉机器人，确认是否正常回复。 