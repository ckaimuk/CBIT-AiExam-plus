#!/bin/bash

echo "=================================="
echo "CBIT AutoExam 部署验证脚本"
echo "=================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装，请先安装docker-compose"
    exit 1
fi

echo "✅ Docker环境检查通过"

# 启动服务
echo "🚀 启动CBIT AutoExam服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动完成..."
sleep 10

# 健康检查
echo "🔍 执行健康检查..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "📊 访问信息："
    echo "🌐 主页: http://localhost:8080"
    echo "📋 管理后台: http://localhost:8080/admin/dashboard"
    echo "👤 管理员账号: admin"
    echo "🔐 管理员密码: imbagogo"
    echo ""
    echo "🎉 部署完成！"
else
    echo "❌ 服务启动失败"
    echo "📋 查看日志："
    docker-compose logs
    exit 1
fi
