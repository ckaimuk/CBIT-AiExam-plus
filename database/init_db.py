#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""

import os
import sys

# 添加项目根目录和backend目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(project_root, 'backend')
sys.path.append(project_root)
sys.path.append(backend_dir)

from backend.app import app, db
from backend.models import Student, Exam, Question, Answer, ExamSession, ExamConfig

def init_database():
    """初始化数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建成功")
        
        # 添加示例题目（可选）
        add_sample_questions()
        
        # 添加默认考试配置
        add_default_exam_config()
        
        print("数据库初始化完成")
        print("管理员账户信息:")
        print("用户名: admin")
        print("密码: imbagogo")

def add_sample_questions():
    """添加示例题目"""
    sample_questions = [
        {
            'subject': '统计学',
            'difficulty': '高中水平',
            'cognitive_level': '理解',
            'question_type': '选择题',
            'content': '下列哪个是描述性统计的指标？',
            'options': '["平均数", "假设检验", "回归分析", "方差分析"]',
            'correct_answer': '平均数',
            'explanation': '描述性统计用于描述数据的基本特征，包括平均数、中位数、众数等。',
            'points': 1
        },
        {
            'subject': '微积分',
            'difficulty': 'GRE水平',
            'cognitive_level': '应用',
            'question_type': '简答题',
            'content': '求函数 f(x) = x² + 2x + 1 的导数。',
            'options': '[]',
            'correct_answer': 'f\'(x) = 2x + 2',
            'explanation': '使用幂函数求导法则，x²的导数是2x，2x的导数是2，常数的导数是0。',
            'points': 2
        },
        {
            'subject': '线性代数',
            'difficulty': '研究生水平',
            'cognitive_level': '综合',
            'question_type': '编程题',
            'content': '编写Python代码计算矩阵A和B的乘积，其中A是2x3矩阵，B是3x2矩阵。',
            'options': '[]',
            'correct_answer': 'import numpy as np\nA = np.array([[1,2,3],[4,5,6]])\nB = np.array([[1,2],[3,4],[5,6]])\nC = np.dot(A, B)',
            'explanation': '使用NumPy库的dot函数计算矩阵乘法。',
            'points': 3
        }
    ]
    
    for q_data in sample_questions:
        question = Question(**q_data)
        db.session.add(question)
    
    db.session.commit()
    print("示例题目添加成功")

def add_default_exam_config():
    """添加默认考试配置"""
    # 检查是否已有默认配置
    existing_config = ExamConfig.query.filter_by(is_default=True, is_active=True).first()
    if existing_config:
        print("默认考试配置已存在")
        return
    
    # 创建默认考试配置
    default_config = ExamConfig(
        name='默认考试配置',
        description='系统默认的考试配置，包含5道题目，75分钟时间限制',
        total_questions=5,
        time_limit=75,
        subject_filter='数学,英语,计算机,逻辑,统计学',
        difficulty_filter='简单,中等,困难',
        type_filter='multiple_choice,short_answer,programming',
        is_default=True,
        is_active=True
    )
    
    db.session.add(default_config)
    db.session.commit()
    print("默认考试配置添加成功")


if __name__ == '__main__':
    init_database()
