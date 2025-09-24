#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# 创建db实例，稍后在app.py中初始化
db = SQLAlchemy()


class Student(db.Model):
    """学生信息表"""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    id_number = db.Column(db.String(18), unique=True, nullable=False)
    application_number = db.Column(db.String(50), unique=True, nullable=False)
    device_ip = db.Column(db.String(45))
    device_id = db.Column(db.String(50))
    has_taken_exam = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    sessions = db.relationship("ExamSession", backref="student", lazy=True)

    def __repr__(self):
        return f"<Student {self.name}>"


class ExamSession(db.Model):
    """考试会话表"""

    __tablename__ = "exam_sessions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    device_ip = db.Column(db.String(45))
    device_id = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")  # pending, verified, active, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    exams = db.relationship("Exam", backref="session", lazy=True)

    def __repr__(self):
        return f"<ExamSession {self.id}>"


class ExamTemplate(db.Model):
    """考试模板表 - 管理员创建的考试"""

    __tablename__ = "exam_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # 考试名称，如"2026年IMBA管理入学考试第一轮"
    description = db.Column(db.Text)  # 考试描述
    config_id = db.Column(db.Integer, db.ForeignKey("exam_configs.id"), nullable=True)  # 关联的考试配置（可选）
    questions = db.Column(db.Text)  # JSON格式存储题目
    time_limit = db.Column(db.Integer, default=75)  # 时间限制（分钟）
    total_questions = db.Column(db.Integer, default=20)  # 总题目数
    passing_score = db.Column(db.Float, default=60.0)  # 及格分数
    is_active = db.Column(db.Boolean, default=True)  # 是否开放
    show_results = db.Column(db.Boolean, default=True)  # 是否显示成绩
    start_time = db.Column(db.DateTime)  # 开始时间（可选）
    end_time = db.Column(db.DateTime)  # 结束时间（可选）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    exam_instances = db.relationship("ExamInstance", backref="template", lazy=True)
    template_questions = db.relationship(
        "ExamTemplateQuestion",
        backref="template",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "config_id": self.config_id,
            "time_limit": self.time_limit,
            "total_questions": self.total_questions,
            "passing_score": self.passing_score,
            "is_active": self.is_active,
            "show_results": self.show_results,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ExamTemplate {self.name}>"


class ExamInstance(db.Model):
    """考试实例表 - 学生参加的具体考试"""

    __tablename__ = "exam_instances"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("exam_templates.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id"), nullable=True)  # 可选，兼容新旧流程
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)  # 可选，兼容新旧流程
    name = db.Column(db.String(200), nullable=False)  # 实例名称
    description = db.Column(db.Text)  # 实例描述
    questions = db.Column(db.Text)  # JSON格式存储题目（从模板复制或随机生成）
    status = db.Column(db.String(20), default="active")  # active, completed, expired
    score = db.Column(db.Float)  # 得分
    total_score = db.Column(db.Float)  # 总分
    percentage = db.Column(db.Float)  # 百分比
    start_time = db.Column(db.DateTime)  # 考试开始时间
    end_time = db.Column(db.DateTime)  # 考试结束时间
    max_attempts = db.Column(db.Integer, default=1)  # 最大尝试次数
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    answers = db.relationship("Answer", backref="exam_instance", lazy=True)
    student_exams = db.relationship("StudentExam", backref="exam_instance", lazy=True)

    def get_time_remaining(self):
        """获取剩余时间（秒）"""
        if self.status != "active":
            return 0

        elapsed = datetime.utcnow() - self.started_at
        remaining_seconds = (self.template.time_limit * 60) - elapsed.total_seconds()
        return max(0, int(remaining_seconds))

    def is_expired(self):
        """检查是否超时"""
        return self.get_time_remaining() <= 0

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "max_attempts": self.max_attempts,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ExamInstance {self.name}>"


# 保留原有的Exam类以便兼容，但标记为已弃用
class Exam(db.Model):
    """考试表 - 已弃用，保留以便兼容"""

    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id"), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey("exam_configs.id"), nullable=True)  # 关联的考试配置
    questions = db.Column(db.Text)  # JSON格式存储题目
    time_limit = db.Column(db.Integer, default=75)  # 时间限制（分钟）
    status = db.Column(db.String(20), default="active")  # active, completed, expired
    scores = db.Column(db.Text)  # JSON格式存储成绩
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # 关系
    answers = db.relationship("Answer", backref="exam", lazy=True)

    def get_time_remaining(self):
        """获取剩余时间（秒）"""
        if self.status != "active":
            return 0

        elapsed = datetime.utcnow() - self.started_at
        remaining_seconds = (self.time_limit * 60) - elapsed.total_seconds()
        return max(0, int(remaining_seconds))

    def is_expired(self):
        """检查是否超时"""
        return self.get_time_remaining() <= 0

    def __repr__(self):
        return f"<Exam {self.id}>"


class Question(db.Model):
    """题库表"""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)  # 学科
    sub_tag = db.Column(db.String(50))  # 子标签
    language = db.Column(db.String(10), default="zh")  # 语言：zh(中文), en(英文)
    difficulty = db.Column(db.String(20), nullable=False)  # 难度等级
    cognitive_level = db.Column(db.String(20), nullable=False)  # 认知层级
    question_type = db.Column(db.String(20), nullable=False)  # 题型：multiple_choice, short_answer, programming
    content = db.Column(db.Text, nullable=False)  # 题目内容
    options = db.Column(db.Text)  # 选项（JSON格式）
    correct_answer = db.Column(db.Text)  # 正确答案
    explanation = db.Column(db.Text)  # 解析
    points = db.Column(db.Integer, default=1)  # 分值
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        import json

        return {
            "id": str(self.id),
            "subject": self.subject,
            "sub_tag": self.sub_tag,
            "language": self.language,
            "difficulty": self.difficulty,
            "cognitive_level": self.cognitive_level,
            "type": self.question_type,
            "type_key": self.question_type,
            "question_type": self.question_type,  # 添加兼容字段
            "content": self.content,
            "options": json.loads(self.options) if self.options else [],
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "points": self.points,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Question {self.id}>"


class ExamConfig(db.Model):
    """考试配置表"""

    __tablename__ = "exam_configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 配置名称
    description = db.Column(db.Text)  # 配置描述
    total_questions = db.Column(db.Integer, default=5)  # 总题目数
    time_limit = db.Column(db.Integer, default=75)  # 时间限制（分钟）
    subject_filter = db.Column(db.String(100))  # 学科筛选（逗号分隔）
    difficulty_filter = db.Column(db.String(100))  # 难度筛选（逗号分隔）
    type_filter = db.Column(db.String(100))  # 题型筛选（逗号分隔）
    is_default = db.Column(db.Boolean, default=False)  # 是否为默认配置
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    show_results = db.Column(db.Boolean, default=True)  # 是否在考试完成后立即显示成绩

    # 新增：支持精确题目选择
    question_selection_mode = db.Column(db.String(20), default="filter")  # 'filter' 或 'manual'
    passing_score = db.Column(db.Float, default=60.0)  # 及格分数

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    config_questions = db.relationship("ExamConfigQuestion", backref="config", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "total_questions": self.total_questions,
            "time_limit": self.time_limit,
            "subject_filter": self.subject_filter,
            "difficulty_filter": self.difficulty_filter,
            "type_filter": self.type_filter,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "show_results": self.show_results,
            "question_selection_mode": self.question_selection_mode,
            "passing_score": self.passing_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ExamConfig {self.name}>"


class ExamConfigQuestion(db.Model):
    """考试配置题目关联表 - 支持精确题目选择"""

    __tablename__ = "exam_config_questions"

    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey("exam_configs.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    question_order = db.Column(db.Integer, default=0)  # 题目顺序
    points = db.Column(db.Float, default=1.0)  # 该题目在考试中的分值
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    question = db.relationship("Question", backref=db.backref("config_questions", cascade="all, delete-orphan"))

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "question_id": self.question_id,
            "question_order": self.question_order,
            "points": self.points,
            "question": self.question.to_dict() if self.question else None,
        }

    def __repr__(self):
        return f"<ExamConfigQuestion {self.config_id}-{self.question_id}>"


class ExamQuestion(db.Model):
    """考试题目关联表"""

    __tablename__ = "exam_questions"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    question_order = db.Column(db.Integer, default=0)  # 题目顺序
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    exam = db.relationship("Exam", backref="exam_questions")
    question = db.relationship("Question", backref=db.backref("exam_questions", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<ExamQuestion {self.exam_id}-{self.question_id}>"


class Answer(db.Model):
    """答案表"""

    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=True)  # 兼容旧版
    exam_instance_id = db.Column(db.Integer, db.ForeignKey("exam_instances.id"), nullable=True)  # 新版支持
    question_id = db.Column(db.String(50), nullable=False)  # 题目ID（在考试中的ID）
    answer_text = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)
    score = db.Column(db.Float, default=0.0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Answer {self.id}>"


class StudentExamRecord(db.Model):
    """学生考试记录表"""

    __tablename__ = "student_exam_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    total_score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    correct_count = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="in_progress")  # in_progress, completed, abandoned
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    student = db.relationship("Student", backref="exam_records")
    exam = db.relationship("Exam", backref="student_records")

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "exam_id": self.exam_id,
            "student_name": self.student.name if self.student else "",
            "student_id_number": self.student.id_number if self.student else "",
            "total_score": self.total_score,
            "max_score": self.max_score,
            "correct_count": self.correct_count,
            "total_questions": self.total_questions,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<StudentExamRecord {self.id}>"


class ExamTemplateQuestion(db.Model):
    """考试模板题目关联表"""

    __tablename__ = "exam_template_questions"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("exam_templates.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    question_order = db.Column(db.Integer, default=0)  # 题目顺序
    points = db.Column(db.Float, default=1.0)  # 该题目在考试中的分值
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    question = db.relationship(
        "Question",
        backref=db.backref("template_questions", cascade="all, delete-orphan"),
    )

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "question_id": self.question_id,
            "question_order": self.question_order,
            "points": self.points,
            "question": self.question.to_dict() if self.question else None,
        }

    def __repr__(self):
        return f"<ExamTemplateQuestion {self.template_id}-{self.question_id}>"


class StudentExam(db.Model):
    """学生考试记录表"""

    __tablename__ = "student_exams"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    exam_instance_id = db.Column(db.Integer, db.ForeignKey("exam_instances.id"), nullable=False)
    attempt_number = db.Column(db.Integer, default=1)  # 尝试次数
    status = db.Column(db.String(20), default="not_started")  # not_started, in_progress, completed, abandoned
    start_time = db.Column(db.DateTime)  # 开始时间
    end_time = db.Column(db.DateTime)  # 结束时间
    duration_minutes = db.Column(db.Integer, default=0)  # 实际用时（分钟）
    total_score = db.Column(db.Float, default=0.0)  # 总得分
    max_score = db.Column(db.Float, default=0.0)  # 满分
    correct_count = db.Column(db.Integer, default=0)  # 正确题数
    total_questions = db.Column(db.Integer, default=0)  # 总题数
    is_passed = db.Column(db.Boolean, default=False)  # 是否通过
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    student = db.relationship("Student", backref="student_exams")
    answers = db.relationship("StudentAnswer", backref="student_exam", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "exam_instance_id": self.exam_instance_id,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "correct_count": self.correct_count,
            "total_questions": self.total_questions,
            "is_passed": self.is_passed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<StudentExam {self.id}>"


class StudentAnswer(db.Model):
    """学生答案表"""

    __tablename__ = "student_answers"

    id = db.Column(db.Integer, primary_key=True)
    student_exam_id = db.Column(db.Integer, db.ForeignKey("student_exams.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    answer_text = db.Column(db.Text)  # 学生答案
    is_correct = db.Column(db.Boolean)  # 是否正确
    score = db.Column(db.Float, default=0.0)  # 得分
    feedback = db.Column(db.Text)  # 批改反馈
    auto_graded = db.Column(db.Boolean, default=False)  # 是否自动批改
    graded_at = db.Column(db.DateTime)  # 批改时间
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)  # 提交时间

    # 关系
    question = db.relationship("Question", backref=db.backref("student_answers", cascade="all, delete-orphan"))

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "student_exam_id": self.student_exam_id,
            "question_id": self.question_id,
            "answer_text": self.answer_text,
            "is_correct": self.is_correct,
            "score": self.score,
            "feedback": self.feedback,
            "auto_graded": self.auto_graded,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "submitted_at": (self.submitted_at.isoformat() if self.submitted_at else None),
        }

    def __repr__(self):
        return f"<StudentAnswer {self.id}>"


class VerificationConfig(db.Model):
    """考生验证字段配置表"""

    __tablename__ = "verification_configs"

    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.String(50), nullable=False)  # 字段名称 (name, id_number, application_number)
    display_name = db.Column(db.String(100), nullable=False)  # 显示名称
    is_required = db.Column(db.Boolean, default=True)  # 是否必填
    is_enabled = db.Column(db.Boolean, default=True)  # 是否启用
    field_type = db.Column(db.String(20), default="text")  # 字段类型 (text, number, email)
    placeholder = db.Column(db.String(200))  # 占位符文本
    validation_pattern = db.Column(db.String(500))  # 验证正则表达式
    error_message = db.Column(db.String(200))  # 错误提示信息
    field_order = db.Column(db.Integer, default=0)  # 字段显示顺序
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "field_name": self.field_name,
            "display_name": self.display_name,
            "is_required": self.is_required,
            "is_enabled": self.is_enabled,
            "field_type": self.field_type,
            "placeholder": self.placeholder,
            "validation_pattern": self.validation_pattern,
            "error_message": self.error_message,
            "field_order": self.field_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<VerificationConfig {self.field_name}>"


class SystemConfig(db.Model):
    """系统配置表"""

    __tablename__ = "system_configs"

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text)
    config_type = db.Column(db.String(20), default="text")  # text, file, boolean, number
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "config_key": self.config_key,
            "config_value": self.config_value,
            "config_type": self.config_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<SystemConfig {self.config_key}>"


class ApiProvider(db.Model):
    """API提供商配置表"""

    __tablename__ = "api_providers"

    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(50), unique=True, nullable=False)  # openrouter, openai, anthropic
    display_name = db.Column(db.String(100), nullable=False)  # 显示名称
    api_url = db.Column(db.String(500), nullable=False)  # API端点URL
    api_key = db.Column(db.Text)  # API密钥（加密存储）
    is_active = db.Column(db.Boolean, default=False)  # 是否启用
    is_verified = db.Column(db.Boolean, default=False)  # 是否已验证
    default_model = db.Column(db.String(100))  # 默认模型
    supported_models = db.Column(db.Text)  # 支持的模型列表（JSON格式）
    headers_template = db.Column(db.Text)  # 请求头模板（JSON格式）
    request_template = db.Column(db.Text)  # 请求体模板（JSON格式）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        import json

        return {
            "id": self.id,
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "api_url": self.api_url,
            "api_key": (self.api_key[:10] + "..." if self.api_key else None),  # 隐藏API密钥
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "default_model": self.default_model,
            "supported_models": (json.loads(self.supported_models) if self.supported_models else []),
            "headers_template": (json.loads(self.headers_template) if self.headers_template else {}),
            "request_template": (json.loads(self.request_template) if self.request_template else {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ApiProvider {self.provider_name}>"
