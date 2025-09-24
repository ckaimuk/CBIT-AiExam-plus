#!/bin/bash

# ====================================
# 数据库路径问题专用修复脚本
# ====================================

set -e

echo "======================================"
echo "🔧 修复数据库路径问题"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR=$(pwd)
log_info "项目目录: $PROJECT_DIR"

# 1. 停止现有容器
log_info "1. 停止现有容器..."
docker stop cbit-autoexam 2>/dev/null || true
docker rm cbit-autoexam 2>/dev/null || true

# 2. 确保主机目录和文件存在
log_info "2. 创建主机数据库目录和文件..."
mkdir -p "$PROJECT_DIR/instance"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/static/uploads"

# 如果数据库文件不存在，创建一个
if [ ! -f "$PROJECT_DIR/instance/exam.db" ]; then
    log_info "创建新的数据库文件..."
    touch "$PROJECT_DIR/instance/exam.db"
fi

# 设置正确的权限
chmod 755 "$PROJECT_DIR/instance"
chmod 666 "$PROJECT_DIR/instance/exam.db"
log_success "目录和文件创建完成"

# 3. 启动容器，使用绝对路径映射
log_info "3. 启动容器（使用绝对路径）..."

SECRET_KEY="cbit-prod-secret-key-$(date +%s)"

docker run -d \
    --name cbit-autoexam \
    --restart unless-stopped \
    -p 8080:8080 \
    -e FLASK_ENV=production \
    -e DEPLOYMENT=server \
    -e SECRET_KEY="$SECRET_KEY" \
    -e DATABASE_URL="sqlite:////app/instance/exam.db" \
    -e TZ=Asia/Shanghai \
    -v "$PROJECT_DIR/instance:/app/instance:rw" \
    -v "$PROJECT_DIR/static/uploads:/app/static/uploads:rw" \
    -v "$PROJECT_DIR/logs:/app/logs:rw" \
    --workdir /app \
    cbit-autoexam:latest

if [ $? -ne 0 ]; then
    log_error "容器启动失败"
    exit 1
fi

log_success "容器启动成功"

# 4. 等待容器启动
log_info "4. 等待容器初始化..."
sleep 10

# 5. 在容器内初始化数据库
log_info "5. 在容器内初始化数据库..."
docker exec cbit-autoexam bash -c "
cd /app
echo '当前工作目录:' \$(pwd)
echo '环境变量 DATABASE_URL:' \$DATABASE_URL
echo '目录内容:'
ls -la
echo 'instance目录内容:'
ls -la instance/ 2>/dev/null || echo 'instance目录不存在'

# 确保数据库文件存在
if [ ! -f '/app/instance/exam.db' ]; then
    echo '在容器内创建数据库文件...'
    mkdir -p /app/instance
    touch /app/instance/exam.db
    chmod 666 /app/instance/exam.db
fi

echo '数据库文件状态:'
ls -la /app/instance/exam.db

# 尝试初始化数据库
echo '初始化数据库...'
PYTHONPATH='/app:/app/backend' python3 database/init_db.py || {
    echo '使用Flask应用初始化数据库...'
    PYTHONPATH='/app:/app/backend' python3 -c \"
from backend.app import app, db
with app.app_context():
    db.create_all()
    print('数据库表创建完成')
\"
}
"

# 6. 验证数据库
log_info "6. 验证数据库连接..."
docker exec cbit-autoexam python3 -c "
import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

try:
    from backend.app import app, db
    with app.app_context():
        # 测试数据库连接
        result = db.engine.execute('SELECT 1').fetchone()
        if result:
            print('✅ 数据库连接成功')
        else:
            print('❌ 数据库连接失败')
except Exception as e:
    print(f'❌ 数据库连接错误: {e}')
    # 输出更多调试信息
    print(f'DATABASE_URL: {os.getenv(\"DATABASE_URL\")}')
    print(f'当前目录: {os.getcwd()}')
    print(f'instance目录存在: {os.path.exists(\"/app/instance\")}')
    print(f'数据库文件存在: {os.path.exists(\"/app/instance/exam.db\")}')
"

# 7. 等待服务启动
log_info "7. 等待服务启动..."
for i in {1..30}; do
    if curl -f http://localhost:8080 >/dev/null 2>&1; then
        log_success "服务启动成功！"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        log_error "服务启动超时，查看日志："
        docker logs cbit-autoexam --tail 20
        exit 1
    fi
done

# 8. 最终验证
log_info "8. 最终验证..."
echo ""
echo "=== 容器状态 ==="
docker ps | grep cbit-autoexam

echo ""
echo "=== 主机数据库文件 ==="
ls -la "$PROJECT_DIR/instance/exam.db"

echo ""
echo "=== 容器内数据库文件 ==="
docker exec cbit-autoexam ls -la /app/instance/exam.db

echo ""
echo "=== 服务测试 ==="
if curl -f http://localhost:8080 >/dev/null 2>&1; then
    log_success "✅ 服务正常运行"
else
    log_warning "⚠️ 服务可能有问题"
fi

echo ""
echo "======================================"
echo "🎉 数据库路径修复完成！"
echo "======================================"
echo ""
echo "🌐 访问地址: http://localhost:8080"
echo "📋 管理后台: http://localhost:8080/admin/dashboard"
echo ""
echo "🔍 如果仍有问题，请运行: ./debug_database.sh"
echo "======================================"
