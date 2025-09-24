#!/bin/bash

# ====================================
# CBIT AutoExam 最简单部署脚本
# ====================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "======================================"
echo "🚀 CBIT AutoExam 最简单部署"
echo "======================================"

# 检查当前目录
if [ ! -f "run.py" ]; then
    log_error "请在项目根目录下运行此脚本"
    exit 1
fi

PROJECT_DIR=$(pwd)
log_info "项目目录: $PROJECT_DIR"

# 第1步：停止旧容器
log_info "步骤1: 停止旧容器..."
docker stop cbit-autoexam 2>/dev/null || true
docker rm cbit-autoexam 2>/dev/null || true
log_success "旧容器已清理"

# 第2步：备份现有数据库
log_info "步骤2: 备份现有数据库..."
if [ -f "instance/exam.db" ]; then
    cp instance/exam.db "instance/exam.db.backup.$(date +%s)" 2>/dev/null || true
    log_info "数据库已备份"
else
    log_info "未发现现有数据库文件"
fi

# 第3步：确保目录存在
log_info "步骤3: 确保目录结构..."
mkdir -p instance
mkdir -p static/uploads
mkdir -p frontend/static/uploads
mkdir -p logs

# 第4步：构建镜像
log_info "步骤4: 构建Docker镜像..."
docker build -f docker/Dockerfile -t cbit-autoexam:latest .
if [ $? -ne 0 ]; then
    log_error "Docker镜像构建失败"
    exit 1
fi
log_success "Docker镜像构建完成"

# 第5步：启动容器（保留现有数据库）
log_info "步骤5: 启动容器..."
docker run -d \
    --name cbit-autoexam \
    --restart unless-stopped \
    -p 8080:8080 \
    -e FLASK_ENV=production \
    -e SECRET_KEY="cbit-prod-secret-key-$(date +%s)" \
    -e DATABASE_URL=sqlite:///instance/exam.db \
    -e TZ=Asia/Shanghai \
    --privileged \
    -v "$PROJECT_DIR/instance:/app/instance:rw" \
    -v "$PROJECT_DIR/static:/app/static:rw" \
    -v "$PROJECT_DIR/frontend/static:/app/frontend/static:rw" \
    -v "$PROJECT_DIR/logs:/app/logs:rw" \
    cbit-autoexam:latest

if [ $? -ne 0 ]; then
    log_error "容器启动失败"
    exit 1
fi
log_success "容器启动成功"

# 第6步：等待服务启动
log_info "步骤6: 等待服务启动..."
sleep 15

# 第7步：检查是否需要初始化数据库
log_info "步骤7: 检查数据库状态..."
if [ ! -f "instance/exam.db" ] || [ ! -s "instance/exam.db" ]; then
    log_info "数据库文件不存在或为空，正在初始化..."
    
    # 在容器内创建空数据库文件
    docker exec cbit-autoexam touch /app/instance/exam.db
    docker exec cbit-autoexam chmod 666 /app/instance/exam.db
    
    # 尝试初始化数据库
    docker exec cbit-autoexam python3 database/init_db.py || {
        log_error "数据库初始化失败，尝试手动创建基础表..."
        
        # 手动创建基础表
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
    }
else
    log_info "使用现有数据库文件"
fi

# 第8步：验证部署
log_info "步骤8: 验证部署..."
for i in {1..30}; do
    if curl -f http://localhost:8080 >/dev/null 2>&1; then
        log_success "服务启动成功！"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        log_error "服务启动超时"
        echo "容器日志："
        docker logs cbit-autoexam --tail 20
        exit 1
    fi
done

# 第9步：最终检查
log_info "步骤9: 最终检查..."
echo ""
echo "=== 容器状态 ==="
docker ps | grep cbit-autoexam

echo ""
echo "=== 数据库文件 ==="
ls -la instance/exam.db 2>/dev/null || echo "数据库文件不在主机上（这是正常的）"

echo ""
echo "=== 容器内数据库 ==="
docker exec cbit-autoexam ls -la /app/instance/exam.db

echo ""
echo "======================================"
echo "🎉 部署完成！"
echo "======================================"
echo ""
echo "✅ 访问地址: http://localhost:8080"
echo "✅ 管理后台: http://localhost:8080/admin/dashboard"  
echo "✅ 管理员账号: admin / imbagogo"
echo ""
echo "📋 常用命令:"
echo "   查看日志: docker logs cbit-autoexam"
echo "   进入容器: docker exec -it cbit-autoexam bash"
echo "   重启服务: docker restart cbit-autoexam"
echo "   停止服务: docker stop cbit-autoexam"
echo ""
echo "🔍 如果遇到问题，请查看容器日志进行排查"
echo "======================================"
