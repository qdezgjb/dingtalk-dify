FROM python:3.9-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONHTTPSVERIFY=0
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"
ENV PYTHONPATH=/app
ENV CURL_CA_BUNDLE=""
ENV CURL_SSL_VERIFY=0
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV TZ=Asia/Shanghai

# 更新系统并安装证书包和依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    curl \
    wget \
    tzdata \
    libmagic1 \
    file \
    && rm -rf /var/lib/apt/lists/*

# 更新CA证书
RUN update-ca-certificates

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 升级pip
RUN pip install --upgrade pip

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 设置权限
RUN chmod +x /app/app.py

# 健康检查 - 检查Python进程是否运行
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ps aux | grep "python app.py" | grep -v grep || exit 1

# 启动命令
CMD ["python", "app.py"] 