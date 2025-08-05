FROM python:3.9-slim

WORKDIR /app

# 更新系统并安装证书包和依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 更新CA证书
RUN update-ca-certificates

# 设置环境变量，允许不安全的SSL连接
ENV PYTHONHTTPSVERIFY=0
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"
ENV PYTHONPATH=/app

# 强制禁用SSL验证的环境变量（用于Python requests库）
ENV CURL_CA_BUNDLE=""
ENV CURL_SSL_VERIFY=0
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

# 升级pip
RUN pip install --upgrade pip

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pyOpenSSL ndg-httpsclient pyasn1 requests[security]

# 设置Python路径
ENV PYTHONPATH=/app

# 拷贝应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 启动命令
CMD ["python", "app.py"] 