# 使用Python 3.11官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
# SECRET_KEY 应该在运行时通过环境变量设置
# ENV SECRET_KEY 将在运行时设置
ENV DATABASE_URL=sqlite:///instance/exam.db

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录并设置最高权限
RUN mkdir -p instance && \
    mkdir -p frontend/static/uploads && \
    mkdir -p static/uploads && \
    mkdir -p logs && \
    chmod 777 instance && \
    chmod 777 frontend/static/uploads && \
    chmod 777 static/uploads && \
    chmod 777 logs

# 确保数据库文件有最高权限（如果存在）
RUN if [ -f instance/exam.db ]; then chmod 777 instance/exam.db; fi

# 设置脚本权限
RUN chmod +x run.py && chmod +x docker_run.py

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || curl -f http://localhost:8080/ || exit 1

# 启动命令 - 使用gunicorn在生产环境
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "docker_run:app"]