#!/bin/bash

# ====================================
# 修复SQLite数据库权限问题脚本
# ====================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "======================================"
echo "🔧 修复SQLite数据库权限问题"
echo "======================================"

# 检查当前目录
if [ ! -f "run.py" ]; then
    log_error "请在项目根目录下运行此脚本"
    exit 1
fi

PROJECT_DIR=$(pwd)
log_info "项目目录: $PROJECT_DIR"

# 1. 停止容器（如果正在运行）
log_info "停止现有容器..."
if docker ps -q -f name=cbit-autoexam | grep -q .; then
    docker stop cbit-autoexam
    docker rm cbit-autoexam
    log_success "容器已停止"
else
    log_info "没有运行中的容器"
fi

# 2. 创建必要目录
log_info "创建必要目录..."
mkdir -p instance
mkdir -p logs
mkdir -p static/uploads
mkdir -p frontend/static/uploads

# 3. 初始化数据库文件
log_info "初始化数据库文件..."
if [ ! -f "instance/exam.db" ]; then
    log_info "创建新的数据库文件..."
    # 创建空数据库文件
    touch instance/exam.db
    
    # 使用Python初始化数据库
    PYTHONPATH=".:backend" python3 database/init_db.py
    
    if [ $? -eq 0 ]; then
        log_success "数据库初始化完成"
    else
        log_warning "数据库初始化遇到问题，但继续执行..."
    fi
else
    log_info "数据库文件已存在"
fi

# 4. 修复文件权限
log_info "修复文件权限..."

# 设置项目目录权限
chown -R www:www "$PROJECT_DIR" 2>/dev/null || chown -R 1000:1000 "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"

# 特别设置数据库相关权限
chmod 755 instance
chmod 664 instance/exam.db
chmod 755 static/uploads
chmod 755 frontend/static/uploads

# 确保数据库目录和文件有写权限
chown www:www instance/exam.db 2>/dev/null || chown 1000:1000 instance/exam.db
chown www:www instance/ 2>/dev/null || chown 1000:1000 instance/
chown -R www:www static/ 2>/dev/null || chown -R 1000:1000 static/
chown -R www:www frontend/static/ 2>/dev/null || chown -R 1000:1000 frontend/static/

log_success "权限修复完成"

# 5. 验证数据库文件
log_info "验证数据库文件..."
if [ -f "instance/exam.db" ] && [ -r "instance/exam.db" ] && [ -w "instance/exam.db" ]; then
    log_success "数据库文件权限正常"
    
    # 检查数据库内容
    if command -v sqlite3 &> /dev/null; then
        table_count=$(sqlite3 instance/exam.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
        log_info "数据库包含 $table_count 个表"
    fi
else
    log_error "数据库文件权限异常"
    ls -la instance/
fi

# 6. 更新Docker配置以确保正确的权限映射
log_info "检查Docker配置..."

# 创建带有正确用户ID的Docker运行命令
USER_ID=$(id -u www 2>/dev/null || echo "1000")
GROUP_ID=$(id -g www 2>/dev/null || echo "1000")

log_info "使用用户ID: $USER_ID, 组ID: $GROUP_ID"

# 7. 重新启动容器
log_info "重新启动容器..."

docker run -d \
    --name cbit-autoexam \
    --restart unless-stopped \
    -p 8080:8080 \
    -e FLASK_ENV=production \
    -e SECRET_KEY=cbit-prod-secret-key-$(date +%s) \
    -e DATABASE_URL=sqlite:///instance/exam.db \
    -e TZ=Asia/Shanghai \
    -u "$USER_ID:$GROUP_ID" \
    -v "$PROJECT_DIR/instance:/app/instance:rw" \
    -v "$PROJECT_DIR/static/uploads:/app/static/uploads:rw" \
    -v "$PROJECT_DIR/frontend/static/uploads:/app/frontend/static/uploads:rw" \
    -v "$PROJECT_DIR/logs:/app/logs:rw" \
    cbit-autoexam:latest

if [ $? -eq 0 ]; then
    log_success "容器启动成功"
else
    log_error "容器启动失败，尝试不使用用户映射..."
    
    # 备用方案：不指定用户ID
    docker run -d \
        --name cbit-autoexam-fallback \
        --restart unless-stopped \
        -p 8080:8080 \
        -e FLASK_ENV=production \
        -e SECRET_KEY=cbit-prod-secret-key-$(date +%s) \
        -e DATABASE_URL=sqlite:///instance/exam.db \
        -e TZ=Asia/Shanghai \
        -v "$PROJECT_DIR/instance:/app/instance:rw" \
        -v "$PROJECT_DIR/static/uploads:/app/static/uploads:rw" \
        -v "$PROJECT_DIR/frontend/static/uploads:/app/frontend/static/uploads:rw" \
        -v "$PROJECT_DIR/logs:/app/logs:rw" \
        cbit-autoexam:latest
fi

# 8. 等待服务启动并测试
log_info "等待服务启动..."
sleep 10

for i in {1..30}; do
    if curl -f http://localhost:8080 >/dev/null 2>&1; then
        log_success "服务启动成功！"
        echo ""
        echo "🎉 问题已修复！"
        echo ""
        echo "📊 验证信息:"
        echo "   - 数据库文件: $(ls -la instance/exam.db)"
        echo "   - 容器状态: $(docker ps --format 'table {{.Names}}\t{{.Status}}' | grep cbit)"
        echo ""
        echo "🌐 访问地址:"
        echo "   - 应用: http://localhost:8080"
        echo "   - 管理后台: http://localhost:8080/admin/dashboard"
        echo "   - 账号: admin / imbagogo"
        exit 0
    fi
    sleep 2
done

log_error "服务启动失败，请查看日志:"
echo "容器日志:"
docker logs cbit-autoexam --tail 20 2>/dev/null || docker logs cbit-autoexam-fallback --tail 20

echo ""
echo "🔧 手动排查步骤:"
echo "1. 检查容器状态: docker ps -a | grep cbit"
echo "2. 查看详细日志: docker logs cbit-autoexam"
echo "3. 进入容器调试: docker exec -it cbit-autoexam /bin/bash"
echo "4. 检查数据库: sqlite3 instance/exam.db '.tables'"
