#!/bin/bash

# 🚀 CBIT AutoExam 服务器快速部署脚本
# 当upgrade.sh文件缺失时的紧急部署方案

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================"
echo "🚀 CBIT AutoExam 紧急部署脚本"
echo "========================================"

PROJECT_DIR="/www/wwwroot/cbit-autoexam"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 确保在正确目录
cd "$PROJECT_DIR"

# 1. 强制拉取最新代码
log "强制同步最新代码..."
git fetch --all
git reset --hard origin/main
success "代码同步完成"

# 2. 检查upgrade.sh是否存在
if [ ! -f "upgrade.sh" ]; then
    warn "upgrade.sh文件缺失，创建临时版本..."
    
    # 创建临时升级脚本
    cat > upgrade.sh << 'EOF'
#!/bin/bash
# 临时升级脚本

echo "🚀 开始升级..."

# 停止服务
docker-compose down 2>/dev/null || docker-compose -f docker-compose.bt.yml down 2>/dev/null || true

# 清理容器
docker ps -aq --filter "name=cbit" | xargs -r docker rm -f 2>/dev/null || true

# 运行迁移
python3 database/migrate_quantity_control.py 2>/dev/null || echo "迁移脚本不存在或已运行"
python3 database/normalize_tags.py 2>/dev/null || echo "标签规范化不存在或已运行"

# 启动服务
if [ -f "docker-compose.bt.yml" ]; then
    docker-compose -f docker-compose.bt.yml up -d --force-recreate
else
    docker-compose up -d --force-recreate
fi

echo "✅ 升级完成！"
echo "🌐 访问地址: http://你的服务器IP:8080"
EOF

    chmod +x upgrade.sh
    success "临时升级脚本已创建"
fi

# 3. 运行升级
log "执行升级..."
./upgrade.sh

echo "========================================"
success "🎉 部署完成!"
echo "🌐 访问地址: http://你的服务器IP:8080"
echo "📋 管理后台: http://你的服务器IP:8080/admin/dashboard"
echo "========================================"
