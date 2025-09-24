#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地运行脚本
"""

import os
import sys

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置必要的环境变量
os.environ["SECRET_KEY"] = "dev-secret-key"
os.environ["DATABASE_URL"] = (
    f'sqlite:///{os.path.join(os.path.dirname(__file__), "instance", "exam.db")}'
)
os.environ["FLASK_ENV"] = "development"
os.environ["FLASK_DEBUG"] = "True"

# 添加项目根目录和backend目录到Python路径
project_root = os.path.dirname(__file__)
backend_dir = os.path.join(project_root, "backend")
sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)

# 导入并运行应用
try:
    from backend.app import app, db

    print("✅ Flask应用导入成功")
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
        print("🚀 启动智能考试系统...")
        print("🌐 访问地址: http://localhost:8080")
        print("📋 管理后台: http://localhost:8080/admin/dashboard")
        print("🔧 要停止服务器，请按 Ctrl+C")
        print("-" * 50)

        # 启动Flask应用
        app.run(debug=True, host="0.0.0.0", port=8080, threaded=True)

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
