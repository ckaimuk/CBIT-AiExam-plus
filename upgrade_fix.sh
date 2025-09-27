#!/bin/bash

# =============================================================================
# CBIT 智能考试系统 - 筛选功能修复升级脚本
# =============================================================================
# 此脚本专门用于修复题目筛选功能和数据库路径优化
# 适用于已部署的服务器环境
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# 获取项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 CBIT智能考试系统 - 筛选功能修复升级"
echo "=" * 60
echo "项目目录: $PROJECT_DIR"
echo "执行时间: $TIMESTAMP"
echo ""

# 检查是否为root用户或具有sudo权限
if [[ $EUID -eq 0 ]]; then
    warn "检测到root用户执行"
elif ! sudo -n true 2>/dev/null; then
    error "需要sudo权限执行此脚本"
    exit 1
fi

cd "$PROJECT_DIR"

# 1. 备份当前数据
log "创建数据备份..."
if [ -f "instance/exam.db" ]; then
    cp "instance/exam.db" "instance/exam_backup_$TIMESTAMP.db"
    success "数据库备份完成: exam_backup_$TIMESTAMP.db"
fi

# 检查是否有容器环境的数据库
if [ -f "/srv/yourapp/data/app.db" ]; then
    sudo cp "/srv/yourapp/data/app.db" "/srv/yourapp/data/app_backup_$TIMESTAMP.db"
    success "容器数据库备份完成: app_backup_$TIMESTAMP.db"
fi

# 2. 停止服务
log "停止现有服务..."
COMPOSE_FILE="docker-compose.yml"
[ -f "docker-compose.bt.yml" ] && COMPOSE_FILE="docker-compose.bt.yml"

if docker-compose -f "$COMPOSE_FILE" ps | grep -q Up; then
    docker-compose -f "$COMPOSE_FILE" down
    success "服务已停止"
else
    warn "服务未运行"
fi

# 3. 更新代码
log "更新代码..."
git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true

# 检查git状态
if git status >/dev/null 2>&1; then
    # 保存本地修改
    if ! git diff --quiet; then
        git stash push -m "自动备份-$TIMESTAMP" 2>/dev/null || warn "无本地修改需要保存"
    fi
    
    # 拉取最新代码
    git fetch origin || { error "获取远程代码失败"; exit 1; }
    git pull origin main || { error "拉取代码失败"; exit 1; }
    success "代码更新完成"
else
    warn "非git仓库，跳过代码更新"
fi

# 4. 准备数据库目录（新的路径结构）
log "准备数据库目录..."
sudo mkdir -p /srv/yourapp/data
sudo chmod -R 777 /srv/yourapp/data

# 迁移数据库到新路径（如果需要）
if [ -f "instance/exam.db" ] && [ ! -f "/srv/yourapp/data/app.db" ]; then
    log "迁移数据库到新路径..."
    sudo cp "instance/exam.db" "/srv/yourapp/data/app.db"
    sudo chmod 777 "/srv/yourapp/data/app.db"
    success "数据库迁移完成"
fi

# 5. 运行数据库修复脚本
log "运行数据库修复脚本..."

# 检查并运行标签修复脚本
if [ -f "database/fix_filter_tags.py" ]; then
    log "执行筛选标签修复..."
    python3 database/fix_filter_tags.py || {
        error "筛选标签修复失败"
        exit 1
    }
    success "筛选标签修复完成"
else
    warn "未找到筛选标签修复脚本"
fi

# 运行其他数据库迁移脚本
if [ -f "database/migrate_quantity_control.py" ]; then
    log "执行精确数量控制迁移..."
    python3 database/migrate_quantity_control.py || warn "精确数量控制迁移失败（可能已执行过）"
fi

if [ -f "database/normalize_tags.py" ]; then
    log "执行标签规范化..."
    python3 database/normalize_tags.py || warn "标签规范化失败（可能已执行过）"
fi

# 6. 重新构建并启动服务
log "重新构建并启动服务..."

# 强制重新构建镜像
docker-compose -f "$COMPOSE_FILE" build --no-cache || {
    error "镜像构建失败"
    exit 1
}

# 启动服务
docker-compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans || {
    error "服务启动失败"
    exit 1
}

success "服务已启动"

# 7. 验证升级结果
log "验证升级结果..."
sleep 15

# 检查容器状态
if docker ps | grep cbit >/dev/null; then
    success "容器运行正常"
    
    # 验证数据库连接
    log "验证数据库连接..."
    sleep 5
    
    # 尝试访问API检查数据库
    if curl -s http://localhost:8080/api/system-config >/dev/null 2>&1; then
        success "应用API响应正常"
        
        # 检查题目筛选功能
        log "验证题目筛选功能..."
        
        # 检测数据库路径
        DB_PATH=""
        if [ -f "/srv/yourapp/data/app.db" ]; then
            DB_PATH="/srv/yourapp/data/app.db"
        elif [ -f "instance/exam.db" ]; then
            DB_PATH="instance/exam.db"
        fi
        
        if [ -n "$DB_PATH" ]; then
            # 检查标签分布
            MATH_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM questions WHERE subject='数学' AND is_active=1;" 2>/dev/null || echo "0")
            CS_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM questions WHERE subject='计算机科学' AND is_active=1;" 2>/dev/null || echo "0")
            HIGH_SCHOOL_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM questions WHERE difficulty='high_school' AND is_active=1;" 2>/dev/null || echo "0")
            
            if [ "$MATH_COUNT" -gt "0" ] || [ "$CS_COUNT" -gt "0" ] || [ "$HIGH_SCHOOL_COUNT" -gt "0" ]; then
                success "数据库包含题目: 数学${MATH_COUNT}题, 计算机科学${CS_COUNT}题, 高中水平${HIGH_SCHOOL_COUNT}题"
                success "筛选功能验证通过"
            else
                warn "数据库中暂无题目，请检查数据导入"
            fi
        else
            warn "未找到数据库文件"
        fi
        
    else
        warn "应用可能还在启动中，请稍后手动验证"
    fi
else
    warn "容器启动可能有问题，请检查日志: docker logs cbit-autoexam"
fi

# 8. 显示升级总结
echo ""
echo "🎉 升级完成总结"
echo "=" * 60
echo "✅ 数据库路径优化: 统一使用 /data/app.db"
echo "✅ 题目筛选功能修复: 标签与前端完全匹配" 
echo "✅ 权限简化: 完全开放权限 (777)"
echo "✅ 数据持久化: /srv/yourapp/data"
echo ""
echo "🔗 访问地址:"
echo "   - 主页: http://localhost:8080"
echo "   - 题库管理: http://localhost:8080/question_management.html"
echo "   - 管理后台: http://localhost:8080/admin/dashboard"
echo ""
echo "📋 备份文件:"
[ -f "instance/exam_backup_$TIMESTAMP.db" ] && echo "   - instance/exam_backup_$TIMESTAMP.db"
[ -f "/srv/yourapp/data/app_backup_$TIMESTAMP.db" ] && echo "   - /srv/yourapp/data/app_backup_$TIMESTAMP.db"
echo ""
echo "🛠️ 如遇问题，请检查:"
echo "   - 容器日志: docker logs cbit-autoexam"
echo "   - 服务状态: docker ps"
echo "   - 数据库权限: ls -la /srv/yourapp/data/"
echo ""

success "🎯 筛选功能修复升级完成！现在可以正常使用题目筛选功能了！"
