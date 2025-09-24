#!/bin/bash

# ====================================
# CBIT AutoExam 完全重新部署脚本
# ====================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

echo "======================================"
echo "🚀 CBIT AutoExam 完全重新部署"
echo "======================================"

# 检查是否在正确的目录
if [ ! -f "run.py" ]; then
    log_error "请在项目根目录下运行此脚本"
    exit 1
fi

PROJECT_DIR=$(pwd)
log_info "项目目录: $PROJECT_DIR"

# 第一步：完全清理
log_step "第1步：完全清理现有环境"
log_info "停止并删除所有相关容器..."

# 停止所有可能的容器名称
docker stop cbit-autoexam 2>/dev/null || true
docker stop cbit-autoexam-fallback 2>/dev/null || true
docker stop cbit-exam 2>/dev/null || true

# 删除所有可能的容器
docker rm cbit-autoexam 2>/dev/null || true
docker rm cbit-autoexam-fallback 2>/dev/null || true
docker rm cbit-exam 2>/dev/null || true

# 删除旧镜像（可选）
log_info "清理旧镜像..."
docker rmi cbit-autoexam:latest 2>/dev/null || true
docker rmi cbit-autoexam:test 2>/dev/null || true

log_success "环境清理完成"

# 第二步：备份现有数据
log_step "第2步：备份现有数据"
if [ -d "instance" ]; then
    backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    cp -r instance "$backup_dir" 2>/dev/null || true
    log_info "数据已备份到: $backup_dir"
fi

# 第三步：重建目录结构
log_step "第3步：重建目录结构"
log_info "重建instance目录..."
rm -rf instance/
mkdir -p instance
mkdir -p static/uploads
mkdir -p frontend/static/uploads
mkdir -p logs

# 设置最宽松的权限
chmod 777 instance
chmod 777 static/uploads
chmod 777 frontend/static/uploads
chmod 777 logs

log_success "目录结构重建完成"

# 第四步：创建数据库文件
log_step "第4步：创建数据库文件"
log_info "创建exam.db文件..."
touch instance/exam.db

# 设置数据库文件最高权限
chmod 777 instance/exam.db
log_info "数据库文件权限: $(ls -la instance/exam.db)"

log_success "数据库文件创建完成"

# 第五步：更新Dockerfile以确保权限
log_step "第5步：更新Dockerfile配置"
cat > docker/Dockerfile << 'DOCKERFILE_EOF'
# 使用Python 3.11官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
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

# 复制现有数据库文件（如果存在）
COPY instance/ instance/ 2>/dev/null || true

# 确保数据库文件有最高权限
RUN if [ -f instance/exam.db ]; then chmod 777 instance/exam.db; fi

# 设置脚本权限
RUN chmod +x run.py && chmod +x docker_run.py

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || curl -f http://localhost:8080/ || exit 1

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "docker_run:app"]
DOCKERFILE_EOF

log_success "Dockerfile更新完成"

# 第六步：构建新镜像
log_step "第6步：构建Docker镜像"
log_info "构建镜像中，这可能需要几分钟..."

docker build -f docker/Dockerfile -t cbit-autoexam:latest . --no-cache

if [ $? -eq 0 ]; then
    log_success "Docker镜像构建成功"
else
    log_error "Docker镜像构建失败"
    exit 1
fi

# 第七步：启动容器（最高权限模式）
log_step "第7步：启动容器（最高权限模式）"
log_info "使用最高权限启动容器..."

docker run -d \
    --name cbit-autoexam \
    --restart unless-stopped \
    -p 8080:8080 \
    -e FLASK_ENV=production \
    -e SECRET_KEY="cbit-prod-secret-key-$(date +%s)" \
    -e DATABASE_URL=sqlite:///instance/exam.db \
    -e TZ=Asia/Shanghai \
    --privileged \
    --user root \
    -v "$PROJECT_DIR/instance:/app/instance:rw" \
    -v "$PROJECT_DIR/static:/app/static:rw" \
    -v "$PROJECT_DIR/frontend/static:/app/frontend/static:rw" \
    -v "$PROJECT_DIR/logs:/app/logs:rw" \
    cbit-autoexam:latest

if [ $? -eq 0 ]; then
    log_success "容器启动成功"
else
    log_error "容器启动失败"
    exit 1
fi

# 第八步：容器内权限设置
log_step "第8步：容器内权限设置"
log_info "等待容器启动..."
sleep 10

# 在容器内设置最高权限
docker exec cbit-autoexam chmod 777 /app/instance
docker exec cbit-autoexam chmod 777 /app/instance/exam.db 2>/dev/null || true
docker exec cbit-autoexam chmod 777 /app/static/uploads
docker exec cbit-autoexam chmod 777 /app/frontend/static/uploads
docker exec cbit-autoexam chmod 777 /app/logs

log_success "容器内权限设置完成"

# 第九步：初始化数据库
log_step "第9步：初始化数据库"
log_info "在容器内初始化数据库..."

docker exec cbit-autoexam python3 database/init_db.py

if [ $? -eq 0 ]; then
    log_success "数据库初始化成功"
else
    log_warning "数据库初始化失败，尝试手动创建..."
    
    # 手动创建基础表结构
    docker exec cbit-autoexam sqlite3 /app/instance/exam.db << 'SQL'
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    id_number VARCHAR(18) UNIQUE NOT NULL,
    application_number VARCHAR(50) UNIQUE NOT NULL,
    device_ip VARCHAR(45),
    device_id VARCHAR(50),
    has_taken_exam BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    total_questions INTEGER DEFAULT 5,
    time_limit INTEGER DEFAULT 75,
    subject_filter TEXT,
    difficulty_filter TEXT,
    type_filter TEXT,
    is_default BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO exam_config (name, description, total_questions, time_limit, subject_filter, difficulty_filter, type_filter, is_default, is_active)
VALUES ('默认配置', '系统默认考试配置', 5, 75, '数学,英语,计算机', '简单,中等,困难', 'multiple_choice,short_answer', 1, 1);
SQL

    log_info "基础表结构创建完成"
fi

# 再次确保数据库权限
docker exec cbit-autoexam chmod 777 /app/instance/exam.db

# 第十步：验证部署
log_step "第10步：验证部署"
log_info "等待服务完全启动..."
sleep 15

# 检查容器状态
log_info "检查容器状态..."
if docker ps | grep -q cbit-autoexam; then
    log_success "容器运行正常"
else
    log_error "容器未运行"
    docker logs cbit-autoexam --tail 20
    exit 1
fi

# 检查服务响应
log_info "检查服务响应..."
for i in {1..30}; do
    if curl -f http://localhost:8080 >/dev/null 2>&1; then
        log_success "服务响应正常"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        log_error "服务启动超时"
        docker logs cbit-autoexam --tail 20
        exit 1
    fi
done

# 检查API端点
log_info "检查API端点..."
if curl -f http://localhost:8080/api/questions >/dev/null 2>&1; then
    log_success "API端点正常"
else
    log_warning "API可能有问题，查看详细日志"
fi

# 最终状态检查
log_step "最终状态检查"
echo ""
echo "=== 容器信息 ==="
docker ps | grep cbit-autoexam

echo ""
echo "=== 数据库文件状态 ==="
ls -la instance/exam.db

echo ""
echo "=== 容器内数据库状态 ==="
docker exec cbit-autoexam ls -la /app/instance/exam.db

echo ""
echo "=== 数据库表检查 ==="
docker exec cbit-autoexam sqlite3 /app/instance/exam.db ".tables" || echo "数据库可能为空"

echo ""
echo "======================================"
echo "🎉 部署完成！"
echo "======================================"
echo ""
echo "✅ 访问地址: http://localhost:8080"
echo "✅ 管理后台: http://localhost:8080/admin/dashboard"
echo "✅ 管理员账号: admin / imbagogo"
echo ""
echo "📋 容器管理命令:"
echo "   查看日志: docker logs cbit-autoexam"
echo "   进入容器: docker exec -it cbit-autoexam bash"
echo "   重启容器: docker restart cbit-autoexam"
echo "   停止容器: docker stop cbit-autoexam"
echo ""
echo "🔧 如果仍有问题，数据库文件现在有最高权限(777)，应该可以正常访问"
echo "======================================"
