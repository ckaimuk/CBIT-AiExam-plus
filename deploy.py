#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器部署脚本
用于在服务器环境下正确启动应用
"""

import os
import sys

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置服务器环境变量
os.environ["FLASK_ENV"] = "production"
os.environ["DEPLOYMENT"] = "server"
os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-production-secret-key")
os.environ["FLASK_DEBUG"] = "False"

# 如果没有设置DATABASE_URL，使用当前目录下的instance
if not os.getenv("DATABASE_URL"):
    instance_dir = os.path.join(os.getcwd(), "instance")
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, "exam.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

# 添加项目路径
project_root = os.path.dirname(__file__)
backend_dir = os.path.join(project_root, "backend")
sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)

# 导入并运行应用
try:
    from backend.app import app, db

    print("✅ Flask应用导入成功")
    print(f"🗄️  数据库路径: {os.getenv('DATABASE_URL')}")
except ImportError as e:
    print(f"❌ 导入Flask应用失败: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        # 创建数据库表
        with app.app_context():
            db.create_all()
            print("✅ 数据库初始化完成")

        # 运行应用
        print("🚀 启动智能考试系统 (生产环境)...")
        print("🌐 访问地址: http://0.0.0.0:8080")
        print("📋 管理后台: http://0.0.0.0:8080/admin/dashboard")
        print("🔧 要停止服务器，请按 Ctrl+C")
        print("-" * 50)

        # 启动Flask应用
        app.run(debug=False, host="0.0.0.0", port=8080, threaded=True)

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
