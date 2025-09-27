#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker环境启动脚本
"""

import os
import sys

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置必要的环境变量
os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY", "prod-secret-key-2024-cbit-autoexam")
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
os.environ["FLASK_ENV"] = os.getenv("FLASK_ENV", "production")

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# 导入并运行应用
try:
    from backend.app import app, db

    print("✅ Flask应用导入成功")
except ImportError as e:
    print(f"❌ 导入Flask应用失败: {e}")
    sys.exit(1)

# 创建应用实例供gunicorn使用
if __name__ == "__main__":
    try:
        # 创建数据库表
        with app.app_context():
            db.create_all()
            print("✅ 数据库初始化完成")

        print("🚀 启动智能考试系统...")
        print("🌐 访问地址: http://localhost:8080")
        print("📋 管理后台: http://localhost:8080/admin/dashboard")
        print("👤 管理员账号: admin / imbagogo")
        print("-" * 50)

        # 启动Flask应用
        app.run(debug=False, host="0.0.0.0", port=8080, threaded=True)

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
else:
    # 被gunicorn导入时
    with app.app_context():
        try:
            db.create_all()
            print("✅ 数据库自动初始化完成")
        except Exception as e:
            print(f"⚠️ 数据库初始化警告: {e}")
