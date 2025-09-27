#!/bin/bash

# 🚀 CBIT AutoExam 服务器升级脚本 v2.0
# 简洁版 - 解决Docker冲突和Git权限问题

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 全局变量
PROJECT_DIR="/www/wwwroot/cbit-autoexam"
BACKUP_DIR="/www/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================"
echo "🚀 CBIT AutoExam 升级脚本 v2.0"
echo "========================================"

# 检查环境
log "检查运行环境..."
[ ! -d "$PROJECT_DIR" ] && { error "项目目录不存在: $PROJECT_DIR"; exit 1; }
command -v docker >/dev/null || { error "Docker未安装"; exit 1; }
command -v git >/dev/null || { error "Git未安装"; exit 1; }
success "环境检查通过"

# 进入项目目录
cd "$PROJECT_DIR"

# 创建备份
log "创建备份..."
mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/cbit-autoexam-backup-$TIMESTAMP"
cp -r "$PROJECT_DIR" "$BACKUP_PATH"
[ -f "instance/exam.db" ] && cp "instance/exam.db" "$BACKUP_PATH/exam_$TIMESTAMP.db"
success "备份完成: $BACKUP_PATH"

# 强制停止和清理容器
log "停止服务并清理容器..."
docker ps -q --filter "name=cbit" | xargs -r docker stop 2>/dev/null || true
docker ps -aq --filter "name=cbit" | xargs -r docker rm -f 2>/dev/null || true

# 停止docker-compose
if [ -f "docker-compose.yml" ]; then
    docker-compose down --remove-orphans 2>/dev/null || warn "停止docker-compose失败"
elif [ -f "docker-compose.bt.yml" ]; then
    docker-compose -f docker-compose.bt.yml down --remove-orphans 2>/dev/null || warn "停止docker-compose失败"
fi

# 清理Docker资源
docker container prune -f 2>/dev/null || true
docker network prune -f 2>/dev/null || true
success "服务已停止"

# 修复Git权限并更新代码
log "更新代码..."
git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
git stash push -m "自动备份-$TIMESTAMP" 2>/dev/null || warn "无本地修改需要保存"
git fetch origin || { error "获取远程代码失败"; exit 1; }
git pull origin main || { error "拉取代码失败"; exit 1; }
success "代码更新完成"

# 运行数据库迁移
log "运行数据库迁移..."
[ -f "database/migrate_quantity_control.py" ] && {
    python3 database/migrate_quantity_control.py || error "精确数量控制迁移失败"
}
[ -f "database/normalize_tags.py" ] && {
    python3 database/normalize_tags.py || error "标签规范化失败"
}
success "数据库迁移完成"

# 启动服务
log "启动服务..."
COMPOSE_FILE="docker-compose.yml"
[ -f "docker-compose.bt.yml" ] && COMPOSE_FILE="docker-compose.bt.yml"

# 强制重新创建容器
docker-compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans || {
    error "服务启动失败"
    exit 1
}
success "服务已启动"

# 验证升级
log "验证升级结果..."
sleep 10

# 检查容器状态
if docker ps | grep cbit >/dev/null; then
    success "容器运行正常"
    
    # 验证数据库连接
    log "验证数据库连接..."
    sleep 5
    
    # 尝试访问API检查数据库
    if curl -s http://localhost:8080/api/system-config >/dev/null 2>&1; then
        success "应用API响应正常"
        
        # 检查数据库题目数量（如果可能）
        log "检查数据库完整性..."
        if [ -f "instance/exam.db" ]; then
            QUESTION_COUNT=$(sqlite3 instance/exam.db "SELECT COUNT(*) FROM questions;" 2>/dev/null || echo "0")
            if [ "$QUESTION_COUNT" -gt "0" ]; then
                success "数据库包含 $QUESTION_COUNT 道题目"
            else
                warn "数据库中暂无题目，请检查数据导入"
            fi
        fi
    else
        warn "应用可能还在启动中，请稍后手动验证"
    fi
else
    warn "容器启动可能有问题，请检查日志"
fi

# 清理旧备份 (保留5个)
log "清理旧备份..."
ls -1t "$BACKUP_DIR"/cbit-autoexam-backup-* 2>/dev/null | tail -n +6 | xargs -r rm -rf

echo "========================================"
success "🎉 升级完成!"
echo "========================================"
echo "🌐 访问地址: http://你的服务器IP:8080"
echo "📋 管理后台: http://你的服务器IP:8080/admin/dashboard"
echo "📝 备份位置: $BACKUP_PATH"
echo "========================================"
echo ""
echo "📖 如遇问题，回滚命令:"
echo "cd $PROJECT_DIR"
echo "docker-compose down"
echo "rm -rf * .* 2>/dev/null || true"
echo "cp -r $BACKUP_PATH/* ."
echo "docker-compose up -d"
echo "========================================"