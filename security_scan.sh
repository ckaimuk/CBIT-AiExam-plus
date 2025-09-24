#!/bin/bash

echo "=================================="
echo "CBIT AutoExam 安全扫描脚本"
echo "=================================="

# 检查是否安装了必要的工具
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 未安装，请先安装: pip install $1"
        return 1
    fi
    return 0
}

# Python代码安全扫描
echo "🔍 运行Python代码安全扫描 (Bandit)..."
if check_tool bandit; then
    bandit -r . -x tests/ -f txt
    echo ""
fi

# 依赖安全检查
echo "🔍 运行依赖安全检查 (Safety)..."
if check_tool safety; then
    safety check
    echo ""
fi

# Docker镜像扫描（如果有Docker）
if command -v docker &> /dev/null; then
    echo "🔍 运行Docker镜像安全扫描..."
    if docker image inspect cbit-autoexam:latest &> /dev/null; then
        echo "扫描现有Docker镜像..."
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy:latest image cbit-autoexam:latest
    else
        echo "Docker镜像 cbit-autoexam:latest 不存在，跳过扫描"
        echo "请先构建镜像: docker build -f docker/Dockerfile -t cbit-autoexam:latest ."
    fi
    echo ""
fi

# 代码质量检查
echo "🔍 运行代码质量检查..."
if check_tool flake8; then
    echo "运行flake8检查..."
    flake8 . --max-line-length=120 --extend-ignore=E203,W503,E501,F541,F401,F811,F841,E722,E402,E712,F402,F601 --statistics
    echo ""
fi

if check_tool black; then
    echo "检查代码格式..."
    black --check --diff . || echo "代码格式需要调整，运行: black ."
    echo ""
fi

echo "✅ 安全扫描完成"
echo ""
echo "📋 如需安装扫描工具："
echo "pip install bandit safety flake8 black"
echo ""
echo "🐳 如需详细Docker扫描："
echo "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image cbit-autoexam:latest"
