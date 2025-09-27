#!/bin/bash

# 🚀 CBIT AutoExam 服务器升级脚本 v1.0
# 适用于宝塔面板Docker部署环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 全局变量
PROJECT_DIR="/www/wwwroot/cbit-autoexam"
BACKUP_DIR="/www/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 检查环境
check_environment() {
    log_info "检查运行环境..."
    
    # 检查项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        log_info "请确认你在正确的服务器上运行此脚本"
        exit 1
    fi
    
    # 检查必要工具
    command -v docker >/dev/null || { log_error "Docker未安装"; exit 1; }
    command -v docker-compose >/dev/null || { log_error "docker-compose未安装"; exit 1; }
    command -v git >/dev/null || { log_error "Git未安装"; exit 1; }
    command -v python3 >/dev/null || { log_error "Python3未安装"; exit 1; }
    
    log_success "环境检查通过"
}

# 创建备份
create_backup() {
    log_info "创建系统备份..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_PATH="$BACKUP_DIR/cbit-autoexam-backup-$TIMESTAMP"
    
    log_info "备份项目文件到: $BACKUP_PATH"
    cp -r "$PROJECT_DIR" "$BACKUP_PATH"
    
    cd "$PROJECT_DIR"
    
    # 备份SQLite数据库
    if [ -f "instance/exam.db" ]; then
        log_info "备份SQLite数据库..."
        cp "instance/exam.db" "$BACKUP_PATH/exam_$TIMESTAMP.db"
    fi
    
    # 备份重要目录
    if [ -d "static/uploads" ]; then
        log_info "备份上传文件..."
        cp -r "static/uploads" "$BACKUP_PATH/uploads_backup"
    fi
    
    log_success "备份完成: $BACKUP_PATH"
}

# 停止服务
stop_services() {
    log_info "停止当前服务..."
    cd "$PROJECT_DIR"
    
    # 检查并停止Docker服务
    if [ -f "docker-compose.yml" ]; then
        docker-compose down || log_warning "停止docker-compose服务失败"
    elif [ -f "docker-compose.bt.yml" ]; then
        docker-compose -f docker-compose.bt.yml down || log_warning "停止docker-compose服务失败"
    else
        log_warning "未找到docker-compose文件"
    fi
    
    log_success "服务已停止"
}

# 更新代码
update_code() {
    log_info "更新项目代码..."
    cd "$PROJECT_DIR"
    
    # 检查Git仓库
    if [ ! -d ".git" ]; then
        log_error "这不是一个Git仓库，无法自动更新"
        log_info "请手动克隆最新代码或联系管理员"
        exit 1
    fi
    
    # 保存本地修改（如果有）
    git stash push -m "自动备份本地修改 - $TIMESTAMP" 2>/dev/null || log_warning "没有本地修改需要保存"
    
    # 获取最新代码
    log_info "拉取最新代码..."
    git fetch origin || { log_error "获取远程代码失败"; exit 1; }
    git pull origin main || { log_error "拉取代码失败"; exit 1; }
    
    log_success "代码更新完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    cd "$PROJECT_DIR"
    
    # 运行精确数量控制迁移
    if [ -f "database/migrate_quantity_control.py" ]; then
        log_info "运行精确数量控制功能迁移..."
        python3 database/migrate_quantity_control.py || { 
            log_error "精确数量控制迁移失败"
            exit 1 
        }
    else
        log_warning "未找到精确数量控制迁移脚本"
    fi
    
    # 运行标签规范化
    if [ -f "database/normalize_tags.py" ]; then
        log_info "运行标签规范化..."
        python3 database/normalize_tags.py || { 
            log_error "标签规范化失败"
            exit 1 
        }
    else
        log_warning "未找到标签规范化脚本"
    fi
    
    log_success "数据库迁移完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    cd "$PROJECT_DIR"
    
    # 选择合适的docker-compose文件
    COMPOSE_FILE="docker-compose.yml"
    if [ -f "docker-compose.bt.yml" ]; then
        COMPOSE_FILE="docker-compose.bt.yml"
        log_info "使用宝塔配置文件: $COMPOSE_FILE"
    else
        log_info "使用标准配置文件: $COMPOSE_FILE"
    fi
    
    # 重新构建镜像（确保包含最新代码）
    log_info "重新构建Docker镜像..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache || log_warning "镜像构建失败，尝试直接启动"
    
    # 启动服务
    log_info "启动Docker容器..."
    docker-compose -f "$COMPOSE_FILE" up -d || {
        log_error "服务启动失败"
        log_info "请检查docker-compose配置文件"
        exit 1
    }
    
    log_success "服务已启动"
}

# 验证升级
verify_upgrade() {
    log_info "验证升级结果..."
    
    # 等待服务启动
    log_info "等待服务完全启动..."
    sleep 15
    
    cd "$PROJECT_DIR"
    COMPOSE_FILE="docker-compose.yml"
    [ -f "docker-compose.bt.yml" ] && COMPOSE_FILE="docker-compose.bt.yml"
    
    # 检查容器状态
    log_info "检查容器状态:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    # 检查应用是否可访问
    log_info "检查应用访问..."
    local retries=3
    local count=0
    
    while [ $count -lt $retries ]; do
        if curl -s -f http://localhost:8080/ >/dev/null 2>&1; then
            log_success "✅ 应用访问正常"
            break
        else
            count=$((count + 1))
            if [ $count -lt $retries ]; then
                log_info "尝试 $count/$retries 失败，等待重试..."
                sleep 10
            else
                log_warning "⚠️  应用可能还在启动中，请稍后手动检查"
            fi
        fi
    done
    
    # 显示最近日志
    log_info "最近的应用日志:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=10 app 2>/dev/null || echo "无法获取应用日志"
}

# 清理旧备份（保留最近5个）
cleanup_old_backups() {
    log_info "清理旧备份..."
    
    if [ -d "$BACKUP_DIR" ]; then
        # 保留最近5个备份，删除其他的
        ls -1t "$BACKUP_DIR"/cbit-autoexam-backup-* 2>/dev/null | tail -n +6 | xargs -r rm -rf
        log_success "旧备份清理完成"
    fi
}

# 显示升级后信息
show_post_upgrade_info() {
    echo ""
    echo "========================================"
    log_success "🎉 升级完成！"
    echo "========================================"
    echo "📝 备份位置: $BACKUP_PATH"
    echo "🌐 访问地址: http://你的服务器IP:8080"
    echo "📋 管理后台: http://你的服务器IP:8080/admin/dashboard"
    echo "👤 管理员账号: admin / imbagogo"
    echo ""
    echo "✨ 新功能："
    echo "  🎯 精确数量控制 - 可精确设置每种题型的数量"
    echo "  🏷️  统一标签体系 - 修复题目筛选匹配问题"
    echo "  🎨 全新UI设计 - 独立模态窗口，更清爽的界面"
    echo "  🌐 完整多语言 - 中英文界面支持"
    echo "========================================"
    echo ""
    log_info "测试新功能："
    echo "1. 登录管理后台"
    echo "2. 进入「考试配置管理」"
    echo "3. 创建新配置时启用「精确数量控制」"
    echo "4. 测试题目筛选：计算机科学+高中水平+选择题"
    echo ""
    log_warning "如果遇到问题，回滚命令："
    echo "cd $PROJECT_DIR"
    echo "docker-compose down"
    echo "rm -rf * .* 2>/dev/null || true"
    echo "cp -r $BACKUP_PATH/* ."
    echo "docker-compose up -d"
    echo "========================================"
}

# 主函数
main() {
    echo "========================================"
    echo "🚀 CBIT AutoExam 升级脚本 v1.0"
    echo "========================================"
    echo "时间: $(date)"
    echo "目标: $PROJECT_DIR"
    echo "========================================"
    echo ""
    echo "本次升级将带来以下新功能："
    echo "✨ 精确数量控制功能"
    echo "🏷️  统一题目标签体系"
    echo "🎨 全新UI界面设计"
    echo "🌐 完整多语言支持"
    echo ""
    
    # 确认升级
    read -p "确认要升级系统吗? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "升级已取消"
        exit 0
    fi
    
    echo "开始升级..."
    echo "========================================"
    
    # 执行升级步骤
    check_environment
    create_backup
    stop_services
    update_code
    run_migrations
    start_services
    verify_upgrade
    cleanup_old_backups
    show_post_upgrade_info
}

# 错误处理
trap 'echo ""; log_error "升级过程中发生错误，请检查上面的日志信息"; echo "如需回滚，请参考上面显示的回滚命令"; exit 1' ERR

# 执行主函数
main "$@"
