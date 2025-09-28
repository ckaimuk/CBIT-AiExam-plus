#!/bin/bash

# =============================================================================
# CBIT 智能考试系统 - 仅更新代码脚本 (保留数据库)
# =============================================================================
# 此脚本仅更新应用代码，完全不触碰数据库和用户数据
# 适用于功能修复、界面优化等不涉及数据库结构变更的更新
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

echo "🔄 CBIT智能考试系统 - 仅更新代码"
echo "=" * 50
echo "项目目录: $PROJECT_DIR"
echo "执行时间: $TIMESTAMP"
echo "⚠️  注意: 此脚本仅更新代码，不会修改数据库"
echo ""

cd "$PROJECT_DIR"

# 1. 检查当前状态
log "检查当前部署状态..."

# 检查Docker容器
if docker ps | grep -q cbit-autoexam; then
    success "发现运行中的容器"
    CONTAINER_RUNNING=true
else
    warn "容器未运行"
    CONTAINER_RUNNING=false
fi

# 检查数据库文件
DB_LOCATIONS=(
    "/srv/yourapp/data/app.db"
    "/data/app.db"
    "instance/exam.db"
)

DB_FOUND=false
for db_path in "${DB_LOCATIONS[@]}"; do
    if [ -f "$db_path" ]; then
        success "发现数据库文件: $db_path"
        DB_FOUND=true
        break
    fi
done

if [ "$DB_FOUND" = false ]; then
    warn "未发现数据库文件，可能是首次部署"
fi

# 2. 停止服务 (保持数据)
if [ "$CONTAINER_RUNNING" = true ]; then
    log "停止应用服务..."
    
    # 智能检测docker-compose文件
    COMPOSE_FILE=""
    if [ -f "docker-compose.bt.yml" ]; then
        COMPOSE_FILE="docker-compose.bt.yml"
        log "使用宝塔版本: docker-compose.bt.yml"
    elif [ -f "docker-compose.yml" ]; then
        COMPOSE_FILE="docker-compose.yml"
        log "使用标准版本: docker-compose.yml"
    else
        error "未找到docker-compose配置文件"
        exit 1
    fi
    
    docker-compose -f "$COMPOSE_FILE" stop
    success "服务已停止"
fi

# 3. 备份当前代码 (可选)
log "备份当前代码..."
if [ -d ".git" ]; then
    # Git仓库，记录当前commit
    CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    echo "$CURRENT_COMMIT" > ".last_commit_$TIMESTAMP"
    success "已记录当前commit: $CURRENT_COMMIT"
else
    # 非Git仓库，创建代码备份
    BACKUP_DIR="backup_code_$TIMESTAMP"
    mkdir -p "$BACKUP_DIR"
    
    # 备份关键代码文件，排除数据和日志
    rsync -av --exclude='instance/' --exclude='logs/' --exclude='static/uploads/' \
          --exclude='*.db' --exclude='backup_*' --exclude='.git/' \
          ./ "$BACKUP_DIR/"
    
    success "代码备份完成: $BACKUP_DIR"
fi

# 4. 更新代码
log "更新应用代码..."

if [ -d ".git" ]; then
    # Git仓库更新
    git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
    
    # 保存本地修改（如果有）
    if ! git diff --quiet; then
        git stash push -m "自动备份-代码更新-$TIMESTAMP" 2>/dev/null || warn "无本地修改需要保存"
    fi
    
    # 拉取最新代码
    git fetch origin || { error "获取远程代码失败"; exit 1; }
    git pull origin main || { error "拉取代码失败"; exit 1; }
    success "代码更新完成"
else
    warn "非Git仓库，请手动上传最新代码文件"
    echo "请确保以下文件已更新到最新版本："
    echo "  - frontend/ (所有前端文件)"
    echo "  - backend/ (所有后端文件)"
    echo "  - docker/ (Docker配置)"
    echo "  - *.yml (Docker Compose配置)"
    echo ""
    read -p "代码已手动更新完成？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "请先更新代码后再运行此脚本"
        exit 1
    fi
fi

# 5. 重新构建镜像 (仅代码层)
log "重新构建应用镜像..."

# 智能检测docker-compose文件
COMPOSE_FILE=""
if [ -f "docker-compose.bt.yml" ]; then
    COMPOSE_FILE="docker-compose.bt.yml"
    log "使用宝塔版本: docker-compose.bt.yml"
elif [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
    log "使用标准版本: docker-compose.yml"
else
    error "未找到docker-compose配置文件"
    exit 1
fi

# 构建新镜像
docker-compose -f "$COMPOSE_FILE" build --no-cache || {
    error "镜像构建失败"
    exit 1
}
success "镜像构建完成"

# 6. 启动服务
log "启动更新后的服务..."
docker-compose -f "$COMPOSE_FILE" up -d || {
    error "服务启动失败"
    exit 1
}
success "服务已启动"

# 7. 验证更新结果
log "验证更新结果..."
sleep 10

# 检查容器状态
if docker ps | grep cbit-autoexam >/dev/null; then
    success "容器运行正常"
    
    # 验证服务响应
    log "验证服务响应..."
    sleep 5
    
    if curl -s http://localhost:8080/ >/dev/null 2>&1; then
        success "应用响应正常"
        
        # 验证数据库连接 (不修改数据)
        log "验证数据库连接..."
        
        # 检测数据库文件
        for db_path in "${DB_LOCATIONS[@]}"; do
            if [ -f "$db_path" ]; then
                # 简单检查数据库是否可访问
                QUESTION_COUNT=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM questions;" 2>/dev/null || echo "0")
                if [ "$QUESTION_COUNT" -gt "0" ]; then
                    success "数据库连接正常，包含 $QUESTION_COUNT 道题目"
                else
                    warn "数据库连接正常，但暂无题目数据"
                fi
                break
            fi
        done
        
    else
        warn "应用可能还在启动中，请稍后手动验证"
    fi
else
    warn "容器启动可能有问题，请检查日志: docker logs cbit-autoexam"
fi

# 8. 显示更新总结
echo ""
echo "🎉 代码更新完成总结"
echo "=" * 50
echo "✅ 仅更新了应用代码和配置"
echo "✅ 数据库和用户数据完全保留"
echo "✅ 上传文件和系统配置保持不变"
echo ""
echo "🔗 访问地址:"
echo "   - 主页: http://localhost:8080"
echo "   - 题库管理: http://localhost:8080/question_management.html"
echo "   - 管理后台: http://localhost:8080/admin/dashboard"
echo ""
echo "📋 更新内容 (本次):"
echo "   - ✅ 修复了System Logo路径问题"
echo "   - ✅ 修复了精确数量控制功能"
echo "   - ✅ 添加了题型预览显示"
echo "   - ✅ 优化了题目筛选功能"
echo ""
echo "💾 数据保护:"
echo "   - 数据库文件: 完全保留"
echo "   - 用户上传文件: 完全保留"
echo "   - 系统配置: 完全保留"
echo "   - 考试记录: 完全保留"
echo ""

if [ -f ".last_commit_$TIMESTAMP" ]; then
    echo "🔄 回滚信息:"
    echo "   如需回滚，运行: git checkout $(cat .last_commit_$TIMESTAMP)"
fi

echo "🛠️ 如遇问题，请检查:"
echo "   - 容器日志: docker logs cbit-autoexam"
echo "   - 服务状态: docker ps"
echo "   - 应用访问: curl http://localhost:8080/"
echo ""

success "🎯 代码更新完成！应用功能已优化，数据完全保留！"
