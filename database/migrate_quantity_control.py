#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加精确数量控制字段
"""

import os
import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def migrate_database():
    """迁移数据库，添加新的字段"""

    # 数据库文件路径
    db_paths = [
        os.path.join(project_root, "instance", "exam.db"),
        os.path.join(project_root, "backend", "instance", "exam.db"),
    ]

    # 找到存在的数据库文件
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("❌ 未找到数据库文件")
        return False

    print(f"📁 使用数据库文件: {db_path}")

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否已经存在新字段
        cursor.execute("PRAGMA table_info(exam_configs)")
        columns = [column[1] for column in cursor.fetchall()]

        if "enable_quantity_control" in columns:
            print("✅ 字段已存在，无需迁移")
            conn.close()
            return True

        print("🔄 开始数据库迁移...")

        # 添加新字段
        cursor.execute(
            """
            ALTER TABLE exam_configs 
            ADD COLUMN enable_quantity_control BOOLEAN DEFAULT 0
        """
        )

        cursor.execute(
            """
            ALTER TABLE exam_configs 
            ADD COLUMN quantity_distribution TEXT
        """
        )

        # 提交更改
        conn.commit()

        print("✅ 数据库迁移完成！")
        print("🎯 已添加字段:")
        print("   - enable_quantity_control (BOOLEAN)")
        print("   - quantity_distribution (TEXT)")

        # 验证字段是否添加成功
        cursor.execute("PRAGMA table_info(exam_configs)")
        new_columns = [column[1] for column in cursor.fetchall()]

        if "enable_quantity_control" in new_columns and "quantity_distribution" in new_columns:
            print("✅ 字段验证成功")
        else:
            print("❌ 字段验证失败")
            return False

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        if "conn" in locals():
            conn.rollback()
            conn.close()
        return False


def main():
    """主函数"""
    print("🚀 开始精确数量控制功能数据库迁移")
    print("=" * 50)

    success = migrate_database()

    print("=" * 50)
    if success:
        print("🎉 迁移完成！现在可以重启应用程序使用新功能")
    else:
        print("💥 迁移失败！请检查错误信息")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
