#!/usr/bin/env python3
"""
题目标签规范化脚本
统一数据库中的所有标签，确保筛选功能正常工作
"""

import sys
import os
import sqlite3

# 添加后端路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def normalize_tags():
    """规范化所有题目标签"""
    
    # 定义标准标签映射
    SUBJECT_MAPPING = {
        # 数学相关
        '数学': '数学',
        'Mathematics': '数学',
        'math': '数学',
        '微积分': '数学',
        '线性代数': '数学',
        '统计学': '统计学',
        'Statistics': '统计学',
        
        # 计算机相关
        '计算机科学': '计算机科学',
        'Computer Science': '计算机科学',
        '计算机': '计算机科学',
        'Programming': '计算机科学',
        
        # 工程相关
        '工程': '工程学',
        'Engineering': '工程学',
        
        # 英语相关
        '英语': '英语',
        'English': '英语',
        
        # 逻辑相关
        '逻辑': '逻辑学',
        'Logic': '逻辑学',
        
        # 物理相关
        '物理': '物理学',
        'Physics': '物理学',
        
        # 化学相关
        '化学': '化学',
        'Chemistry': '化学',
        
        # 经济相关
        '经济': '经济学',
        '经济学': '经济学',
        'Economics': '经济学',
    }
    
    DIFFICULTY_MAPPING = {
        # 高中水平
        '高中水平': 'high_school',
        'High School Level': 'high_school',
        'high_school': 'high_school',
        '简单': 'high_school',
        'Easy': 'high_school',
        
        # 本科基础
        '本科基础': 'undergraduate_basic',
        'Undergraduate Basic': 'undergraduate_basic',
        'undergraduate_basic': 'undergraduate_basic',
        '中等': 'undergraduate_basic',
        'Medium': 'undergraduate_basic',
        
        # 本科进阶
        '本科进阶': 'undergraduate_advanced',
        'Undergraduate Advanced': 'undergraduate_advanced',
        'undergraduate_advanced': 'undergraduate_advanced',
        '困难': 'undergraduate_advanced',
        'Hard': 'undergraduate_advanced',
        
        # 研究生水平
        '研究生水平': 'graduate',
        'Graduate Study Level': 'graduate',
        'graduate': 'graduate',
        'GRE水平': 'graduate',
        'GRE Level': 'graduate',
        'GRE难度': 'graduate',
    }
    
    TYPE_MAPPING = {
        # 选择题
        '选择题': 'multiple_choice',
        'multiple_choice': 'multiple_choice',
        'Multiple Choice': 'multiple_choice',
        '单选题': 'multiple_choice',
        '多选题': 'multiple_choice',
        
        # 简答题
        '简答题': 'short_answer',
        'short_answer': 'short_answer',
        'Short Answer': 'short_answer',
        '填空题': 'short_answer',
        
        # 编程题
        '编程题': 'programming',
        'programming': 'programming',
        'Programming': 'programming',
        '代码题': 'programming',
    }
    
    print("🚀 开始题目标签规范化")
    print("=" * 50)
    
    try:
        # 连接数据库
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        db_file = os.path.join(project_root, "instance", "exam.db")
        
        if not os.path.exists(db_file):
            print(f"❌ 数据库文件不存在: {db_file}")
            return False
            
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 获取所有题目
        cursor.execute("SELECT id, subject, difficulty, question_type FROM questions")
        questions = cursor.fetchall()
        
        print(f"📊 找到 {len(questions)} 道题目")
        
        updated_count = 0
        skipped_count = 0
        
        for question_id, subject, difficulty, question_type in questions:
            original_subject = subject
            original_difficulty = difficulty
            original_type = question_type
            
            # 规范化学科
            normalized_subject = SUBJECT_MAPPING.get(subject, subject)
            
            # 规范化难度
            normalized_difficulty = DIFFICULTY_MAPPING.get(difficulty, difficulty)
            
            # 规范化题型
            normalized_type = TYPE_MAPPING.get(question_type, question_type)
            
            # 检查是否需要更新
            if (normalized_subject != original_subject or 
                normalized_difficulty != original_difficulty or 
                normalized_type != original_type):
                
                cursor.execute("""
                    UPDATE questions 
                    SET subject = ?, difficulty = ?, question_type = ?
                    WHERE id = ?
                """, (normalized_subject, normalized_difficulty, normalized_type, question_id))
                
                updated_count += 1
                print(f"✅ 题目 {question_id}:")
                if normalized_subject != original_subject:
                    print(f"   学科: {original_subject} → {normalized_subject}")
                if normalized_difficulty != original_difficulty:
                    print(f"   难度: {original_difficulty} → {normalized_difficulty}")
                if normalized_type != original_type:
                    print(f"   题型: {original_type} → {normalized_type}")
            else:
                skipped_count += 1
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 50)
        print(f"✅ 规范化完成!")
        print(f"📊 更新题目数: {updated_count}")
        print(f"📊 跳过题目数: {skipped_count}")
        
        # 验证结果
        print("\n🔍 验证规范化结果:")
        
        cursor.execute("SELECT DISTINCT subject FROM questions ORDER BY subject")
        subjects = [row[0] for row in cursor.fetchall()]
        print(f"📋 学科标签: {subjects}")
        
        cursor.execute("SELECT DISTINCT difficulty FROM questions ORDER BY difficulty")
        difficulties = [row[0] for row in cursor.fetchall()]
        print(f"📋 难度标签: {difficulties}")
        
        cursor.execute("SELECT DISTINCT question_type FROM questions ORDER BY question_type")
        types = [row[0] for row in cursor.fetchall()]
        print(f"📋 题型标签: {types}")
        
        # 测试特定组合
        cursor.execute("""
            SELECT COUNT(*) FROM questions 
            WHERE is_active = 1 AND subject = '计算机科学' AND difficulty = 'high_school' AND question_type = 'multiple_choice'
        """)
        combo_count = cursor.fetchone()[0]
        print(f"\n🎯 测试组合 '计算机科学+high_school+multiple_choice': {combo_count} 题")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 规范化失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if normalize_tags():
        print("\n🎉 标签规范化成功完成!")
    else:
        print("\n💥 标签规范化失败!")
        sys.exit(1)
