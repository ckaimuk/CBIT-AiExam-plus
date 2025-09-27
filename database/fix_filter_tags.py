#!/usr/bin/env python3
"""
修复题目筛选标签脚本
确保数据库中的标签与前端筛选器完全匹配
"""

import os
import sqlite3
import sys

# 添加后端路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))


def fix_filter_tags():
    """修复筛选标签，确保与前端完全匹配"""
    
    print("🔧 开始修复题目筛选标签")
    print("=" * 50)

    try:
        # 连接数据库 - 支持新的数据库路径
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # 优先使用新路径 /data/app.db
        if os.path.exists("/data/app.db"):
            db_file = "/data/app.db"
            print(f"📍 使用容器数据库路径: {db_file}")
        else:
            # 开发环境使用旧路径
            db_file = os.path.join(project_root, "instance", "exam.db")
            print(f"📍 使用开发数据库路径: {db_file}")

        if not os.path.exists(db_file):
            print(f"❌ 数据库文件不存在: {db_file}")
            return False

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        print(f"✅ 数据库连接成功: {db_file}")

        # 检查当前状态
        print("\n📊 当前数据库状态:")
        
        # 学科分布
        cursor.execute("SELECT subject, COUNT(*) FROM questions GROUP BY subject ORDER BY COUNT(*) DESC")
        subjects = cursor.fetchall()
        print("  学科分布:")
        for subject, count in subjects:
            print(f"    {subject}: {count}题")
        
        # 难度分布
        cursor.execute("SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty ORDER BY COUNT(*) DESC")
        difficulties = cursor.fetchall()
        print("  难度分布:")
        for difficulty, count in difficulties:
            print(f"    {difficulty}: {count}题")

        # 标签修复映射
        subject_fixes = {
            "工程": "工程学",  # 确保统一为工程学
            "Engineering": "工程学",
            "Computer Science": "计算机科学",
            "Mathematics": "数学",
            "Statistics": "统计学"
        }
        
        difficulty_fixes = {
            # 旧标签 → 新标签
            "High School Level": "high_school",
            "本科基础": "undergraduate_basic", 
            "Undergraduate Basic": "undergraduate_basic",
            "Undergraduate Advanced": "undergraduate_advanced",
            "GRE Level": "graduate",
            "GRE难度": "graduate",
            "Graduate Study Level": "graduate",
            "Graduate Level": "graduate"
        }

        # 开始修复
        print("\n🛠️ 开始标签修复:")
        
        updated_count = 0
        
        # 修复学科标签
        for old_subject, new_subject in subject_fixes.items():
            cursor.execute("SELECT COUNT(*) FROM questions WHERE subject = ?", (old_subject,))
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("UPDATE questions SET subject = ? WHERE subject = ?", (new_subject, old_subject))
                print(f"  学科: {old_subject} → {new_subject} ({count}题)")
                updated_count += count

        # 修复难度标签  
        for old_difficulty, new_difficulty in difficulty_fixes.items():
            cursor.execute("SELECT COUNT(*) FROM questions WHERE difficulty = ?", (old_difficulty,))
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("UPDATE questions SET difficulty = ? WHERE difficulty = ?", (new_difficulty, old_difficulty))
                print(f"  难度: {old_difficulty} → {new_difficulty} ({count}题)")
                updated_count += count

        # 提交更改
        conn.commit()
        
        if updated_count > 0:
            print(f"\n✅ 修复完成，共更新 {updated_count} 道题目的标签")
        else:
            print(f"\n✅ 检查完成，所有标签都已正确")

        # 验证修复结果
        print("\n🔍 验证修复结果:")
        
        # 检查最终的学科分布
        cursor.execute("SELECT subject, COUNT(*) FROM questions GROUP BY subject ORDER BY subject")
        final_subjects = cursor.fetchall()
        print("  最终学科分布:")
        for subject, count in final_subjects:
            print(f"    {subject}: {count}题")
        
        # 检查最终的难度分布
        cursor.execute("SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty ORDER BY difficulty")
        final_difficulties = cursor.fetchall()
        print("  最终难度分布:")
        for difficulty, count in final_difficulties:
            print(f"    {difficulty}: {count}题")

        # 测试筛选功能
        print("\n🧪 测试筛选功能:")
        
        # 测试组合筛选
        test_cases = [
            ("数学", "undergraduate_basic", "multiple_choice"),
            ("计算机科学", "high_school", None),
            ("统计学", "graduate", None),
            ("工程学", None, None)
        ]
        
        for subject, difficulty, qtype in test_cases:
            query = "SELECT COUNT(*) FROM questions WHERE subject = ? AND is_active = 1"
            params = [subject]
            
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            
            if qtype:
                query += " AND question_type = ?"
                params.append(qtype)
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            filters = [subject]
            if difficulty:
                filters.append(difficulty)
            if qtype:
                filters.append(qtype)
            
            print(f"  {' + '.join(filters)}: {count}题")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        if "conn" in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    if fix_filter_tags():
        print("\n🎉 标签修复成功完成!")
        print("📱 前端筛选功能现在应该能正常工作了!")
    else:
        print("\n💥 标签修复失败!")
        sys.exit(1)
