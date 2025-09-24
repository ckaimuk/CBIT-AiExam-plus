#!/bin/bash

# ====================================
# CBIT AutoExam 宝塔面板一键部署脚本
# ====================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用root用户运行此脚本"
        exit 1
    fi
}

# 检查宝塔面板
check_bt_panel() {
    if ! command -v bt &> /dev/null; then
        log_error "未检测到宝塔面板，请先安装宝塔面板"
        exit 1
    fi
    log_success "宝塔面板检测通过"
}

# 检查Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_warning "Docker未安装，正在安装..."
        # 通过宝塔安装Docker
        bt install docker
        systemctl enable docker
        systemctl start docker
    fi
    
    if ! docker --version &> /dev/null; then
        log_error "Docker安装失败，请手动安装"
        exit 1
    fi
    log_success "Docker检测通过"
}

# 检查docker-compose
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_warning "docker-compose未安装，正在安装..."
        curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    fi
    
    if ! docker-compose --version &> /dev/null; then
        log_error "docker-compose安装失败"
        exit 1
    fi
    log_success "docker-compose检测通过"
}

# 设置项目目录
setup_project_dir() {
    PROJECT_DIR="/www/wwwroot/cbit-autoexam"
    
    log_info "设置项目目录: $PROJECT_DIR"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        mkdir -p "$PROJECT_DIR"
        log_success "创建项目目录"
    fi
    
    cd "$PROJECT_DIR"
}

# 下载项目代码
download_project() {
    log_info "下载项目代码..."
    
    if [ -d ".git" ]; then
        log_info "更新现有代码..."
        git pull origin main
    else
        log_info "克隆项目代码..."
        git clone https://github.com/reneverland/CBIT-AiExam-plus.git .
    fi
    
    log_success "项目代码下载完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p instance
    mkdir -p logs
    mkdir -p static/uploads
    mkdir -p frontend/static/uploads
    
    log_success "目录创建完成"
}

# 设置权限
set_permissions() {
    log_info "设置文件权限..."
    
    chown -R www:www "$PROJECT_DIR"
    chmod -R 755 "$PROJECT_DIR"
    chmod +x bt_deploy.sh deploy_test.sh security_scan.sh
    
    # 设置数据库文件权限
    if [ -f "instance/exam.db" ]; then
        chmod 644 instance/exam.db
    fi
    
    log_success "权限设置完成"
}

# 构建Docker镜像
build_docker_image() {
    log_info "构建Docker镜像..."
    
    docker build -f docker/Dockerfile -t cbit-autoexam:latest .
    
    if [ $? -eq 0 ]; then
        log_success "Docker镜像构建成功"
    else
        log_error "Docker镜像构建失败"
        exit 1
    fi
}

# 停止现有容器
stop_existing_container() {
    if docker ps -q -f name=cbit-autoexam | grep -q .; then
        log_info "停止现有容器..."
        docker stop cbit-autoexam
        docker rm cbit-autoexam
        log_success "现有容器已停止"
    fi
}

# 启动容器
start_container() {
    log_info "启动新容器..."
    
    docker run -d \
        --name cbit-autoexam \
        --restart unless-stopped \
        -p 8080:8080 \
        -e FLASK_ENV=production \
        -e SECRET_KEY=cbit-prod-secret-key-$(date +%s) \
        -e DATABASE_URL=sqlite:///instance/exam.db \
        -e TZ=Asia/Shanghai \
        -v "$PROJECT_DIR/instance:/app/instance" \
        -v "$PROJECT_DIR/static/uploads:/app/static/uploads" \
        -v "$PROJECT_DIR/frontend/static/uploads:/app/frontend/static/uploads" \
        -v "$PROJECT_DIR/logs:/app/logs" \
        cbit-autoexam:latest
    
    if [ $? -eq 0 ]; then
        log_success "容器启动成功"
    else
        log_error "容器启动失败"
        exit 1
    fi
}

# 等待服务启动
wait_for_service() {
    log_info "等待服务启动..."
    
    for i in {1..30}; do
        if curl -f http://localhost:8080 >/dev/null 2>&1; then
            log_success "服务启动成功"
            return 0
        fi
        sleep 2
    done
    
    log_error "服务启动超时"
    docker logs cbit-autoexam --tail 20
    return 1
}

# 创建宝塔站点配置
create_bt_site() {
    log_info "创建宝塔站点配置提示..."
    
    cat << EOF

====================================
🎉 部署完成！
====================================

📋 接下来请在宝塔面板中进行以下配置：

1. 创建网站：
   - 域名：your-domain.com
   - 根目录：$PROJECT_DIR
   - PHP版本：纯静态

2. 配置反向代理：
   - 代理名称：CBIT AutoExam
   - 目标URL：http://127.0.0.1:8080
   - 发送域名：\$host

3. 配置SSL（推荐）：
   - 申请Let's Encrypt证书
   - 开启强制HTTPS

🌐 访问地址：
   - 直接访问：http://your-server-ip:8080
   - 域名访问：https://your-domain.com
   - 管理后台：/admin/dashboard

👤 默认管理员账号：
   - 用户名：admin
   - 密码：imbagogo

📊 容器管理：
   - 查看状态：docker ps | grep cbit-autoexam
   - 查看日志：docker logs cbit-autoexam
   - 重启容器：docker restart cbit-autoexam

🛠️ 维护操作：
   - 更新应用：./bt_deploy.sh
   - 安全扫描：./security_scan.sh
   - 部署测试：./deploy_test.sh

====================================

EOF
}

# 主函数
main() {
    echo "======================================"
    echo "🚀 CBIT AutoExam 宝塔面板一键部署"
    echo "======================================"
    
    # 执行检查
    check_root
    check_bt_panel
    check_docker
    check_docker_compose
    
    # 部署步骤
    setup_project_dir
    download_project
    create_directories
    set_permissions
    build_docker_image
    stop_existing_container
    start_container
    
    # 等待服务
    if wait_for_service; then
        create_bt_site
    else
        log_error "部署失败，请查看日志"
        exit 1
    fi
}

# 运行主函数
main "$@"
