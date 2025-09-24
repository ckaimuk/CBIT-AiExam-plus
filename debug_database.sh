#!/bin/bash

# ====================================
# 数据库问题诊断脚本
# ====================================

echo "======================================"
echo "🔍 CBIT AutoExam 数据库问题诊断"
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

# 1. 检查容器状态
log_info "1. 检查容器状态..."
CONTAINER_ID=$(docker ps -q -f name=cbit-autoexam)
if [ -z "$CONTAINER_ID" ]; then
    log_error "容器未运行！"
    exit 1
else
    log_success "容器正在运行: $CONTAINER_ID"
fi

# 2. 检查主机数据库文件
log_info "2. 检查主机数据库文件..."
if [ -f "instance/exam.db" ]; then
    DB_SIZE=$(du -h instance/exam.db | cut -f1)
    DB_PERMS=$(ls -la instance/exam.db)
    log_success "主机数据库文件存在"
    echo "   大小: $DB_SIZE"
    echo "   权限: $DB_PERMS"
else
    log_warning "主机数据库文件不存在"
fi

# 3. 检查容器内数据库文件
log_info "3. 检查容器内数据库文件..."
docker exec $CONTAINER_ID ls -la /app/instance/ 2>/dev/null || log_error "容器内instance目录不存在"
docker exec $CONTAINER_ID ls -la /app/instance/exam.db 2>/dev/null || log_warning "容器内数据库文件不存在"

# 4. 检查容器内环境变量
log_info "4. 检查容器内环境变量..."
echo "DATABASE_URL:"
docker exec $CONTAINER_ID printenv DATABASE_URL || log_error "DATABASE_URL未设置"
echo "FLASK_ENV:"
docker exec $CONTAINER_ID printenv FLASK_ENV || log_warning "FLASK_ENV未设置"

# 5. 检查容器内工作目录
log_info "5. 检查容器内工作目录..."
echo "当前工作目录:"
docker exec $CONTAINER_ID pwd
echo "工作目录内容:"
docker exec $CONTAINER_ID ls -la

# 6. 测试数据库连接
log_info "6. 测试Python数据库连接..."
docker exec $CONTAINER_ID python3 -c "
import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

# 模拟应用的数据库配置
def get_database_uri():
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    
    if os.getenv('FLASK_ENV') == 'production' or os.getenv('DEPLOYMENT') == 'server':
        instance_dir = os.path.join(os.getcwd(), 'instance')
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        instance_dir = os.path.join(project_root, 'instance')
    
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, 'exam.db')
    return f'sqlite:///{db_path}'

db_uri = get_database_uri()
print(f'计算出的数据库URI: {db_uri}')

# 检查文件是否存在
if 'sqlite:///' in db_uri:
    db_file = db_uri.replace('sqlite:///', '')
    print(f'数据库文件路径: {db_file}')
    if os.path.exists(db_file):
        print('✅ 数据库文件存在')
        print(f'文件大小: {os.path.getsize(db_file)} bytes')
        print(f'可读: {os.access(db_file, os.R_OK)}')
        print(f'可写: {os.access(db_file, os.W_OK)}')
    else:
        print('❌ 数据库文件不存在')
        print(f'目录存在: {os.path.exists(os.path.dirname(db_file))}')
        print(f'目录内容: {os.listdir(os.path.dirname(db_file)) if os.path.exists(os.path.dirname(db_file)) else \"目录不存在\"}')
"

# 7. 检查容器日志
log_info "7. 查看容器最近日志..."
echo "最近20条日志:"
docker logs $CONTAINER_ID --tail 20

# 8. 尝试在容器内创建数据库
log_info "8. 尝试在容器内创建数据库..."
docker exec $CONTAINER_ID bash -c "
cd /app
mkdir -p instance
touch instance/exam.db
chmod 666 instance/exam.db
echo '数据库文件创建完成'
ls -la instance/exam.db
"

# 9. 提供修复建议
echo ""
echo "======================================"
echo "🛠️ 修复建议"
echo "======================================"

if [ ! -f "instance/exam.db" ]; then
    log_warning "建议1: 在主机创建数据库文件"
    echo "mkdir -p instance"
    echo "touch instance/exam.db"
    echo "chmod 666 instance/exam.db"
fi

log_info "建议2: 重新启动容器并挂载数据库"
echo "docker stop cbit-autoexam"
echo "docker rm cbit-autoexam"
echo "# 然后重新运行部署脚本"

log_info "建议3: 使用绝对路径环境变量"
echo "export DATABASE_URL=sqlite:////app/instance/exam.db"

log_info "建议4: 检查容器内Python路径"
echo "docker exec cbit-autoexam python3 -c \"import sys; print(sys.path)\""

echo "======================================"
