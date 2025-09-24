#!/bin/bash

# ====================================
# CBIT AutoExam 快速修复脚本
# 解决常见的部署问题
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
echo "🚀 CBIT AutoExam 快速修复"
echo "======================================"

# 检查当前目录
if [ ! -f "run.py" ]; then
    log_error "请在项目根目录下运行此脚本"
    log_info "正确的使用方式："
    log_info "cd /www/wwwroot/cbit-autoexam"
    log_info "./quick_fix.sh"
    exit 1
fi

PROJECT_DIR=$(pwd)
log_info "项目目录: $PROJECT_DIR"

# 步骤1：更新代码
log_info "📥 第1步：获取最新代码..."
if [ -d ".git" ]; then
    git pull origin main
    log_success "代码更新完成"
else
    log_warning "不是Git仓库，跳过代码更新"
fi

# 步骤2：停止现有容器
log_info "🛑 第2步：停止现有容器..."
CONTAINERS=$(docker ps -q -f name=cbit-autoexam)
if [ ! -z "$CONTAINERS" ]; then
    docker stop $CONTAINERS
    docker rm $CONTAINERS
    log_success "容器已停止并删除"
else
    log_info "没有运行中的容器"
fi

# 步骤3：重新构建镜像
log_info "🔨 第3步：重新构建Docker镜像..."
docker build -f docker/Dockerfile -t cbit-autoexam:latest .
if [ $? -eq 0 ]; then
    log_success "Docker镜像构建完成"
else
    log_error "Docker镜像构建失败"
    exit 1
fi

# 步骤4：创建必要目录
log_info "📁 第4步：创建必要目录..."
mkdir -p instance
mkdir -p logs
mkdir -p static/uploads
mkdir -p frontend/static/uploads
log_success "目录创建完成"

# 步骤5：初始化数据库
log_info "🗃️ 第5步：初始化数据库..."
if [ ! -f "instance/exam.db" ]; then
    log_info "创建新的数据库文件..."
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

# 步骤6：修复权限
log_info "🔧 第6步：修复文件权限..."

# 获取www用户ID
USER_ID=$(id -u www 2>/dev/null || echo "1000")
GROUP_ID=$(id -g www 2>/dev/null || echo "1000")

log_info "使用用户ID: $USER_ID, 组ID: $GROUP_ID"

# 设置基础权限
chown -R www:www "$PROJECT_DIR" 2>/dev/null || chown -R $USER_ID:$GROUP_ID "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"

# 特别设置数据库相关权限
chmod 755 instance
chmod 755 static/uploads
chmod 755 frontend/static/uploads
chmod +x *.sh

# 设置数据库文件权限
if [ -f "instance/exam.db" ]; then
    chmod 664 instance/exam.db
    chown www:www instance/exam.db 2>/dev/null || chown $USER_ID:$GROUP_ID instance/exam.db
fi

log_success "权限修复完成"

# 步骤7：启动新容器
log_info "🚀 第7步：启动新容器..."

SECRET_KEY="cbit-prod-secret-key-$(date +%s)"

# 尝试使用用户映射启动
docker run -d \
    --name cbit-autoexam \
    --restart unless-stopped \
    -p 8080:8080 \
    -e FLASK_ENV=production \
    -e SECRET_KEY="$SECRET_KEY" \
    -e DATABASE_URL=sqlite:///instance/exam.db \
    -e TZ=Asia/Shanghai \
    -u "$USER_ID:$GROUP_ID" \
    -v "$PROJECT_DIR/instance:/app/instance:rw" \
    -v "$PROJECT_DIR/static/uploads:/app/static/uploads:rw" \
    -v "$PROJECT_DIR/frontend/static/uploads:/app/frontend/static/uploads:rw" \
    -v "$PROJECT_DIR/logs:/app/logs:rw" \
    cbit-autoexam:latest

if [ $? -eq 0 ]; then
    log_success "容器启动成功（使用用户映射）"
else
    log_warning "用户映射启动失败，尝试默认方式..."
    
    # 备用方案：不指定用户ID
    docker run -d \
        --name cbit-autoexam \
        --restart unless-stopped \
        -p 8080:8080 \
        -e FLASK_ENV=production \
        -e SECRET_KEY="$SECRET_KEY" \
        -e DATABASE_URL=sqlite:///instance/exam.db \
        -e TZ=Asia/Shanghai \
        -v "$PROJECT_DIR/instance:/app/instance:rw" \
        -v "$PROJECT_DIR/static/uploads:/app/static/uploads:rw" \
        -v "$PROJECT_DIR/frontend/static/uploads:/app/frontend/static/uploads:rw" \
        -v "$PROJECT_DIR/logs:/app/logs:rw" \
        cbit-autoexam:latest
    
    if [ $? -eq 0 ]; then
        log_success "容器启动成功（默认方式）"
    else
        log_error "容器启动失败"
        exit 1
    fi
fi

# 步骤8：等待服务启动并验证
log_info "⏳ 第8步：等待服务启动..."
sleep 10

for i in {1..30}; do
    if curl -f http://localhost:8080 >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

# 最终验证
log_info "🔍 第9步：验证部署状态..."

# 检查容器状态
CONTAINER_STATUS=$(docker ps --format "{{.Status}}" -f name=cbit-autoexam)
if [ ! -z "$CONTAINER_STATUS" ]; then
    log_success "容器运行状态: $CONTAINER_STATUS"
else
    log_error "容器未运行"
fi

# 检查服务响应
if curl -f http://localhost:8080 >/dev/null 2>&1; then
    log_success "服务响应正常"
else
    log_warning "服务未响应，查看日志："
    docker logs cbit-autoexam --tail 10
fi

# 检查数据库文件
if [ -f "instance/exam.db" ] && [ -r "instance/exam.db" ] && [ -w "instance/exam.db" ]; then
    DB_SIZE=$(du -h instance/exam.db | cut -f1)
    log_success "数据库文件正常 (大小: $DB_SIZE)"
else
    log_warning "数据库文件权限可能有问题"
fi

echo ""
echo "======================================"
echo "🎉 快速修复完成！"
echo "======================================"
echo ""
echo "📊 部署信息："
echo "   容器名称: cbit-autoexam"
echo "   端口映射: 8080:8080"
echo "   数据库: sqlite:///instance/exam.db"
echo ""
echo "🌐 访问地址："
echo "   主页: http://localhost:8080"
echo "   管理后台: http://localhost:8080/admin/dashboard"
echo "   账号: admin / imbagogo"
echo ""
echo "🛠️ 维护命令："
echo "   查看状态: docker ps | grep cbit"
echo "   查看日志: docker logs cbit-autoexam"
echo "   重启容器: docker restart cbit-autoexam"
echo ""
echo "📞 如果仍有问题："
echo "   1. 查看容器日志: docker logs cbit-autoexam --tail 50"
echo "   2. 检查文件权限: ls -la instance/"
echo "   3. 运行完整修复: ./fix_database_permissions.sh"
echo ""
