#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CBIT Lite Trainer - 主应用文件
AI智能考试系统后端API
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

import pytz
import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

# 加载环境变量
load_dotenv()

# 设置中国时区
CHINA_TZ = pytz.timezone("Asia/Shanghai")


def get_china_now():
    """获取中国当前时间"""
    return datetime.now(CHINA_TZ)


def to_china_time(dt):
    """将UTC时间转换为中国时间"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 假设是UTC时间
        dt = pytz.utc.localize(dt)
    return dt.astimezone(CHINA_TZ)


# 创建Flask应用
app = Flask(
    __name__,
    template_folder="../frontend",
    static_folder="../frontend",
    static_url_path="",
)

# 配置
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
# 使用绝对路径确保连接正确的数据库
db_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "exam.db"
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", f"sqlite:///{db_path}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True  # 自动重新加载模板
app.jinja_env.auto_reload = True  # 自动重新加载Jinja环境

# 导入模型
from models import (
    Answer,
    ApiProvider,
    Exam,
    ExamConfig,
    ExamConfigQuestion,
    ExamInstance,
    ExamQuestion,
    ExamSession,
    ExamTemplate,
    ExamTemplateQuestion,
    Question,
    Student,
    StudentAnswer,
    StudentExam,
    StudentExamRecord,
    SystemConfig,
    VerificationConfig,
    db,
)

# 初始化扩展
db.init_app(app)
CORS(app)

import os

# 导入AI引擎
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "backend"))

try:
    from ai_engine.generator import QuestionGenerator
    from ai_engine.validator import QuestionValidator
except ImportError:
    # 如果导入失败，创建空的类以避免错误
    class QuestionGenerator:
        def __init__(self):
            pass

    class QuestionValidator:
        def __init__(self):
            pass


# 导入评分系统
try:
    from .scoring import ScoringSystem
except ImportError:
    try:
        from backend.scoring import ScoringSystem
    except ImportError:
        from scoring import ScoringSystem

# 初始化AI引擎（延迟初始化）
question_generator = None
question_validator = None
scoring_system = None


def get_question_generator():
    """获取题目生成器（延迟初始化）"""
    global question_generator
    if question_generator is None:
        question_generator = QuestionGenerator()
    return question_generator


def get_question_validator():
    """获取题目验证器（延迟初始化）"""
    global question_validator
    if question_validator is None:
        question_validator = QuestionValidator()
    return question_validator


def get_scoring_system():
    """获取评分系统（每次重新初始化以确保配置更新）"""
    # 每次都创建新实例，确保配置是最新的
    return ScoringSystem()


# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "需要管理员权限",
                        "error_code": "ADMIN_REQUIRED",
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return decorated_function


# 检查管理员权限的辅助函数
def is_admin():
    return session.get("admin_logged_in", False)


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/verification")
def verification():
    """身份验证页面"""
    return render_template("verification.html")


@app.route("/exam")
def exam():
    """考试页面"""
    exam_id = request.args.get("exam_id")
    instance_id = request.args.get("instance_id")

    # 支持新旧两种模式
    if not exam_id and not instance_id:
        return redirect(url_for("verification"))

    # 传递相应的参数到模板
    if instance_id:
        return render_template("exam.html", instance_id=instance_id)
    else:
        return render_template("exam.html", exam_id=exam_id)


@app.route("/admin/login")
def admin_login():
    """管理员登录页面"""
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """管理员仪表板"""
    return render_template("admin_dashboard.html")


@app.route("/question_management.html")
@admin_required
def question_management():
    """题库管理页面"""
    return render_template("question_management.html")


@app.route("/exam_config_management.html")
@admin_required
def exam_config_management():
    """考试配置管理页面"""
    return render_template("exam_config_management.html")


@app.route("/student_records.html")
@admin_required
def student_records():
    """学生答题记录管理页面"""
    return render_template("student_records.html")


@app.route("/student_cleanup.html")
@admin_required
def student_cleanup():
    """学生信息清理管理页面"""
    return render_template("student_cleanup.html")


@app.route("/test_api.html")
def test_api():
    """API测试页面"""
    return render_template("test_api.html")


@app.route("/api/verify-student", methods=["POST"])
def verify_student():
    """验证学生身份"""
    try:
        data = request.get_json()
        name = data.get("name", "").strip()
        # 兼容新旧字段名称
        id_number = data.get("id_number", data.get("idNumber", "")).strip()
        application_number = data.get(
            "application_number", data.get("applicationNumber", "")
        ).strip()
        device_ip = data.get("deviceIP", "")
        device_id = data.get("deviceId", "")

        # 验证必填字段
        if not all([name, id_number, application_number]):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "请填写所有必填字段",
                        "error_code": "MISSING_FIELDS",
                    }
                ),
                400,
            )

        # 验证身份证号格式
        if (
            len(id_number) != 18
            or not id_number[:-1].isdigit()
            or id_number[-1] not in "0123456789Xx"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "身份证号格式不正确，请输入18位有效身份证号",
                        "error_code": "INVALID_ID_NUMBER",
                    }
                ),
                400,
            )

        # 验证申请号格式
        if len(application_number) < 6 or len(application_number) > 20:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "申请号长度应在6-20个字符之间",
                        "error_code": "INVALID_APPLICATION_NUMBER",
                    }
                ),
                400,
            )

        # 检查是否为管理员（基于会话）
        is_admin_test = is_admin()

        # 检查是否已经参加过考试（管理员可以绕过）
        existing_student = Student.query.filter_by(
            id_number=id_number, application_number=application_number
        ).first()

        if existing_student and existing_student.has_taken_exam and not is_admin_test:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "该考生已经参加过考试，每人仅有一次机会。如需重新测试，请先登录管理员账号。",
                        "error_code": "ALREADY_TAKEN_EXAM",
                    }
                ),
                400,
            )

        # 创建或更新学生记录
        if existing_student:
            student = existing_student
            # 如果是管理员测试，重置考试状态
            if is_admin_test:
                student.has_taken_exam = False
                student.name = name  # 更新姓名
                student.device_ip = device_ip
                student.device_id = device_id
        else:
            # 检查身份证号是否已被使用（非管理员）
            if not is_admin_test:
                existing_id = Student.query.filter_by(id_number=id_number).first()
                if existing_id:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "该身份证号已被使用，请检查身份证号是否正确",
                                "error_code": "ID_NUMBER_USED",
                            }
                        ),
                        400,
                    )

                # 检查申请号是否已被使用
                existing_app = Student.query.filter_by(
                    application_number=application_number
                ).first()
                if existing_app:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "该申请号已被使用，请检查申请号是否正确",
                                "error_code": "APPLICATION_NUMBER_USED",
                            }
                        ),
                        400,
                    )
            else:
                # 管理员模式：检查是否有相同身份证号的学生，如果有则更新
                existing_id = Student.query.filter_by(id_number=id_number).first()
                if existing_id:
                    student = existing_id
                    student.name = name
                    student.application_number = application_number
                    student.device_ip = device_ip
                    student.device_id = device_id
                    student.has_taken_exam = False  # 重置考试状态
                else:
                    # 创建新学生记录
                    student = Student(
                        name=name,
                        id_number=id_number,
                        application_number=application_number,
                        device_ip=device_ip,
                        device_id=device_id,
                        has_taken_exam=False,
                    )
                    db.session.add(student)
                    db.session.flush()

            if not is_admin_test:
                student = Student(
                    name=name,
                    id_number=id_number,
                    application_number=application_number,
                    device_ip=device_ip,
                    device_id=device_id,
                    has_taken_exam=False,
                )
                db.session.add(student)
                db.session.flush()  # 确保student.id被分配

        # 创建考试会话
        exam_session = ExamSession(
            student_id=student.id,
            device_ip=device_ip,
            device_id=device_id,
            status="verified",
        )
        db.session.add(exam_session)
        db.session.commit()

        return jsonify(
            {"success": True, "message": "身份验证成功", "session_id": exam_session.id}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"验证失败: {str(e)}"}), 500


@app.route("/api/generate-exam", methods=["POST"])
def generate_exam():
    """从题库生成考试题目"""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        config_id = data.get("config_id")  # 可选的考试配置ID

        if not session_id:
            return jsonify({"success": False, "message": "无效的会话ID"}), 400

        # 获取考试会话
        exam_session = ExamSession.query.get(session_id)
        if not exam_session:
            return jsonify({"success": False, "message": "会话不存在"}), 404

        # 获取考试配置
        if config_id:
            exam_config = ExamConfig.query.get(config_id)
        else:
            # 使用默认配置
            exam_config = ExamConfig.query.filter_by(
                is_default=True, is_active=True
            ).first()

        if not exam_config:
            # 如果没有配置，使用默认值
            total_questions = 5
            time_limit = 75
            subject_filter = None
            difficulty_filter = None
            type_filter = None
        else:
            total_questions = exam_config.total_questions
            time_limit = exam_config.time_limit
            subject_filter = (
                exam_config.subject_filter.split(",")
                if exam_config.subject_filter
                else None
            )
            difficulty_filter = (
                exam_config.difficulty_filter.split(",")
                if exam_config.difficulty_filter
                else None
            )
            type_filter = (
                exam_config.type_filter.split(",") if exam_config.type_filter else None
            )

        # 从题库中抽取题目
        query = Question.query.filter_by(is_active=True)

        # 应用筛选条件
        if subject_filter:
            query = query.filter(Question.subject.in_(subject_filter))
        if difficulty_filter:
            query = query.filter(Question.difficulty.in_(difficulty_filter))
        if type_filter:
            query = query.filter(Question.question_type.in_(type_filter))

        # 随机抽取题目
        available_questions = query.all()
        if len(available_questions) < total_questions:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"题库中可用题目不足，需要{total_questions}题，但只有{len(available_questions)}题",
                    }
                ),
                400,
            )

        # 随机选择题目
        import random

        selected_questions = random.sample(available_questions, total_questions)

        # 创建考试记录
        exam = Exam(
            session_id=session_id,
            config_id=exam_config.id if exam_config else None,
            questions=json.dumps([], ensure_ascii=False),  # 题目将通过关联表存储
            time_limit=time_limit,
            status="active",
        )
        db.session.add(exam)
        db.session.flush()  # 获取exam.id

        # 创建考试题目关联
        exam_questions = []
        for i, question in enumerate(selected_questions):
            exam_question = ExamQuestion(
                exam_id=exam.id, question_id=question.id, question_order=i + 1
            )
            db.session.add(exam_question)
            exam_questions.append(question.to_dict())

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "exam_id": exam.id,
                "questions": exam_questions,
                "time_limit": exam.time_limit,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"生成考试失败: {str(e)}"}), 500


@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    """提交答案"""
    try:
        data = request.get_json()
        exam_id = data.get("exam_id")
        question_id = data.get("question_id")
        answer_text = data.get("answer", "")

        # 查找或创建答案记录
        answer = Answer.query.filter_by(
            exam_id=exam_id, question_id=question_id
        ).first()

        if answer:
            answer.answer_text = answer_text
            answer.submitted_at = datetime.utcnow()
        else:
            answer = Answer(
                exam_id=exam_id,
                question_id=question_id,
                answer_text=answer_text,
                submitted_at=datetime.utcnow(),
            )
            db.session.add(answer)

        db.session.commit()

        return jsonify({"success": True, "message": "答案提交成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"提交答案失败: {str(e)}"}), 500


@app.route("/api/submit-exam", methods=["POST"])
def submit_exam():
    """提交整个考试"""
    try:
        data = request.get_json()
        exam_id = data.get("exam_id")
        instance_id = data.get("instance_id")
        answers = data.get("answers", {})

        # 支持新旧两种模式
        if instance_id:
            return submit_exam_instance(instance_id, answers)
        elif exam_id:
            return submit_exam_legacy(exam_id, answers)
        else:
            return jsonify({"success": False, "message": "缺少考试ID或实例ID"}), 400

    except Exception as e:
        db.session.rollback()
        print(f"❌ 提交考试失败: {str(e)}")
        return jsonify({"success": False, "message": f"提交考试失败: {str(e)}"}), 500


def submit_exam_instance(instance_id, answers):
    """提交考试实例"""
    try:
        # 获取考试实例
        instance = ExamInstance.query.get(instance_id)
        if not instance:
            return jsonify({"success": False, "message": "考试实例不存在"}), 404

        # 保存所有答案
        for question_id, answer_text in answers.items():
            answer = Answer.query.filter_by(
                exam_instance_id=instance_id, question_id=question_id
            ).first()

            if answer:
                answer.answer_text = answer_text
                answer.submitted_at = datetime.utcnow()
            else:
                answer = Answer(
                    exam_instance_id=instance_id,
                    question_id=question_id,
                    answer_text=answer_text,
                    submitted_at=datetime.utcnow(),
                )
                db.session.add(answer)

        # 获取考试题目
        questions_data = json.loads(instance.questions)
        questions = []
        for q_data in questions_data:
            question = Question.query.get(q_data["id"])
            if question:
                questions.append(question.to_dict())

        # 计算成绩
        scoring = get_scoring_system()
        scores = scoring.calculate_scores_for_instance(instance_id, questions, answers)

        # 更新考试实例状态
        instance.status = "completed"
        instance.completed_at = datetime.utcnow()
        instance.score = scores.get("total_score", 0)
        instance.total_score = scores.get("max_score", 0)
        instance.percentage = scores.get("percentage_score", 0)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "考试提交成功",
                "instance_id": instance_id,
                "scores": scores,
                "redirect_url": f"/completion?instance_id={instance_id}",
            }
        )

    except Exception as e:
        db.session.rollback()
        raise e


def submit_exam_legacy(exam_id, answers):
    """提交考试（旧版兼容）"""
    try:
        # 获取考试记录
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"success": False, "message": "考试不存在"}), 404

        # 保存所有答案
        for question_id, answer_text in answers.items():
            answer = Answer.query.filter_by(
                exam_id=exam_id, question_id=question_id
            ).first()

            if answer:
                answer.answer_text = answer_text
                answer.submitted_at = datetime.utcnow()
            else:
                answer = Answer(
                    exam_id=exam_id,
                    question_id=question_id,
                    answer_text=answer_text,
                    submitted_at=datetime.utcnow(),
                )
                db.session.add(answer)

        # 获取考试题目（从关联表）
        exam_questions = (
            ExamQuestion.query.filter_by(exam_id=exam_id)
            .order_by(ExamQuestion.question_order)
            .all()
        )
        questions = []
        for eq in exam_questions:
            question = eq.question
            if question and question.is_active:
                questions.append(question.to_dict())

        # 计算成绩
        scoring = get_scoring_system()
        scores = scoring.calculate_scores(exam_id, questions, answers)

        # 更新考试状态
        exam.status = "completed"
        exam.completed_at = datetime.utcnow()
        exam.scores = json.dumps(scores, ensure_ascii=False)

        # 更新学生状态
        student = exam.session.student
        student.has_taken_exam = True

        # 创建学生答题记录
        total_score = scores.get("total_score", 0) if scores else 0
        max_score = (
            scores.get("max_score", len(questions) * 5)
            if scores
            else len(questions) * 5
        )
        correct_count = (
            sum(1 for q_score in (scores.get("question_scores", []) if scores else []))
            if scores
            else 0
        )
        total_questions = len(questions)

        # 计算考试用时
        start_time = exam.started_at
        end_time = datetime.utcnow()
        duration_minutes = (
            int((end_time - start_time).total_seconds() / 60) if start_time else 0
        )

        student_record = StudentExamRecord(
            student_id=student.id,
            exam_id=exam_id,
            total_score=total_score,
            max_score=max_score,
            correct_count=correct_count,
            total_questions=total_questions,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            status="completed",
        )
        db.session.add(student_record)

        db.session.commit()

        # 检查考试配置是否允许显示成绩
        show_results = True  # 默认显示成绩
        if exam.config_id:
            config = ExamConfig.query.get(exam.config_id)
            if config:
                show_results = getattr(config, "show_results", True)

        response_data = {
            "success": True,
            "scores": scores,
            "total_score": scores.get("total_score", 0),
            "message": "考试提交成功",
            "show_results": show_results,
        }

        # 根据配置决定重定向页面
        if show_results:
            response_data["redirect_url"] = f"/results/{exam_id}"
        else:
            response_data["redirect_url"] = f"/completion?exam_id={exam_id}"

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"提交考试失败: {str(e)}"}), 500


@app.route("/api/exam-instance-questions/<int:instance_id>")
def get_exam_instance_questions(instance_id):
    """获取考试实例题目"""
    try:
        instance = ExamInstance.query.get_or_404(instance_id)

        if not instance.questions:
            return jsonify({"success": False, "message": "考试实例没有题目"}), 400

        questions_data = json.loads(instance.questions)
        questions = []

        for q_data in questions_data:
            question = Question.query.get(q_data["id"])
            if question:
                question_dict = question.to_dict()
                question_dict["order"] = q_data.get("order", 0)
                question_dict["points"] = q_data.get("points", 1.0)
                questions.append(question_dict)

        # 按顺序排序
        questions.sort(key=lambda x: x.get("order", 0))

        # 计算剩余时间
        time_remaining_seconds = instance.get_time_remaining()

        return jsonify(
            {
                "success": True,
                "questions": questions,
                "instance_info": {
                    "id": instance.id,
                    "name": instance.name,
                    "description": instance.description,
                    "time_limit": (
                        instance.template.time_limit if instance.template else 75
                    ),
                    "time_remaining": time_remaining_seconds,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取考试实例题目失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-questions/<int:exam_id>")
def get_exam_questions(exam_id):
    """获取考试题目（旧版兼容）"""
    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"success": False, "message": "考试不存在"}), 404

        # 从关联表获取题目
        exam_questions = (
            ExamQuestion.query.filter_by(exam_id=exam_id)
            .order_by(ExamQuestion.question_order)
            .all()
        )
        questions = []

        for eq in exam_questions:
            question = eq.question
            if question and question.is_active:
                questions.append(question.to_dict())

        return jsonify(
            {
                "success": True,
                "questions": questions,
                "time_limit": exam.time_limit,
                "status": exam.status,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"获取题目失败: {str(e)}"}), 500


@app.route("/api/exam-status/<int:exam_id>")
def get_exam_status(exam_id):
    """获取考试状态"""
    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"success": False, "message": "考试不存在"}), 404

        # 获取答题数量
        questions_answered = len(exam.answers)

        # 获取总题目数量
        questions_data = json.loads(exam.questions) if exam.questions else []
        total_questions = len(questions_data)

        # 计算用时
        time_spent_minutes = 0
        if exam.started_at:
            if exam.completed_at:
                # 已完成的考试
                time_spent = exam.completed_at - exam.started_at
                time_spent_minutes = round(time_spent.total_seconds() / 60, 1)
            else:
                # 进行中的考试
                time_spent = datetime.utcnow() - exam.started_at
                time_spent_minutes = round(time_spent.total_seconds() / 60, 1)

        # 解析成绩数据
        score_data = {}
        if exam.scores:
            try:
                score_data = json.loads(exam.scores)
            except:
                pass

        return jsonify(
            {
                "success": True,
                "status": exam.status,
                "time_remaining": exam.get_time_remaining(),
                "total_questions": total_questions,
                "questions_answered": questions_answered,
                "time_spent_minutes": time_spent_minutes,
                "score": score_data.get("score", 0),
                "total_score": score_data.get("total_score", total_questions),
                "percentage": score_data.get("percentage", 0),
                "completed_at": (
                    exam.completed_at.isoformat() if exam.completed_at else None
                ),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"获取状态失败: {str(e)}"}), 500


@app.route("/api/exam-instance-status/<int:instance_id>")
def get_exam_instance_status(instance_id):
    """获取考试实例状态"""
    try:
        instance = ExamInstance.query.get(instance_id)
        if not instance:
            return jsonify({"success": False, "message": "考试实例不存在"}), 404

        # 获取答题数量
        answered_count = Answer.query.filter_by(exam_instance_id=instance_id).count()

        # 获取总题目数量
        questions_data = json.loads(instance.questions) if instance.questions else []
        total_questions = len(questions_data)

        # 计算用时
        time_spent_minutes = 0
        if instance.started_at:
            if instance.completed_at:
                # 已完成的考试
                time_spent = instance.completed_at - instance.started_at
                time_spent_minutes = round(time_spent.total_seconds() / 60, 1)
            else:
                # 进行中的考试
                time_spent = datetime.utcnow() - instance.started_at
                time_spent_minutes = round(time_spent.total_seconds() / 60, 1)

        return jsonify(
            {
                "success": True,
                "status": instance.status,
                "total_questions": total_questions,
                "questions_answered": answered_count,
                "time_spent_minutes": time_spent_minutes,
                "score": instance.score,
                "total_score": instance.total_score,
                "percentage": instance.percentage,
                "name": instance.name,
                "description": instance.description,
                "started_at": (
                    instance.started_at.isoformat() if instance.started_at else None
                ),
                "completed_at": (
                    instance.completed_at.isoformat() if instance.completed_at else None
                ),
                "template_time_limit": (
                    instance.template.time_limit if instance.template else 60
                ),
            }
        )

    except Exception as e:
        print(f"❌ 获取考试实例状态失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取状态失败: {str(e)}"}), 500


@app.route("/api/exam-results/<int:exam_id>")
def get_exam_results(exam_id):
    """获取考试结果"""
    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"success": False, "message": "考试不存在"}), 404

        scores = json.loads(exam.scores) if exam.scores else {}

        return jsonify(
            {
                "success": True,
                "exam": {
                    "id": exam.id,
                    "status": exam.status,
                    "completed_at": (
                        exam.completed_at.isoformat() if exam.completed_at else None
                    ),
                },
                "scores": scores,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"获取结果失败: {str(e)}"}), 500


# 管理员API
@app.route("/api/admin/login", methods=["POST"])
def admin_login_api():
    """管理员登录API"""
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        # 简单的管理员验证
        if username == "admin" and password == "imbagogo":
            # 设置管理员会话
            session["admin_logged_in"] = True
            session["admin_username"] = username
            session.permanent = True  # 设置会话为永久

            return jsonify({"success": True, "message": "登录成功"})
        else:
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401

    except Exception as e:
        return jsonify({"success": False, "message": f"登录失败: {str(e)}"}), 500


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    """管理员登出API"""
    try:
        session.pop("admin_logged_in", None)
        session.pop("admin_username", None)
        return jsonify({"success": True, "message": "登出成功"})
    except Exception as e:
        return jsonify({"success": False, "message": f"登出失败: {str(e)}"}), 500


@app.route("/api/admin/status")
def admin_status():
    """检查管理员登录状态"""
    return jsonify(
        {
            "success": True,
            "is_admin": is_admin(),
            "logged_in": is_admin(),  # 同时返回logged_in字段保持兼容性
            "is_logged_in": is_admin(),  # 再添加is_logged_in字段保持兼容性
            "username": session.get("admin_username", ""),
        }
    )


@app.route("/api/admin/start-exam", methods=["POST"])
@admin_required
def admin_start_exam():
    """管理员直接开始考试"""
    try:
        # 生成管理员测试数据
        import time

        timestamp = int(time.time())

        # 创建或更新管理员测试学生记录
        admin_student = Student.query.filter_by(id_number="110101199001011234").first()

        if admin_student:
            # 更新现有记录
            admin_student.name = "管理员测试"
            admin_student.application_number = f"ADMIN_{timestamp}"
            admin_student.device_ip = "127.0.0.1"
            admin_student.device_id = f"ADMIN_DEV_{timestamp}"
            admin_student.has_taken_exam = False
        else:
            # 创建新记录
            admin_student = Student(
                name="管理员测试",
                id_number="110101199001011234",
                application_number=f"ADMIN_{timestamp}",
                device_ip="127.0.0.1",
                device_id=f"ADMIN_DEV_{timestamp}",
                has_taken_exam=False,
            )
            db.session.add(admin_student)
            db.session.flush()

        # 创建考试会话
        exam_session = ExamSession(
            student_id=admin_student.id,
            device_ip="127.0.0.1",
            device_id=f"ADMIN_DEV_{timestamp}",
            status="verified",
        )
        db.session.add(exam_session)
        db.session.commit()

        # 从题库中抽取题目
        # 获取默认考试配置
        exam_config = ExamConfig.query.filter_by(
            is_default=True, is_active=True
        ).first()

        if exam_config:
            total_questions = exam_config.total_questions
            time_limit = exam_config.time_limit
            subject_filter = (
                exam_config.subject_filter.split(",")
                if exam_config.subject_filter
                else None
            )
            difficulty_filter = (
                exam_config.difficulty_filter.split(",")
                if exam_config.difficulty_filter
                else None
            )
            type_filter = (
                exam_config.type_filter.split(",") if exam_config.type_filter else None
            )
        else:
            # 使用默认值
            total_questions = 5
            time_limit = 75
            subject_filter = None
            difficulty_filter = None
            type_filter = None

        # 从题库中抽取题目
        query = Question.query.filter_by(is_active=True)

        # 应用筛选条件
        if subject_filter:
            query = query.filter(Question.subject.in_(subject_filter))
        if difficulty_filter:
            query = query.filter(Question.difficulty.in_(difficulty_filter))
        if type_filter:
            query = query.filter(Question.question_type.in_(type_filter))

        # 随机抽取题目
        available_questions = query.all()
        if len(available_questions) < total_questions:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"题库中可用题目不足，需要{total_questions}题，但只有{len(available_questions)}题",
                    }
                ),
                400,
            )

        # 随机选择题目
        import random

        selected_questions = random.sample(available_questions, total_questions)

        # 创建考试记录
        exam = Exam(
            session_id=exam_session.id,
            config_id=exam_config.id if exam_config else None,
            questions=json.dumps([], ensure_ascii=False),  # 题目将通过关联表存储
            time_limit=time_limit,
            status="active",
        )
        db.session.add(exam)
        db.session.flush()  # 获取exam.id

        # 创建考试题目关联
        exam_questions = []
        for i, question in enumerate(selected_questions):
            exam_question = ExamQuestion(
                exam_id=exam.id, question_id=question.id, question_order=i + 1
            )
            db.session.add(exam_question)
            exam_questions.append(question.to_dict())

        db.session.commit()

        return jsonify({"success": True, "exam_id": exam.id, "message": "考试生成成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"生成考试失败: {str(e)}"}), 500


@app.route("/api/admin/get-models", methods=["POST"])
def get_ai_models():
    """获取AI模型列表"""
    try:
        data = request.get_json()
        provider = data.get("provider", "openrouter")

        # 不同提供商的模型列表
        models = {
            "openrouter": [
                {
                    "id": "openai/gpt-4-turbo-preview",
                    "name": "GPT-4 Turbo",
                    "recommended": True,
                },
                {
                    "id": "anthropic/claude-3-sonnet",
                    "name": "Claude-3 Sonnet",
                    "recommended": True,
                },
                {"id": "google/gemini-pro", "name": "Gemini Pro", "recommended": False},
                {
                    "id": "meta-llama/llama-2-70b-chat",
                    "name": "Llama-2 70B",
                    "recommended": False,
                },
                {
                    "id": "openai/gpt-3.5-turbo",
                    "name": "GPT-3.5 Turbo",
                    "recommended": False,
                },
                {
                    "id": "anthropic/claude-3-haiku",
                    "name": "Claude-3 Haiku",
                    "recommended": False,
                },
            ],
            "openai": [
                {
                    "id": "gpt-4-turbo-preview",
                    "name": "GPT-4 Turbo",
                    "recommended": True,
                },
                {"id": "gpt-4", "name": "GPT-4", "recommended": True},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "recommended": False},
            ],
            "anthropic": [
                {
                    "id": "claude-3-sonnet-20240229",
                    "name": "Claude-3 Sonnet",
                    "recommended": True,
                },
                {
                    "id": "claude-3-haiku-20240307",
                    "name": "Claude-3 Haiku",
                    "recommended": False,
                },
                {"id": "claude-2.1", "name": "Claude-2.1", "recommended": False},
            ],
            "google": [
                {"id": "gemini-pro", "name": "Gemini Pro", "recommended": True},
                {
                    "id": "gemini-pro-vision",
                    "name": "Gemini Pro Vision",
                    "recommended": False,
                },
            ],
            "custom": [
                {"id": "custom-model", "name": "自定义模型", "recommended": False}
            ],
        }

        return jsonify(
            {"success": True, "models": models.get(provider, models["openrouter"])}
        )

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"获取模型列表失败: {str(e)}"}),
            500,
        )


@app.route("/api/admin/test-ai-model", methods=["POST"])
def test_ai_model():
    """测试AI模型连接"""
    try:
        data = request.get_json()
        provider = data.get("provider", "openrouter")
        model = data.get("model", "openai/gpt-4-turbo-preview")
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 2000)
        top_p = data.get("top_p", 0.9)
        frequency_penalty = data.get("frequency_penalty", 0)
        custom_config = data.get("custom_config", {})

        print(f"测试AI模型 - Provider: {provider}, Model: {model}")
        print(
            f"环境变量 OPENROUTER_API_KEY: {os.getenv('OPENROUTER_API_KEY', 'NOT_SET')[:20]}..."
        )

        # 使用AI生成器测试连接
        from ai_engine.generator import QuestionGenerator

        generator = QuestionGenerator()

        print(
            f"生成器API Key: {generator.api_key[:20] if generator.api_key else 'None'}..."
        )

        # 生成一个简单的测试题目
        test_question = generator._generate_single_question(
            subject_key="statistics",
            subject_info={"name": "统计学", "topics": ["基础概念"]},
            difficulty={"name": "高中水平", "key": "high_school"},
            cognitive_level={"name": "理解", "key": "understanding"},
            question_type={"name": "选择题", "key": "multiple_choice"},
            question_id=1,
        )

        if test_question:
            return jsonify(
                {
                    "success": True,
                    "message": "AI模型连接成功",
                    "test_question": test_question["content"][:200] + "...",
                }
            )
        else:
            return jsonify(
                {"success": False, "message": "AI模型连接失败 - 无法生成测试题目"}
            )

    except Exception as e:
        print(f"测试AI模型异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": f"测试失败: {str(e)}"}), 500


@app.route("/api/admin/save-config", methods=["POST"])
def save_admin_config():
    """保存管理员配置"""
    try:
        data = request.get_json()

        # 这里可以将配置保存到数据库或配置文件
        # 暂时只返回成功
        return jsonify({"success": True, "message": "配置保存成功"})

    except Exception as e:
        return jsonify({"success": False, "message": f"保存失败: {str(e)}"}), 500


@app.route("/results/<int:exam_id>")
def show_results(exam_id):
    """显示考试结果"""
    exam = Exam.query.get(exam_id)
    if not exam or exam.status != "completed":
        return redirect(url_for("index"))

    scores = json.loads(exam.scores) if exam.scores else {}
    return render_template("results.html", exam=exam, scores=scores)


@app.route("/completion")
def completion_page():
    """考试完成确认页面"""
    return render_template("completion.html")


@app.route("/exam_management.html")
@admin_required
def exam_management():
    """考试管理页面"""
    return render_template("exam_management.html")


@app.route("/exam_history_management.html")
@admin_required
def exam_history_management():
    """考试历史管理页面（重定向到新的考试管理页面）"""
    return redirect("/exam_management.html")


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


# ==================== 题库管理API ====================


@app.route("/api/questions", methods=["GET"])
@admin_required
def get_questions():
    """获取题库列表"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        subject = request.args.get("subject", "")
        sub_tag = request.args.get("sub_tag", "")
        language = request.args.get("language", "")
        difficulty = request.args.get("difficulty", "")
        question_type = request.args.get("type", "")
        is_active = request.args.get("is_active", None)
        search = request.args.get("search", "")

        query = Question.query

        # 筛选条件
        if subject:
            query = query.filter(Question.subject == subject)
        if sub_tag:
            query = query.filter(Question.sub_tag == sub_tag)
        if language:
            query = query.filter(Question.language == language)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        if question_type:
            query = query.filter(Question.question_type == question_type)
        if is_active is not None:
            query = query.filter(Question.is_active == (is_active.lower() == "true"))
        if search:
            query = query.filter(Question.content.contains(search))

        # 分页
        questions = query.order_by(Question.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "success": True,
                "questions": [q.to_dict() for q in questions.items],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": questions.total,
                    "pages": questions.pages,
                    "has_next": questions.has_next,
                    "has_prev": questions.has_prev,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/questions", methods=["POST"])
@admin_required
def create_question():
    """创建题目"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = [
            "subject",
            "difficulty",
            "cognitive_level",
            "question_type",
            "content",
        ]
        for field in required_fields:
            if not data.get(field):
                return (
                    jsonify({"success": False, "message": f"缺少必填字段: {field}"}),
                    400,
                )

        # 创建题目
        question = Question(
            subject=data["subject"],
            sub_tag=data.get("sub_tag", ""),
            language=data.get("language", "zh"),
            difficulty=data["difficulty"],
            cognitive_level=data["cognitive_level"],
            question_type=data["question_type"],
            content=data["content"],
            options=(
                json.dumps(data.get("options", [])) if data.get("options") else None
            ),
            correct_answer=data.get("correct_answer", ""),
            explanation=data.get("explanation", ""),
            points=data.get("points", 1),
            is_active=data.get("is_active", True),
        )

        db.session.add(question)
        db.session.commit()

        return jsonify(
            {"success": True, "message": "题目创建成功", "question": question.to_dict()}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/questions/<int:question_id>", methods=["GET"])
@admin_required
def get_question(question_id):
    """获取单个题目"""
    try:
        question = Question.query.get_or_404(question_id)
        return jsonify({"success": True, "question": question.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/questions/<int:question_id>", methods=["PUT"])
@admin_required
def update_question(question_id):
    """更新题目"""
    try:
        question = Question.query.get_or_404(question_id)
        data = request.get_json()

        # 更新字段
        if "subject" in data:
            question.subject = data["subject"]
        if "sub_tag" in data:
            question.sub_tag = data["sub_tag"]
        if "language" in data:
            question.language = data["language"]
        if "difficulty" in data:
            question.difficulty = data["difficulty"]
        if "cognitive_level" in data:
            question.cognitive_level = data["cognitive_level"]
        if "question_type" in data:
            question.question_type = data["question_type"]
        if "content" in data:
            question.content = data["content"]
        if "options" in data:
            question.options = json.dumps(data["options"]) if data["options"] else None
        if "correct_answer" in data:
            question.correct_answer = data["correct_answer"]
        if "explanation" in data:
            question.explanation = data["explanation"]
        if "points" in data:
            question.points = data["points"]
        if "is_active" in data:
            question.is_active = data["is_active"]

        question.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {"success": True, "message": "题目更新成功", "question": question.to_dict()}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/questions/<int:question_id>", methods=["DELETE"])
@admin_required
def delete_question(question_id):
    """删除题目"""
    try:
        question = Question.query.get_or_404(question_id)

        # 记录删除的题目信息
        print(f"🗑️  准备删除题目 ID: {question_id}")
        print(f"题目内容: {question.content[:100]}...")

        # 检查关联的记录数量
        template_questions_count = (
            len(question.template_questions)
            if hasattr(question, "template_questions")
            else 0
        )
        config_questions_count = (
            len(question.config_questions)
            if hasattr(question, "config_questions")
            else 0
        )
        exam_questions_count = (
            len(question.exam_questions) if hasattr(question, "exam_questions") else 0
        )
        student_answers_count = (
            len(question.student_answers) if hasattr(question, "student_answers") else 0
        )

        print(
            f"关联记录: 模板题目({template_questions_count}), 配置题目({config_questions_count}), 考试题目({exam_questions_count}), 学生答案({student_answers_count})"
        )

        # 删除题目（级联删除会自动处理关联记录）
        db.session.delete(question)
        db.session.commit()

        print(f"✅ 题目 {question_id} 删除成功")
        return jsonify({"success": True, "message": "题目删除成功"})

    except Exception as e:
        db.session.rollback()
        print(f"❌ 删除题目 {question_id} 失败: {str(e)}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500


@app.route("/api/questions/batch-update", methods=["PUT"])
@admin_required
def batch_update_questions():
    """批量更新题目"""
    try:
        data = request.get_json()
        question_ids = data.get("question_ids", [])
        update_data = {k: v for k, v in data.items() if k != "question_ids"}

        if not question_ids:
            return jsonify({"success": False, "message": "请选择要更新的题目"}), 400

        # 更新题目
        updated_count = 0
        for question_id in question_ids:
            question = Question.query.get(question_id)
            if question:
                for key, value in update_data.items():
                    if hasattr(question, key):
                        setattr(question, key, value)
                question.updated_at = datetime.utcnow()
                updated_count += 1

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"成功更新 {updated_count} 道题目",
                "updated_count": updated_count,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"批量更新失败: {str(e)}"}), 500


@app.route("/api/questions/batch-delete", methods=["DELETE"])
@admin_required
def batch_delete_questions():
    """批量删除题目"""
    try:
        data = request.get_json()
        question_ids = data.get("question_ids", [])

        if not question_ids:
            return jsonify({"success": False, "message": "请选择要删除的题目"}), 400

        deleted_count = 0
        for question_id in question_ids:
            question = Question.query.get(question_id)
            if question:
                db.session.delete(question)
                deleted_count += 1

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"成功删除 {deleted_count} 道题目",
                "deleted_count": deleted_count,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"批量删除失败: {str(e)}"}), 500


@app.route("/api/questions/clear-all", methods=["DELETE"])
@admin_required
def clear_all_questions():
    """清空所有题目"""
    try:
        # 获取总数
        total_count = Question.query.count()

        if total_count == 0:
            return jsonify({"success": False, "message": "题库中没有题目"}), 400

        # 删除所有题目
        Question.query.delete()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"成功清空题库，共删除 {total_count} 道题目",
                "deleted_count": total_count,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"清空题库失败: {str(e)}"}), 500


@app.route("/api/questions/batch", methods=["POST"])
@admin_required
def batch_create_questions():
    """批量创建题目"""
    try:
        data = request.get_json()
        questions_data = data.get("questions", [])

        if not questions_data:
            return jsonify({"success": False, "message": "没有提供题目数据"}), 400

        created_questions = []
        for q_data in questions_data:
            question = Question(
                subject=q_data.get("subject", "默认学科"),
                sub_tag=q_data.get("sub_tag", ""),
                language=q_data.get("language", "zh"),
                difficulty=q_data.get("difficulty", "中等"),
                cognitive_level=q_data.get("cognitive_level", "理解"),
                question_type=q_data.get("question_type", "short_answer"),
                content=q_data.get("content", ""),
                options=(
                    json.dumps(q_data.get("options", []))
                    if q_data.get("options")
                    else None
                ),
                correct_answer=q_data.get("correct_answer", ""),
                explanation=q_data.get("explanation", ""),
                points=q_data.get("points", 1),
                is_active=q_data.get("is_active", True),
            )
            db.session.add(question)
            created_questions.append(question)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"成功创建 {len(created_questions)} 道题目",
                "questions": [q.to_dict() for q in created_questions],
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/questions/ai-generate", methods=["POST"])
@admin_required
def ai_generate_questions():
    """智能AI生成题目 - 新版本"""
    try:
        data = request.get_json()
        count = data.get("count", 5)
        subject = data.get("subject", "数学")
        sub_domain = data.get("sub_domain", "")
        language = data.get("language", "zh")
        difficulty = data.get("difficulty", "undergraduate_basic")
        question_type = data.get("question_type", "multiple_choice")
        use_scenarios = data.get("use_scenarios", False)
        custom_prompt = data.get("custom_prompt", "")
        points_per_question = data.get("points_per_question", 1)

        # 向后兼容旧版本API
        if "types" in data and data["types"]:
            question_type = data["types"][0]

        # 向后兼容旧版本sub_tag参数
        if "sub_tag" in data and data["sub_tag"]:
            sub_domain = data["sub_tag"]

        # 难度映射（向后兼容）
        difficulty_mapping = {
            "简单": "high_school",
            "中等": "undergraduate_basic",
            "困难": "undergraduate_advanced",
            "gre_math": "gre_level",
            "graduate_study": "graduate_study",
        }
        if difficulty in difficulty_mapping:
            difficulty = difficulty_mapping[difficulty]

        if count > 20:
            return (
                jsonify({"success": False, "message": "单次生成题目数量不能超过20道"}),
                400,
            )

        print(f"🎯 智能AI生成题目请求:")
        print(f"学科: {subject}, 子领域: {sub_domain}")
        print(f"难度: {difficulty}, 题型: {question_type}")
        print(f"语言: {language}, 场景题目: {use_scenarios}")
        print(f"数量: {count}, 自定义提示: {custom_prompt[:50]}...")

        # 检查API状态
        try:
            print("🔍 开始检查API状态...")
            from ai_engine.smart_generator import SmartQuestionGenerator

            print("📋 初始化SmartQuestionGenerator...")
            generator = SmartQuestionGenerator()
            print("✅ SmartQuestionGenerator初始化成功")

            print("📊 获取API状态...")
            api_status = generator.get_api_status()
            print(f"📈 API状态: {api_status}")

            if not api_status["available"]:
                print(f"❌ API不可用: {api_status['message']}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": api_status["message"],
                            "error_type": "api_not_configured",
                            "redirect_to": "/admin_dashboard.html#system-settings",
                        }
                    ),
                    400,
                )

            print(f"✅ API状态检查通过: {api_status['message']}")
        except Exception as api_check_error:
            print(f"❌ API状态检查失败: {str(api_check_error)}")
            import traceback

            traceback.print_exc()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"无法检查API状态: {str(api_check_error)}",
                        "error_type": "api_check_failed",
                        "redirect_to": "/admin_dashboard.html#system-settings",
                    }
                ),
                500,
            )

        # 使用新的智能生成器
        try:
            from ai_engine.smart_generator import generate_questions_with_config

            print(f"🤖 使用智能AI生成器生成 {count} 道题目...")
            generated_questions = generate_questions_with_config(
                subject=subject,
                difficulty=difficulty,
                question_type=question_type,
                language=language,
                count=count,
                use_scenarios=use_scenarios,
                sub_domain=sub_domain,
                custom_prompt=custom_prompt,
                points_per_question=points_per_question,
            )

            print(f"✅ 智能生成器成功生成 {len(generated_questions)} 道题目")

            # 检查生成数量是否足够
            if len(generated_questions) < count:
                print(
                    f"⚠️  生成数量不足：期望 {count} 道，实际 {len(generated_questions)} 道"
                )

                # 尝试补充生成
                remaining_count = count - len(generated_questions)
                print(f"🔄 尝试补充生成 {remaining_count} 道题目...")

                additional_questions = generate_questions_with_config(
                    subject=subject,
                    difficulty=difficulty,
                    question_type=question_type,
                    language=language,
                    count=remaining_count,
                    use_scenarios=use_scenarios,
                    sub_domain=sub_domain,
                    custom_prompt=custom_prompt,
                    points_per_question=points_per_question,
                )

                generated_questions.extend(additional_questions)
                print(f"🔄 补充生成后总数: {len(generated_questions)} 道题目")

        except Exception as e:
            print(f"❌ 智能生成器失败: {str(e)}")
            # 直接返回错误，不再降级到旧版生成器
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"AI生成器失败: {str(e)}。请检查API配置或稍后重试。",
                    }
                ),
                500,
            )

        # 保存生成的题目
        created_questions = []
        for q_data in generated_questions:
            # 兼容新旧生成器的字段名
            question_sub_tag = q_data.get("sub_tag", sub_domain) or sub_domain
            question_difficulty = q_data.get("difficulty", difficulty)
            question_cognitive_level = q_data.get("cognitive_level", "理解")

            question = Question(
                subject=q_data.get("subject", subject),
                sub_tag=question_sub_tag,
                language=q_data.get("language", language),
                difficulty=question_difficulty,
                cognitive_level=question_cognitive_level,
                question_type=q_data.get("question_type", question_type),
                content=q_data.get("content", ""),
                options=(
                    json.dumps(q_data.get("options", []))
                    if q_data.get("options")
                    else None
                ),
                correct_answer=q_data.get("correct_answer", ""),
                explanation=q_data.get("explanation", ""),
                points=q_data.get("points", points_per_question),
                is_active=True,
            )
            db.session.add(question)
            created_questions.append(question)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"成功生成 {len(created_questions)} 道题目",
                "generated_count": len(created_questions),
                "questions": [q.to_dict() for q in created_questions],
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/questions/ai-config", methods=["GET"])
@admin_required
def get_ai_generation_config():
    """获取AI生题配置选项"""
    try:
        from ai_engine.smart_generator import SmartQuestionGenerator

        generator = SmartQuestionGenerator()

        config = {
            "subjects": generator.get_available_subjects(),
            "difficulty_levels": generator.get_difficulty_levels(),
            "question_types": generator.get_question_types(),
            "languages": {
                "zh": {"name": "中文", "name_en": "Chinese"},
                "en": {"name": "English", "name_en": "English"},
            },
        }

        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def _generate_mock_questions(
    count,
    subject,
    sub_tag,
    difficulty,
    cognitive_level,
    types,
    language="zh",
    custom_prompt="",
):
    """生成模拟题目数据"""
    mock_questions = []

    # 解析自定义提示词中的关键词
    custom_keywords = []
    if custom_prompt:
        print(f"应用自定义提示词: {custom_prompt}")
        # 检查常见的自定义要求
        if "英文" in custom_prompt or "english" in custom_prompt.lower():
            language = "en"
        if "概率" in custom_prompt or "probability" in custom_prompt.lower():
            custom_keywords.append("概率")
        if "统计" in custom_prompt or "statistics" in custom_prompt.lower():
            custom_keywords.append("统计")
        if "微积分" in custom_prompt or "calculus" in custom_prompt.lower():
            custom_keywords.append("微积分")

    for i in range(count):
        question_type = types[i % len(types)] if types else "short_answer"

        if language == "en":
            # 英文题目，根据自定义提示词调整内容
            if question_type == "multiple_choice":
                # 根据关键词生成更相关的题目
                if "概率" in custom_keywords or "probability" in custom_prompt.lower():
                    content = f"What is the probability of getting heads in {i+1} coin tosses?"
                    options = ["0.5", "0.25", "0.75", "1.0"]
                    correct_answer = "0.5"
                    explanation = "The probability of getting heads in any coin toss is always 0.5 or 50%."
                elif "统计" in custom_keywords or "statistics" in custom_prompt.lower():
                    content = f"Which measure of central tendency is most affected by outliers?"
                    options = ["Mean", "Median", "Mode", "Range"]
                    correct_answer = "Mean"
                    explanation = "The mean is most affected by outliers because it takes into account all values."
                else:
                    # 默认题目，但添加自定义要求
                    custom_desc = (
                        f" (Custom requirement: {custom_prompt[:50]}...)"
                        if custom_prompt
                        else ""
                    )
                    content = f"Question {i+1} about {subject} - {difficulty} level{custom_desc}"
                    options = ["Option A", "Option B", "Option C", "Option D"]
                    correct_answer = "Option A"
                    explanation = (
                        f"This is a {difficulty} difficulty question about {subject}."
                    )

                mock_questions.append(
                    {
                        "subject": subject,
                        "sub_tag": sub_tag,
                        "language": language,
                        "difficulty": difficulty,
                        "cognitive_level": (
                            cognitive_level if cognitive_level else "Understanding"
                        ),
                        "question_type": "multiple_choice",
                        "content": content,
                        "options": options,
                        "correct_answer": correct_answer,
                        "explanation": explanation,
                        "points": 1,
                    }
                )
            elif question_type == "short_answer":
                mock_questions.append(
                    {
                        "subject": subject,
                        "sub_tag": sub_tag,
                        "language": language,
                        "difficulty": difficulty,
                        "cognitive_level": (
                            cognitive_level if cognitive_level else "Application"
                        ),
                        "question_type": "short_answer",
                        "content": f'Please briefly answer: This is question {i+1} about {subject} with {difficulty} difficulty level{f" focusing on {sub_tag}" if sub_tag else ""}.',
                        "correct_answer": f"This is the reference answer for question {i+1}.",
                        "explanation": f"This is the detailed explanation for question {i+1}.",
                        "points": 2,
                    }
                )
            else:  # programming
                mock_questions.append(
                    {
                        "subject": subject,
                        "sub_tag": sub_tag,
                        "language": language,
                        "difficulty": difficulty,
                        "cognitive_level": (
                            cognitive_level if cognitive_level else "Application"
                        ),
                        "question_type": "programming",
                        "content": f'Please write code to solve: This is question {i+1} about {subject} with {difficulty} difficulty level{f" focusing on {sub_tag}" if sub_tag else ""}.',
                        "correct_answer": f"def solution{i+1}():\n    # Code implementation\n    pass",
                        "explanation": f"This is the explanation for programming question {i+1}.",
                        "points": 5,
                    }
                )
        else:
            # 中文题目，根据自定义提示词调整内容
            if question_type == "multiple_choice":
                # 根据关键词生成更相关的题目
                if "概率" in custom_keywords:
                    content = f"抛硬币{i+1}次，每次都得到正面的概率是多少？"
                    options = ["1/2", f"1/{2**(i+1)}", "1/4", "1/8"]
                    correct_answer = f"1/{2**(i+1)}"
                    explanation = f"连续{i+1}次抛硬币都得到正面的概率是 (1/2)^{i+1} = 1/{2**(i+1)}"
                elif "统计" in custom_keywords:
                    content = f"下列哪个统计量最容易受到异常值影响？"
                    options = ["平均数", "中位数", "众数", "四分位数"]
                    correct_answer = "平均数"
                    explanation = "平均数会受到所有数值的影响，包括异常值，因此最容易受到异常值影响。"
                elif "微积分" in custom_keywords:
                    content = f"函数 f(x) = x^{i+2} 的导数是什么？"
                    options = [f"{i+2}x^{i+1}", f"x^{i+1}", f"{i+1}x^{i}", f"x^{i+3}"]
                    correct_answer = f"{i+2}x^{i+1}"
                    explanation = f"根据幂函数求导法则，f(x) = x^{i+2} 的导数为 f'(x) = {i+2}x^{i+1}"
                else:
                    # 默认题目，但添加自定义要求说明
                    custom_desc = (
                        f"（用户要求：{custom_prompt[:30]}...）"
                        if custom_prompt
                        else ""
                    )
                    content = f'这是第{i+1}道{subject}学科的{difficulty}难度选择题{f"，重点考察{sub_tag}相关内容" if sub_tag else ""}{custom_desc}'
                    options = ["选项A", "选项B", "选项C", "选项D"]
                    correct_answer = "选项A"
                    explanation = f'这是第{i+1}道题的解析。{custom_prompt[:50] if custom_prompt else ""}'

                mock_questions.append(
                    {
                        "subject": subject,
                        "sub_tag": sub_tag,
                        "language": language,
                        "difficulty": difficulty,
                        "cognitive_level": "理解",  # 固定设置为理解
                        "question_type": "multiple_choice",
                        "content": content,
                        "options": options,
                        "correct_answer": correct_answer,
                        "explanation": explanation,
                        "points": 1,
                    }
                )
            elif question_type == "short_answer":
                mock_questions.append(
                    {
                        "subject": subject,
                        "sub_tag": sub_tag,
                        "language": language,
                        "difficulty": difficulty,
                        "cognitive_level": (
                            cognitive_level if cognitive_level else "应用"
                        ),
                        "question_type": "short_answer",
                        "content": f'请简要回答：这是第{i+1}道{subject}学科的{difficulty}难度简答题{f"，重点考察{sub_tag}相关内容" if sub_tag else ""}',
                        "correct_answer": f"这是第{i+1}道题的参考答案",
                        "explanation": f"这是第{i+1}道题的详细解析",
                        "points": 2,
                    }
                )
            else:  # programming
                mock_questions.append(
                    {
                        "subject": subject,
                        "sub_tag": sub_tag,
                        "language": language,
                        "difficulty": difficulty,
                        "cognitive_level": (
                            cognitive_level if cognitive_level else "应用"
                        ),
                        "question_type": "programming",
                        "content": f'请编写代码解决：这是第{i+1}道{subject}学科的{difficulty}难度编程题{f"，重点考察{sub_tag}相关内容" if sub_tag else ""}',
                        "correct_answer": f"def solution{i+1}():\n    # 代码实现\n    pass",
                        "explanation": f"这是第{i+1}道编程题的解析",
                        "points": 5,
                    }
                )

    return mock_questions


# ==================== 考试配置管理API ====================


@app.route("/api/exam-configs", methods=["GET"])
def get_exam_configs():
    """获取考试配置列表"""
    try:
        configs = ExamConfig.query.order_by(ExamConfig.created_at.desc()).all()
        return jsonify(
            {
                "success": True,
                "configs": [
                    {
                        "id": config.id,
                        "name": config.name,
                        "description": config.description,
                        "total_questions": config.total_questions,
                        "time_limit": config.time_limit,
                        "subject_filter": config.subject_filter,
                        "difficulty_filter": config.difficulty_filter,
                        "type_filter": config.type_filter,
                        "is_default": config.is_default,
                        "is_active": config.is_active,
                        "show_results": getattr(config, "show_results", True),
                        "created_at": config.created_at.isoformat(),
                    }
                    for config in configs
                ],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-configs", methods=["POST"])
@admin_required
def create_exam_config():
    """创建考试配置"""
    try:
        data = request.get_json()

        # 验证题目选择模式
        question_selection_mode = data.get("question_selection_mode", "filter")
        if question_selection_mode == "manual" and not data.get("question_ids"):
            return (
                jsonify({"success": False, "message": "手动选择模式下必须选择题目"}),
                400,
            )

        # 如果设置为默认配置，先取消其他默认配置
        if data.get("is_default"):
            ExamConfig.query.filter_by(is_default=True).update({"is_default": False})

        config = ExamConfig(
            name=data["name"],
            description=data.get("description", ""),
            total_questions=data.get("total_questions", 5),
            time_limit=data.get("time_limit", 75),
            subject_filter=data.get("subject_filter", ""),
            difficulty_filter=data.get("difficulty_filter", ""),
            type_filter=data.get("type_filter", ""),
            is_default=data.get("is_default", False),
            is_active=data.get("is_active", True),
            show_results=data.get("show_results", True),
            question_selection_mode=question_selection_mode,
            passing_score=data.get("passing_score", 60.0),
        )

        db.session.add(config)
        db.session.flush()  # 获取config.id

        # 如果是手动选择模式，添加选定的题目
        if question_selection_mode == "manual" and data.get("question_ids"):
            for i, question_id in enumerate(data["question_ids"]):
                config_question = ExamConfigQuestion(
                    config_id=config.id,
                    question_id=question_id,
                    question_order=i + 1,
                    points=data.get("points", 1.0),
                )
                db.session.add(config_question)

        db.session.commit()

        return jsonify(
            {"success": True, "message": "考试配置创建成功", "config": config.to_dict()}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-configs/<int:config_id>", methods=["PUT"])
@admin_required
def update_exam_config(config_id):
    """更新考试配置"""
    try:
        config = ExamConfig.query.get_or_404(config_id)
        data = request.get_json()

        # 验证题目选择模式
        if "question_selection_mode" in data:
            question_selection_mode = data["question_selection_mode"]
            if question_selection_mode == "manual" and not data.get("question_ids"):
                return (
                    jsonify(
                        {"success": False, "message": "手动选择模式下必须选择题目"}
                    ),
                    400,
                )

        # 如果设置为默认配置，先取消其他默认配置
        if data.get("is_default") and not config.is_default:
            ExamConfig.query.filter_by(is_default=True).update({"is_default": False})

        # 更新字段
        if "name" in data:
            config.name = data["name"]
        if "description" in data:
            config.description = data["description"]
        if "total_questions" in data:
            config.total_questions = data["total_questions"]
        if "time_limit" in data:
            config.time_limit = data["time_limit"]
        if "subject_filter" in data:
            config.subject_filter = data["subject_filter"]
        if "difficulty_filter" in data:
            config.difficulty_filter = data["difficulty_filter"]
        if "type_filter" in data:
            config.type_filter = data["type_filter"]
        if "is_default" in data:
            config.is_default = data["is_default"]
        if "is_active" in data:
            config.is_active = data["is_active"]
        if "show_results" in data:
            config.show_results = data["show_results"]
        if "question_selection_mode" in data:
            config.question_selection_mode = data["question_selection_mode"]
        if "passing_score" in data:
            config.passing_score = data["passing_score"]

        # 如果更新了题目选择模式或题目列表，更新关联的题目
        if "question_selection_mode" in data or "question_ids" in data:
            # 删除现有的题目关联
            ExamConfigQuestion.query.filter_by(config_id=config.id).delete()

            # 如果是手动选择模式，添加新的题目关联
            if config.question_selection_mode == "manual" and data.get("question_ids"):
                for i, question_id in enumerate(data["question_ids"]):
                    config_question = ExamConfigQuestion(
                        config_id=config.id,
                        question_id=question_id,
                        question_order=i + 1,
                        points=data.get("points", 1.0),
                    )
                    db.session.add(config_question)

        config.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {"success": True, "message": "考试配置更新成功", "config": config.to_dict()}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-configs/<int:config_id>", methods=["DELETE"])
@admin_required
def delete_exam_config(config_id):
    """删除考试配置"""
    try:
        config = ExamConfig.query.get_or_404(config_id)

        # 检查是否有考试使用此配置
        exams_using_config = Exam.query.filter_by(config_id=config_id).count()
        if exams_using_config > 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"无法删除配置，已有 {exams_using_config} 个考试使用此配置",
                    }
                ),
                400,
            )

        # 如果是默认配置，需要检查是否有其他配置可以设为默认
        if config.is_default:
            other_configs = ExamConfig.query.filter(ExamConfig.id != config_id).count()
            if other_configs > 0:
                # 自动将第一个其他配置设为默认
                new_default = ExamConfig.query.filter(
                    ExamConfig.id != config_id
                ).first()
                if new_default:
                    new_default.is_default = True

        # 真正删除配置
        db.session.delete(config)
        db.session.commit()

        return jsonify({"success": True, "message": "考试配置删除成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-configs/<int:config_id>/set-default", methods=["POST"])
@admin_required
def set_default_exam_config(config_id):
    """设置默认考试配置"""
    try:
        # 取消所有默认配置
        ExamConfig.query.filter_by(is_default=True).update({"is_default": False})

        # 设置新的默认配置
        config = ExamConfig.query.get_or_404(config_id)
        config.is_default = True
        db.session.commit()

        return jsonify({"success": True, "message": "默认配置设置成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-configs/<int:config_id>/questions", methods=["GET"])
@admin_required
def get_config_questions(config_id):
    """获取考试配置的题目列表"""
    try:
        config = ExamConfig.query.get_or_404(config_id)

        if config.question_selection_mode == "manual":
            # 手动选择模式：返回精确选择的题目
            config_questions = (
                ExamConfigQuestion.query.filter_by(config_id=config_id)
                .order_by(ExamConfigQuestion.question_order)
                .all()
            )
            questions = [cq.to_dict() for cq in config_questions]
        else:
            # 筛选模式：基于筛选条件动态获取题目
            query = Question.query.filter_by(is_active=True)

            if config.subject_filter:
                subjects = [
                    s.strip() for s in config.subject_filter.split(",") if s.strip()
                ]
                if subjects:
                    query = query.filter(Question.subject.in_(subjects))

            if config.difficulty_filter:
                difficulties = [
                    d.strip() for d in config.difficulty_filter.split(",") if d.strip()
                ]
                if difficulties:
                    query = query.filter(Question.difficulty.in_(difficulties))

            if config.type_filter:
                types = [t.strip() for t in config.type_filter.split(",") if t.strip()]
                if types:
                    query = query.filter(Question.type.in_(types))

            questions_list = query.limit(config.total_questions).all()
            questions = [
                {"question": q.to_dict(), "points": 1.0, "question_order": i + 1}
                for i, q in enumerate(questions_list)
            ]

        return jsonify(
            {"success": True, "questions": questions, "config": config.to_dict()}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# 学生答题记录管理API
@app.route("/api/student-records", methods=["GET"])
@admin_required
def get_student_records():
    """获取学生答题记录列表"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        status_filter = request.args.get("status", "")
        student_name = request.args.get("student_name", "")

        query = StudentExamRecord.query.join(Student)

        # 状态筛选
        if status_filter:
            query = query.filter(StudentExamRecord.status == status_filter)

        # 学生姓名筛选
        if student_name:
            query = query.filter(Student.name.contains(student_name))

        # 按创建时间倒序排列
        query = query.order_by(StudentExamRecord.created_at.desc())

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        records = [record.to_dict() for record in pagination.items]

        return jsonify(
            {
                "success": True,
                "records": records,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_prev": pagination.has_prev,
                    "has_next": pagination.has_next,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/student-records/<int:record_id>", methods=["GET"])
@admin_required
def get_student_record_detail(record_id):
    """获取学生答题记录详情"""
    try:
        record = StudentExamRecord.query.get_or_404(record_id)

        # 获取该考试的题目和答案
        exam_questions = (
            db.session.query(ExamQuestion, Question)
            .join(Question, ExamQuestion.question_id == Question.id)
            .filter(ExamQuestion.exam_id == record.exam_id)
            .all()
        )

        # 获取学生的答案
        answers = Answer.query.filter(Answer.exam_id == record.exam_id).all()
        answer_dict = {answer.question_id: answer for answer in answers}

        # 构建题目详情
        questions_detail = []
        for eq, question in exam_questions:
            answer = answer_dict.get(str(eq.question_order), None)
            questions_detail.append(
                {
                    "question_order": eq.question_order,
                    "question_id": question.id,
                    "content": question.content,
                    "question_type": question.question_type,
                    "options": json.loads(question.options) if question.options else [],
                    "correct_answer": question.correct_answer,
                    "student_answer": answer.answer_text if answer else "",
                    "is_correct": answer.is_correct if answer else False,
                    "score": answer.score if answer else 0,
                    "points": question.points,
                }
            )

        return jsonify(
            {"success": True, "record": record.to_dict(), "questions": questions_detail}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/student-records/statistics", methods=["GET"])
@admin_required
def get_student_records_statistics():
    """获取学生答题记录统计信息"""
    try:
        # 总记录数
        total_records = StudentExamRecord.query.count()

        # 按状态统计
        status_stats = (
            db.session.query(
                StudentExamRecord.status, db.func.count(StudentExamRecord.id)
            )
            .group_by(StudentExamRecord.status)
            .all()
        )

        # 平均分
        avg_score = (
            db.session.query(db.func.avg(StudentExamRecord.total_score))
            .filter(StudentExamRecord.status == "completed")
            .scalar()
            or 0
        )

        # 最高分
        max_score = (
            db.session.query(db.func.max(StudentExamRecord.total_score))
            .filter(StudentExamRecord.status == "completed")
            .scalar()
            or 0
        )

        # 最低分
        min_score = (
            db.session.query(db.func.min(StudentExamRecord.total_score))
            .filter(StudentExamRecord.status == "completed")
            .scalar()
            or 0
        )

        return jsonify(
            {
                "success": True,
                "statistics": {
                    "total_records": total_records,
                    "status_stats": dict(status_stats),
                    "avg_score": round(avg_score, 2),
                    "max_score": max_score,
                    "min_score": min_score,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 考试模板管理API（已废弃，功能已整合到 Exam Configuration） ====================


@app.route("/admin/exam-templates")
@admin_required
def exam_template_management():
    """考试模板管理页面 - 重定向到考试配置管理"""
    return redirect("/exam_config_management.html")


# @app.route('/admin/exam-instances')
# @admin_required
# def exam_instance_management():
#     """考试实例管理页面"""
#     return render_template('exam_instance_management.html')


@app.route("/api/exam-templates", methods=["GET"])
@admin_required
def get_exam_templates():
    """获取考试模板列表"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search", "")
        status = request.args.get("status", "")

        query = ExamTemplate.query

        # 搜索条件
        if search:
            query = query.filter(ExamTemplate.name.contains(search))
        if status:
            if status == "active":
                query = query.filter(ExamTemplate.is_active == True)
            elif status == "inactive":
                query = query.filter(ExamTemplate.is_active == False)

        # 分页
        templates = query.order_by(ExamTemplate.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "success": True,
                "templates": [template.to_dict() for template in templates.items],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": templates.total,
                    "pages": templates.pages,
                    "has_next": templates.has_next,
                    "has_prev": templates.has_prev,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-templates", methods=["POST"])
@admin_required
def create_exam_template():
    """创建考试模板"""
    try:
        data = request.get_json()

        # 验证必填字段
        if not data.get("name"):
            return jsonify({"success": False, "message": "模板名称不能为空"}), 400

        if not data.get("question_ids") or len(data["question_ids"]) == 0:
            return jsonify({"success": False, "message": "请至少选择一道题目"}), 400

        # 创建模板
        template = ExamTemplate(
            name=data["name"],
            description=data.get("description", ""),
            total_questions=len(data["question_ids"]),
            time_limit=data.get("time_limit", 75),
            passing_score=data.get("passing_score", 60.0),
            is_active=data.get("is_active", True),
        )

        db.session.add(template)
        db.session.flush()  # 获取template.id

        # 添加题目到模板
        for i, question_id in enumerate(data["question_ids"]):
            template_question = ExamTemplateQuestion(
                template_id=template.id,
                question_id=question_id,
                question_order=i + 1,
                points=data.get("points", 1.0),
            )
            db.session.add(template_question)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "考试模板创建成功",
                "template": template.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-templates/<int:template_id>", methods=["GET"])
@admin_required
def get_exam_template(template_id):
    """获取考试模板详情"""
    try:
        template = ExamTemplate.query.get_or_404(template_id)

        # 获取模板题目
        template_questions = (
            ExamTemplateQuestion.query.filter_by(template_id=template_id)
            .order_by(ExamTemplateQuestion.question_order)
            .all()
        )

        questions = []
        for tq in template_questions:
            question = tq.question
            if question:
                question_dict = question.to_dict()
                question_dict["points"] = tq.points
                question_dict["order"] = tq.question_order
                questions.append(question_dict)

        template_dict = template.to_dict()
        template_dict["questions"] = questions

        return jsonify({"success": True, "template": template_dict})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-templates/<int:template_id>", methods=["PUT"])
@admin_required
def update_exam_template(template_id):
    """更新考试模板"""
    try:
        template = ExamTemplate.query.get_or_404(template_id)
        data = request.get_json()

        # 更新模板基本信息
        if "name" in data:
            template.name = data["name"]
        if "description" in data:
            template.description = data["description"]
        if "time_limit" in data:
            template.time_limit = data["time_limit"]
        if "passing_score" in data:
            template.passing_score = data["passing_score"]
        if "is_active" in data:
            template.is_active = data["is_active"]

        # 如果提供了新的题目列表，更新题目
        if "question_ids" in data:
            # 删除现有题目关联
            ExamTemplateQuestion.query.filter_by(template_id=template_id).delete()

            # 添加新题目
            for i, question_id in enumerate(data["question_ids"]):
                template_question = ExamTemplateQuestion(
                    template_id=template_id,
                    question_id=question_id,
                    question_order=i + 1,
                    points=data.get("points", 1.0),
                )
                db.session.add(template_question)

            template.total_questions = len(data["question_ids"])

        template.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "考试模板更新成功",
                "template": template.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-templates/<int:template_id>", methods=["DELETE"])
@admin_required
def delete_exam_template(template_id):
    """删除考试模板"""
    try:
        template = ExamTemplate.query.get_or_404(template_id)

        # 检查是否有考试实例使用此模板
        instances = ExamInstance.query.filter_by(template_id=template_id).count()
        if instances > 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"无法删除模板，已有 {instances} 个考试实例使用此模板",
                    }
                ),
                400,
            )

        # 删除模板题目关联
        ExamTemplateQuestion.query.filter_by(template_id=template_id).delete()

        # 删除模板
        db.session.delete(template)
        db.session.commit()

        return jsonify({"success": True, "message": "考试模板删除成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-templates/<int:template_id>/create-instance", methods=["POST"])
@admin_required
def create_exam_instance(template_id):
    """基于模板创建考试实例"""
    try:
        template = ExamTemplate.query.get_or_404(template_id)
        data = request.get_json()

        # 创建考试实例
        instance = ExamInstance(
            template_id=template_id,
            name=data.get(
                "name", f'{template.name} - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            ),
            description=data.get("description", template.description),
            start_time=(
                datetime.fromisoformat(data["start_time"])
                if data.get("start_time")
                else None
            ),
            end_time=(
                datetime.fromisoformat(data["end_time"])
                if data.get("end_time")
                else None
            ),
            max_attempts=data.get("max_attempts", 1),
            is_active=data.get("is_active", True),
        )

        db.session.add(instance)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "考试实例创建成功",
                "instance": instance.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 考试实例管理API ====================


@app.route("/api/exam-instances", methods=["GET"])
@admin_required
def get_exam_instances():
    """获取考试实例列表"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search", "")
        status = request.args.get("status", "")

        query = ExamInstance.query

        # 搜索条件
        if search:
            query = query.filter(ExamInstance.name.contains(search))
        if status:
            query = query.filter(ExamInstance.status == status)

        # 分页
        instances = query.order_by(ExamInstance.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "success": True,
                "instances": [instance.to_dict() for instance in instances.items],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": instances.total,
                    "pages": instances.pages,
                    "has_next": instances.has_next,
                    "has_prev": instances.has_prev,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-instances/<int:instance_id>", methods=["GET"])
@admin_required
def get_exam_instance(instance_id):
    """获取考试实例详情"""
    try:
        instance = ExamInstance.query.get_or_404(instance_id)

        # 获取参与人数
        participant_count = StudentExam.query.filter_by(
            exam_instance_id=instance_id
        ).count()

        instance_dict = instance.to_dict()
        instance_dict["participant_count"] = participant_count

        return jsonify({"success": True, "instance": instance_dict})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-instances/<int:instance_id>", methods=["PUT"])
@admin_required
def update_exam_instance(instance_id):
    """更新考试实例"""
    try:
        instance = ExamInstance.query.get_or_404(instance_id)
        data = request.get_json()

        # 更新字段
        if "name" in data:
            instance.name = data["name"]
        if "description" in data:
            instance.description = data["description"]
        if "start_time" in data:
            instance.start_time = (
                datetime.fromisoformat(data["start_time"])
                if data["start_time"]
                else None
            )
        if "end_time" in data:
            instance.end_time = (
                datetime.fromisoformat(data["end_time"]) if data["end_time"] else None
            )
        if "max_attempts" in data:
            instance.max_attempts = data["max_attempts"]
        if "is_active" in data:
            instance.is_active = data["is_active"]
        if "status" in data:
            instance.status = data["status"]

        instance.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "考试实例更新成功",
                "instance": instance.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-instances/<int:instance_id>", methods=["DELETE"])
@admin_required
def delete_exam_instance(instance_id):
    """删除考试实例"""
    try:
        instance = ExamInstance.query.get_or_404(instance_id)

        # 检查是否有学生参与
        participant_count = StudentExam.query.filter_by(
            exam_instance_id=instance_id
        ).count()
        if participant_count > 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"无法删除实例，已有 {participant_count} 名学生参与考试",
                    }
                ),
                400,
            )

        # 删除实例
        db.session.delete(instance)
        db.session.commit()

        return jsonify({"success": True, "message": "考试实例删除成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 考试记录删除API ====================


@app.route("/api/exam-records/<int:exam_id>", methods=["DELETE"])
@admin_required
def delete_single_exam_record(exam_id):
    """删除单个考试记录（包括答案数据）"""
    try:
        # 根据考试ID查找对应的考试记录
        # 这里exam_id实际上是activity的id或exam instance的id

        # 首先尝试找到对应的答案记录
        answers = Answer.query.filter_by(exam_instance_id=exam_id).all()
        if answers:
            # 删除所有答案记录
            for answer in answers:
                db.session.delete(answer)

        # 删除考试实例记录（如果存在）
        exam_instance = ExamInstance.query.get(exam_id)
        if exam_instance:
            # 删除关联的学生考试记录
            StudentExam.query.filter_by(exam_instance_id=exam_id).delete()
            # 删除考试实例
            db.session.delete(exam_instance)

        db.session.commit()
        return jsonify({"success": True, "message": "考试记录删除成功"})

    except Exception as e:
        db.session.rollback()
        print(f"❌ 删除考试记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500


@app.route("/api/exam-records/batch-delete", methods=["DELETE"])
@admin_required
def batch_delete_exam_records():
    """批量删除考试记录"""
    try:
        data = request.get_json()
        exam_ids = data.get("exam_ids", [])

        if not exam_ids:
            return (
                jsonify({"success": False, "message": "未提供要删除的考试记录ID"}),
                400,
            )

        deleted_count = 0

        for exam_id in exam_ids:
            try:
                # 删除答案记录
                answers = Answer.query.filter_by(exam_instance_id=exam_id).all()
                for answer in answers:
                    db.session.delete(answer)

                # 删除考试实例记录
                exam_instance = ExamInstance.query.get(exam_id)
                if exam_instance:
                    # 删除关联的学生考试记录
                    StudentExam.query.filter_by(exam_instance_id=exam_id).delete()
                    # 删除考试实例
                    db.session.delete(exam_instance)

                deleted_count += 1

            except Exception as e:
                print(f"❌ 删除考试记录 {exam_id} 失败: {str(e)}")
                continue

        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": f"成功删除 {deleted_count} 条考试记录",
                "deleted_count": deleted_count,
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 批量删除考试记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"批量删除失败: {str(e)}"}), 500


@app.route("/api/exam-records/delete-all", methods=["DELETE"])
@admin_required
def delete_all_exam_records():
    """删除所有考试记录"""
    try:
        # 获取所有考试记录数量用于统计
        total_answers = Answer.query.count()
        total_instances = ExamInstance.query.count()

        # 删除所有答案记录
        Answer.query.delete()

        # 删除所有学生考试记录
        StudentExam.query.delete()

        # 删除所有考试实例
        ExamInstance.query.delete()

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"成功删除所有考试记录（{total_answers} 条答案记录，{total_instances} 个考试实例）",
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 删除所有考试记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500


# ==================== 学生信息清理API ====================


@app.route("/api/cleanup-students", methods=["POST"])
@admin_required
def cleanup_students():
    """清理所有学生信息和考试记录"""
    try:
        data = request.get_json()
        confirm = data.get("confirm", False)

        if not confirm:
            return jsonify({"success": False, "message": "请确认清理操作"}), 400

        # 统计当前数据
        students_count = Student.query.count()
        sessions_count = ExamSession.query.count()
        exams_count = Exam.query.count()
        instances_count = ExamInstance.query.count()
        answers_count = Answer.query.count()
        records_count = StudentExamRecord.query.count()

        print(f"🧹 开始清理学生数据...")
        print(
            f"当前数据统计: 学生({students_count}), 会话({sessions_count}), 考试({exams_count}), 实例({instances_count}), 答案({answers_count}), 记录({records_count})"
        )

        # 删除答案记录
        Answer.query.delete()
        print("✅ 删除所有答案记录")

        # 删除学生考试记录
        StudentExamRecord.query.delete()
        print("✅ 删除所有学生考试记录")

        # 删除考试实例
        ExamInstance.query.delete()
        print("✅ 删除所有考试实例")

        # 删除旧版考试记录
        Exam.query.delete()
        print("✅ 删除所有旧版考试记录")

        # 删除考试会话
        ExamSession.query.delete()
        print("✅ 删除所有考试会话")

        # 删除学生信息
        Student.query.delete()
        print("✅ 删除所有学生信息")

        # 提交更改
        db.session.commit()

        print(f"🎉 学生数据清理完成!")

        return jsonify(
            {
                "success": True,
                "message": "学生数据清理完成",
                "deleted_counts": {
                    "students": students_count,
                    "sessions": sessions_count,
                    "exams": exams_count,
                    "instances": instances_count,
                    "answers": answers_count,
                    "records": records_count,
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 清理学生数据失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/student-statistics", methods=["GET"])
@admin_required
def get_student_statistics():
    """获取学生数据统计"""
    try:
        stats = {
            "students_count": Student.query.count(),
            "sessions_count": ExamSession.query.count(),
            "exams_count": Exam.query.count(),
            "instances_count": ExamInstance.query.count(),
            "answers_count": Answer.query.count(),
            "records_count": StudentExamRecord.query.count(),
        }

        return jsonify({"success": True, "statistics": stats})

    except Exception as e:
        print(f"❌ 获取学生统计失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 学生考试流程API ====================


@app.route("/api/available-exam-templates", methods=["GET"])
def get_available_exam_templates():
    """获取可用的考试模板列表（学生端），包括基于当前默认配置的考试"""
    try:
        current_time = datetime.utcnow()
        templates_data = []

        # 1. 获取所有激活的考试配置并创建基于配置的考试选项
        active_configs = (
            ExamConfig.query.filter_by(is_active=True)
            .order_by(
                ExamConfig.is_default.desc(),  # 默认配置排在前面
                ExamConfig.created_at.desc(),
            )
            .all()
        )

        for config in active_configs:
            # 创建基于配置的考试选项
            description = f"基于考试配置 '{config.name}' 生成的考试。系统将根据配置的筛选条件自动选择题目。"
            if config.is_default:
                description = f"基于当前默认配置 '{config.name}' 生成的考试。系统将根据配置的筛选条件自动选择题目。"

            templates_data.append(
                {
                    "id": f"config_{config.id}",  # 使用特殊ID标识这是基于配置的考试
                    "name": config.name,
                    "description": description,
                    "time_limit": config.time_limit,
                    "total_questions": config.total_questions,
                    "passing_score": config.passing_score,
                    "start_time": None,
                    "end_time": None,
                    "questions_count": config.total_questions,
                    "type": "config",  # 标识这是基于配置的考试
                    "config_id": config.id,
                    "subjects": config.subject_filter
                    or "数学、英语、计算机、逻辑、统计学等",
                    "is_default": config.is_default,  # 标识是否为默认配置
                }
            )

        # 2. 查询当前可用的考试模板
        templates = (
            ExamTemplate.query.filter(
                ExamTemplate.is_active == True,
                or_(
                    ExamTemplate.start_time.is_(None),
                    ExamTemplate.start_time <= current_time,
                ),
                or_(
                    ExamTemplate.end_time.is_(None),
                    ExamTemplate.end_time >= current_time,
                ),
            )
            .order_by(ExamTemplate.created_at.desc())
            .all()
        )

        # 3. 添加考试模板
        for template in templates:
            # 计算题目数量
            questions_count = template.total_questions
            if template.questions:
                try:
                    questions_list = json.loads(template.questions)
                    questions_count = (
                        len(questions_list)
                        if isinstance(questions_list, list)
                        else template.total_questions
                    )
                except:
                    questions_count = template.total_questions

            templates_data.append(
                {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "time_limit": template.time_limit,
                    "total_questions": template.total_questions,
                    "passing_score": template.passing_score,
                    "start_time": (
                        template.start_time.isoformat() if template.start_time else None
                    ),
                    "end_time": (
                        template.end_time.isoformat() if template.end_time else None
                    ),
                    "questions_count": questions_count,
                    "type": "template",  # 标识这是考试模板
                    "template_id": template.id,
                }
            )

        print(f"📋 返回 {len(templates_data)} 个可用考试选项")

        return jsonify({"success": True, "templates": templates_data})

    except Exception as e:
        print(f"❌ 获取可用考试模板失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/available-exam-instances", methods=["GET"])
def get_available_exam_instances():
    """获取可用的考试实例（学生端）"""
    try:
        # 获取当前激活的考试实例
        current_time = datetime.utcnow()
        instances = ExamInstance.query.filter(
            ExamInstance.is_active == True,
            ExamInstance.status == "active",
            or_(
                ExamInstance.start_time.is_(None),
                ExamInstance.start_time <= current_time,
            ),
            or_(ExamInstance.end_time.is_(None), ExamInstance.end_time >= current_time),
        ).all()

        return jsonify(
            {
                "success": True,
                "instances": [instance.to_dict() for instance in instances],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/create-exam-from-template", methods=["POST"])
def create_exam_from_template():
    """学生基于考试模板或配置创建考试实例"""
    try:
        data = request.get_json()
        template_id = data.get("template_id")
        session_id = data.get("session_id")

        if not template_id:
            return jsonify({"success": False, "message": "缺少模板ID"}), 400

        if not session_id:
            return jsonify({"success": False, "message": "缺少会话ID"}), 400

        # 获取会话信息
        session = ExamSession.query.get(session_id)
        if not session:
            return jsonify({"success": False, "message": "会话不存在"}), 404

        # 检查是否是基于配置的考试（template_id 格式为 'config_X'）
        if isinstance(template_id, str) and template_id.startswith("config_"):
            # 基于配置创建考试（旧系统逻辑）
            config_id = int(template_id.replace("config_", ""))
            config = ExamConfig.query.get(config_id)

            if not config:
                return jsonify({"success": False, "message": "考试配置不存在"}), 404

            if not config.is_active:
                return jsonify({"success": False, "message": "考试配置已停用"}), 400

            # 检查学生是否已经参加过基于这个配置的考试
            existing_exam = Exam.query.filter_by(
                session_id=session_id, status="completed"
            ).first()

            if existing_exam:
                return jsonify({"success": False, "message": "您已经完成过考试"}), 400

            # 使用旧系统逻辑创建考试
            questions = generate_questions_from_config(config)

            if not questions:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "无法生成考试题目，题库中没有满足条件的题目",
                        }
                    ),
                    400,
                )

            # 创建旧系统考试记录
            # questions现在是字典列表，提取question_id
            question_ids = [q["id"] for q in questions]
            exam = Exam(
                session_id=session_id,
                config_id=config_id,
                questions=json.dumps(question_ids),
                time_limit=config.time_limit,
                status="active",
            )

            db.session.add(exam)
            db.session.flush()  # 获取exam.id

            # 创建考试题目关联记录
            for i, question_data in enumerate(questions):
                exam_question = ExamQuestion(
                    exam_id=exam.id,
                    question_id=question_data["id"],
                    question_order=i + 1,
                )
                db.session.add(exam_question)

            db.session.commit()

            print(f"✅ 为学生 {session.student.name} 创建基于配置的考试: {config.name}")

            return jsonify(
                {
                    "success": True,
                    "exam_id": exam.id,
                    "message": "考试创建成功",
                    "type": "config",
                }
            )

        else:
            # 基于模板创建考试（新系统逻辑）
            template = ExamTemplate.query.get(template_id)
            if not template:
                return jsonify({"success": False, "message": "考试模板不存在"}), 404

            if not template.is_active:
                return jsonify({"success": False, "message": "考试模板已停用"}), 400

            # 检查时间限制
            current_time = datetime.utcnow()
            if template.start_time and current_time < template.start_time:
                return jsonify({"success": False, "message": "考试尚未开始"}), 400

            if template.end_time and current_time > template.end_time:
                return jsonify({"success": False, "message": "考试已结束"}), 400

            # 检查学生是否已经参加过这个模板的考试
            existing_instance = ExamInstance.query.filter_by(
                template_id=template_id,
                student_id=session.student_id,
                status="completed",
            ).first()

            if existing_instance:
                return jsonify({"success": False, "message": "您已经完成过此考试"}), 400

            # 创建考试实例
            instance = ExamInstance(
                template_id=template_id,
                session_id=session_id,
                student_id=session.student_id,
                name=f"{template.name} - {session.student.name}",
                description=template.description,
                questions=template.questions,  # 复制题目
                status="active",
                started_at=datetime.utcnow(),  # 记录开始时间
            )

            db.session.add(instance)
            db.session.commit()

            print(f"✅ 为学生 {session.student.name} 创建考试实例: {instance.name}")

            return jsonify(
                {
                    "success": True,
                    "instance_id": instance.id,
                    "message": "考试实例创建成功",
                    "type": "template",
                }
            )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 创建考试实例失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/create-exam-instance", methods=["POST"])
def create_exam_instance_from_config():
    """基于考试配置创建考试实例"""
    try:
        data = request.get_json()
        config_id = data.get("config_id")
        session_id = data.get("session_id")  # 支持传入session_id

        if not config_id:
            return jsonify({"success": False, "message": "缺少配置ID"}), 400

        # 获取考试配置
        config = ExamConfig.query.get(config_id)
        if not config:
            return jsonify({"success": False, "message": "考试配置不存在"}), 404

        # 处理考试会话
        if session_id:
            # 使用传入的session_id
            exam_session = ExamSession.query.get(session_id)
            if not exam_session:
                return jsonify({"success": False, "message": "会话不存在"}), 404
        else:
            # 创建管理员测试学生记录（如果不存在）
            admin_student = Student.query.filter_by(
                id_number="110101199001011234"
            ).first()

            if not admin_student:
                admin_student = Student(
                    name="管理员测试",
                    id_number="110101199001011234",
                    application_number=f"ADMIN_{int(datetime.utcnow().timestamp())}",
                    device_ip="127.0.0.1",
                    device_id=f"ADMIN_DEV_{int(datetime.utcnow().timestamp())}",
                    has_taken_exam=False,
                )
                db.session.add(admin_student)
                db.session.flush()

            # 创建考试会话
            exam_session = ExamSession(
                student_id=admin_student.id,
                device_ip="127.0.0.1",
                device_id=f"ADMIN_DEV_{int(datetime.utcnow().timestamp())}",
                status="verified",
            )
            db.session.add(exam_session)
            db.session.flush()

        # 根据配置生成题目
        questions = generate_questions_from_config(config)

        # 创建考试记录（使用传统Exam表结构）
        exam = Exam(
            session_id=exam_session.id,
            config_id=config.id,
            questions=json.dumps(questions, ensure_ascii=False),
            time_limit=config.time_limit,
            status="active",
        )
        db.session.add(exam)
        db.session.flush()  # 获取exam.id

        # 创建考试题目关联记录
        for i, question_data in enumerate(questions):
            # 查找对应的Question记录
            question = Question.query.get(question_data.get("question_id"))
            if question:
                exam_question = ExamQuestion(
                    exam_id=exam.id, question_id=question.id, question_order=i + 1
                )
                db.session.add(exam_question)

        db.session.commit()

        return jsonify({"success": True, "message": "考试创建成功", "exam_id": exam.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"创建考试失败: {str(e)}"}), 500


def generate_questions_from_config(config):
    """根据考试配置生成题目"""
    try:
        print(f"🎯 题目选择模式: {config.question_selection_mode}")

        # 检查题目选择模式
        if config.question_selection_mode == "manual":
            # 手动选择模式：使用预先选定的题目
            print("📝 使用手动选择模式")
            config_questions = (
                ExamConfigQuestion.query.filter_by(config_id=config.id)
                .order_by(ExamConfigQuestion.question_order)
                .all()
            )

            if not config_questions:
                print("⚠️  手动选择模式下没有找到预设题目，回退到筛选模式")
                # 如果没有预设题目，回退到筛选模式
                return generate_questions_by_filter(config)

            # 获取预设的题目
            selected_questions = []
            for cq in config_questions:
                question = Question.query.get(cq.question_id)
                if question and question.is_active:
                    selected_questions.append(question)

            print(f"✅ 手动选择模式：找到 {len(selected_questions)} 道预设题目")

        else:
            # 筛选模式：根据条件动态选择题目
            print("🔍 使用筛选模式")
            selected_questions = generate_questions_by_filter(config)

        # 转换为字典格式（兼容考试页面）
        question_list = []
        for i, q in enumerate(selected_questions):
            question_data = {
                "id": q.id,  # 使用真实的question ID
                "question_id": q.id,
                "content": q.content,
                "options": json.loads(q.options) if q.options else [],
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "points": q.points,
                "type": q.question_type,
                "type_key": q.question_type,  # 添加type_key字段
                "subject": q.subject,
                "difficulty": q.difficulty,
                "cognitive_level": q.cognitive_level,
            }
            question_list.append(question_data)

        print(f"🎉 最终生成 {len(question_list)} 道题目")
        return question_list

    except Exception as e:
        print(f"生成题目失败: {str(e)}")
        # 返回模拟题目
        return _generate_mock_questions(
            config.total_questions, "数学", "", "中等", "", ["multiple_choice"], "zh"
        )


def generate_questions_by_filter(config):
    """根据筛选条件生成题目"""
    # 解析筛选条件
    subjects = (
        [s.strip() for s in config.subject_filter.split(",")]
        if config.subject_filter
        else []
    )
    difficulties = (
        [d.strip() for d in config.difficulty_filter.split(",")]
        if config.difficulty_filter
        else []
    )
    types = (
        [t.strip() for t in config.type_filter.split(",")] if config.type_filter else []
    )

    print(f"筛选条件 - 学科: {subjects}, 难度: {difficulties}, 题型: {types}")

    # 构建查询条件
    query = Question.query.filter_by(is_active=True)

    if subjects:
        query = query.filter(Question.subject.in_(subjects))
    if difficulties:
        query = query.filter(Question.difficulty.in_(difficulties))
    if types:
        query = query.filter(Question.question_type.in_(types))

    # 随机选择题目
    import random

    available_questions = query.all()
    if len(available_questions) < config.total_questions:
        # 如果题目不够，补充其他题目
        additional_questions = Question.query.filter_by(is_active=True).all()
        available_questions.extend(additional_questions)

    # 随机选择指定数量的题目
    selected_questions = random.sample(
        available_questions, min(config.total_questions, len(available_questions))
    )
    print(f"筛选模式：选择了 {len(selected_questions)} 道题目")

    return selected_questions


@app.route("/api/start-exam-from-instance", methods=["POST"])
def start_exam_from_instance():
    """从考试实例开始考试"""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        instance_id = data.get("instance_id")

        if not session_id or not instance_id:
            return jsonify({"success": False, "message": "缺少必要参数"}), 400

        # 验证会话
        session_data = session.get(f"student_session_{session_id}")
        if not session_data:
            return jsonify({"success": False, "message": "会话无效"}), 401

        # 获取考试实例
        instance = ExamInstance.query.get_or_404(instance_id)
        if not instance.is_active or instance.status != "active":
            return jsonify({"success": False, "message": "考试实例不可用"}), 400

        # 检查时间限制
        current_time = datetime.utcnow()
        if instance.start_time and instance.start_time > current_time:
            return jsonify({"success": False, "message": "考试尚未开始"}), 400
        if instance.end_time and instance.end_time < current_time:
            return jsonify({"success": False, "message": "考试已结束"}), 400

        # 获取模板题目
        template_questions = (
            ExamTemplateQuestion.query.filter_by(template_id=instance.template_id)
            .order_by(ExamTemplateQuestion.question_order)
            .all()
        )

        if not template_questions:
            return jsonify({"success": False, "message": "考试模板中没有题目"}), 400

        # 创建学生考试记录
        student_exam = StudentExam(
            student_id=session_data["student_id"],
            exam_instance_id=instance_id,
            status="in_progress",
            start_time=current_time,
            total_questions=len(template_questions),
            max_score=sum(q.points for q in template_questions),
        )

        db.session.add(student_exam)
        db.session.flush()  # 获取student_exam.id

        # 创建题目记录（使用旧的Exam表结构以兼容现有系统）
        exam = Exam(
            name=instance.name,
            description=instance.description,
            total_questions=len(template_questions),
            time_limit=75,  # 默认75分钟
            is_active=True,
        )

        db.session.add(exam)
        db.session.flush()  # 获取exam.id

        # 创建考试题目记录
        for i, template_question in enumerate(template_questions):
            exam_question = ExamQuestion(
                exam_id=exam.id,
                question_id=template_question.question_id,
                question_number=i + 1,
                points=template_question.points,
            )
            db.session.add(exam_question)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "考试开始成功",
                "exam_id": exam.id,
                "student_exam_id": student_exam.id,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 智能批改系统 ====================


@app.route("/api/auto-grade", methods=["POST"])
@admin_required
def auto_grade_exam():
    """自动批改考试"""
    try:
        data = request.get_json()
        student_exam_id = data.get("student_exam_id")

        if not student_exam_id:
            return jsonify({"success": False, "message": "缺少学生考试ID"}), 400

        # 获取学生考试记录
        student_exam = StudentExam.query.get_or_404(student_exam_id)

        # 获取考试实例和模板
        exam_instance = student_exam.exam_instance
        template = exam_instance.template

        # 获取模板题目
        template_questions = (
            ExamTemplateQuestion.query.filter_by(template_id=template.id)
            .order_by(ExamTemplateQuestion.question_order)
            .all()
        )

        total_score = 0
        max_score = 0
        correct_count = 0

        # 批改每道题目
        for tq in template_questions:
            question = tq.question
            if not question:
                continue

            # 获取学生答案
            student_answer = StudentAnswer.query.filter_by(
                student_exam_id=student_exam_id, question_id=question.id
            ).first()

            if not student_answer:
                continue

            # 根据题型进行批改
            is_correct, score, feedback = grade_question(
                question, student_answer.answer_text, tq.points
            )

            # 更新答案记录
            student_answer.is_correct = is_correct
            student_answer.score = score
            student_answer.feedback = feedback
            student_answer.auto_graded = True
            student_answer.graded_at = datetime.utcnow()

            total_score += score
            max_score += tq.points
            if is_correct:
                correct_count += 1

        # 更新学生考试记录
        student_exam.total_score = total_score
        student_exam.max_score = max_score
        student_exam.correct_count = correct_count
        student_exam.total_questions = len(template_questions)
        student_exam.is_passed = (
            total_score / max_score * 100
        ) >= template.passing_score
        student_exam.status = "completed"
        student_exam.end_time = datetime.utcnow()

        # 计算考试用时
        if student_exam.start_time:
            duration = student_exam.end_time - student_exam.start_time
            student_exam.duration_minutes = int(duration.total_seconds() / 60)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "自动批改完成",
                "result": {
                    "total_score": total_score,
                    "max_score": max_score,
                    "correct_count": correct_count,
                    "total_questions": len(template_questions),
                    "is_passed": student_exam.is_passed,
                    "percentage": (
                        round(total_score / max_score * 100, 2) if max_score > 0 else 0
                    ),
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


def grade_question(question, student_answer, max_points):
    """批改单道题目"""
    try:
        if question.question_type == "multiple_choice":
            # 选择题：直接比较答案
            is_correct = (
                student_answer.strip().lower()
                == question.correct_answer.strip().lower()
            )
            score = max_points if is_correct else 0
            feedback = (
                "回答正确！" if is_correct else f"正确答案是：{question.correct_answer}"
            )

        elif question.question_type == "short_answer":
            # 简答题：使用AI进行语义比较
            # 这里可以集成AI评分系统
            # 暂时使用简单的关键词匹配
            correct_keywords = question.correct_answer.lower().split()
            student_keywords = student_answer.lower().split()

            # 计算关键词匹配度
            match_count = sum(
                1 for keyword in correct_keywords if keyword in student_keywords
            )
            match_ratio = match_count / len(correct_keywords) if correct_keywords else 0

            is_correct = match_ratio >= 0.6  # 60%以上匹配认为正确
            score = max_points * match_ratio
            feedback = f"匹配度：{match_ratio:.1%}。参考答案：{question.correct_answer}"

        elif question.question_type == "programming":
            # 编程题：使用AI进行代码分析
            # 这里可以集成代码分析系统
            # 暂时使用简单的长度和关键词匹配
            if len(student_answer.strip()) < 10:
                is_correct = False
                score = 0
                feedback = "代码太短，请提供完整的实现"
            else:
                # 简单的代码质量评估
                score = max_points * 0.8  # 暂时给80%的分数
                is_correct = score >= max_points * 0.6
                feedback = "代码已提交，建议参考标准答案进行优化"
        else:
            is_correct = False
            score = 0
            feedback = "未知题型，无法自动批改"

        return is_correct, score, feedback

    except Exception as e:
        return False, 0, f"批改出错：{str(e)}"


def ensure_default_config():
    """确保存在默认考试配置"""
    with app.app_context():
        # 检查是否已有默认配置
        existing_config = ExamConfig.query.filter_by(
            is_default=True, is_active=True
        ).first()
        if not existing_config:
            # 创建默认考试配置
            default_config = ExamConfig(
                name="默认考试配置",
                description="系统默认的考试配置，包含5道题目，75分钟时间限制",
                total_questions=5,
                time_limit=75,
                subject_filter="数学,英语,计算机,逻辑,统计学",
                difficulty_filter="简单,中等,困难",
                type_filter="multiple_choice,short_answer,programming",
                is_default=True,
                is_active=True,
                show_results=True,
            )

            db.session.add(default_config)
            db.session.commit()
            print("默认考试配置创建成功")


# ==================== 考试历史管理API ====================


@app.route("/api/exam-templates-with-participants", methods=["GET"])
@admin_required
def get_exam_templates_with_participants():
    """获取考试模板及其参与学生信息，包括基于当前默认配置的考试"""
    try:
        result = []

        # 1. 获取所有激活的考试配置
        active_configs = (
            ExamConfig.query.filter_by(is_active=True)
            .order_by(
                ExamConfig.is_default.desc(),  # 默认配置排在前面
                ExamConfig.created_at.desc(),
            )
            .all()
        )

        # 2. 为每个激活的配置创建考试条目
        for config in active_configs:
            # 查找使用当前配置创建的考试记录（旧系统）
            config_exams = Exam.query.filter_by(config_id=config.id).all()

            # 统计旧系统的参与者信息
            old_participants = []
            for exam in config_exams:
                # 获取该考试对应的会话
                session = (
                    ExamSession.query.get(exam.session_id) if exam.session_id else None
                )
                if not session:
                    continue
                student = session.student
                if student:
                    # 优先使用已保存的分数数据
                    percentage = 0
                    score = 0
                    total_score = 0

                    if exam.scores:
                        try:
                            import json

                            scores_data = json.loads(exam.scores)
                            percentage = round(
                                scores_data.get("percentage_score", 0), 1
                            )
                            score = scores_data.get("total_score", 0)
                            total_score = scores_data.get("max_score", 0)
                        except (json.JSONDecodeError, AttributeError):
                            # 如果分数数据解析失败，fallback到答案统计
                            answers = Answer.query.filter_by(exam_id=exam.id).all()
                            total_questions = len(answers)
                            correct_count = len([a for a in answers if a.is_correct])
                            percentage = round(
                                (
                                    (correct_count / total_questions * 100)
                                    if total_questions > 0
                                    else 0
                                ),
                                1,
                            )
                            score = correct_count
                            total_score = total_questions
                    else:
                        # 如果没有分数数据，使用答案统计
                        answers = Answer.query.filter_by(exam_id=exam.id).all()
                        total_questions = len(answers)
                        correct_count = len([a for a in answers if a.is_correct])
                        percentage = round(
                            (
                                (correct_count / total_questions * 100)
                                if total_questions > 0
                                else 0
                            ),
                            1,
                        )
                        score = correct_count
                        total_score = total_questions

                    old_participants.append(
                        {
                            "instance_id": f"old_{exam.id}",
                            "student_id": student.id,
                            "student_name": student.name,
                            "student_id_number": student.id_number,
                            "student_application_number": student.application_number,
                            "status": (
                                "completed" if exam.status == "completed" else "active"
                            ),
                            "score": score,
                            "percentage": percentage,
                            "started_at": (
                                exam.started_at.isoformat() if exam.started_at else None
                            ),
                            "completed_at": (
                                exam.completed_at.isoformat()
                                if exam.completed_at
                                else None
                            ),
                            "time_spent_minutes": 0,  # Exam模型没有duration_minutes字段
                        }
                    )

            # 添加基于当前配置的考试条目
            config_exam_info = {
                "id": f"config_{config.id}",
                "name": config.name,
                "description": config.description
                or (
                    f'基于{"默认" if config.is_default else ""}配置 "{config.name}" 的考试'
                ),
                "time_limit": config.time_limit,
                "total_questions": config.total_questions,
                "passing_score": config.passing_score,
                "is_active": config.is_active,
                "created_at": (
                    config.created_at.isoformat() if config.created_at else None
                ),
                "statistics": {
                    "total_participants": len(old_participants),
                    "completed_count": len(
                        [p for p in old_participants if p["status"] == "completed"]
                    ),
                    "active_count": len(
                        [p for p in old_participants if p["status"] == "active"]
                    ),
                    "avg_score": round(
                        (
                            sum(p["percentage"] for p in old_participants)
                            / len(old_participants)
                            if old_participants
                            else 0
                        ),
                        1,
                    ),
                },
                "participants": sorted(
                    old_participants,
                    key=lambda x: x["completed_at"] or "1970-01-01T00:00:00",
                    reverse=True,
                ),
            }

            result.append(config_exam_info)

        # 3. 查询所有激活的考试模板（新系统）
        templates = (
            ExamTemplate.query.filter_by(is_active=True)
            .order_by(ExamTemplate.created_at.desc())
            .all()
        )

        for template in templates:
            # 获取该模板的所有考试实例
            instances = ExamInstance.query.filter_by(template_id=template.id).all()

            # 统计信息
            total_participants = len(instances)
            completed_count = len([i for i in instances if i.status == "completed"])
            active_count = len([i for i in instances if i.status == "active"])

            # 计算平均分
            completed_instances = [
                i
                for i in instances
                if i.status == "completed" and i.percentage is not None
            ]
            avg_score = (
                sum(i.percentage for i in completed_instances)
                / len(completed_instances)
                if completed_instances
                else 0
            )

            # 获取参与学生详情
            participants = []
            for instance in instances:
                # 获取学生信息
                session = (
                    ExamSession.query.get(instance.session_id)
                    if instance.session_id
                    else None
                )
                student = session.student if session else None

                # 如果没有通过session找到学生，直接通过student_id查找
                if not student and instance.student_id:
                    student = Student.query.get(instance.student_id)

                participant_info = {
                    "instance_id": instance.id,
                    "student_id": student.id if student else None,
                    "student_name": student.name if student else "Unknown",
                    "student_id_number": student.id_number if student else "",
                    "student_application_number": (
                        student.application_number if student else ""
                    ),
                    "status": instance.status,
                    "score": instance.score or 0,
                    "percentage": instance.percentage or 0,
                    "started_at": (
                        instance.started_at.isoformat() if instance.started_at else None
                    ),
                    "completed_at": (
                        instance.completed_at.isoformat()
                        if instance.completed_at
                        else None
                    ),
                    "time_spent_minutes": 0,
                }

                # 计算用时
                if instance.started_at and instance.completed_at:
                    time_spent = instance.completed_at - instance.started_at
                    participant_info["time_spent_minutes"] = round(
                        time_spent.total_seconds() / 60, 1
                    )

                participants.append(participant_info)

            # 按完成时间排序
            participants.sort(
                key=lambda x: x["completed_at"] or "1970-01-01T00:00:00", reverse=True
            )

            template_info = {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "time_limit": template.time_limit,
                "total_questions": template.total_questions,
                "passing_score": template.passing_score,
                "is_active": template.is_active,
                "created_at": (
                    template.created_at.isoformat() if template.created_at else None
                ),
                "statistics": {
                    "total_participants": total_participants,
                    "completed_count": completed_count,
                    "active_count": active_count,
                    "avg_score": round(avg_score, 1),
                },
                "participants": participants,
            }

            result.append(template_info)

        return jsonify({"success": True, "templates": result})

    except Exception as e:
        print(f"❌ 获取考试模板参与者信息失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/students-management", methods=["GET"])
@admin_required
def get_students_management():
    """获取学生管理信息"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search", "")

        query = Student.query

        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    Student.name.contains(search),
                    Student.id_number.contains(search),
                    Student.application_number.contains(search),
                )
            )

        # 分页
        students_paginated = query.order_by(Student.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        students_data = []
        for student in students_paginated.items:
            # 获取该学生的考试统计
            exam_count = ExamInstance.query.filter_by(student_id=student.id).count()
            completed_exams = ExamInstance.query.filter_by(
                student_id=student.id, status="completed"
            ).all()

            avg_score = 0
            if completed_exams:
                scores = [
                    exam.percentage
                    for exam in completed_exams
                    if exam.percentage is not None
                ]
                avg_score = sum(scores) / len(scores) if scores else 0

            student_info = {
                "id": student.id,
                "name": student.name,
                "id_number": student.id_number,
                "application_number": student.application_number,
                "device_ip": student.device_ip or "未记录",
                "created_at": (
                    student.created_at.isoformat() if student.created_at else None
                ),
                "exam_count": exam_count,
                "completed_count": len(completed_exams),
                "avg_score": round(avg_score, 1),
            }

            students_data.append(student_info)

        return jsonify(
            {
                "success": True,
                "students": students_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": students_paginated.total,
                    "pages": students_paginated.pages,
                    "has_next": students_paginated.has_next,
                    "has_prev": students_paginated.has_prev,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取学生管理信息失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/students-management", methods=["POST"])
@admin_required
def create_student():
    """创建新学生"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = ["name", "id_number", "application_number"]
        for field in required_fields:
            if not data.get(field):
                return (
                    jsonify({"success": False, "message": f"缺少必填字段: {field}"}),
                    400,
                )

        # 检查ID号和申请号是否已存在
        existing_student = Student.query.filter(
            or_(
                Student.id_number == data["id_number"],
                Student.application_number == data["application_number"],
            )
        ).first()

        if existing_student:
            return jsonify({"success": False, "message": "学号或申请号已存在"}), 400

        # 创建新学生
        student = Student(
            name=data["name"],
            id_number=data["id_number"],
            application_number=data["application_number"],
        )

        db.session.add(student)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "学生创建成功",
                "student": {
                    "id": student.id,
                    "name": student.name,
                    "id_number": student.id_number,
                    "application_number": student.application_number,
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 创建学生失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/students-management/<int:student_id>", methods=["PUT"])
@admin_required
def update_student(student_id):
    """更新学生信息"""
    try:
        student = Student.query.get_or_404(student_id)
        data = request.get_json()

        # 检查ID号和申请号是否与其他学生冲突
        if "id_number" in data or "application_number" in data:
            existing_student = Student.query.filter(
                Student.id != student_id,
                or_(
                    Student.id_number == data.get("id_number", student.id_number),
                    Student.application_number
                    == data.get("application_number", student.application_number),
                ),
            ).first()

            if existing_student:
                return jsonify({"success": False, "message": "学号或申请号已存在"}), 400

        # 更新字段
        if "name" in data:
            student.name = data["name"]
        if "id_number" in data:
            student.id_number = data["id_number"]
        if "application_number" in data:
            student.application_number = data["application_number"]

        db.session.commit()

        return jsonify({"success": True, "message": "学生信息更新成功"})

    except Exception as e:
        db.session.rollback()
        print(f"❌ 更新学生信息失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/students-management/<int:student_id>", methods=["DELETE"])
@admin_required
def delete_student(student_id):
    """删除学生（安全级联删除）"""
    try:
        student = Student.query.get_or_404(student_id)

        # 安全的级联删除，按依赖关系顺序
        # 1. 删除学生相关的答案记录
        # 删除通过exam_id关联的答案
        sessions = ExamSession.query.filter_by(student_id=student_id).all()
        for session in sessions:
            exams = Exam.query.filter_by(session_id=session.id).all()
            for exam in exams:
                Answer.query.filter_by(exam_id=exam.id).delete(
                    synchronize_session=False
                )

        # 删除通过exam_instance_id关联的答案
        instances = ExamInstance.query.filter_by(student_id=student_id).all()
        for instance in instances:
            Answer.query.filter_by(exam_instance_id=instance.id).delete(
                synchronize_session=False
            )

        # 2. 删除学生答案记录
        student_exams = StudentExam.query.filter_by(student_id=student_id).all()
        for student_exam in student_exams:
            StudentAnswer.query.filter_by(student_exam_id=student_exam.id).delete(
                synchronize_session=False
            )

        # 3. 删除考试题目关联记录
        for session in sessions:
            exams = Exam.query.filter_by(session_id=session.id).all()
            for exam in exams:
                ExamQuestion.query.filter_by(exam_id=exam.id).delete(
                    synchronize_session=False
                )

        # 4. 删除学生考试记录
        StudentExamRecord.query.filter_by(student_id=student_id).delete(
            synchronize_session=False
        )
        StudentExam.query.filter_by(student_id=student_id).delete(
            synchronize_session=False
        )

        # 5. 删除考试记录
        for session in sessions:
            Exam.query.filter_by(session_id=session.id).delete(
                synchronize_session=False
            )

        # 6. 删除考试实例
        ExamInstance.query.filter_by(student_id=student_id).delete(
            synchronize_session=False
        )

        # 7. 删除考试会话
        ExamSession.query.filter_by(student_id=student_id).delete(
            synchronize_session=False
        )

        # 8. 最后删除学生记录
        db.session.delete(student)
        db.session.commit()

        return jsonify({"success": True, "message": "学生及其关联记录删除成功"})

    except Exception as e:
        db.session.rollback()
        print(f"❌ 删除学生失败: {str(e)}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500


@app.route("/api/exams-history", methods=["GET"])
@admin_required
def get_exams_history():
    """获取考试历史列表（包含新旧两种模式的数据）"""
    try:
        # 1. 查询考试实例（新模式）
        instance_list = []
        instances_query = db.session.query(
            ExamInstance.id,
            ExamInstance.status,
            ExamInstance.name,
            ExamInstance.description,
            ExamInstance.started_at,
            ExamInstance.completed_at,
            ExamInstance.questions,
            ExamInstance.score,
            ExamInstance.total_score,
            ExamInstance.percentage,
            ExamInstance.template_id,
            ExamTemplate.name.label("template_name"),
            ExamTemplate.time_limit,
        ).outerjoin(ExamTemplate, ExamInstance.template_id == ExamTemplate.id)

        instances = instances_query.all()

        for instance in instances:
            # 获取题目数量
            question_count = 0
            if instance.questions:
                try:
                    questions_data = json.loads(instance.questions)
                    question_count = (
                        len(questions_data) if isinstance(questions_data, list) else 0
                    )
                except:
                    question_count = 0

            # 获取学生信息
            student_name = "未知学生"
            if instance.id:
                # 通过session查找学生名称
                session_query = (
                    db.session.query(ExamSession.student_id)
                    .join(ExamInstance, ExamInstance.session_id == ExamSession.id)
                    .filter(ExamInstance.id == instance.id)
                    .first()
                )

                if session_query:
                    student = Student.query.get(session_query.student_id)
                    if student:
                        student_name = student.name

            instance_list.append(
                {
                    "id": f"instance_{instance.id}",  # 加前缀区分
                    "type": "instance",
                    "real_id": instance.id,
                    "status": instance.status,
                    "name": instance.name,
                    "description": instance.description,
                    "template_name": instance.template_name,
                    "student_name": student_name,
                    "time_limit": instance.time_limit,
                    "started_at": (
                        instance.started_at.isoformat() if instance.started_at else None
                    ),
                    "completed_at": (
                        instance.completed_at.isoformat()
                        if instance.completed_at
                        else None
                    ),
                    "student_count": 1,  # 每个实例对应一个学生
                    "question_count": question_count,
                    "score": instance.score or 0,
                    "total_score": instance.total_score or 0,
                    "avg_score": (
                        round(instance.percentage, 1) if instance.percentage else 0
                    ),
                }
            )

        # 2. 查询旧模式考试记录（兼容性）
        legacy_list = []
        exams_query = db.session.query(
            Exam.id,
            Exam.status,
            Exam.time_limit,
            Exam.started_at,
            Exam.completed_at,
            Exam.config_id,
            Exam.scores,
            Exam.questions,
            ExamConfig.name.label("config_name"),
        ).outerjoin(ExamConfig, Exam.config_id == ExamConfig.id)

        exams = exams_query.all()

        for exam in exams:
            # 获取参与学生数量
            student_count = (
                ExamSession.query.join(Exam).filter(Exam.id == exam.id).count()
            )

            # 获取题目数量
            question_count = ExamQuestion.query.filter_by(exam_id=exam.id).count()
            if question_count == 0 and exam.questions:
                try:
                    questions_data = json.loads(exam.questions)
                    question_count = (
                        len(questions_data) if isinstance(questions_data, list) else 0
                    )
                except:
                    question_count = 0

            # 计算平均分
            avg_score = 0
            total_score = 0
            if exam.status == "completed" and exam.scores:
                try:
                    scores_data = json.loads(exam.scores)
                    if scores_data and "percentage_score" in scores_data:
                        avg_score = round(scores_data["percentage_score"], 1)
                        total_score = scores_data.get("total_score", 0)
                except:
                    avg_score = 0

            # 获取学生名称
            student_name = "未知学生"
            session = ExamSession.query.filter_by(exam_id=exam.id).first()
            if session and session.student:
                student_name = session.student.name

            legacy_list.append(
                {
                    "id": f"legacy_{exam.id}",  # 加前缀区分
                    "type": "legacy",
                    "real_id": exam.id,
                    "status": exam.status,
                    "name": f"考试 #{exam.id}",
                    "description": "传统考试模式",
                    "template_name": exam.config_name or "未知配置",
                    "student_name": student_name,
                    "time_limit": exam.time_limit,
                    "started_at": (
                        exam.started_at.isoformat() if exam.started_at else None
                    ),
                    "completed_at": (
                        exam.completed_at.isoformat() if exam.completed_at else None
                    ),
                    "student_count": student_count,
                    "question_count": question_count,
                    "score": total_score,
                    "total_score": total_score,
                    "avg_score": avg_score,
                }
            )

        # 3. 合并所有考试记录，按时间排序
        all_exams = instance_list + legacy_list
        all_exams.sort(
            key=lambda x: x["started_at"] or "1970-01-01T00:00:00", reverse=True
        )

        return jsonify(
            {
                "success": True,
                "exams": all_exams,
                "statistics": {
                    "total_instances": len(instance_list),
                    "total_legacy": len(legacy_list),
                    "total_all": len(all_exams),
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取考试历史失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam/<int:exam_id>/students", methods=["GET"])
@admin_required
def get_exam_students(exam_id):
    """获取考试的学生详情"""
    try:
        exam = Exam.query.get_or_404(exam_id)

        # 获取考试会话
        session = ExamSession.query.get(exam.session_id)
        if not session:
            return jsonify({"success": True, "students": []})

        # 获取学生信息
        student = session.student
        if not student:
            return jsonify({"success": True, "students": []})

        # 计算成绩信息
        score_info = {
            "id": student.id,
            "name": student.name,
            "id_number": student.id_number,
            "application_number": student.application_number,
            "status": exam.status,
            "score": 0,
            "max_score": 0,
            "percentage": 0,
            "duration": 0,
        }

        if exam.status == "completed" and exam.scores:
            try:
                scores_data = json.loads(exam.scores)
                score_info.update(
                    {
                        "score": scores_data.get("total_score", 0),
                        "max_score": scores_data.get("max_score", 0),
                        "percentage": round(scores_data.get("percentage_score", 0), 1),
                    }
                )
            except:
                pass

        # 计算用时
        if exam.started_at and exam.completed_at:
            duration = (exam.completed_at - exam.started_at).total_seconds() / 60
            score_info["duration"] = round(duration, 1)

        return jsonify({"success": True, "students": [score_info]})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-config/<int:config_id>/usage", methods=["GET"])
@admin_required
def get_config_usage(config_id):
    """获取配置使用情况"""
    try:
        config = ExamConfig.query.get_or_404(config_id)

        # 获取使用此配置的考试
        exams = Exam.query.filter_by(config_id=config_id).all()

        exam_list = []
        for exam in exams:
            # 获取参与学生数量
            student_count = (
                ExamSession.query.join(Exam).filter(Exam.id == exam.id).count()
            )

            exam_list.append(
                {
                    "id": exam.id,
                    "status": exam.status,
                    "started_at": (
                        exam.started_at.isoformat() if exam.started_at else None
                    ),
                    "completed_at": (
                        exam.completed_at.isoformat() if exam.completed_at else None
                    ),
                    "student_count": student_count,
                }
            )

        return jsonify(
            {
                "success": True,
                "config": {
                    "id": config.id,
                    "name": config.name,
                    "description": config.description,
                    "total_questions": config.total_questions,
                    "time_limit": config.time_limit,
                    "is_active": config.is_active,
                    "is_default": config.is_default,
                },
                "exams": exam_list,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam/<int:exam_id>", methods=["DELETE"])
@admin_required
def delete_exam_record(exam_id):
    """删除考试记录"""
    try:
        exam = Exam.query.get_or_404(exam_id)
        force = request.args.get("force", "false").lower() == "true"

        # 检查考试状态
        if exam.status == "active" and not force:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "不能删除进行中的考试，请使用强制停止",
                    }
                ),
                400,
            )

        # 如果是进行中的考试且使用强制模式，先强制结束考试
        if exam.status == "active" and force:
            exam.status = "completed"
            exam.completed_at = datetime.utcnow()
            # 可以选择设置一个默认的完成分数或者保持现有分数
            if not exam.scores:
                exam.scores = json.dumps(
                    {
                        "total_score": 0,
                        "max_score": 0,
                        "percentage_score": 0,
                        "forced_stop": True,
                        "stop_reason": "管理员强制停止",
                    }
                )

        # 删除相关的答案记录
        Answer.query.filter_by(exam_id=exam_id).delete()

        # 删除考试题目关联
        ExamQuestion.query.filter_by(exam_id=exam_id).delete()

        # 删除学生考试记录
        StudentExamRecord.query.filter_by(exam_id=exam_id).delete()

        # 如果有考试会话，重置学生状态但保留会话记录
        if exam.session_id:
            session = ExamSession.query.get(exam.session_id)
            if session and session.student:
                # 重置学生的考试状态，允许重新参加考试
                session.student.has_taken_exam = False

        # 删除考试记录
        db.session.delete(exam)
        db.session.commit()

        action = "强制停止并删除" if (exam.status == "completed" and force) else "删除"
        return jsonify({"success": True, "message": f"考试记录{action}成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam/<int:exam_id>/student/<student_id>/answers", methods=["GET"])
@admin_required
def get_student_answers(exam_id, student_id):
    """获取学生的答案详情"""
    try:
        exam = Exam.query.get_or_404(exam_id)

        # 获取考试题目
        exam_questions = (
            ExamQuestion.query.filter_by(exam_id=exam_id)
            .order_by(ExamQuestion.question_order)
            .all()
        )
        questions = []
        for eq in exam_questions:
            question = eq.question
            if question and question.is_active:
                questions.append(question.to_dict())

        # 如果没有关联表记录，从JSON中获取题目
        if not questions and exam.questions:
            try:
                questions_data = json.loads(exam.questions)
                if isinstance(questions_data, list):
                    questions = questions_data
            except:
                questions = []

        # 获取学生答案
        answers = Answer.query.filter_by(exam_id=exam_id).all()
        answer_dict = {
            str(answer.question_id): answer.answer_text for answer in answers
        }

        # 获取成绩数据
        scores_data = {}
        if exam.scores:
            try:
                scores_data = json.loads(exam.scores)
            except:
                pass

        question_scores = scores_data.get("question_scores", [])
        score_dict = {str(qs.get("question_id", "")): qs for qs in question_scores}

        # 组装答案详情
        answer_details = []
        for i, question in enumerate(questions):
            question_id = str(question.get("id", i + 1))
            student_answer = answer_dict.get(question_id, "未作答")
            score_info = score_dict.get(question_id, {})

            answer_details.append(
                {
                    "question_number": i + 1,
                    "question_id": question_id,
                    "question_content": question.get("content", "题目内容加载失败"),
                    "question_type": question.get("question_type", "unknown"),
                    "correct_answer": question.get("correct_answer", ""),
                    "student_answer": student_answer,
                    "score": score_info.get("score", 0),
                    "max_score": score_info.get("max_score", 1),
                    "percentage": score_info.get("percentage", 0),
                    "is_correct": score_info.get("percentage", 0) >= 80,
                }
            )

        return jsonify(
            {
                "success": True,
                "exam_id": exam_id,
                "student_id": student_id,
                "answers": answer_details,
                "total_score": scores_data.get("total_score", 0),
                "max_score": scores_data.get("max_score", len(questions)),
                "percentage_score": scores_data.get("percentage_score", 0),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-template/<template_id>/type-scores", methods=["GET"])
@admin_required
def get_exam_type_scores(template_id):
    """获取考试模板按题型分类的评分统计"""
    try:
        # 统计不同题型的得分情况
        type_stats = {}

        # 新系统：从ExamInstance获取数据
        instances = ExamInstance.query.filter_by(template_id=template_id).all()
        for instance in instances:
            if not instance.completed_at:
                continue

            # 获取该实例的所有答案
            answers = Answer.query.filter_by(exam_instance_id=instance.id).all()

            for answer in answers:
                # 获取题目信息
                question = (
                    Question.query.get(answer.question_id)
                    if answer.question_id
                    else None
                )
                if not question:
                    continue

                question_type = question.question_type

                # 初始化题型统计
                if question_type not in type_stats:
                    type_stats[question_type] = {
                        "total_score": 0,
                        "max_score": 0,
                        "question_count": 0,
                        "student_count": 0,
                        "correct_count": 0,
                        "students": set(),
                    }

                # 累加统计数据
                type_stats[question_type]["total_score"] += (
                    answer.score if answer.score else 0
                )
                type_stats[question_type]["max_score"] += question.points
                type_stats[question_type]["question_count"] += 1
                type_stats[question_type]["students"].add(instance.id)

                # 判断是否正确：score达到满分则认为正确
                if answer.score and question.points and answer.score >= question.points:
                    type_stats[question_type]["correct_count"] += 1

        # 旧系统：从Exam获取数据（如果没有ExamInstance数据）
        if not type_stats:
            # 查找与该配置ID相关的考试
            exams = Exam.query.filter_by(config_id=template_id).all()

            for exam in exams:
                # 获取该考试的所有答案
                answers = Answer.query.filter_by(exam_id=exam.id).all()

                for answer in answers:
                    # 获取题目信息
                    question = (
                        Question.query.get(answer.question_id)
                        if answer.question_id
                        else None
                    )
                    if not question:
                        continue

                    question_type = question.question_type

                    # 初始化题型统计
                    if question_type not in type_stats:
                        type_stats[question_type] = {
                            "total_score": 0,
                            "max_score": 0,
                            "question_count": 0,
                            "student_count": 0,
                            "correct_count": 0,
                            "students": set(),
                        }

                    # 累加统计数据
                    type_stats[question_type]["total_score"] += (
                        answer.score if answer.score else 0
                    )
                    type_stats[question_type]["max_score"] += question.points
                    type_stats[question_type]["question_count"] += 1
                    type_stats[question_type]["students"].add(exam.id)

                    # 判断是否正确：score达到满分则认为正确
                    if (
                        answer.score
                        and question.points
                        and answer.score >= question.points
                    ):
                        type_stats[question_type]["correct_count"] += 1

        if not type_stats:
            return jsonify(
                {"success": True, "type_scores": {}, "message": "暂无考试数据"}
            )

        # 计算每种题型的统计结果
        result_stats = {}
        for question_type, stats in type_stats.items():
            student_count = len(stats["students"])
            result_stats[question_type] = {
                "type_name": get_question_type_name(question_type),
                "total_score": stats["total_score"],
                "max_score": stats["max_score"],
                "percentage": round(
                    (
                        (stats["total_score"] / stats["max_score"] * 100)
                        if stats["max_score"] > 0
                        else 0
                    ),
                    1,
                ),
                "question_count": stats["question_count"],
                "student_count": student_count,
                "correct_count": stats["correct_count"],
                "accuracy": round(
                    (
                        (stats["correct_count"] / stats["question_count"] * 100)
                        if stats["question_count"] > 0
                        else 0
                    ),
                    1,
                ),
            }

        return jsonify({"success": True, "type_scores": result_stats})

    except Exception as e:
        print(f"获取题型评分统计失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/student/<int:student_id>/type-scores", methods=["GET"])
@admin_required
def get_student_type_scores(student_id):
    """获取单个学生的题型评分统计"""
    try:
        student = Student.query.get_or_404(student_id)

        # 统计不同题型的得分情况
        type_stats = {}

        # 新系统：从ExamInstance获取数据
        instances = ExamInstance.query.filter_by(student_id=student_id).all()
        for instance in instances:
            if not instance.completed_at:
                continue

            # 获取该实例的所有答案
            answers = Answer.query.filter_by(exam_instance_id=instance.id).all()

            for answer in answers:
                # 获取题目信息
                question = (
                    Question.query.get(answer.question_id)
                    if answer.question_id
                    else None
                )
                if not question:
                    continue

                question_type = question.question_type

                # 初始化题型统计
                if question_type not in type_stats:
                    type_stats[question_type] = {
                        "total_score": 0,
                        "max_score": 0,
                        "question_count": 0,
                        "correct_count": 0,
                        "exam_count": 0,
                        "exams": set(),
                        "detailed_scores": [],  # 添加详细得分列表
                    }

                # 累加统计数据
                type_stats[question_type]["total_score"] += (
                    answer.score if answer.score else 0
                )
                type_stats[question_type]["max_score"] += question.points
                type_stats[question_type]["question_count"] += 1
                type_stats[question_type]["exams"].add(instance.id)

                # 判断是否正确：score达到满分则认为正确
                is_correct = bool(
                    answer.score and question.points and answer.score >= question.points
                )

                # 添加详细得分信息
                type_stats[question_type]["detailed_scores"].append(
                    {
                        "question_id": question.id,
                        "question_text": (
                            question.content[:100] + "..."
                            if len(question.content) > 100
                            else question.content
                        ),
                        "score": answer.score if answer.score else 0,
                        "max_score": question.points,
                        "percentage": round(
                            (
                                (answer.score / question.points * 100)
                                if answer.score and question.points > 0
                                else 0
                            ),
                            1,
                        ),
                        "is_correct": is_correct,
                        "exam_instance_id": instance.id,
                        "exam_date": (
                            instance.completed_at.strftime("%Y-%m-%d %H:%M")
                            if instance.completed_at
                            else "N/A"
                        ),
                    }
                )

                if is_correct:
                    type_stats[question_type]["correct_count"] += 1

        # 旧系统：从Exam获取数据（如果学生参与了旧系统考试）
        if not type_stats:
            # 查找学生参与的考试
            sessions = ExamSession.query.filter_by(student_id=student_id).all()
            for session in sessions:
                exams = Exam.query.filter_by(session_id=session.id).all()
                for exam in exams:
                    answers = Answer.query.filter_by(exam_id=exam.id).all()

                    for answer in answers:
                        # 获取题目信息
                        question = (
                            Question.query.get(answer.question_id)
                            if answer.question_id
                            else None
                        )
                        if not question:
                            continue

                        question_type = question.question_type

                        # 初始化题型统计
                        if question_type not in type_stats:
                            type_stats[question_type] = {
                                "total_score": 0,
                                "max_score": 0,
                                "question_count": 0,
                                "correct_count": 0,
                                "exam_count": 0,
                                "exams": set(),
                                "detailed_scores": [],  # 添加详细得分列表
                            }

                        # 累加统计数据
                        type_stats[question_type]["total_score"] += (
                            answer.score if answer.score else 0
                        )
                        type_stats[question_type]["max_score"] += question.points
                        type_stats[question_type]["question_count"] += 1
                        type_stats[question_type]["exams"].add(exam.id)

                        # 判断是否正确：score达到满分则认为正确
                        is_correct = bool(
                            answer.score
                            and question.points
                            and answer.score >= question.points
                        )

                        # 添加详细得分信息
                        type_stats[question_type]["detailed_scores"].append(
                            {
                                "question_id": question.id,
                                "question_text": (
                                    question.content[:100] + "..."
                                    if len(question.content) > 100
                                    else question.content
                                ),
                                "score": answer.score if answer.score else 0,
                                "max_score": question.points,
                                "percentage": round(
                                    (
                                        (answer.score / question.points * 100)
                                        if answer.score and question.points > 0
                                        else 0
                                    ),
                                    1,
                                ),
                                "is_correct": is_correct,
                                "exam_instance_id": exam.id,
                                "exam_date": (
                                    exam.started_at.strftime("%Y-%m-%d %H:%M")
                                    if exam.started_at
                                    else "N/A"
                                ),
                            }
                        )

                        if is_correct:
                            type_stats[question_type]["correct_count"] += 1

        if not type_stats:
            return jsonify(
                {
                    "success": True,
                    "student_name": student.name,
                    "type_scores": {},
                    "message": "该学生暂无考试数据",
                }
            )

        # 计算每种题型的统计结果
        result_stats = {}
        for question_type, stats in type_stats.items():
            exam_count = len(stats["exams"])
            result_stats[question_type] = {
                "type_name": get_question_type_name(question_type),
                "total_score": stats["total_score"],
                "max_score": stats["max_score"],
                "percentage": round(
                    (
                        (stats["total_score"] / stats["max_score"] * 100)
                        if stats["max_score"] > 0
                        else 0
                    ),
                    1,
                ),
                "question_count": stats["question_count"],
                "exam_count": exam_count,
                "correct_count": stats["correct_count"],
                "accuracy": round(
                    (
                        (stats["correct_count"] / stats["question_count"] * 100)
                        if stats["question_count"] > 0
                        else 0
                    ),
                    1,
                ),
                "avg_score_per_question": (
                    round(stats["total_score"] / stats["question_count"], 2)
                    if stats["question_count"] > 0
                    else 0
                ),
                "detailed_scores": stats["detailed_scores"],  # 添加详细得分信息
            }

        return jsonify(
            {"success": True, "student_name": student.name, "type_scores": result_stats}
        )

    except Exception as e:
        print(f"获取学生题型评分统计失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exam-template/<template_id>/detailed-scores", methods=["GET"])
@admin_required
def get_exam_detailed_scores(template_id):
    """获取考试模板中所有学生的详细题型评分"""
    try:
        # 提取数字ID（如果templateId是 "config_2" 格式，提取出 "2"）
        config_id = template_id
        if isinstance(template_id, str) and template_id.startswith("config_"):
            config_id = template_id.replace("config_", "")

        all_students_data = {}

        # 新系统：从ExamInstance获取数据，为每次考试创建单独的记录
        instances = ExamInstance.query.filter_by(template_id=config_id).all()
        for instance in instances:
            if not instance.completed_at or not instance.student_id:
                continue

            student = Student.query.get(instance.student_id)
            if not student:
                continue

            # 为每次考试创建唯一的学生记录
            china_time = (
                to_china_time(instance.completed_at) if instance.completed_at else None
            )
            exam_date = (
                china_time.strftime("%Y-%m-%d %H:%M") if china_time else "未知时间"
            )
            unique_student_key = f"{student.name}_{exam_date}_{instance.id}"

            all_students_data[unique_student_key] = {
                "student_id": student.id,
                "student_name": student.name,
                "exam_date": exam_date,
                "instance_id": instance.id,
                "total_score": 0,
                "total_max_score": 0,
                "exam_count": 1,  # 每次考试都是1
                "type_scores": {},
            }

            # 获取该实例的所有答案
            answers = Answer.query.filter_by(exam_instance_id=instance.id).all()
            student_exam_score = 0
            student_exam_max_score = 0

            for answer in answers:
                question = (
                    Question.query.get(answer.question_id)
                    if answer.question_id
                    else None
                )
                if not question:
                    continue

                question_type = question.question_type

                # 初始化题型统计
                if (
                    question_type
                    not in all_students_data[unique_student_key]["type_scores"]
                ):
                    all_students_data[unique_student_key]["type_scores"][
                        question_type
                    ] = {
                        "type_name": get_question_type_name(question_type),
                        "total_score": 0,
                        "max_score": 0,
                        "question_count": 0,
                        "correct_count": 0,
                    }

                # 累加统计数据
                score = answer.score if answer.score else 0
                all_students_data[unique_student_key]["type_scores"][question_type][
                    "total_score"
                ] += score
                all_students_data[unique_student_key]["type_scores"][question_type][
                    "max_score"
                ] += question.points
                all_students_data[unique_student_key]["type_scores"][question_type][
                    "question_count"
                ] += 1

                # 判断是否正确：score达到满分则认为正确
                if score and question.points and score >= question.points:
                    all_students_data[unique_student_key]["type_scores"][question_type][
                        "correct_count"
                    ] += 1

                student_exam_score += score
                student_exam_max_score += question.points

            all_students_data[unique_student_key]["total_score"] = student_exam_score
            all_students_data[unique_student_key][
                "total_max_score"
            ] = student_exam_max_score

        # 旧系统：从Exam获取数据，为每次考试创建单独的记录
        exams = Exam.query.filter_by(
            config_id=int(config_id) if config_id.isdigit() else config_id
        ).all()

        for exam in exams:
            # 通过session获取学生信息
            session = ExamSession.query.get(exam.session_id)
            if not session or not session.student_id:
                continue

            student = Student.query.get(session.student_id)
            if not student:
                continue

            # 为每次考试创建唯一的学生记录
            china_time = to_china_time(exam.started_at) if exam.started_at else None
            exam_date = (
                china_time.strftime("%Y-%m-%d %H:%M") if china_time else "未知时间"
            )
            unique_student_key = f"{student.name}_{exam_date}_{exam.id}"

            all_students_data[unique_student_key] = {
                "student_id": student.id,
                "student_name": student.name,
                "exam_date": exam_date,
                "exam_id": exam.id,  # 旧系统使用exam_id
                "total_score": 0,
                "total_max_score": 0,
                "exam_count": 1,  # 每次考试都是1
                "type_scores": {},
            }

            answers = Answer.query.filter_by(exam_id=exam.id).all()
            student_exam_score = 0
            student_exam_max_score = 0

            for answer in answers:
                question = (
                    Question.query.get(answer.question_id)
                    if answer.question_id
                    else None
                )
                if not question:
                    continue

                question_type = question.question_type

                # 初始化题型统计
                if (
                    question_type
                    not in all_students_data[unique_student_key]["type_scores"]
                ):
                    all_students_data[unique_student_key]["type_scores"][
                        question_type
                    ] = {
                        "type_name": get_question_type_name(question_type),
                        "total_score": 0,
                        "max_score": 0,
                        "question_count": 0,
                        "correct_count": 0,
                    }

                # 累加统计数据
                score = answer.score if answer.score else 0
                all_students_data[unique_student_key]["type_scores"][question_type][
                    "total_score"
                ] += score
                all_students_data[unique_student_key]["type_scores"][question_type][
                    "max_score"
                ] += question.points
                all_students_data[unique_student_key]["type_scores"][question_type][
                    "question_count"
                ] += 1

                # 判断是否正确：score达到满分则认为正确
                if score and question.points and score >= question.points:
                    all_students_data[unique_student_key]["type_scores"][question_type][
                        "correct_count"
                    ] += 1

                student_exam_score += score
                student_exam_max_score += question.points

            all_students_data[unique_student_key]["total_score"] = student_exam_score
            all_students_data[unique_student_key][
                "total_max_score"
            ] = student_exam_max_score

        # 计算百分比
        for student_name, student_data in all_students_data.items():
            # 计算总体百分比
            if student_data["total_max_score"] > 0:
                student_data["total_percentage"] = round(
                    (student_data["total_score"] / student_data["total_max_score"])
                    * 100,
                    1,
                )
            else:
                student_data["total_percentage"] = 0

            # 计算各题型百分比和正确率
            for question_type, type_data in student_data["type_scores"].items():
                if type_data["max_score"] > 0:
                    type_data["percentage"] = round(
                        (type_data["total_score"] / type_data["max_score"]) * 100, 1
                    )
                else:
                    type_data["percentage"] = 0

                if type_data["question_count"] > 0:
                    type_data["accuracy"] = round(
                        (type_data["correct_count"] / type_data["question_count"])
                        * 100,
                        1,
                    )
                else:
                    type_data["accuracy"] = 0

        return jsonify(
            {
                "success": True,
                "template_id": template_id,
                "students_data": all_students_data,
            }
        )

    except Exception as e:
        print(f"获取考试详细评分统计失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


def get_question_type_name(question_type):
    """获取题型中文名称"""
    type_names = {
        "multiple_choice": "选择题",
        "short_answer": "简答题",
        "programming": "编程题",
        "essay": "论述题",
        "fill_blank": "填空题",
    }
    return type_names.get(question_type, question_type)


@app.route("/api/exams/batch-delete", methods=["POST"])
@admin_required
def batch_delete_exams():
    """批量删除考试记录"""
    try:
        data = request.get_json()
        exam_ids = data.get("exam_ids", [])
        force = data.get("force", False)

        if not exam_ids:
            return jsonify({"success": False, "message": "请选择要删除的考试"}), 400

        deleted_count = 0
        stopped_count = 0
        errors = []

        for exam_id in exam_ids:
            try:
                exam = Exam.query.get(exam_id)
                if not exam:
                    errors.append(f"考试 #{exam_id} 不存在")
                    continue

                # 检查考试状态
                if exam.status == "active" and not force:
                    errors.append(f"考试 #{exam_id} 正在进行中，无法删除")
                    continue

                # 如果是进行中的考试且使用强制模式，先强制结束考试
                was_active = False
                if exam.status == "active" and force:
                    was_active = True
                    exam.status = "completed"
                    exam.completed_at = datetime.utcnow()
                    if not exam.scores:
                        exam.scores = json.dumps(
                            {
                                "total_score": 0,
                                "max_score": 0,
                                "percentage_score": 0,
                                "forced_stop": True,
                                "stop_reason": "管理员批量强制停止",
                            }
                        )
                    stopped_count += 1

                # 删除相关记录
                Answer.query.filter_by(exam_id=exam_id).delete()
                ExamQuestion.query.filter_by(exam_id=exam_id).delete()
                StudentExamRecord.query.filter_by(exam_id=exam_id).delete()

                # 如果有考试会话，重置学生状态但保留会话记录
                if exam.session_id:
                    session = ExamSession.query.get(exam.session_id)
                    if session and session.student:
                        # 重置学生的考试状态，允许重新参加考试
                        session.student.has_taken_exam = False

                # 删除考试记录
                db.session.delete(exam)
                deleted_count += 1

            except Exception as e:
                errors.append(f"处理考试 #{exam_id} 失败: {str(e)}")

        db.session.commit()

        # 构建返回消息
        message_parts = []
        if stopped_count > 0:
            message_parts.append(f"强制停止 {stopped_count} 场进行中的考试")
        if deleted_count > 0:
            message_parts.append(f"删除 {deleted_count} 场考试记录")

        message = "成功" + "并".join(message_parts) if message_parts else "无考试被处理"

        return jsonify(
            {
                "success": True,
                "message": message,
                "deleted_count": deleted_count,
                "stopped_count": stopped_count,
                "errors": errors,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/exams/clear-all", methods=["POST"])
@admin_required
def clear_all_exams():
    """清空所有考试记录"""
    try:
        data = request.get_json()
        confirm_text = data.get("confirm_text", "")

        if confirm_text != "我确认删除所有考试记录":
            return jsonify({"success": False, "message": "请输入正确的确认文本"}), 400

        # 获取所有考试
        all_exams = Exam.query.all()
        active_count = sum(1 for exam in all_exams if exam.status == "active")

        # 强制停止所有进行中的考试
        if active_count > 0:
            for exam in all_exams:
                if exam.status == "active":
                    exam.status = "completed"
                    exam.completed_at = datetime.utcnow()
                    if not exam.scores:
                        exam.scores = json.dumps(
                            {
                                "total_score": 0,
                                "max_score": 0,
                                "percentage_score": 0,
                                "forced_stop": True,
                                "stop_reason": "管理员清空所有考试时强制停止",
                            }
                        )

        # 删除所有相关记录
        total_exams = len(all_exams)

        # 清空所有表的相关记录
        Answer.query.delete()
        ExamQuestion.query.delete()
        StudentExamRecord.query.delete()
        ExamSession.query.delete()  # 清空考试会话
        Exam.query.delete()  # 清空考试记录

        # 重置学生考试状态
        Student.query.update({"has_taken_exam": False})

        db.session.commit()

        message = f"成功清空所有考试记录，共删除 {total_exams} 场考试"
        if active_count > 0:
            message += f"（其中 {active_count} 场正在进行的考试被强制停止）"

        return jsonify(
            {
                "success": True,
                "message": message,
                "deleted_count": total_exams,
                "stopped_count": active_count,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 验证字段配置API ====================


@app.route("/api/verification-config", methods=["GET"])
def get_verification_config():
    """获取验证字段配置"""
    try:
        configs = (
            VerificationConfig.query.filter_by(is_enabled=True)
            .order_by(VerificationConfig.field_order)
            .all()
        )

        # 如果没有配置，返回默认配置
        if not configs:
            default_configs = [
                {
                    "field_name": "name",
                    "display_name": "姓名",
                    "is_required": True,
                    "is_enabled": True,
                    "field_type": "text",
                    "placeholder": "请输入您的姓名",
                    "field_order": 1,
                },
                {
                    "field_name": "id_number",
                    "display_name": "身份证号",
                    "is_required": True,
                    "is_enabled": True,
                    "field_type": "text",
                    "placeholder": "请输入身份证号码",
                    "validation_pattern": "^[1-9]\\d{5}(18|19|20)\\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\\d{3}[0-9Xx]$",
                    "error_message": "请输入有效的身份证号码",
                    "field_order": 2,
                },
                {
                    "field_name": "application_number",
                    "display_name": "报名号",
                    "is_required": True,
                    "is_enabled": True,
                    "field_type": "text",
                    "placeholder": "请输入报名号码",
                    "field_order": 3,
                },
            ]
            return jsonify({"success": True, "configs": default_configs})

        return jsonify(
            {"success": True, "configs": [config.to_dict() for config in configs]}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/verification-config", methods=["GET"])
@admin_required
def get_admin_verification_config():
    """获取管理员验证字段配置（包括禁用的）"""
    try:
        configs = VerificationConfig.query.order_by(
            VerificationConfig.field_order
        ).all()

        # 如果没有配置，创建默认配置
        if not configs:
            default_configs = [
                VerificationConfig(
                    field_name="name",
                    display_name="姓名",
                    is_required=True,
                    is_enabled=True,
                    field_type="text",
                    placeholder="请输入您的姓名",
                    field_order=1,
                ),
                VerificationConfig(
                    field_name="id_number",
                    display_name="身份证号",
                    is_required=True,
                    is_enabled=True,
                    field_type="text",
                    placeholder="请输入身份证号码",
                    validation_pattern="^[1-9]\\d{5}(18|19|20)\\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\\d{3}[0-9Xx]$",
                    error_message="请输入有效的身份证号码",
                    field_order=2,
                ),
                VerificationConfig(
                    field_name="application_number",
                    display_name="报名号",
                    is_required=True,
                    is_enabled=True,
                    field_type="text",
                    placeholder="请输入报名号码",
                    field_order=3,
                ),
            ]

            for config in default_configs:
                db.session.add(config)
            db.session.commit()

            configs = VerificationConfig.query.order_by(
                VerificationConfig.field_order
            ).all()

        return jsonify(
            {"success": True, "configs": [config.to_dict() for config in configs]}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/verification-config", methods=["POST"])
@admin_required
def update_verification_config():
    """更新验证字段配置"""
    try:
        data = request.get_json()
        configs = data.get("configs", [])

        # 删除所有现有配置
        VerificationConfig.query.delete()

        # 添加新配置
        for config_data in configs:
            config = VerificationConfig(
                field_name=config_data.get("field_name"),
                display_name=config_data.get("display_name"),
                is_required=config_data.get("is_required", True),
                is_enabled=config_data.get("is_enabled", True),
                field_type=config_data.get("field_type", "text"),
                placeholder=config_data.get("placeholder", ""),
                validation_pattern=config_data.get("validation_pattern", ""),
                error_message=config_data.get("error_message", ""),
                field_order=config_data.get("field_order", 0),
            )
            db.session.add(config)

        db.session.commit()

        return jsonify({"success": True, "message": "验证字段配置更新成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/system-config", methods=["GET"])
def get_system_config():
    """获取系统配置（公开访问）"""
    try:
        configs = SystemConfig.query.all()
        config_dict = {}

        for config in configs:
            if config.config_type == "boolean":
                config_dict[config.config_key] = (
                    config.config_value.lower() == "true"
                    if config.config_value
                    else False
                )
            elif config.config_type == "number":
                try:
                    config_dict[config.config_key] = (
                        float(config.config_value) if config.config_value else 0
                    )
                except ValueError:
                    config_dict[config.config_key] = 0
            else:
                config_dict[config.config_key] = config.config_value

        return jsonify({"success": True, "data": config_dict})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/get-client-ip", methods=["GET"])
def get_client_ip():
    """获取客户端真实IP地址"""
    try:
        # 获取客户端真实IP，考虑代理和负载均衡器
        client_ip = request.environ.get("HTTP_X_FORWARDED_FOR")
        if client_ip:
            # 如果有多个IP，取第一个
            client_ip = client_ip.split(",")[0].strip()
        else:
            # 备用方法
            client_ip = (
                request.environ.get("HTTP_X_REAL_IP")
                or request.environ.get("HTTP_X_FORWARDED_FOR")
                or request.environ.get("REMOTE_ADDR")
                or request.remote_addr
            )

        return jsonify({"success": True, "ip": client_ip or "127.0.0.1"})
    except Exception as e:
        return jsonify({"success": False, "ip": "127.0.0.1", "message": str(e)}), 500


@app.route("/api/translations", methods=["GET"])
def get_translations():
    """获取多语言翻译（公开访问）"""
    try:
        # 返回所有支持的语言翻译
        translations = {
            "en": {
                # Navigation
                "nav.admin_login": "Admin Login",
                "nav.admin_logged_in": "Admin Logged In",
                "nav.dashboard": "Dashboard",
                "nav.exam_management": "Exam Management",
                "nav.question_management": "Question Management",
                "nav.logout": "Logout",
                # Recent activities
                "recent.title": "Recent Activities",
                # Homepage
                "hero.title": "Smart Exam System",
                "hero.subtitle": "AI-Powered Intelligent Assessment Platform",
                "hero.start_exam": "Start Exam",
                "hero.admin_panel": "Admin Panel",
                # Features
                "features.title": "System Features",
                "features.subtitle": "Advanced examination platform with intelligent assessment",
                "features.security.title": "Secure Authentication",
                "features.security.description": "Advanced identity verification and device binding to ensure exam integrity.",
                "features.ai.title": "AI-Powered Assessment",
                "features.ai.description": "Intelligent question generation and automated scoring with advanced algorithms.",
                "features.analytics.title": "Real-time Analytics",
                "features.analytics.description": "Instant scoring and detailed performance analysis for comprehensive insights.",
                # Footer
                "footer.system_name": "Smart Exam System",
                "footer.copyright": '© 2025 <a href="https://cbit.cuhk.edu.cn" target="_blank" rel="noopener noreferrer" class="text-blue-400 hover:text-blue-300 transition-colors">CBIT</a> Smart Exam System. All rights reserved.',
                # Verification Page
                "verification.title": "Student Identity Verification",
                "verification.subtitle": "Please enter your examination information",
                "verification.name": "Name",
                "verification.id_number": "ID Number",
                "verification.application_number": "Application Number",
                "verification.submit": "Submit",
                "verification.device_info": "Device Information",
                "verification.device_ip": "Device IP",
                "verification.device_id": "Device ID",
                "verification.exam_notes": "Exam Instructions",
                "verification.note1": "Please ensure your information is accurate",
                "verification.note2": "Each student can only take the exam once",
                "verification.note3": "Please complete the exam in the allotted time",
                "verification.device_binding": "Device Binding Information",
                "verification.current_ip": "• Current Device IP: ",
                "verification.device_id_label": "• Device ID: ",
                "verification.device_warning": "• Device will be bound after submission, cannot retake on other devices",
                # System
                "system.name": "Smart Exam System",
                # Dashboard
                "dashboard.title": "Admin Dashboard",
                "dashboard.welcome": "Welcome, Administrator",
                "dashboard.subtitle": "Intelligent Exam System Management Console",
                # Page Titles
                "page.exam_history": "Exam History Management",
                # Student Records Page
                "student.records.title": "Student Answer Records Management - IMBA Smart Exam System",
                "student.records.title_short": "Student Answer Records Management",
                "student.records.completed": "Completed",
                "student.records.in_progress": "In Progress",
                "student.records.abandoned": "Abandoned",
                "student.records.status_filter": "Status Filter",
                "student.records.all_status": "All Status",
                "student.records.student_name": "Student Name",
                "student.records.enter_student_name": "Enter student name",
                "student.records.record_list": "Answer Records List",
                "student.records.student_info": "Student Info",
                "student.records.exam_info": "Exam Info",
                "student.records.score_info": "Score Info",
                "student.records.time_info": "Time Info",
                "student.records.status": "Status",
                "student.records.actions": "Actions",
                "student.records.answer_details": "Answer Details",
                "student.records.view_details": "View Details",
                "student.records.total_records": "Total Records",
                "student.records.search": "Search",
                "student.records.pagination_info": "Showing page",
                "student.records.page": "of",
                "student.records.page_total": "pages",
                "student.records.questions_count": "questions",
                "student.records.accuracy_rate": "Accuracy Rate",
                "student.records.duration": "Duration",
                "student.records.minutes": "minutes",
                # Exam Template Management Page
                "exam.template.title": "Exam Template Management - IMBA Smart Exam System",
                "exam.template.title_short": "Exam Template Management",
                "exam.template.description": "Create and manage exam templates, select questions from the question bank to configure exams",
                "exam.template.search_placeholder": "Search template name...",
                "exam.template.all_status": "All Status",
                "exam.template.status.active": "Active",
                "exam.template.status.inactive": "Inactive",
                "exam.template.create_template": "Create Template",
                "exam.template.exam_instances": "Exam Instances",
                "exam.template.template_name": "Template Name",
                "exam.template.description_short": "Description",
                "exam.template.question_count": "Question Count",
                "exam.template.time_limit": "Time Limit",
                "exam.template.passing_score": "Passing Score",
                "exam.template.status": "Status",
                "exam.template.created_time": "Created Time",
                "exam.template.actions": "Actions",
                "exam.template.template_name_required": "Template Name *",
                "exam.template.template_description": "Template Description",
                "exam.template.description_placeholder": "Describe the purpose and features of this exam template...",
                "exam.template.question_count_required": "Question Count *",
                "exam.template.time_limit_required": "Time Limit (minutes) *",
                "exam.template.passing_score_required": "Passing Score *",
                # Exam History Page
                "exam.history.description": "View and manage all exam records, including student information",
                "exam.history.batch_delete": "Batch Delete",
                "exam.history.clear_all": "Clear All",
                "exam.history.refresh": "Refresh Data",
                "exam.history.danger_operation": "⚠️ Dangerous Operation",
                "exam.history.force_stop": "Force Stop",
                "exam.history.delete_record": "Delete Record",
                "exam.history.total_exams": "Total Exams",
                "exam.history.status_completed": "Completed",
                "exam.history.status_active": "In Progress",
                "exam.history.status_expired": "Expired",
                "exam.history.participating_students": "Participating Students",
                "exam.history.filter_conditions": "Filter Conditions",
                "exam.history.status_filter": "Status Filter",
                "exam.history.all_status": "All Status",
                "exam.history.config_filter": "Config Filter",
                "exam.history.all_configs": "All Configs",
                "exam.history.date_range": "Date Range",
                "exam.history.to": "To",
                "exam.history.apply_filters": "Apply Filters",
                "exam.history.exam_list": "Exam List",
                "exam.history.select_all": "Select All",
                "exam.history.total_count": "Total {count} exams",
                "exam.history.student_details": "Student Details",
                "exam.history.view_results": "View Results",
                "exam.history.config_details": "Config Details",
                "common.unknown": "Unknown",
                # Verification Config (Admin Dashboard Links)
                "admin.verification_settings": "Verification Settings",
                "admin.system_settings": "System Settings",
                "admin.ai_generate_questions": "AI Generate Questions",
                # AI Generate Questions Modal
                "ai.generate.question_count": "Question Count",
                "ai.generate.subject": "Subject",
                "ai.generate.subject.math": "Mathematics",
                "ai.generate.subject.english": "English",
                "ai.generate.subject.computer": "Computer Science",
                "ai.generate.subject.logic": "Logic",
                "ai.generate.subject.statistics": "Statistics",
                "ai.generate.difficulty": "Difficulty",
                "ai.generate.difficulty.easy": "Easy",
                "ai.generate.difficulty.medium": "Medium",
                "ai.generate.difficulty.hard": "Hard",
                # Professional level difficulties
                "ai.generate.difficulty.gre_math": "GRE Math",
                "ai.generate.difficulty.gmat_math": "GMAT Math",
                "ai.generate.difficulty.sat_math_2": "SAT Math II",
                "ai.generate.difficulty.advanced_undergraduate": "Advanced Undergraduate",
                "ai.generate.difficulty.graduate_study": "Graduate Study",
                "ai.generate.difficulty.competition_math": "Math Competition",
                "ai.generate.difficulty.engineering_applications": "Engineering Applications",
                "ai.generate.difficulty.data_science": "Data Science",
                "ai.generate.difficulty.financial_modeling": "Financial Modeling",
                # General difficulty levels for display
                "difficulty.easy": "Easy",
                "difficulty.medium": "Medium",
                "difficulty.hard": "Hard",
                "difficulty.professional": "Professional",
                "difficulty.expert": "Expert",
                "ai.generate.question_type": "Question Type",
                "ai.generate.type.multiple_choice": "Multiple Choice",
                "ai.generate.type.short_answer": "Short Answer",
                "ai.generate.type.programming": "Programming",
                "ai.generate.custom_prompt": "Custom Prompt (Optional)",
                "ai.generate.custom_prompt_placeholder": "Enter additional question requirements...",
                "ai.generate.start_generate": "Start Generate",
                # Exam Management Page
                "exam_management.title": "Exam Management",
                "exam_management.description": "Manage exam templates and student information, view exam statistics",
                "exam_management.total_templates": "Total Exams",
                "exam_management.total_participants": "Total Participants",
                "exam_management.avg_score": "Average Score",
                "exam_management.active_exams": "Active Exams",
                "exam_management.exam_templates": "Exam Management",
                "exam_management.student_management": "Student Management",
                "exam_management.exam_list": "Exam List",
                "exam_management.student_list": "Student List",
                "exam_management.add_student": "Add Student",
                "exam_management.no_exams": "No Exams",
                # Student Management
                "student.name": "Name",
                "student.id_number": "Student ID",
                "student.application_number": "Application Number",
                "student.exam_count": "Exam Count",
                "student.avg_score": "Average Score",
                "student.device_ip": "IP Address",
                "student.created_at": "Registration Date",
                "student.search_placeholder": "Search students...",
                "student.select_all": "Select All",
                "student.batch_delete": "Batch Delete",
                "student.delete_all": "Delete All",
                "student.delete_all_confirm": "Are you sure you want to delete all students? This action cannot be undone.",
                "student.list_header": "Student List",
                "student.selected": "Selected",
                "student.students": "students",
                # Navigation
                "nav.admin_panel": "Admin Panel",
                "nav.exam_config": "Exam Config",
                # Common
                "common.cancel": "Cancel",
                "common.refresh": "Refresh",
                "common.loading": "Loading...",
                "common.actions": "Actions",
                "common.save": "Save",
                "common.previous": "Previous",
                "common.next": "Next",
                "common.showing": "Showing",
                "common.to": "to",
                "common.of": "of",
                "common.results": "results",
                # System Settings
                "admin.system_settings.basic_settings": "Basic Settings",
                "admin.system_settings.system_name": "System Name",
                "admin.system_settings.default_language": "Default Language",
                "admin.system_settings.default_language_desc": "Set the default display language for the system, users can change it via the language toggle button",
                "admin.system_settings.enforce_language": "Force Unified Language",
                "admin.system_settings.enforce_language_text": "Force all users to use the system default language",
                "admin.system_settings.enforce_language_desc": "When enabled, users will not be able to switch languages, all interfaces will use the default language uniformly",
                "admin.system_settings.footer_copyright": "Footer Copyright Information",
                "admin.system_settings.file_settings": "File Settings",
                "admin.system_settings.system_logo": "System Logo",
                "admin.system_settings.select_logo_file": "Select Logo File",
                "admin.system_settings.logo_size_desc": "Recommended size: 40x40px, supports PNG, JPG, SVG formats",
                "admin.system_settings.favicon": "Website Icon (Favicon)",
                "admin.system_settings.select_favicon_file": "Select Favicon File",
                "admin.system_settings.favicon_format_desc": "Recommended format: ICO, PNG or SVG, size: 16x16px or 32x32px",
                "admin.system_settings.current_preview": "Current Settings Preview",
                "admin.system_settings.save_config": "Save Configuration",
                # Verification Settings
                "admin.verification_settings.description": "Customize the verification fields that students need to fill in when logging in. You can enable/disable fields, set whether they are required, customize display names and validation rules.",
                "admin.verification_settings.tip1": "Name, ID number, and registration number are system preset fields",
                "admin.verification_settings.tip2": "You can customize the display name, placeholder and validation rules of fields",
                "admin.verification_settings.tip3": "Disabled fields will not be displayed on the login page",
                "admin.verification_settings.tip4": "At least one field needs to be enabled as student identification",
                "admin.verification_settings.enable_field": "Enable Field",
                "admin.verification_settings.display_name": "Display Name",
                "admin.verification_settings.placeholder": "Placeholder",
                "admin.verification_settings.required_field": "Required Field",
                "admin.verification_settings.validation_rules": "Validation Rules",
                "admin.verification_settings.id_validation_desc": "ID number validation regular expression",
                "admin.verification_settings.error_message": "Error Message",
                "admin.verification_settings.reset_default": "Reset to Default",
                # Common
                "common.tips": "Tips:",
                # System Settings Modal
                "admin.system_settings.description": "Configure basic system information and appearance settings, including logo, name, language and footer information.",
                "admin.system_settings.tip1": "Uploaded logo and favicon files are recommended to use PNG or SVG format",
                "admin.system_settings.tip2": "System name will be displayed in page title and navigation bar",
                "admin.system_settings.tip3": "Language settings will affect the default display language of the frontend interface",
                "admin.system_settings.ai_api_settings": "AI API Settings",
                "admin.system_settings.openrouter_api_key": "OpenRouter API Key",
                "admin.system_settings.api_key_desc": "API key for AI question generation",
                "admin.system_settings.ai_model": "AI Model",
                "admin.system_settings.model_desc": "Select AI model for question generation",
                "admin.system_settings.enable_ai_api": "Enable AI API",
                "admin.system_settings.enable_ai_api_text": "Enable AI question generation",
                "admin.system_settings.enable_ai_api_desc": "When disabled, mock responses will be used for question generation",
                "admin.system_settings.api_warning1": "API keys will be securely stored in the database",
                "admin.system_settings.api_warning2": "Please ensure the API key is valid and has sufficient credits",
                "admin.system_settings.api_warning3": "API settings changes require application restart to take effect",
                "admin.system_settings.validate_api": "Validate",
                "admin.system_settings.select_model_first": "Please validate API key first to load available models",
                "admin.system_settings.model_info": "Model Information",
                "page.exam_config": "Exam Configuration Management",
                "page.question_management": "Question Management",
                # Admin Dashboard
                "admin.dashboard.title": "Admin Dashboard",
                "admin.dashboard.welcome": "Welcome to the Management Console",
                "admin.dashboard.subtitle": "Intelligent Exam System Management Platform",
                "admin.overview": "System Overview",
                "admin.total_questions": "Total Questions",
                "admin.total_exams": "Total Exam Configs",
                "admin.total_exam_records": "Total Exam Records",
                "admin.total_students": "Total Students",
                "admin.active_exams": "Active Exams",
                "admin.quick_actions": "Quick Actions",
                "admin.question_management": "Question Management",
                "admin.question_desc": "Add, edit and organize exam questions",
                "admin.exam_config": "Exam Configuration",
                "admin.exam_config_desc": "Set up exam parameters and settings",
                "admin.student_records": "Student Records",
                "admin.student_records_desc": "View student answers and performance",
                "admin.exam_history": "Exam History",
                "admin.exam_history_desc": "View historical exam records and student information",
                "admin.verification_config": "Verification Config",
                "admin.verification_config_desc": "Customize student login verification fields",
                "admin.system_config": "System Configuration",
                "admin.system_config_desc": "Configure system settings and appearance",
                "admin.ai_generate": "AI Generate Questions",
                "admin.ai_generate_desc": "Use AI to automatically generate exam questions",
                # Admin Dashboard Additional
                "admin.core_management": "Core Management",
                "admin.data_management": "Data Management",
                "admin.quick_stats": "Quick Statistics",
                "admin.today_exams": "Today's Exams",
                "admin.avg_duration": "Average Duration",
                "admin.avg_score": "Average Score",
                "admin.pass_rate": "Pass Rate",
                "admin.exam_templates": "Exam Templates",
                "admin.exam_templates_desc": "Manage exam templates and instances",
                # Admin Dashboard Statistics
                "admin.total_questions": "Total Questions",
                "admin.total_students": "Total Students",
                "admin.total_exams": "Total Exams",
                "admin.total_configs": "Total Configs",
                "admin.question_distribution": "Question Distribution",
                "admin.performance_distribution": "Performance Distribution",
                "admin.recent_activities": "Recent Activities",
                # Student Records Statistics
                "stats.total_students": "Total Students",
                "stats.active_students": "Active Students",
                "stats.total_exams": "Total Exams",
                "stats.average_score": "Average Score",
                # Student Records Tabs
                "tabs.overview": "Overview",
                "tabs.students": "Students",
                "tabs.exams": "Exam Records",
                "tabs.answers": "Answer Details",
                # Student Records Charts
                "charts.score_distribution": "Score Distribution",
                "charts.exam_trend": "Exam Trend",
                # Table Headers
                "admin.table.time": "Time",
                "admin.table.student": "Student",
                "admin.table.action": "Action",
                "admin.table.status": "Status",
                "admin.table.score": "Score",
                # Table Content
                "admin.action.completed_exam": "Completed Exam",
                "admin.action.in_progress": "In Progress",
                "admin.status.completed": "Completed",
                "admin.status.in_progress": "In Progress",
                "admin.score_unit": " pts",
                "admin.unknown": "Unknown",
                # Question Management Page
                "question.management.title": "Question Management - IMBA Smart Exam System",
                "question.management.title_short": "Question Management",
                # Question Statistics
                "question.stats.total_questions": "Total Questions",
                "question.stats.active_questions": "Active",
                "question.stats.subject_count": "Subjects",
                "question.stats.avg_difficulty": "Average Difficulty",
                # Question List
                "question.list.title": "Question List",
                "question.list.total_count": "Total",
                "question.list.questions_unit": "questions",
                "question.list.page_number": "Page",
                "question.list.page_unit": "of",
                # Question Status
                "question.status.active": "Active",
                "question.status.inactive": "Inactive",
                # Question Types
                "question.type.multiple_choice": "Multiple Choice",
                "question.type.short_answer": "Short Answer",
                "question.type.programming": "Programming",
                # Difficulty Levels
                "difficulty.easy": "Easy",
                "difficulty.medium": "Medium",
                "difficulty.hard": "Hard",
                # Subject Names
                "subject.math": "Mathematics",
                "subject.english": "English",
                "subject.computer": "Computer Science",
                "subject.logic": "Logic",
                "subject.statistics": "Statistics",
                # Question Filters
                "question.filter.all_subjects": "All Subjects",
                "question.filter.all_difficulties": "All Difficulties",
                "question.filter.all_types": "All Types",
                "question.filter.all_status": "All Status",
                # Question Pagination
                "question.pagination.showing": "Showing",
                "question.pagination.items_of": "of",
                "question.pagination.items_total": "items",
                # Question AI Generate
                "question.ai_generate.title": "AI Generate Questions",
                "question.ai_generate.question_count": "Question Count",
                "question.ai_generate.subject": "Subject",
                "question.ai_generate.difficulty": "Difficulty",
                "question.ai_generate.question_type": "Question Type",
                "question.ai_generate.custom_prompt": "Custom Prompt (Optional)",
                "question.ai_generate.custom_prompt_placeholder": "Enter additional question requirements...",
                "question.ai_generate.preset_tags": "Quick Select Preset Templates",
                "question.ai_generate.generate_questions": "Generate Questions",
                "question.management.description": "Manage exam questions and configure global question parameters",
                "question.bulk_operations": "Bulk Operations",
                "question.clear_all": "Clear All",
                "question.ai_generate": "AI Generate",
                "question.add_question": "Add Question",
                "question.bulk_delete": "Batch Delete",
                "question.no_questions": "No question data",
                "question.save_question": "Save Question",
                "question.edit_question": "Edit Question",
                "question.update_question": "Update Question",
                "question.confirm_delete": "Are you sure you want to delete this question? This action cannot be undone.",
                # Navigation
                "nav.admin_panel": "Admin Panel",
                "nav.exam_config": "Exam Config",
                "nav.logout": "Logout",
                # Exam Config Management Page
                "exam.config.title": "Exam Configuration Management - IMBA Smart Exam System",
                "exam.config.title_short": "Exam Configuration Management",
                # Exam Config Statistics
                "exam.config.stats.total_configs": "Total Configurations",
                "exam.config.stats.active_configs": "Active Configurations",
                "exam.config.stats.current_config": "Current Configuration",
                "exam.config.stats.show_results": "Show Results",
                # Exam Config Settings
                "exam.config.show_results_after_exam": "Show results after exam completion",
                "exam.config.show_results_desc": "When disabled, students will only see confirmation page after completing exam",
                "exam.config.subject_filter": "Subject Filter",
                "exam.config.difficulty_filter": "Difficulty Filter",
                "exam.config.no_limit": "No Limit",
                "exam.config.time_limit_short": "Time Limit",
                "exam.config.minutes": " min",
                # Exam Config Status
                "exam.config.status.current": "Current Configuration",
                "exam.config.status.active": "Active",
                "exam.config.status.inactive": "Inactive",
                "exam.config.status.show_results": "Show Results",
                "exam.config.status.hide_results": "Hide Results",
                # Exam Config Actions
                "exam.config.edit": "Edit",
                "exam.config.set_current": "Set as Current",
                "exam.config.unset_current": "Unset Current",
                "exam.config.enable": "Enable",
                "exam.config.disable": "Disable",
                "exam.config.delete": "Delete",
                "exam.config.created_time": "Created Time",
                "exam.config.description": "Manage exam configurations, set exam parameters and grading strategies",
                "exam.config.add_config": "Add Configuration",
                "exam.config.no_configs": "No Configurations",
                "exam.config.no_configs_desc": 'Click "Add Configuration" button to create your first exam configuration',
                "exam.config.modal_title": "New Exam Configuration",
                "exam.config.basic_info": "Basic Information",
                "exam.config.config_name": "Configuration Name *",
                "exam.config.question_count": "Question Count *",
                "exam.config.time_limit": "Time Limit (minutes) *",
                "exam.config.save_config": "Save Configuration",
                "exam.config.cancel": "Cancel",
                "exam.config.set_as_current": "Set as Current Exam Configuration",
                "exam.config.set_as_current_desc": "New exams will use this configuration by default",
                "exam.config.question_count_short": "Questions",
                "exam.config.time_limit_short": "Time Limit",
                "exam.config.minutes": " min",
                "exam.config.set_as_current_success": "Set as current exam configuration",
                "exam.config.unset_current_success": "Unset current exam configuration",
                # New Exam Configuration Modal
                "exam.config.config_name_placeholder": "e.g., Mathematics Midterm Exam",
                "exam.config.config_description": "Configuration Description",
                "exam.config.config_description_placeholder": "Describe the purpose and features of this configuration...",
                "exam.config.question_selection_mode": "Question Selection Mode *",
                "exam.config.filter_mode": "Filter Mode",
                "exam.config.manual_mode": "Manual Selection",
                "exam.config.selection_mode_desc": "Filter Mode: Automatically select questions based on criteria; Manual Selection: Precisely select specific questions",
                "exam.config.passing_score": "Passing Score",
                "exam.config.passing_score_desc": "Percentage system, used for grade evaluation",
                "exam.config.config_options": "Configuration Options",
                "exam.config.active_status": "Active Status",
                "exam.config.active_status_desc": "Whether to allow the use of this configuration",
                "exam.config.type_filter": "Question Type Filter",
                # Subject options (Updated for new AI system)
                "exam.config.subject.math": "📐 Mathematics",
                "exam.config.subject.physics": "⚛️ Physics",
                "exam.config.subject.statistics": "📊 Statistics",
                "exam.config.subject.computer_science": "💻 Computer Science",
                "exam.config.subject.engineering": "⚙️ Engineering",
                "exam.config.subject_filter_desc": "No selection means no subject restriction",
                # Difficulty categories
                "exam.config.basic_education": "Basic Education",
                "exam.config.standardized_tests": "Standardized Tests",
                "exam.config.academic_research": "Academic Research",
                # Difficulty options (Updated for new AI system)
                "exam.config.difficulty.high_school": "🎓 High School Level",
                "exam.config.difficulty.undergraduate_basic": "📚 Undergraduate Basic",
                "exam.config.difficulty.undergraduate_advanced": "🎯 Undergraduate Advanced",
                "exam.config.difficulty.gre_level": "🎯 GRE Level",
                "exam.config.difficulty.graduate_study": "🏛️ Graduate Study",
                "exam.config.difficulty.doctoral_research": "🔬 Doctoral Research",
                "exam.config.difficulty_filter_desc": "No selection means no difficulty restriction",
                # Question type options (Updated for new AI system)
                "exam.config.type.multiple_choice": "📝 Multiple Choice",
                "exam.config.type.short_answer": "📄 Short Answer",
                "exam.config.type.programming": "💻 Programming",
                "exam.config.type.true_false": "✅ True/False",
                "exam.config.type.fill_blank": "📝 Fill in the Blank",
                "exam.config.type.essay": "📖 Essay",
                "exam.config.type_filter_desc": "No selection means no question type restriction",
                # Exam Interface
                "exam.title": "Exam in Progress - IMBA Smart Exam System",
                "exam.time_remaining": "Time Remaining",
                "exam.progress": "Progress",
                "exam.question": "Question",
                "exam.question_unit": "",
                "exam.question_navigation": "Question Navigation",
                "exam.of": "of",
                "exam.previous": "Previous",
                "exam.next": "Next",
                "exam.mark": "Mark",
                "exam.submit": "Submit Exam",
                "exam.submit_early": "Submit Early",
                "exam.submit_final": "Submit Exam",
                "exam.submit_suggestion": "Submit Exam",
                "exam.exit": "Exit Exam",
                "exam.exit_confirm_title": "Confirm Exit Exam",
                "exam.exit_confirm_message": "You will not be able to continue answering after exiting, and answered questions will not be saved. Are you sure you want to exit?",
                "exam.submit_confirm_title": "Confirm Submit Exam",
                "exam.submit_confirm_message": "You will not be able to modify answers after submission. Are you sure you want to submit?",
                "exam.submit_early_confirm_title": "Submit Exam Early",
                "exam.submit_early_confirm_message": "You still have unfinished questions. Submitting early may affect your score. Are you sure you want to submit?",
                "exam.submit_final_confirm_title": "Complete Exam",
                "exam.submit_final_confirm_message": "You have completed all questions. Are you sure you want to submit the exam?",
                "exam.cancel": "Cancel",
                "exam.confirm_submit": "Confirm Submit",
                "exam.confirm_submit_early": "Confirm Early Submit",
                "exam.confirm_submit_final": "Submit Exam",
                "exam.confirm_exit": "Confirm Exit",
                "exam.last_question": "Last Question",
                "exam.last_question_tip": "This is the last question. It is recommended to submit the exam after completing the answer.",
                "exam.no_options": "No options available",
                "exam.answer_placeholder": "Please enter your answer...",
                "exam.programming_code": "Programming Code",
                "exam.code_placeholder": "Please enter your code...",
                "exam.code_tip": "Supports Python syntax, please ensure the code can run normally",
                "exam.invalid_id": "Invalid exam ID",
                "exam.load_failed": "Failed to load exam",
                "exam.load_failed_retry": "Failed to load exam, please refresh the page and try again",
                "exam.submit_failed": "Submission failed",
                "exam.submit_failed_retry": "Submission failed, please try again",
                "exam.time_up_auto_submit": "Exam time is up, the system will automatically submit your answers",
                "exam.leave_warning": "You are taking an exam. You will not be able to continue answering after leaving. Are you sure you want to leave?",
                # Verification Page
                "verification.title": "Student Identity Verification - IMBA Smart Exam System",
                "verification.subtitle": "Secure and reliable online exam platform",
                "verification.admin_mode": "Administrator Mode",
                "verification.admin_logged_in": "You are logged in as administrator",
                "verification.select_config": "Select exam configuration...",
                "verification.start_exam_direct": "Start Exam Directly",
                "verification.logout": "Logout",
                "verification.admin_panel": "Admin Panel",
                "verification.student_verification": "Student Identity Verification",
                "verification.form_instruction": "Please fill in your exam information",
                "verification.exam_instructions": "Exam Instructions",
                "verification.auto_generate": "• The system will automatically generate exam questions based on default configuration",
                "verification.time_limit": "• Exam time limit: Loading...",
                "verification.question_count": "• Number of questions: Loading...",
                "verification.subjects": "• Exam subjects: Loading...",
                "verification.one_chance": "• Each student has only one exam opportunity, please answer carefully",
                "verification.device_binding": "Device Binding Information",
                "verification.current_ip": "• Current device IP: ",
                "verification.device_id": "• Device ID: ",
                "verification.device_warning": "• After submission, it will be bound to the current device and cannot be retaken on other devices",
                "verification.start_exam": "Start Exam",
                "verification.admin_login": "Administrator Login",
                "verification.admin_login_title": "Administrator Login",
                "verification.admin_password_prompt": "Please enter administrator password",
                "verification.password": "Password",
                "verification.password_placeholder": "Please enter administrator password",
                "verification.cancel": "Cancel",
                "verification.login": "Login",
                "verification.processing": "Processing, please wait...",
                # Results Page
                "results.page_title": "Exam Results - IMBA Smart Exam System",
                "results.loading": "Loading results...",
                "results.load_failed": "Load Failed",
                "results.load_failed_desc": "Unable to load exam results, please try again later.",
                "results.reload": "Reload",
                "results.title": "Exam Results",
                "results.congratulations": "Congratulations on completing the exam! Here are your detailed results",
                "results.total_score": "Total Score",
                "results.accuracy": "Accuracy",
                "results.grade": "Grade",
                "results.question_analysis": "Question Analysis",
                "results.total_questions": "Total Questions",
                "results.correct_answers": "Correct",
                "results.wrong_answers": "Wrong",
                "results.time_spent": "Time Spent",
                "results.performance_summary": "Performance Summary",
                "results.overall_evaluation": "Overall Evaluation",
                "results.strengths": "Strengths",
                "results.improvements": "Improvement Suggestions",
                "results.print_results": "Print Results",
                "results.back_home": "Back to Homepage",
                # Completion Page
                "completion.page_title": "Exam Completed - IMBA Smart Exam System",
                "completion.title": "Exam Completed!",
                "completion.congratulations": "Congratulations on successfully completing this exam",
                "completion.completion_time": "Completion Time: ",
                "completion.notice_title": "Notice",
                "completion.notice1": "✓ Your answers have been successfully submitted and saved",
                "completion.notice2": "✓ The system is processing your test paper",
                "completion.notice3": "✓ Exam results will be notified through relevant channels later",
                "completion.total_questions": "Total Questions",
                "completion.answered_questions": "Questions Answered",
                "completion.time_spent": "Time Spent",
                "completion.important_notice": "Important Notice:",
                "completion.notice_item1": "• This exam has officially ended and cannot be re-entered or modified",
                "completion.notice_item2": "• Please wait for official notification to get exam results",
                "completion.notice_item3": "• If you have any questions, please contact the relevant person in charge",
                "completion.back_home": "Back to Homepage",
                "completion.print_confirmation": "Print Confirmation",
                "completion.footer_text": "Thank you for participating in this exam | IMBA Smart Exam System",
                # Manual Question Selection
                "manual.open_selection": "Open Manual Selection Window",
                "manual.selection_desc": "Filter and select questions in an independent window",
                "manual.selected_summary": "Selected Questions",
                "manual.total_selected": "Total Selected:",
                "manual.clear_all": "Clear All",
                "manual.window_title": "Manual Question Selection",
                "manual.window_subtitle": "Filter and select exam questions",
                "manual.filter_conditions": "Filter Conditions",
                "manual.subject": "Subject",
                "manual.difficulty": "Difficulty",
                "manual.question_type": "Question Type",
                "manual.search_content": "Search Content",
                "manual.search": "Search Questions",
                "manual.select_all": "Select All Current",
                "manual.clear": "Clear Selection",
                "manual.random_selection": "Random Selection",
                "manual.select_count": "Selection Count:",
                "manual.questions_unit": " questions",
                "manual.random_select_btn": "Random Select",
                "manual.cart_operations": "Cart Operations",
                "manual.add_to_cart": "Add to Cart",
                "cart.clear": "Clear Cart",
                "cart.confirm": "Confirm Selection",
                "status.available_questions": "Filter Results:",
                "status.selected_questions": "Selected:",
                "cart.in_cart": "In Cart:",
                "cart.preview": "Cart Preview",
                "cart.empty_desc": 'Cart is empty, select questions and click "Add to Cart"',
                "manual.instruction": "Tip: Add selected questions to cart, collect questions across subjects, then confirm together",
                "manual.close_and_confirm": "Close and Confirm",
                "manual.all_subjects": "All Subjects",
                "manual.all_difficulties": "All Difficulties",
                "manual.all_types": "All Types",
                "manual.search_placeholder": "Enter keywords to search questions...",
                "questions.empty_title": "Ready to Start Filtering",
                "questions.empty_desc": 'Set filter conditions and click "Search Questions" button',
                "questions.no_questions": "No Questions",
                "questions.adjust_filter": "Please adjust filter conditions or add new questions",
                "question.points": "Points",
                "question.points_unit": " pts",
                "question.selected": "Selected",
            },
            "zh": {
                # Navigation
                "nav.admin_login": "管理员登录",
                "nav.admin_logged_in": "管理员已登录",
                "nav.dashboard": "管理面板",
                "nav.exam_management": "考试管理",
                "nav.question_management": "题库管理",
                "nav.logout": "登出",
                # Recent activities
                "recent.title": "最近活动",
                # Homepage
                "hero.title": "智能考试系统",
                "hero.subtitle": "AI驱动的智能评估平台",
                "hero.start_exam": "开始考试",
                "hero.admin_panel": "管理面板",
                # Features
                "features.title": "系统特色",
                "features.subtitle": "先进的考试平台与智能评估",
                "features.security.title": "安全认证",
                "features.security.description": "先进的身份验证和设备绑定，确保考试完整性。",
                "features.ai.title": "AI智能评估",
                "features.ai.description": "智能题目生成和自动评分，采用先进算法。",
                "features.analytics.title": "实时分析",
                "features.analytics.description": "即时评分和详细性能分析，提供全面洞察。",
                # Footer
                "footer.system_name": "智能考试系统",
                "footer.copyright": '© 2025 <a href="https://cbit.cuhk.edu.cn" target="_blank" rel="noopener noreferrer" class="text-blue-400 hover:text-blue-300 transition-colors">CBIT</a> 智能考试系统. 保留所有权利',
                # Verification Page
                "verification.title": "考生身份验证",
                "verification.subtitle": "请填写您的考试信息",
                "verification.name": "姓名",
                "verification.id_number": "身份证号",
                "verification.application_number": "报名号",
                "verification.submit": "提交",
                "verification.device_info": "设备信息",
                "verification.device_ip": "设备IP",
                "verification.device_id": "设备ID",
                "verification.exam_notes": "考试须知",
                "verification.note1": "请确保您的信息准确无误",
                "verification.note2": "每位考生仅有一次考试机会",
                "verification.note3": "请在规定时间内完成考试",
                "verification.device_binding": "设备绑定信息",
                "verification.current_ip": "• 当前设备 IP：",
                "verification.device_id_label": "• 设备标识：",
                "verification.device_warning": "• 提交后将绑定当前设备，无法在其他设备重复考试",
                # System
                "system.name": "智能考试系统",
                # Dashboard
                "dashboard.title": "管理仪表板",
                "dashboard.welcome": "欢迎，管理员",
                "dashboard.subtitle": "智能考试系统管理控制台",
                # Page Titles
                "page.exam_history": "考试历史管理",
                # Student Records Page
                "student.records.title": "学生答题记录管理 - IMBA智能考试系统",
                "student.records.title_short": "学生答题记录管理",
                "student.records.completed": "已完成",
                "student.records.in_progress": "进行中",
                "student.records.abandoned": "已放弃",
                "student.records.status_filter": "状态筛选",
                "student.records.all_status": "全部状态",
                "student.records.student_name": "学生姓名",
                "student.records.enter_student_name": "输入学生姓名",
                "student.records.record_list": "答题记录列表",
                "student.records.student_info": "学生信息",
                "student.records.exam_info": "考试信息",
                "student.records.score_info": "得分情况",
                "student.records.time_info": "时间信息",
                "student.records.status": "状态",
                "student.records.actions": "操作",
                "student.records.answer_details": "答题详情",
                "student.records.view_details": "查看详情",
                "student.records.total_records": "总记录数",
                "student.records.search": "搜索",
                "student.records.pagination_info": "显示第",
                "student.records.page": "页，共",
                "student.records.page_total": "页",
                "student.records.questions_count": "道题",
                "student.records.accuracy_rate": "正确率",
                "student.records.duration": "用时",
                "student.records.minutes": "分钟",
                # Exam Template Management Page
                "exam.template.title": "考试模板管理 - IMBA 智能考试系统",
                "exam.template.title_short": "考试模板管理",
                "exam.template.description": "创建和管理考试模板，从题库中选择题目配置考试",
                "exam.template.search_placeholder": "搜索模板名称...",
                "exam.template.all_status": "所有状态",
                "exam.template.status.active": "启用",
                "exam.template.status.inactive": "禁用",
                "exam.template.create_template": "创建模板",
                "exam.template.exam_instances": "考试实例",
                "exam.template.template_name": "模板名称",
                "exam.template.description_short": "描述",
                "exam.template.question_count": "题目数量",
                "exam.template.time_limit": "时间限制",
                "exam.template.passing_score": "及格分数",
                "exam.template.status": "状态",
                "exam.template.created_time": "创建时间",
                "exam.template.actions": "操作",
                "exam.template.template_name_required": "模板名称 *",
                "exam.template.template_description": "模板描述",
                "exam.template.description_placeholder": "描述这个考试模板的用途和特点...",
                "exam.template.question_count_required": "题目数量 *",
                "exam.template.time_limit_required": "时间限制（分钟） *",
                "exam.template.passing_score_required": "及格分数 *",
                # Exam History Page
                "exam.history.description": "查看和管理所有考试记录，包括参加考试的学生信息",
                "exam.history.batch_delete": "批量删除",
                "exam.history.clear_all": "清空所有",
                "exam.history.refresh": "刷新数据",
                "exam.history.danger_operation": "⚠️ 危险操作",
                "exam.history.force_stop": "强制停止",
                "exam.history.delete_record": "删除记录",
                "exam.history.total_exams": "总考试数",
                "exam.history.status_completed": "已完成",
                "exam.history.status_active": "进行中",
                "exam.history.status_expired": "已过期",
                "exam.history.participating_students": "参与学生",
                "exam.history.filter_conditions": "筛选条件",
                "exam.history.status_filter": "状态筛选",
                "exam.history.all_status": "全部状态",
                "exam.history.config_filter": "配置筛选",
                "exam.history.all_configs": "全部配置",
                "exam.history.date_range": "日期范围",
                "exam.history.to": "到",
                "exam.history.apply_filters": "应用筛选",
                "exam.history.exam_list": "考试列表",
                "exam.history.select_all": "全选",
                "exam.history.total_count": "共 {count} 场考试",
                "exam.history.student_details": "学生详情",
                "exam.history.view_results": "查看成绩",
                "exam.history.config_details": "配置详情",
                "common.unknown": "未知",
                # Verification Config (Admin Dashboard Links)
                "admin.verification_settings": "验证配置",
                "admin.system_settings": "系统配置",
                "admin.ai_generate_questions": "AI生成题目",
                # AI Generate Questions Modal
                "ai.generate.question_count": "题目数量",
                "ai.generate.subject": "科目",
                "ai.generate.subject.math": "数学",
                "ai.generate.subject.english": "英语",
                "ai.generate.subject.computer": "计算机",
                "ai.generate.subject.logic": "逻辑",
                "ai.generate.subject.statistics": "统计学",
                "ai.generate.difficulty": "难度",
                "ai.generate.difficulty.easy": "简单",
                "ai.generate.difficulty.medium": "中等",
                "ai.generate.difficulty.hard": "困难",
                # 专业级别难度
                "ai.generate.difficulty.gre_math": "GRE 数学",
                "ai.generate.difficulty.gmat_math": "GMAT 数学",
                "ai.generate.difficulty.sat_math_2": "SAT 数学 II",
                "ai.generate.difficulty.advanced_undergraduate": "本科高年级",
                "ai.generate.difficulty.graduate_study": "研究生水平",
                "ai.generate.difficulty.competition_math": "数学竞赛",
                "ai.generate.difficulty.engineering_applications": "工程应用",
                "ai.generate.difficulty.data_science": "数据科学",
                "ai.generate.difficulty.financial_modeling": "金融建模",
                # General difficulty levels for display
                "difficulty.easy": "简单",
                "difficulty.medium": "中等",
                "difficulty.hard": "困难",
                "difficulty.professional": "专业级",
                "difficulty.expert": "专家级",
                "ai.generate.question_type": "题型",
                "ai.generate.type.multiple_choice": "选择题",
                "ai.generate.type.short_answer": "简答题",
                "ai.generate.type.programming": "编程题",
                "ai.generate.custom_prompt": "自定义提示词（可选）",
                "ai.generate.custom_prompt_placeholder": "输入额外的题目要求...",
                "ai.generate.start_generate": "开始生成",
                # Common
                "common.cancel": "取消",
                # System Settings
                "admin.system_settings.basic_settings": "基本设置",
                "admin.system_settings.system_name": "系统名称",
                "admin.system_settings.default_language": "系统默认语言",
                "admin.system_settings.default_language_desc": "设置系统的默认显示语言，用户可以通过语言切换按钮更改",
                "admin.system_settings.enforce_language": "强制统一语言",
                "admin.system_settings.enforce_language_text": "强制所有用户使用系统默认语言",
                "admin.system_settings.enforce_language_desc": "启用后，用户将无法切换语言，所有界面统一使用默认语言",
                "admin.system_settings.footer_copyright": "页脚版权信息",
                "admin.system_settings.file_settings": "文件设置",
                "admin.system_settings.system_logo": "系统Logo",
                "admin.system_settings.select_logo_file": "选择Logo文件",
                "admin.system_settings.logo_size_desc": "推荐尺寸：40x40px，支持PNG、JPG、SVG格式",
                "admin.system_settings.favicon": "网站图标 (Favicon)",
                "admin.system_settings.select_favicon_file": "选择Favicon文件",
                "admin.system_settings.favicon_format_desc": "推荐格式：ICO、PNG或SVG，尺寸：16x16px或32x32px",
                "admin.system_settings.current_preview": "当前设置预览",
                "admin.system_settings.save_config": "保存配置",
                # Verification Settings
                "admin.verification_settings.description": "自定义考生登录时需要填写的验证字段。您可以启用/禁用字段、设置是否必填、自定义显示名称和验证规则。",
                "admin.verification_settings.tip1": "姓名、身份证号、报名号是系统预设字段",
                "admin.verification_settings.tip2": "可以自定义字段的显示名称、占位符和验证规则",
                "admin.verification_settings.tip3": "禁用的字段不会在登录页面显示",
                "admin.verification_settings.tip4": "至少需要启用一个字段作为学生识别",
                "admin.verification_settings.enable_field": "启用字段",
                "admin.verification_settings.display_name": "显示名称",
                "admin.verification_settings.placeholder": "占位符",
                "admin.verification_settings.required_field": "必填字段",
                "admin.verification_settings.validation_rules": "验证规则",
                "admin.verification_settings.id_validation_desc": "身份证号码验证正则表达式",
                "admin.verification_settings.error_message": "错误提示",
                "admin.verification_settings.reset_default": "重置为默认",
                # Common
                "common.tips": "提示：",
                # System Settings Modal
                "admin.system_settings.description": "配置系统的基本信息和外观设置，包括logo、名称、语言和页脚信息。",
                "admin.system_settings.tip1": "上传的logo和favicon文件建议使用PNG或SVG格式",
                "admin.system_settings.tip2": "系统名称将显示在页面标题和导航栏",
                "admin.system_settings.tip3": "语言设置会影响前端界面的默认显示语言",
                "admin.system_settings.ai_api_settings": "AI API 设置",
                "admin.system_settings.openrouter_api_key": "OpenRouter API 密钥",
                "admin.system_settings.api_key_desc": "用于AI题目生成的API密钥",
                "admin.system_settings.ai_model": "AI 模型",
                "admin.system_settings.model_desc": "选择用于生成题目的AI模型",
                "admin.system_settings.enable_ai_api": "启用 AI API",
                "admin.system_settings.enable_ai_api_text": "启用AI题目生成功能",
                "admin.system_settings.enable_ai_api_desc": "禁用后将使用模拟响应生成题目",
                "admin.system_settings.api_warning1": "API密钥将安全存储在数据库中",
                "admin.system_settings.api_warning2": "请确保API密钥有效且有足够的额度",
                "admin.system_settings.api_warning3": "修改API设置后需要重新启动应用才能生效",
                "admin.system_settings.validate_api": "验证",
                "admin.system_settings.select_model_first": "请先验证API密钥以加载可用模型",
                "admin.system_settings.model_info": "模型信息",
                "page.exam_config": "考试配置管理",
                "page.question_management": "题库管理",
                # Admin Dashboard
                "admin.dashboard.title": "管理后台",
                "admin.dashboard.welcome": "欢迎使用管理控制台",
                "admin.dashboard.subtitle": "智能考试系统管理平台",
                "admin.overview": "系统概览",
                "admin.total_questions": "题目总数",
                "admin.total_exams": "考试配置",
                "admin.total_exam_records": "考试记录",
                "admin.total_students": "学生总数",
                "admin.active_exams": "进行中考试",
                "admin.quick_actions": "快速操作",
                "admin.question_management": "题库管理",
                "admin.question_desc": "添加、编辑和组织考试题目",
                "admin.exam_config": "考试配置",
                "admin.exam_config_desc": "设置考试参数和配置",
                "admin.student_records": "答题记录",
                "admin.student_records_desc": "查看学生答题和成绩记录",
                "admin.exam_history": "考试历史",
                "admin.exam_history_desc": "查看历史考试记录和学生信息",
                "admin.verification_config": "验证配置",
                "admin.verification_config_desc": "自定义考生登录验证字段",
                "admin.system_config": "系统配置",
                "admin.system_config_desc": "配置系统设置和外观",
                "admin.ai_generate": "AI生成题目",
                "admin.ai_generate_desc": "使用AI自动生成考试题目",
                # Admin Dashboard Additional
                "admin.core_management": "核心管理",
                "admin.data_management": "数据管理",
                "admin.quick_stats": "快速统计",
                "admin.today_exams": "今日考试次数",
                "admin.avg_duration": "平均考试时长",
                "admin.avg_score": "平均成绩",
                "admin.pass_rate": "通过率",
                "admin.exam_templates": "考试模板",
                "admin.exam_templates_desc": "管理考试模板和实例",
                # Admin Dashboard Statistics
                "admin.total_questions": "题库总数",
                "admin.total_students": "考生总数",
                "admin.total_exams": "考试配置",
                "admin.total_exam_records": "考试记录",
                "admin.question_distribution": "题目分布",
                "admin.performance_distribution": "考试成绩分布",
                "admin.recent_activities": "最近活动",
                # Student Records Statistics
                "stats.total_students": "总学生数",
                "stats.active_students": "活跃学生",
                "stats.total_exams": "总考试次数",
                "stats.average_score": "平均分",
                # Student Records Tabs
                "tabs.overview": "数据概览",
                "tabs.students": "学生列表",
                "tabs.exams": "考试记录",
                "tabs.answers": "答题详情",
                # Student Records Charts
                "charts.score_distribution": "成绩分布",
                "charts.exam_trend": "考试趋势",
                # Table Headers
                "admin.table.time": "时间",
                "admin.table.student": "考生",
                "admin.table.action": "动作",
                "admin.table.status": "状态",
                "admin.table.score": "成绩",
                # Table Content
                "admin.action.completed_exam": "完成考试",
                "admin.action.in_progress": "进行中",
                "admin.status.completed": "已完成",
                "admin.status.in_progress": "进行中",
                "admin.score_unit": "分",
                "admin.unknown": "未知",
                # Question Management Page
                "question.management.title": "题库管理 - IMBA 智能考试系统",
                "question.management.title_short": "题库管理",
                # Question Statistics
                "question.stats.total_questions": "总题目",
                "question.stats.active_questions": "已激活",
                "question.stats.subject_count": "学科数",
                "question.stats.avg_difficulty": "平均难度",
                # Question List
                "question.list.title": "题目列表",
                "question.list.total_count": "共",
                "question.list.questions_unit": "题",
                "question.list.page_number": "第",
                "question.list.page_unit": "页",
                # Question Status
                "question.status.active": "已激活",
                "question.status.inactive": "未激活",
                # Question Types
                "question.type.multiple_choice": "选择题",
                "question.type.short_answer": "简答题",
                "question.type.programming": "编程题",
                # Difficulty Levels
                "difficulty.easy": "简单",
                "difficulty.medium": "中等",
                "difficulty.hard": "困难",
                # Subject Names
                "subject.math": "数学",
                "subject.english": "英语",
                "subject.computer": "计算机",
                "subject.logic": "逻辑",
                "subject.statistics": "统计学",
                # Question Filters
                "question.filter.all_subjects": "所有学科",
                "question.filter.all_difficulties": "所有难度",
                "question.filter.all_types": "所有题型",
                "question.filter.all_status": "所有状态",
                # Question Pagination
                "question.pagination.showing": "显示第",
                "question.pagination.items_of": "项，共",
                "question.pagination.items_total": "项",
                # Question AI Generate
                "question.ai_generate.title": "AI 生成题目",
                "question.ai_generate.question_count": "题目数量",
                "question.ai_generate.subject": "科目",
                "question.ai_generate.difficulty": "难度",
                "question.ai_generate.question_type": "题型",
                "question.ai_generate.custom_prompt": "自定义提示词（可选）",
                "question.ai_generate.custom_prompt_placeholder": "输入额外的题目要求...",
                "question.ai_generate.preset_tags": "快速选择预设模板",
                "question.ai_generate.generate_questions": "生成题目",
                "question.management.description": "管理考试题目，配置全局题目参数",
                "question.bulk_operations": "批量操作",
                "question.clear_all": "清空所有",
                "question.ai_generate": "AI生成",
                "question.add_question": "添加题目",
                "question.bulk_delete": "批量删除",
                "question.no_questions": "暂无题目数据",
                "question.save_question": "保存题目",
                "question.edit_question": "编辑题目",
                "question.update_question": "更新题目",
                "question.confirm_delete": "确定要删除这道题目吗？此操作不可恢复。",
                # Navigation
                "nav.admin_panel": "管理面板",
                "nav.exam_config": "考试配置",
                "nav.logout": "退出登录",
                # Exam Config Management Page
                "exam.config.title": "考试配置管理 - IMBA 智能考试系统",
                "exam.config.title_short": "考试配置管理",
                # Exam Config Statistics
                "exam.config.stats.total_configs": "总配置数",
                "exam.config.stats.active_configs": "启用配置",
                "exam.config.stats.current_config": "当前配置",
                "exam.config.stats.show_results": "显示成绩",
                # Exam Config Settings
                "exam.config.show_results_after_exam": "考试完成后显示成绩",
                "exam.config.show_results_desc": "取消后学生完成考试只显示确认页面",
                "exam.config.subject_filter": "学科筛选",
                "exam.config.difficulty_filter": "难度筛选",
                "exam.config.no_limit": "不限制",
                "exam.config.time_limit_short": "时间限制",
                "exam.config.minutes": "分",
                # Exam Config Status
                "exam.config.status.current": "当前配置",
                "exam.config.status.active": "已启用",
                "exam.config.status.inactive": "未启用",
                "exam.config.status.show_results": "显示成绩",
                "exam.config.status.hide_results": "不显示成绩",
                # Exam Config Actions
                "exam.config.edit": "编辑",
                "exam.config.set_current": "设为当前配置",
                "exam.config.unset_current": "取消当前配置",
                "exam.config.enable": "启用",
                "exam.config.disable": "禁用",
                "exam.config.delete": "删除",
                "exam.config.created_time": "创建时间",
                "exam.config.description": "管理考试配置，设置考试参数和成绩显示策略",
                "exam.config.add_config": "新建配置",
                "exam.config.no_configs": "暂无配置",
                "exam.config.no_configs_desc": '点击"新建配置"按钮创建您的第一个考试配置',
                "exam.config.modal_title": "新建考试配置",
                "exam.config.basic_info": "基本信息",
                "exam.config.config_name": "配置名称 *",
                "exam.config.question_count": "题目数量 *",
                "exam.config.time_limit": "时间限制（分钟）*",
                "exam.config.save_config": "保存配置",
                "exam.config.cancel": "取消",
                "exam.config.set_as_current": "设为当前考试配置",
                "exam.config.set_as_current_desc": "新创建的考试将默认使用此配置",
                "exam.config.question_count_short": "题目数量",
                "exam.config.time_limit_short": "时间限制",
                "exam.config.minutes": "分",
                "exam.config.set_as_current_success": "已设为当前考试配置",
                "exam.config.unset_current_success": "已取消当前考试配置",
                # New Exam Configuration Modal
                "exam.config.config_name_placeholder": "例如：数学期中考试",
                "exam.config.config_description": "配置描述",
                "exam.config.config_description_placeholder": "描述这个配置的用途和特点...",
                "exam.config.question_selection_mode": "题目选择模式 *",
                "exam.config.filter_mode": "筛选模式",
                "exam.config.manual_mode": "手动选择",
                "exam.config.selection_mode_desc": "筛选模式：根据条件自动选择题目；手动选择：精确选择指定题目",
                "exam.config.passing_score": "及格分数",
                "exam.config.passing_score_desc": "百分制，用于成绩评定",
                "exam.config.config_options": "配置选项",
                "exam.config.active_status": "启用状态",
                "exam.config.active_status_desc": "是否允许使用此配置",
                "exam.config.type_filter": "题型筛选",
                # Subject options (Updated for new AI system)
                "exam.config.subject.math": "📐 数学",
                "exam.config.subject.physics": "⚛️ 物理",
                "exam.config.subject.statistics": "📊 统计学",
                "exam.config.subject.computer_science": "💻 计算机科学",
                "exam.config.subject.engineering": "⚙️ 工程",
                "exam.config.subject_filter_desc": "不选择表示不限制学科",
                # Difficulty categories
                "exam.config.basic_education": "基础教育",
                "exam.config.standardized_tests": "标准化考试",
                "exam.config.academic_research": "学术研究",
                # Difficulty options (Updated for new AI system)
                "exam.config.difficulty.high_school": "🎓 高中水平",
                "exam.config.difficulty.undergraduate_basic": "📚 本科基础",
                "exam.config.difficulty.undergraduate_advanced": "🎯 本科高级",
                "exam.config.difficulty.gre_level": "🎯 GRE难度",
                "exam.config.difficulty.graduate_study": "🏛️ 研究生水平",
                "exam.config.difficulty.doctoral_research": "🔬 博士研究",
                "exam.config.difficulty_filter_desc": "不选择表示不限制难度",
                # Question type options (Updated for new AI system)
                "exam.config.type.multiple_choice": "📝 选择题",
                "exam.config.type.short_answer": "📄 简答题",
                "exam.config.type.programming": "💻 编程题",
                "exam.config.type.true_false": "✅ 判断题",
                "exam.config.type.fill_blank": "📝 填空题",
                "exam.config.type.essay": "📖 论述题",
                "exam.config.type_filter_desc": "不选择表示不限制题型",
                # Exam Interface
                "exam.title": "考试进行中 - IMBA 智能考试系统",
                "exam.time_remaining": "剩余时间",
                "exam.progress": "进度",
                "exam.question": "第",
                "exam.question_unit": "题",
                "exam.question_navigation": "题目导航",
                "exam.of": "题，共",
                "exam.previous": "上一题",
                "exam.next": "下一题",
                "exam.mark": "标记",
                "exam.submit": "提交考试",
                "exam.submit_early": "提前提交",
                "exam.submit_final": "提交考试",
                "exam.submit_suggestion": "建议提交",
                "exam.exit": "退出考试",
                "exam.exit_confirm_title": "确认退出考试",
                "exam.exit_confirm_message": "退出后您将无法继续作答，已答题目将不会保存。确定要退出吗？",
                "exam.submit_confirm_title": "确认提交考试",
                "exam.submit_confirm_message": "提交后将无法修改答案，确定要提交吗？",
                "exam.submit_early_confirm_title": "提前提交考试",
                "exam.submit_early_confirm_message": "您还有未完成的题目，提前提交可能影响成绩。确定要提交吗？",
                "exam.submit_final_confirm_title": "完成考试",
                "exam.submit_final_confirm_message": "您已完成所有题目，确定要提交考试吗？",
                "exam.cancel": "取消",
                "exam.confirm_submit": "确认提交",
                "exam.confirm_submit_early": "确认提前提交",
                "exam.confirm_submit_final": "提交考试",
                "exam.confirm_exit": "确认退出",
                "exam.last_question": "最后一题",
                "exam.last_question_tip": "这是最后一题，答题完成后建议提交考试。",
                "exam.no_options": "暂无选项",
                "exam.answer_placeholder": "请输入您的答案...",
                "exam.programming_code": "编程代码",
                "exam.code_placeholder": "请输入您的代码...",
                "exam.code_tip": "支持Python语法，请确保代码可以正常运行",
                "exam.invalid_id": "无效的考试ID",
                "exam.load_failed": "加载考试失败",
                "exam.load_failed_retry": "加载考试失败，请刷新页面重试",
                "exam.submit_failed": "提交失败",
                "exam.submit_failed_retry": "提交失败，请重试",
                "exam.time_up_auto_submit": "考试时间已到，系统将自动提交您的答案",
                "exam.leave_warning": "您正在进行考试，退出后将无法继续作答。确定要离开吗？",
                # Verification Page
                "verification.title": "考生身份验证 - IMBA 智能考试系统",
                "verification.subtitle": "安全可靠的在线考试平台",
                "verification.admin_mode": "管理员模式",
                "verification.admin_logged_in": "您已登录管理员账户",
                "verification.select_config": "选择考试配置...",
                "verification.start_exam_direct": "直接进入考试",
                "verification.logout": "退出登录",
                "verification.admin_panel": "管理面板",
                "verification.student_verification": "学生身份验证",
                "verification.form_instruction": "请填写您的考试信息",
                "verification.exam_instructions": "考试须知",
                "verification.auto_generate": "• 系统将根据默认配置自动生成考试题目",
                "verification.time_limit": "• 考试时间限制：加载中...",
                "verification.question_count": "• 题目数量：加载中...",
                "verification.subjects": "• 考试科目：加载中...",
                "verification.one_chance": "• 每位考生仅有一次考试机会，请认真作答",
                "verification.device_binding": "设备绑定信息",
                "verification.current_ip": "• 当前设备 IP：",
                "verification.device_id": "• 设备标识：",
                "verification.device_warning": "• 提交后将绑定当前设备，无法在其他设备重复考试",
                "verification.start_exam": "开始考试",
                "verification.admin_login": "管理员登录",
                "verification.admin_login_title": "管理员登录",
                "verification.admin_password_prompt": "请输入管理员密码",
                "verification.password": "密码",
                "verification.password_placeholder": "请输入管理员密码",
                "verification.cancel": "取消",
                "verification.login": "登录",
                "verification.processing": "正在处理，请稍候...",
                # Results Page
                "results.page_title": "考试成绩 - IMBA 智能考试系统",
                "results.loading": "正在加载成绩...",
                "results.load_failed": "加载失败",
                "results.load_failed_desc": "无法加载考试成绩，请稍后重试。",
                "results.reload": "重新加载",
                "results.title": "考试成绩",
                "results.congratulations": "恭喜您完成考试！以下是您的成绩详情",
                "results.total_score": "总分",
                "results.accuracy": "正确率",
                "results.grade": "等级",
                "results.question_analysis": "答题分析",
                "results.total_questions": "总题数",
                "results.correct_answers": "答对",
                "results.wrong_answers": "答错",
                "results.time_spent": "用时",
                "results.performance_summary": "成绩总结",
                "results.overall_evaluation": "总体评价",
                "results.strengths": "表现优异",
                "results.improvements": "改进建议",
                "results.print_results": "打印成绩单",
                "results.back_home": "返回首页",
                # Completion Page
                "completion.page_title": "考试完成 - IMBA 智能考试系统",
                "completion.title": "考试已完成！",
                "completion.congratulations": "恭喜您顺利完成本次考试",
                "completion.completion_time": "完成时间：",
                "completion.notice_title": "温馨提示",
                "completion.notice1": "✓ 您的答案已成功提交并保存",
                "completion.notice2": "✓ 系统正在处理您的答卷",
                "completion.notice3": "✓ 考试结果将在稍后通过相关渠道通知您",
                "completion.total_questions": "题目总数",
                "completion.answered_questions": "已答题目",
                "completion.time_spent": "用时",
                "completion.important_notice": "重要说明：",
                "completion.notice_item1": "• 本次考试已正式结束，无法再次进入或修改答案",
                "completion.notice_item2": "• 请等待官方通知获取考试结果",
                "completion.notice_item3": "• 如有疑问，请联系相关负责人",
                "completion.back_home": "返回首页",
                "completion.print_confirmation": "打印确认单",
                "completion.footer_text": "感谢您参与本次考试 | IMBA 智能考试系统",
                # Exam Management Page
                "exam_management.title": "考试管理",
                "exam_management.description": "管理考试模板和学生信息，查看考试统计数据",
                "exam_management.total_templates": "总考试数",
                "exam_management.total_participants": "总参与人数",
                "exam_management.avg_score": "平均分",
                "exam_management.active_exams": "进行中考试",
                "exam_management.exam_templates": "考试管理",
                "exam_management.student_management": "学生管理",
                "exam_management.exam_list": "考试列表",
                "exam_management.student_list": "学生列表",
                "exam_management.add_student": "添加学生",
                "exam_management.no_exams": "暂无考试",
                # Student Management
                "student.name": "姓名",
                "student.id_number": "学号",
                "student.application_number": "申请号",
                "student.exam_count": "考试次数",
                "student.avg_score": "平均分",
                "student.device_ip": "IP地址",
                "student.created_at": "注册时间",
                "student.search_placeholder": "搜索学生...",
                "student.select_all": "全选",
                "student.batch_delete": "批量删除",
                "student.delete_all": "全部删除",
                "student.delete_all_confirm": "确定要删除所有学生吗？此操作无法撤销。",
                "student.list_header": "学生列表",
                "student.selected": "已选择",
                "student.students": "个学生",
                # Navigation
                "nav.admin_panel": "管理面板",
                "nav.exam_config": "考试配置",
                # Common
                "common.cancel": "取消",
                "common.refresh": "刷新",
                "common.loading": "加载中...",
                "common.actions": "操作",
                "common.save": "保存",
                "common.previous": "上一页",
                "common.next": "下一页",
                "common.showing": "显示",
                "common.to": "到",
                "common.of": "共",
                "common.results": "条结果",
            },
        }

        return jsonify({"success": True, "translations": translations})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/students-management/batch-delete", methods=["DELETE"])
@admin_required
def batch_delete_students():
    """批量删除学生（安全级联删除）"""
    try:
        data = request.get_json()
        student_ids = data.get("student_ids", [])

        if not student_ids:
            return jsonify({"success": False, "message": "请选择要删除的学生"}), 400

        # 验证学生ID是否存在
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        if not students:
            return jsonify({"success": False, "message": "未找到要删除的学生"}), 404

        deleted_count = 0
        failed_deletions = []

        for student in students:
            try:
                student_id = student.id

                # 安全的级联删除，按依赖关系顺序
                # 1. 删除答案记录
                sessions = ExamSession.query.filter_by(student_id=student_id).all()
                for session in sessions:
                    exams = Exam.query.filter_by(session_id=session.id).all()
                    for exam in exams:
                        Answer.query.filter_by(exam_id=exam.id).delete(
                            synchronize_session=False
                        )

                instances = ExamInstance.query.filter_by(student_id=student_id).all()
                for instance in instances:
                    Answer.query.filter_by(exam_instance_id=instance.id).delete(
                        synchronize_session=False
                    )

                # 2. 删除学生答案记录
                student_exams = StudentExam.query.filter_by(student_id=student_id).all()
                for student_exam in student_exams:
                    StudentAnswer.query.filter_by(
                        student_exam_id=student_exam.id
                    ).delete(synchronize_session=False)

                # 3. 删除考试题目关联记录
                for session in sessions:
                    exams = Exam.query.filter_by(session_id=session.id).all()
                    for exam in exams:
                        ExamQuestion.query.filter_by(exam_id=exam.id).delete(
                            synchronize_session=False
                        )

                # 4. 删除学生考试记录
                StudentExamRecord.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )
                StudentExam.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )

                # 5. 删除考试记录
                for session in sessions:
                    Exam.query.filter_by(session_id=session.id).delete(
                        synchronize_session=False
                    )

                # 6. 删除考试实例
                ExamInstance.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )

                # 7. 删除考试会话
                ExamSession.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )

                # 8. 删除学生记录
                db.session.delete(student)
                deleted_count += 1

            except Exception as e:
                failed_deletions.append(
                    f"学生 {student.name} (ID: {student.id}): {str(e)}"
                )
                continue

        # 提交所有更改
        db.session.commit()

        if failed_deletions:
            message = f"成功删除 {deleted_count} 个学生，{len(failed_deletions)} 个失败"
            return jsonify(
                {"success": True, "message": message, "details": failed_deletions}
            )
        else:
            return jsonify(
                {"success": True, "message": f"成功删除 {deleted_count} 个学生"}
            )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 批量删除失败: {str(e)}")
        return jsonify({"success": False, "message": f"批量删除失败: {str(e)}"}), 500


@app.route("/api/students-management/delete-all", methods=["DELETE"])
@admin_required
def delete_all_students():
    """删除所有学生（安全级联删除）"""
    try:
        # 获取所有学生
        students = Student.query.all()

        if not students:
            return jsonify({"success": False, "message": "没有学生可以删除"}), 400

        deleted_count = 0
        failed_deletions = []

        for student in students:
            try:
                student_id = student.id

                # 安全的级联删除，按依赖关系顺序
                # 1. 删除答案记录
                sessions = ExamSession.query.filter_by(student_id=student_id).all()
                for session in sessions:
                    exams = Exam.query.filter_by(session_id=session.id).all()
                    for exam in exams:
                        Answer.query.filter_by(exam_id=exam.id).delete(
                            synchronize_session=False
                        )

                instances = ExamInstance.query.filter_by(student_id=student_id).all()
                for instance in instances:
                    Answer.query.filter_by(exam_instance_id=instance.id).delete(
                        synchronize_session=False
                    )

                # 2. 删除学生答案记录
                student_exams = StudentExam.query.filter_by(student_id=student_id).all()
                for student_exam in student_exams:
                    StudentAnswer.query.filter_by(
                        student_exam_id=student_exam.id
                    ).delete(synchronize_session=False)

                # 3. 删除考试题目关联记录
                for session in sessions:
                    exams = Exam.query.filter_by(session_id=session.id).all()
                    for exam in exams:
                        ExamQuestion.query.filter_by(exam_id=exam.id).delete(
                            synchronize_session=False
                        )

                # 4. 删除学生考试记录
                StudentExamRecord.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )
                StudentExam.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )

                # 5. 删除考试记录
                for session in sessions:
                    Exam.query.filter_by(session_id=session.id).delete(
                        synchronize_session=False
                    )

                # 6. 删除考试实例
                ExamInstance.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )

                # 7. 删除考试会话
                ExamSession.query.filter_by(student_id=student_id).delete(
                    synchronize_session=False
                )

                # 8. 删除学生记录
                db.session.delete(student)
                deleted_count += 1

            except Exception as e:
                failed_deletions.append(
                    f"学生 {student.name} (ID: {student.id}): {str(e)}"
                )
                continue

        # 提交所有更改
        db.session.commit()

        if failed_deletions:
            message = f"成功删除 {deleted_count} 个学生，{len(failed_deletions)} 个失败"
            return jsonify(
                {"success": True, "message": message, "details": failed_deletions}
            )
        else:
            return jsonify(
                {"success": True, "message": f"成功删除所有 {deleted_count} 个学生"}
            )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 全部删除失败: {str(e)}")
        return jsonify({"success": False, "message": f"全部删除失败: {str(e)}"}), 500


@app.route("/api/student-answers/<int:student_id>", methods=["GET"])
@admin_required
def get_student_answer_details(student_id):
    """获取学生答题详情"""
    try:
        student = Student.query.get_or_404(student_id)

        # 获取学生的所有考试记录
        exam_records = []

        # 从ExamInstance获取记录
        instances = ExamInstance.query.filter_by(student_id=student_id).all()
        for instance in instances:
            # 获取该实例的答案
            answers = Answer.query.filter_by(exam_instance_id=instance.id).all()

            questions_data = []
            total_questions = 0
            correct_count = 0

            if answers:
                for answer in answers:
                    # 从questions表获取题目信息
                    question = Question.query.get(answer.question_id)
                    if question:
                        is_correct = (
                            answer.is_correct
                            if answer.is_correct is not None
                            else False
                        )
                        questions_data.append(
                            {
                                "question_text": question.content,
                                "student_answer": answer.answer_text,
                                "correct_answer": question.correct_answer,
                                "is_correct": is_correct,
                            }
                        )
                        total_questions += 1
                        if is_correct:
                            correct_count += 1

            # 计算分数
            score = correct_count
            total_score = total_questions
            percentage = round((score / total_score * 100) if total_score > 0 else 0, 1)

            # 计算用时（如果有开始和结束时间）
            time_spent_minutes = None
            if instance.started_at and instance.completed_at:
                time_delta = instance.completed_at - instance.started_at
                time_spent_minutes = int(time_delta.total_seconds() / 60)

            exam_records.append(
                {
                    "exam_name": instance.name,
                    "status": instance.status,
                    "score": score,
                    "total_score": total_score,
                    "percentage": percentage,
                    "completed_at": (
                        instance.completed_at.isoformat()
                        if instance.completed_at
                        else None
                    ),
                    "time_spent_minutes": time_spent_minutes,
                    "questions": questions_data,
                }
            )

        # 从Exam表获取记录（兼容旧版本）
        sessions = ExamSession.query.filter_by(student_id=student_id).all()
        for session in sessions:
            exams = Exam.query.filter_by(session_id=session.id).all()
            for exam in exams:
                answers = Answer.query.filter_by(exam_id=exam.id).all()

                questions_data = []
                total_questions = 0
                correct_count = 0

                if answers:
                    for answer in answers:
                        # 尝试从question_id获取题目
                        question = None
                        if answer.question_id and answer.question_id.isdigit():
                            question = Question.query.get(int(answer.question_id))

                        if question:
                            is_correct = (
                                answer.is_correct
                                if answer.is_correct is not None
                                else False
                            )
                            questions_data.append(
                                {
                                    "question_text": question.content,
                                    "student_answer": answer.answer_text,
                                    "correct_answer": question.correct_answer,
                                    "is_correct": is_correct,
                                }
                            )
                            total_questions += 1
                            if is_correct:
                                correct_count += 1

                # 计算分数
                score = correct_count
                total_score = total_questions
                percentage = round(
                    (score / total_score * 100) if total_score > 0 else 0, 1
                )

                # 计算用时（如果有开始和结束时间）
                time_spent_minutes = None
                if exam.started_at and exam.completed_at:
                    time_delta = exam.completed_at - exam.started_at
                    time_spent_minutes = int(time_delta.total_seconds() / 60)

                # 获取考试配置名称
                exam_name = f"考试 #{exam.id}"
                if exam.config_id:
                    config = ExamConfig.query.get(exam.config_id)
                    if config:
                        exam_name = config.name

                exam_records.append(
                    {
                        "exam_name": exam_name,
                        "status": "completed" if exam.completed_at else "in_progress",
                        "score": score,
                        "total_score": total_score,
                        "percentage": percentage,
                        "completed_at": (
                            exam.completed_at.isoformat() if exam.completed_at else None
                        ),
                        "time_spent_minutes": time_spent_minutes,
                        "questions": questions_data,
                    }
                )

        return jsonify(
            {"success": True, "student_name": student.name, "answers": exam_records}
        )

    except Exception as e:
        print(f"❌ 获取学生答题详情失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@app.route("/api/admin/dashboard-stats", methods=["GET"])
@admin_required
def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        from datetime import datetime, timedelta

        # 统计题目总数
        total_questions = Question.query.count()

        # 统计学生总数
        total_students = Student.query.count()

        # 统计考试配置总数 (即"Total Exams"应该显示的数字)
        total_exams = ExamConfig.query.count()

        # 统计考试实例总数 (实际的考试记录数)
        exam_instances_count = ExamInstance.query.count()
        exam_records_count = Exam.query.count()
        total_exam_records = exam_instances_count + exam_records_count

        # 计算今日考试次数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        today_exams = ExamInstance.query.filter(
            ExamInstance.created_at >= today_start, ExamInstance.created_at < today_end
        ).count()

        # 计算平均考试时长 (分钟)
        completed_exams = ExamInstance.query.filter(
            ExamInstance.completed_at.isnot(None), ExamInstance.created_at.isnot(None)
        ).all()

        if completed_exams:
            total_duration = 0
            valid_durations = 0
            for exam in completed_exams:
                if exam.completed_at and exam.created_at:
                    duration = (
                        exam.completed_at - exam.created_at
                    ).total_seconds() / 60
                    if 0 < duration < 300:  # 合理的时间范围 (0-300分钟)
                        total_duration += duration
                        valid_durations += 1
            avg_duration = (
                round(total_duration / valid_durations) if valid_durations > 0 else 0
            )
        else:
            avg_duration = 0

        # 计算平均成绩
        scored_exams = ExamInstance.query.filter(
            ExamInstance.percentage.isnot(None)
        ).all()
        avg_score = (
            round(sum(exam.percentage for exam in scored_exams) / len(scored_exams))
            if scored_exams
            else 0
        )

        # 计算通过率 (假设60分及格)
        if scored_exams:
            passed_exams = [exam for exam in scored_exams if exam.percentage >= 60]
            pass_rate = (
                round((len(passed_exams) / len(scored_exams)) * 100)
                if scored_exams
                else 0
            )
        else:
            pass_rate = 0

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_questions": total_questions,
                    "total_students": total_students,
                    "total_exams": total_exams,  # 现在是考试配置数量
                    "total_exam_records": total_exam_records,  # 实际考试记录数
                    "today_exams": today_exams,
                    "avg_duration": avg_duration,
                    "avg_score": avg_score,
                    "pass_rate": pass_rate,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取仪表板统计数据失败: {str(e)}")
        return (
            jsonify({"success": False, "message": f"获取统计数据失败: {str(e)}"}),
            500,
        )


@app.route("/api/admin/dashboard-charts", methods=["GET"])
@admin_required
def get_dashboard_charts_data():
    """获取仪表板图表数据"""
    try:
        # 1. 题目分布数据（按学科统计）
        question_distribution = {}
        questions = Question.query.all()
        for question in questions:
            subject = question.subject
            question_distribution[subject] = question_distribution.get(subject, 0) + 1

        question_chart_data = {
            "labels": list(question_distribution.keys()),
            "data": list(question_distribution.values()),
        }

        # 2. 成绩分布数据
        performance_distribution = {
            "0-60": 0,
            "60-70": 0,
            "70-80": 0,
            "80-90": 0,
            "90-100": 0,
        }

        # 从ExamInstance获取成绩
        instances = ExamInstance.query.filter(ExamInstance.percentage.isnot(None)).all()
        for instance in instances:
            score = instance.percentage
            if score < 60:
                performance_distribution["0-60"] += 1
            elif score < 70:
                performance_distribution["60-70"] += 1
            elif score < 80:
                performance_distribution["70-80"] += 1
            elif score < 90:
                performance_distribution["80-90"] += 1
            else:
                performance_distribution["90-100"] += 1

        # 从Exam表获取成绩（兼容旧版本）
        # 注意：旧版Exam可能没有percentage字段，需要从scores字段解析
        exams = Exam.query.filter(Exam.scores.isnot(None)).all()
        for exam in exams:
            try:
                # 尝试解析scores JSON字段获取百分比
                import json

                scores_data = json.loads(exam.scores) if exam.scores else {}
                score = scores_data.get("percentage", 0)

                if score < 60:
                    performance_distribution["0-60"] += 1
                elif score < 70:
                    performance_distribution["60-70"] += 1
                elif score < 80:
                    performance_distribution["70-80"] += 1
                elif score < 90:
                    performance_distribution["80-90"] += 1
                else:
                    performance_distribution["90-100"] += 1
            except (json.JSONDecodeError, AttributeError):
                # 如果解析失败，跳过这条记录
                continue

        performance_chart_data = {
            "labels": list(performance_distribution.keys()),
            "data": list(performance_distribution.values()),
        }

        # 3. 最近活动数据
        recent_activities = []

        # 获取最近的考试实例
        recent_instances = (
            ExamInstance.query.filter(ExamInstance.completed_at.isnot(None))
            .order_by(ExamInstance.completed_at.desc())
            .limit(10)
            .all()
        )

        for instance in recent_instances:
            student = Student.query.get(instance.student_id)
            if student:
                # 计算用时
                time_spent = None
                if instance.started_at and instance.completed_at:
                    time_delta = instance.completed_at - instance.started_at
                    time_spent = f"{int(time_delta.total_seconds() / 60)}分钟"

                recent_activities.append(
                    {
                        "student_name": student.name,
                        "exam_name": instance.name,
                        "score": (
                            f"{instance.percentage:.1f}%"
                            if instance.percentage
                            else "-"
                        ),
                        "status": (
                            "已完成" if instance.status == "completed" else "进行中"
                        ),
                        "completed_at": (
                            instance.completed_at.isoformat()
                            if instance.completed_at
                            else None
                        ),
                        "time_spent": time_spent or "-",
                    }
                )

        # 如果实例数据不足，补充旧版Exam数据
        if len(recent_activities) < 10:
            remaining_count = 10 - len(recent_activities)
            recent_exams = (
                Exam.query.filter(Exam.completed_at.isnot(None))
                .order_by(Exam.completed_at.desc())
                .limit(remaining_count)
                .all()
            )

            for exam in recent_exams:
                session = ExamSession.query.get(exam.session_id)
                if session:
                    student = Student.query.get(session.student_id)
                    if student:
                        # 计算用时
                        time_spent_text = "-"
                        if exam.started_at and exam.completed_at:
                            time_delta = exam.completed_at - exam.started_at
                            time_spent_minutes = int(time_delta.total_seconds() / 60)
                            time_spent_text = f"{time_spent_minutes}分钟"

                        # 获取分数
                        score_text = "-"
                        try:
                            import json

                            scores_data = json.loads(exam.scores) if exam.scores else {}
                            percentage = scores_data.get("percentage_score", 0)
                            if percentage:
                                score_text = f"{percentage:.1f}%"
                        except (json.JSONDecodeError, AttributeError):
                            pass

                        # 获取考试配置名称
                        exam_name = f"考试 #{exam.id}"
                        if exam.config_id:
                            config = ExamConfig.query.get(exam.config_id)
                            if config:
                                exam_name = config.name

                        recent_activities.append(
                            {
                                "student_name": student.name,
                                "exam_name": exam_name,
                                "score": score_text,
                                "status": "已完成",
                                "completed_at": (
                                    exam.completed_at.isoformat()
                                    if exam.completed_at
                                    else None
                                ),
                                "time_spent": time_spent_text,
                            }
                        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "question_distribution": question_chart_data,
                    "performance_distribution": performance_chart_data,
                    "recent_activities": recent_activities,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取仪表板图表数据失败: {str(e)}")
        return (
            jsonify({"success": False, "message": f"获取图表数据失败: {str(e)}"}),
            500,
        )


@app.route("/api/all-student-answers", methods=["GET"])
@admin_required
def get_all_student_answers():
    """获取所有学生答题记录"""
    try:
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 10)), 100)

        answers_data = []

        # 从Answer表获取答题记录（新版本）
        answers_query = (
            Answer.query.join(Question)
            .outerjoin(ExamInstance, Answer.exam_instance_id == ExamInstance.id)
            .outerjoin(Student, ExamInstance.student_id == Student.id)
            .filter(Answer.exam_instance_id.isnot(None))
            .with_entities(
                Answer.answer_text,
                Answer.is_correct,
                Answer.submitted_at,
                Question.content.label("question_text"),
                Question.correct_answer,
                Student.name.label("student_name"),
                ExamInstance.name.label("exam_name"),
            )
            .order_by(Answer.submitted_at.desc())
        )

        # 获取总数和分页
        total = answers_query.count()
        answers = answers_query.offset((page - 1) * per_page).limit(per_page).all()

        for answer in answers:
            answers_data.append(
                {
                    "student_name": answer.student_name or "未知学生",
                    "exam_name": answer.exam_name or "未知考试",
                    "question_text": answer.question_text,
                    "student_answer": answer.answer_text or "未作答",
                    "correct_answer": answer.correct_answer,
                    "is_correct": (
                        answer.is_correct if answer.is_correct is not None else False
                    ),
                    "submitted_at": (
                        answer.submitted_at.isoformat() if answer.submitted_at else None
                    ),
                }
            )

        # 如果新版数据不足，补充旧版Answer数据
        if len(answers_data) < per_page and page == 1:
            remaining_count = per_page - len(answers_data)

            # 从Answer表获取旧版答题记录
            old_answers_query = (
                Answer.query.join(Question)
                .outerjoin(Exam, Answer.exam_id == Exam.id)
                .outerjoin(ExamSession, Exam.session_id == ExamSession.id)
                .outerjoin(Student, ExamSession.student_id == Student.id)
                .filter(Answer.exam_id.isnot(None))
                .with_entities(
                    Answer.answer_text,
                    Answer.is_correct,
                    Answer.submitted_at,
                    Question.content.label("question_text"),
                    Question.correct_answer,
                    Student.name.label("student_name"),
                    Exam.id.label("exam_id"),
                )
                .order_by(Answer.submitted_at.desc())
                .limit(remaining_count)
            )

            old_answers = old_answers_query.all()
            for answer in old_answers:
                answers_data.append(
                    {
                        "student_name": answer.student_name or "未知学生",
                        "exam_name": (
                            f"考试 #{answer.exam_id}" if answer.exam_id else "未知考试"
                        ),
                        "question_text": answer.question_text,
                        "student_answer": answer.answer_text or "未作答",
                        "correct_answer": answer.correct_answer,
                        "is_correct": (
                            answer.is_correct
                            if answer.is_correct is not None
                            else False
                        ),
                        "submitted_at": (
                            answer.submitted_at.isoformat()
                            if answer.submitted_at
                            else None
                        ),
                    }
                )

        # 分页信息
        pages = (total + per_page - 1) // per_page
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
        }

        return jsonify(
            {"success": True, "answers": answers_data, "pagination": pagination}
        )

    except Exception as e:
        print(f"❌ 获取学生答题记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@app.route("/api/admin/all-student-answers-summary", methods=["GET"])
@admin_required
def get_admin_all_student_answers_summary():
    """管理员查看所有学生答题汇总"""
    try:
        # 获取所有学生的基本信息和考试概况
        students = Student.query.all()
        students_data = []

        for student in students:
            # 统计该学生的考试次数和平均分
            # 新版ExamInstance
            instances = ExamInstance.query.filter_by(student_id=student.id).all()
            instance_count = len(instances)
            instance_avg_score = 0

            if instances:
                total_percentage = sum(i.percentage or 0 for i in instances)
                instance_avg_score = (
                    total_percentage / instance_count if instance_count > 0 else 0
                )

            # 旧版Exam
            sessions = ExamSession.query.filter_by(student_id=student.id).all()
            exam_count = 0
            exam_avg_score = 0

            if sessions:
                total_scores = []
                for session in sessions:
                    exams = Exam.query.filter_by(session_id=session.id).all()
                    exam_count += len(exams)
                    for exam in exams:
                        if exam.scores:
                            try:
                                import json

                                scores_data = json.loads(exam.scores)
                                percentage = scores_data.get("percentage", 0)
                                total_scores.append(percentage)
                            except:
                                pass

                exam_avg_score = (
                    sum(total_scores) / len(total_scores) if total_scores else 0
                )

            # 计算总体统计
            total_exams = instance_count + exam_count
            overall_avg = (
                ((instance_avg_score * instance_count) + (exam_avg_score * exam_count))
                / total_exams
                if total_exams > 0
                else 0
            )

            # 获取最近一次考试时间
            last_exam_time = None
            if instances:
                last_instance = max(
                    instances, key=lambda x: x.completed_at or x.created_at
                )
                last_exam_time = last_instance.completed_at or last_instance.created_at

            if sessions and exam_count > 0:
                last_session = max(sessions, key=lambda x: x.created_at)
                session_exams = Exam.query.filter_by(session_id=last_session.id).all()
                if session_exams:
                    last_exam = max(
                        session_exams, key=lambda x: x.completed_at or x.created_at
                    )
                    session_last_time = last_exam.completed_at or last_exam.created_at
                    if not last_exam_time or (
                        session_last_time and session_last_time > last_exam_time
                    ):
                        last_exam_time = session_last_time

            students_data.append(
                {
                    "id": student.id,
                    "name": student.name,
                    "student_id": student.id_number,
                    "total_exams": total_exams,
                    "avg_score": round(overall_avg, 1),
                    "last_exam_at": (
                        last_exam_time.isoformat() if last_exam_time else None
                    ),
                    "status": "活跃" if total_exams > 0 else "未参加",
                }
            )

        # 按最近考试时间排序
        students_data.sort(
            key=lambda x: x["last_exam_at"] or "1970-01-01T00:00:00", reverse=True
        )

        return jsonify({"success": True, "students": students_data})

    except Exception as e:
        print(f"❌ 获取学生答题汇总失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@app.route("/api/admin/system-config", methods=["GET"])
@admin_required
def get_admin_system_config():
    """获取管理员系统配置"""
    try:
        configs = SystemConfig.query.all()
        config_list = [config.to_dict() for config in configs]

        return jsonify({"success": True, "configs": config_list})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/validate-api", methods=["POST"])
@admin_required
def validate_api_key():
    """验证API密钥并获取可用模型"""
    try:
        data = request.get_json()
        api_key = data.get("api_key", "").strip()

        if not api_key:
            return jsonify({"success": False, "message": "API密钥不能为空"}), 400

        # 验证API密钥并获取模型列表
        try:
            import requests

            # 测试API密钥有效性
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cbit-exam-system.com",
                "X-Title": "CBIT Exam Question Generator",
            }

            # 获取可用模型列表
            models_url = "https://openrouter.ai/api/v1/models"
            models_response = requests.get(models_url, headers=headers, timeout=10)

            if models_response.status_code == 200:
                models_data = models_response.json()
                available_models = []

                # 提取模型信息
                for model in models_data.get("data", []):
                    model_id = model.get("id", "")
                    model_name = model.get("name", model_id)

                    # 只显示推荐的模型
                    if any(
                        recommended in model_id.lower()
                        for recommended in [
                            "gpt-4",
                            "gpt-3.5",
                            "claude-3",
                            "claude-2",
                            "gemini-pro",
                            "llama-2",
                        ]
                    ):
                        available_models.append(
                            {
                                "id": model_id,
                                "name": model_name,
                                "context_length": model.get("context_length", 0),
                                "pricing": model.get("pricing", {}),
                            }
                        )

                # 按名称排序
                available_models.sort(key=lambda x: x["name"])

                return jsonify(
                    {
                        "success": True,
                        "message": "API密钥验证成功",
                        "models": available_models,
                    }
                )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"API密钥验证失败: {models_response.status_code}",
                        }
                    ),
                    400,
                )

        except requests.exceptions.RequestException as e:
            return (
                jsonify({"success": False, "message": f"网络请求失败: {str(e)}"}),
                500,
            )
        except Exception as e:
            return jsonify({"success": False, "message": f"API验证失败: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/api-providers", methods=["GET"])
@admin_required
def get_api_providers():
    """获取所有API提供商配置"""
    try:
        from ai_engine.api_manager import ApiManager

        api_manager = ApiManager()
        providers = api_manager.get_available_providers()

        return jsonify({"success": True, "providers": providers})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/api-providers/<provider_name>/validate", methods=["POST"])
@admin_required
def validate_provider_api(provider_name):
    """验证指定提供商的API密钥"""
    try:
        from ai_engine.api_manager import ApiManager, ApiProvider

        data = request.get_json()
        api_key = data.get("api_key", "").strip()

        if not api_key:
            return jsonify({"success": False, "message": "API密钥不能为空"}), 400

        # 验证provider_name是否有效
        try:
            provider = ApiProvider(provider_name)
        except ValueError:
            return (
                jsonify(
                    {"success": False, "message": f"不支持的API提供商: {provider_name}"}
                ),
                400,
            )

        api_manager = ApiManager()
        result = api_manager.validate_api_key(provider, api_key)

        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "message": "API密钥验证成功",
                    "models": result["models"],
                }
            )
        else:
            return jsonify({"success": False, "message": result["error"]}), 400

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/api-providers/<provider_name>", methods=["POST"])
@admin_required
def save_provider_config(provider_name):
    """保存API提供商配置"""
    try:
        from ai_engine.api_manager import ApiManager, ApiProvider

        data = request.get_json()
        api_key = data.get("api_key", "").strip()
        model = data.get("model", "").strip()

        if not api_key:
            return jsonify({"success": False, "message": "API密钥不能为空"}), 400

        # 验证provider_name是否有效
        try:
            provider = ApiProvider(provider_name)
        except ValueError:
            return (
                jsonify(
                    {"success": False, "message": f"不支持的API提供商: {provider_name}"}
                ),
                400,
            )

        print(
            f"🔧 尝试保存 {provider_name} 配置: API密钥={api_key[:10]}..., 模型={model}"
        )

        api_manager = ApiManager()
        success = api_manager.save_provider_config(provider, api_key, model)

        print(f"📊 保存结果: {success}")

        if success:
            return jsonify(
                {"success": True, "message": f"{provider_name.title()} API配置保存成功"}
            )
        else:
            return (
                jsonify(
                    {"success": False, "message": "保存配置失败，请检查API密钥是否有效"}
                ),
                400,
            )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/api-providers/<provider_name>/activate", methods=["POST"])
@admin_required
def activate_provider(provider_name):
    """激活指定的API提供商"""
    try:
        from ai_engine.api_manager import ApiManager, ApiProvider

        # 验证provider_name是否有效
        try:
            provider = ApiProvider(provider_name)
        except ValueError:
            return (
                jsonify(
                    {"success": False, "message": f"不支持的API提供商: {provider_name}"}
                ),
                400,
            )

        api_manager = ApiManager()
        success = api_manager.activate_provider(provider)

        if success:
            return jsonify(
                {"success": True, "message": f"已成功激活 {provider_name.title()} API"}
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"激活失败，请确保已正确配置 {provider_name.title()} API",
                    }
                ),
                400,
            )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/api-providers/<provider_name>/details", methods=["GET"])
@admin_required
def get_provider_details(provider_name):
    """获取指定API提供商的详细配置"""
    try:
        from models import ApiProvider as ApiProviderModel

        from ai_engine.api_manager import ApiProvider

        # 验证provider_name是否有效
        try:
            provider = ApiProvider(provider_name)
        except ValueError:
            return (
                jsonify(
                    {"success": False, "message": f"不支持的API提供商: {provider_name}"}
                ),
                400,
            )

        # 从数据库获取配置
        provider_config = ApiProviderModel.query.filter_by(
            provider_name=provider_name
        ).first()

        if not provider_config:
            return (
                jsonify({"success": False, "message": f"{provider_name} 配置不存在"}),
                404,
            )

        return jsonify(
            {
                "success": True,
                "config": {
                    "provider_name": provider_config.provider_name,
                    "api_key": provider_config.api_key,  # 完整密钥，前端会处理显示
                    "default_model": provider_config.default_model,
                    "is_active": provider_config.is_active,
                    "is_verified": provider_config.is_verified,
                    "api_url": provider_config.api_url,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取 {provider_name} 详细配置失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/test-scoring", methods=["POST"])
@admin_required
def test_scoring():
    """测试评分系统（调试用）"""
    try:
        print("🧪 开始测试评分系统...")

        # 创建ScoringSystem实例
        scoring = get_scoring_system()
        print(f"📊 AI评分启用: {scoring.ai_scoring_enabled}")
        print(f"🔑 API密钥: {'已配置' if scoring.api_key else '未配置'}")
        print(f"🎯 AI模型: {scoring.model or '未设置'}")

        # 测试简答题评分
        test_question = {
            "id": 999,
            "content": "什么是机器学习？",
            "correct_answer": "机器学习是人工智能的一个分支，通过算法让计算机从数据中学习",
            "question_type": "short_answer",
            "points": 5,
        }

        test_answer = "机器学习是AI的重要组成部分，能让计算机自动学习"

        score, max_score = scoring._score_short_answer(test_question, test_answer, 5.0)
        print(f"📝 简答题测试结果: {score}/{max_score} = {score/max_score*100:.1f}%")

        # 测试选择题评分
        test_mc_question = {
            "id": 998,
            "content": "1+1等于？",
            "options": json.dumps(["A. 1", "B. 2", "C. 3", "D. 4"]),
            "correct_answer": "B",
            "question_type": "multiple_choice",
            "points": 2,
        }

        test_mc_answer = "B"
        mc_score, mc_max_score = scoring._score_multiple_choice(
            test_mc_question, test_mc_answer, 2.0
        )
        print(
            f"📋 选择题测试结果: {mc_score}/{mc_max_score} = {mc_score/mc_max_score*100:.1f}%"
        )

        return jsonify(
            {
                "success": True,
                "results": {
                    "ai_scoring_enabled": scoring.ai_scoring_enabled,
                    "api_configured": bool(scoring.api_key),
                    "model": scoring.model,
                    "short_answer_score": f"{score}/{max_score}",
                    "multiple_choice_score": f"{mc_score}/{mc_max_score}",
                },
            }
        )

    except Exception as e:
        print(f"❌ 评分测试失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/rescore-answers", methods=["POST"])
@admin_required
def rescore_answers():
    """重新评分所有答案（修复用）"""
    try:
        data = request.get_json()
        student_id = data.get("student_id")  # 可选，指定学生

        print(
            f"🔄 开始重新评分答案{f'（学生ID: {student_id}）' if student_id else '（所有学生）'}..."
        )

        # 获取需要重新评分的答案
        if student_id:
            # 通过exam_instance和exam关联查找答案
            exam_instance_answers = (
                Answer.query.join(ExamInstance)
                .filter(ExamInstance.student_id == student_id)
                .all()
            )
            exam_answers = (
                Answer.query.join(Exam)
                .join(ExamSession)
                .filter(ExamSession.student_id == student_id)
                .all()
            )
            answers = exam_instance_answers + exam_answers
        else:
            answers = Answer.query.all()

        print(f"📋 找到 {len(answers)} 个答案需要重新评分")

        scoring = get_scoring_system()
        rescored_count = 0
        error_count = 0

        for answer in answers:
            try:
                # 获取题目信息
                question = Question.query.get(answer.question_id)
                if not question:
                    print(f"⚠️  跳过答案 {answer.id}：题目 {answer.question_id} 不存在")
                    continue

                old_score = answer.score

                # 根据题目类型重新评分
                if question.question_type == "multiple_choice":
                    score, max_score = scoring._score_multiple_choice(
                        question.to_dict(), answer.answer_text, question.points
                    )
                elif question.question_type == "short_answer":
                    score, max_score = scoring._score_short_answer(
                        question.to_dict(), answer.answer_text, question.points
                    )
                elif question.question_type == "programming":
                    score, max_score = scoring._score_programming(
                        question.to_dict(), answer.answer_text, question.points
                    )
                else:
                    print(
                        f"⚠️  跳过答案 {answer.id}：未知题目类型 {question.question_type}"
                    )
                    continue

                # 更新答案
                answer.score = score
                answer.is_correct = score >= max_score * 0.8  # 80%以上算正确

                if old_score != score:
                    print(
                        f"📝 题目 {question.id} ({question.question_type}): {old_score} → {score}/{max_score}"
                    )
                    rescored_count += 1

            except Exception as e:
                print(f"❌ 评分答案 {answer.id} 失败: {str(e)}")
                error_count += 1

        # 保存更改
        db.session.commit()

        print(f"✅ 重新评分完成：{rescored_count} 个答案被更新，{error_count} 个错误")

        return jsonify(
            {
                "success": True,
                "rescored_count": rescored_count,
                "error_count": error_count,
                "total_answers": len(answers),
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"❌ 重新评分失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/debug-export", methods=["GET"])
@admin_required
def debug_export():
    """调试导出数据问题"""
    try:
        print("🔍 调试导出数据问题...")

        # 查找管理员测试学生的所有答案
        answers = Answer.query.all()
        print(f"📋 数据库中总答案数: {len(answers)}")

        student_answers = []
        for answer in answers:
            # 通过ExamInstance查找
            if answer.exam_instance_id:
                instance = ExamInstance.query.get(answer.exam_instance_id)
                if instance and instance.student_id == 1:  # 管理员测试
                    student_answers.append(
                        {
                            "type": "instance",
                            "answer_id": answer.id,
                            "instance_id": instance.id,
                            "template_id": instance.template_id,
                            "question_id": answer.question_id,
                            "score": answer.score,
                            "answer_text": (
                                answer.answer_text[:50] + "..."
                                if answer.answer_text
                                else None
                            ),
                        }
                    )

            # 通过Exam查找
            if answer.exam_id:
                exam = Exam.query.get(answer.exam_id)
                if exam and exam.session_id:
                    session = ExamSession.query.get(exam.session_id)
                    if session and session.student_id == 1:  # 管理员测试
                        student_answers.append(
                            {
                                "type": "exam",
                                "answer_id": answer.id,
                                "exam_id": exam.id,
                                "config_id": exam.config_id,
                                "question_id": answer.question_id,
                                "score": answer.score,
                                "answer_text": (
                                    answer.answer_text[:50] + "..."
                                    if answer.answer_text
                                    else None
                                ),
                            }
                        )

        print(f"🎯 管理员测试的答案数: {len(student_answers)}")

        # 查找所有考试模板
        templates = ExamTemplate.query.all()
        template_info = [{"id": t.id, "name": t.name} for t in templates]

        # 查找所有考试实例
        instances = ExamInstance.query.filter_by(student_id=1).all()
        instance_info = [
            {"id": i.id, "template_id": i.template_id, "status": i.status}
            for i in instances
        ]

        return jsonify(
            {
                "success": True,
                "debug_info": {
                    "total_answers": len(answers),
                    "student_answers": student_answers,
                    "templates": template_info,
                    "instances": instance_info,
                },
            }
        )

    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/api-status", methods=["GET"])
@admin_required
def get_api_status():
    """获取当前API状态"""
    try:
        print("🔍 检查API状态...")
        from ai_engine.smart_generator import SmartQuestionGenerator

        print("📋 初始化SmartQuestionGenerator...")
        generator = SmartQuestionGenerator()
        print("✅ SmartQuestionGenerator初始化成功")

        status = generator.get_api_status()
        print(f"📊 API状态: {status}")

        return jsonify({"success": True, "status": status})
    except Exception as e:
        print(f"❌ 获取API状态失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/system-config", methods=["POST"])
@admin_required
def update_system_config():
    """更新系统配置"""
    try:
        data = request.get_json()
        configs = data.get("configs", [])

        for config_data in configs:
            config_key = config_data.get("config_key")
            config_value = config_data.get("config_value")
            config_type = config_data.get("config_type", "text")
            description = config_data.get("description", "")

            # 查找或创建配置
            config = SystemConfig.query.filter_by(config_key=config_key).first()
            if config:
                config.config_value = config_value
                config.config_type = config_type
                config.description = description
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(
                    config_key=config_key,
                    config_value=config_value,
                    config_type=config_type,
                    description=description,
                )
                db.session.add(config)

        db.session.commit()

        return jsonify({"success": True, "message": "系统配置更新成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/static/uploads/<path:filename>")
def uploaded_files(filename):
    """静态文件服务"""
    import os

    # 使用绝对路径确保文件能被找到
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(current_dir, "static", "uploads")
    print(f"尝试从目录提供文件: {upload_dir}")
    print(f"请求的文件: {filename}")
    return send_from_directory(upload_dir, filename)


@app.route("/api/admin/upload-file", methods=["POST"])
@admin_required
def upload_file():
    """文件上传接口"""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "没有文件"})

        file = request.files["file"]
        file_type = request.form.get("type", "image")  # image, icon

        if file.filename == "":
            return jsonify({"success": False, "message": "没有选择文件"})

        # 检查文件类型
        allowed_extensions = {
            "image": {"png", "jpg", "jpeg", "gif", "svg"},
            "icon": {"ico", "png", "svg"},
        }

        if file_type not in allowed_extensions:
            return jsonify({"success": False, "message": "不支持的文件类型"})

        file_ext = file.filename.rsplit(".", 1)[1].lower()
        if file_ext not in allowed_extensions[file_type]:
            return jsonify({"success": False, "message": f"不支持的{file_type}格式"})

        # 保存文件
        import uuid

        filename = f"{file_type}_{uuid.uuid4().hex}.{file_ext}"
        upload_dir = "static/uploads"

        import os

        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # 返回访问URL
        file_url = f"/static/uploads/{filename}"

        return jsonify(
            {"success": True, "file_url": file_url, "message": "文件上传成功"}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def ensure_default_system_config():
    """确保存在默认系统配置"""
    default_configs = [
        {
            "config_key": "systemName",
            "config_value": "Smart Exam System",
            "config_type": "text",
            "description": "系统名称",
        },
        {
            "config_key": "language",
            "config_value": "en",
            "config_type": "text",
            "description": "默认语言",
        },
        {
            "config_key": "logo",
            "config_value": "",
            "config_type": "file",
            "description": "系统logo图片URL",
        },
        {
            "config_key": "favicon",
            "config_value": "/favicon.ico",
            "config_type": "file",
            "description": "网站图标URL",
        },
        {
            "config_key": "footerText",
            "config_value": "© 2025 Smart Exam System. All rights reserved.",
            "config_type": "text",
            "description": "页脚版权文本",
        },
        {
            "config_key": "enforceLanguage",
            "config_value": "false",
            "config_type": "boolean",
            "description": "强制统一语言",
        },
        # 保留旧的API配置以便兼容
        {
            "config_key": "openrouterApiKey",
            "config_value": "",  # 清空默认值，让用户自己配置
            "config_type": "text",
            "description": "OpenRouter API密钥（已废弃，请使用新的API管理功能）",
        },
        {
            "config_key": "aiModel",
            "config_value": "openai/gpt-4-turbo-preview",
            "config_type": "text",
            "description": "AI模型名称（已废弃，请使用新的API管理功能）",
        },
        {
            "config_key": "aiApiEnabled",
            "config_value": "true",
            "config_type": "boolean",
            "description": "启用AI API（出题功能）",
        },
        {
            "config_key": "aiScoringEnabled",
            "config_value": "true",
            "config_type": "boolean",
            "description": "启用AI智能评分",
        },
    ]

    try:
        for config_data in default_configs:
            existing = SystemConfig.query.filter_by(
                config_key=config_data["config_key"]
            ).first()
            if not existing:
                config = SystemConfig(**config_data)
                db.session.add(config)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"创建默认系统配置失败: {e}")


def check_expired_exam_instances():
    """检查并自动结束过期的考试实例"""
    try:
        with app.app_context():
            # 查找所有活跃的考试实例
            active_instances = ExamInstance.query.filter_by(status="active").all()

            current_time = datetime.utcnow()
            expired_count = 0

            for instance in active_instances:
                if instance.started_at and instance.template:
                    # 计算过期时间
                    time_limit_minutes = instance.template.time_limit or 75
                    expiry_time = instance.started_at + timedelta(
                        minutes=time_limit_minutes
                    )

                    # 检查是否过期
                    if current_time >= expiry_time:
                        print(
                            f"⏰ 考试实例 {instance.id} ({instance.name}) 已过期，自动结束"
                        )

                        # 更新状态为过期
                        instance.status = "expired"
                        instance.completed_at = current_time

                        # 如果还没有分数，计算当前已回答的题目分数
                        if instance.score is None:
                            try:
                                # 获取已回答的答案
                                answers = Answer.query.filter_by(
                                    exam_instance_id=instance.id
                                ).all()
                                answer_dict = {
                                    str(answer.question_id): answer.answer_text
                                    for answer in answers
                                }

                                # 获取考试题目
                                if instance.questions:
                                    questions_data = json.loads(instance.questions)
                                    questions = []
                                    for q_data in questions_data:
                                        question = Question.query.get(q_data["id"])
                                        if question:
                                            question_dict = question.to_dict()
                                            question_dict["order"] = q_data.get(
                                                "order", 0
                                            )
                                            question_dict["points"] = q_data.get(
                                                "points", 1.0
                                            )
                                            questions.append(question_dict)

                                    # 计算分数
                                    scorer = get_scoring_system()
                                    results = scorer.calculate_scores_for_instance(
                                        instance.id, questions, answer_dict
                                    )

                                    # 更新分数
                                    instance.score = results["total_score"]
                                    instance.total_score = results["total_possible"]
                                    instance.percentage = results["percentage"]

                                    print(
                                        f"✅ 自动计算过期考试分数: {instance.score}/{instance.total_score} ({instance.percentage}%)"
                                    )
                            except Exception as score_error:
                                print(f"❌ 计算过期考试分数失败: {str(score_error)}")

                        expired_count += 1

            if expired_count > 0:
                db.session.commit()
                print(f"🎯 已自动结束 {expired_count} 个过期考试实例")

    except Exception as e:
        print(f"❌ 检查过期考试实例失败: {str(e)}")


def start_exam_monitor():
    """启动考试监控定时任务"""

    def monitor_loop():
        while True:
            try:
                check_expired_exam_instances()
                # 每分钟检查一次
                time.sleep(60)
            except Exception as e:
                print(f"❌ 考试监控循环异常: {str(e)}")
                time.sleep(60)  # 出错后等待60秒再重试

    # 在后台线程中运行监控
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print("🔄 考试时间监控已启动（每分钟检查一次过期考试）")


# 补充缺失的学生记录API
@app.route("/api/student-answers-for-records", methods=["GET"])
@admin_required
def get_student_answers_for_records():
    """获取所有学生答题记录（用于Student Records页面），包括新旧系统的记录"""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 30))

        print(f"📊 加载答题记录，页码: {page}, 每页: {per_page}")

        # 合并新旧系统的答题记录
        all_answers_data = []

        # 1. 获取新系统的记录（ExamInstance -> Answer）
        new_answers = Answer.query.filter(Answer.exam_instance_id.isnot(None)).all()

        for answer in new_answers:
            try:
                # 获取考试实例信息
                exam_instance = (
                    ExamInstance.query.get(answer.exam_instance_id)
                    if answer.exam_instance_id
                    else None
                )

                # 获取学生信息
                student = None
                if exam_instance and exam_instance.student_id:
                    student = Student.query.get(exam_instance.student_id)
                elif exam_instance and exam_instance.session_id:
                    session = ExamSession.query.get(exam_instance.session_id)
                    student = session.student if session else None

                # 获取题目信息
                question = None
                question_text = f"题目 #{answer.question_id}"
                correct_answer = "-"

                if answer.question_id and str(answer.question_id).isdigit():
                    try:
                        question = Question.query.get(int(answer.question_id))
                        if question:
                            question_text = (
                                question.content
                                or question.question_text
                                or question_text
                            )
                            correct_answer = question.correct_answer or "-"
                    except:
                        pass

                # 获取考试名称
                exam_name = "Unknown Exam"
                if exam_instance:
                    exam_name = exam_instance.name or f"考试实例 #{exam_instance.id}"
                    # 尝试通过模板获取更好的名称
                    if exam_instance.template_id:
                        template = ExamTemplate.query.get(exam_instance.template_id)
                        if template:
                            exam_name = template.name

                all_answers_data.append(
                    {
                        "id": f"new_{answer.id}",
                        "student_name": student.name if student else "未知学生",
                        "student_id": student.id_number if student else "-",
                        "exam_name": exam_name,
                        "question_id": answer.question_id,
                        "question_text": question_text,
                        "question_type": (
                            question.question_type if question else "unknown"
                        ),
                        "student_answer": answer.answer_text or "未作答",
                        "correct_answer": correct_answer,
                        "is_correct": (
                            answer.is_correct
                            if answer.is_correct is not None
                            else False
                        ),
                        "score": answer.score or 0,
                        "submitted_at": (
                            answer.submitted_at.isoformat()
                            if answer.submitted_at
                            else (
                                answer.created_at.isoformat()
                                if hasattr(answer, "created_at") and answer.created_at
                                else None
                            )
                        ),
                        "exam_instance_id": answer.exam_instance_id,
                        "system_type": "new",
                    }
                )

            except Exception as e:
                print(f"⚠️ 处理新系统答题记录 {answer.id} 时出错: {str(e)}")
                continue

        # 2. 获取旧系统的记录（ExamSession -> Exam -> Answer）
        old_answers = Answer.query.filter(
            Answer.exam_id.isnot(None), Answer.exam_instance_id.is_(None)
        ).all()

        for answer in old_answers:
            try:
                # 获取考试信息
                exam = Exam.query.get(answer.exam_id) if answer.exam_id else None

                # 获取学生信息
                student = None
                if exam and exam.session_id:
                    session = ExamSession.query.get(exam.session_id)
                    student = session.student if session else None

                # 获取题目信息
                question = None
                question_text = f"题目 #{answer.question_id}"
                correct_answer = "-"

                if answer.question_id and str(answer.question_id).isdigit():
                    try:
                        question = Question.query.get(int(answer.question_id))
                        if question:
                            question_text = (
                                question.content
                                or question.question_text
                                or question_text
                            )
                            correct_answer = question.correct_answer or "-"
                    except:
                        pass

                # 获取考试名称 - 使用当前默认配置的名称
                exam_name = "Unknown Exam"
                if exam:
                    # 尝试获取当前默认配置的名称
                    default_config = ExamConfig.query.filter_by(
                        is_default=True, is_active=True
                    ).first()
                    if default_config:
                        exam_name = default_config.name
                    else:
                        exam_name = f"考试 #{exam.id}"

                all_answers_data.append(
                    {
                        "id": f"old_{answer.id}",
                        "student_name": student.name if student else "未知学生",
                        "student_id": student.id_number if student else "-",
                        "exam_name": exam_name,
                        "question_id": answer.question_id,
                        "question_text": question_text,
                        "question_type": (
                            question.question_type if question else "unknown"
                        ),
                        "student_answer": answer.answer_text or "未作答",
                        "correct_answer": correct_answer,
                        "is_correct": (
                            answer.is_correct
                            if answer.is_correct is not None
                            else False
                        ),
                        "score": answer.score or 0,
                        "submitted_at": (
                            answer.submitted_at.isoformat()
                            if answer.submitted_at
                            else (
                                answer.created_at.isoformat()
                                if hasattr(answer, "created_at") and answer.created_at
                                else None
                            )
                        ),
                        "exam_instance_id": answer.exam_id,
                        "system_type": "old",
                    }
                )

            except Exception as e:
                print(f"⚠️ 处理旧系统答题记录 {answer.id} 时出错: {str(e)}")
                continue

        # 按提交时间排序
        all_answers_data.sort(
            key=lambda x: x["submitted_at"] or "1970-01-01T00:00:00", reverse=True
        )

        # 手动分页
        total_records = len(all_answers_data)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_data = all_answers_data[start_idx:end_idx]

        total_pages = (total_records + per_page - 1) // per_page

        print(
            f"📊 找到总共 {total_records} 条答题记录（新系统: {len(new_answers)}, 旧系统: {len(old_answers)}）"
        )
        print(f"✅ 成功处理 {len(paginated_data)} 条答题记录")

        return jsonify(
            {
                "success": True,
                "answers": paginated_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_records,
                    "pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取所有学生答题记录失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@app.route("/api/student-records-data", methods=["GET"])
@admin_required
def get_student_records_data():
    """获取学生记录数据（用于Student Records页面），包括新旧系统的考试记录"""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 100))

        # 获取学生数据
        students_query = Student.query
        paginated_students = students_query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        students_data = []
        for student in paginated_students.items:
            # 计算新系统的考试统计
            exam_instances = ExamInstance.query.filter_by(student_id=student.id).all()
            new_exams_count = len(exam_instances)
            new_total_score = sum(
                instance.percentage or 0 for instance in exam_instances
            )
            new_last_exam = (
                max(exam_instances, key=lambda x: x.started_at or datetime.min)
                if exam_instances
                else None
            )

            # 计算旧系统的考试统计
            old_exam_sessions = ExamSession.query.filter_by(student_id=student.id).all()
            old_exams_count = 0
            old_total_score = 0
            old_last_exam = None

            for session in old_exam_sessions:
                exams = Exam.query.filter_by(session_id=session.id).all()
                for exam in exams:
                    old_exams_count += 1
                    # 优先使用已保存的分数数据
                    exam_percentage = 0
                    if exam.scores:
                        try:
                            import json

                            scores_data = json.loads(exam.scores)
                            exam_percentage = scores_data.get("percentage_score", 0)
                        except (json.JSONDecodeError, AttributeError):
                            # 如果分数数据解析失败，fallback到答案统计
                            answers = Answer.query.filter_by(exam_id=exam.id).all()
                            if answers:
                                total_questions = len(answers)
                                correct_count = len(
                                    [a for a in answers if a.is_correct]
                                )
                                exam_percentage = (
                                    (correct_count / total_questions * 100)
                                    if total_questions > 0
                                    else 0
                                )
                    else:
                        # 如果没有分数数据，使用答案统计
                        answers = Answer.query.filter_by(exam_id=exam.id).all()
                        if answers:
                            total_questions = len(answers)
                            correct_count = len([a for a in answers if a.is_correct])
                            exam_percentage = (
                                (correct_count / total_questions * 100)
                                if total_questions > 0
                                else 0
                            )

                    old_total_score += exam_percentage

                    # 更新最后考试时间
                    if exam.started_at and (
                        not old_last_exam or exam.started_at > old_last_exam
                    ):
                        old_last_exam = exam.started_at

            # 合并统计
            total_exams = new_exams_count + old_exams_count
            if total_exams > 0:
                avg_score = (new_total_score + old_total_score) / total_exams

                # 确定最后考试时间
                last_exam_at = None
                if new_last_exam and old_last_exam:
                    last_exam_at = max(new_last_exam.started_at, old_last_exam)
                elif new_last_exam:
                    last_exam_at = new_last_exam.started_at
                elif old_last_exam:
                    last_exam_at = old_last_exam
            else:
                avg_score = 0
                last_exam_at = None

            students_data.append(
                {
                    "id": student.id,
                    "student_name": student.name,
                    "student_id": student.id_number,
                    "student_application_number": student.application_number,
                    "total_exams": total_exams,
                    "avg_score": round(avg_score, 1),
                    "last_exam_at": last_exam_at.isoformat() if last_exam_at else None,
                    "status": "活跃" if total_exams > 0 else "未参加",
                    "new_exams": new_exams_count,
                    "old_exams": old_exams_count,
                }
            )

        return jsonify(
            {
                "success": True,
                "records": students_data,  # 改为records保持前端一致性
                "students": students_data,  # 同时保留students以保持兼容性
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": paginated_students.total,
                    "pages": paginated_students.pages,
                    "has_next": paginated_students.has_next,
                    "has_prev": paginated_students.has_prev,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取学生记录失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@app.route("/api/student-records-statistics", methods=["GET"])
@admin_required
def get_student_records_statistics_data():
    """获取学生记录统计信息，包括新旧系统的数据"""
    try:
        # 基础统计数据
        total_students = Student.query.count()
        total_questions = Question.query.count()
        total_answers = Answer.query.count()

        # 新系统考试数量
        total_new_exams = ExamInstance.query.count()

        # 旧系统考试数量
        total_old_exams = Exam.query.count()

        # 总考试数量
        total_exams = total_new_exams + total_old_exams

        # 计算平均分（新旧系统合并）
        # 新系统的分数
        new_exam_instances = ExamInstance.query.filter(
            ExamInstance.percentage.isnot(None)
        ).all()
        new_total_score = sum(instance.percentage for instance in new_exam_instances)
        new_exam_count = len(new_exam_instances)

        # 旧系统的分数
        old_exams = Exam.query.all()
        old_total_score = 0
        old_exam_count = 0

        for exam in old_exams:
            answers = Answer.query.filter_by(exam_id=exam.id).all()
            if answers:
                total_exam_questions = len(answers)
                correct_count = len([a for a in answers if a.is_correct])
                exam_percentage = (
                    (correct_count / total_exam_questions * 100)
                    if total_exam_questions > 0
                    else 0
                )
                old_total_score += exam_percentage
                old_exam_count += 1

        # 计算整体平均分
        total_exam_count = new_exam_count + old_exam_count
        if total_exam_count > 0:
            avg_score = (new_total_score + old_total_score) / total_exam_count
        else:
            avg_score = 0

        # 活跃学生数（有考试记录的学生）
        # 新系统活跃学生
        new_active_students = (
            db.session.query(Student.id).join(ExamInstance).distinct().count()
        )

        # 旧系统活跃学生
        old_active_students = (
            db.session.query(Student.id).join(ExamSession).distinct().count()
        )

        # 合并活跃学生（去重）
        new_student_ids = set(
            db.session.query(Student.id).join(ExamInstance).distinct().all()
        )
        old_student_ids = set(
            db.session.query(Student.id).join(ExamSession).distinct().all()
        )
        active_students = len(new_student_ids.union(old_student_ids))

        return jsonify(
            {
                "success": True,
                "statistics": {
                    "total_students": total_students,
                    "total_exams": total_exams,
                    "total_questions": total_questions,
                    "total_answers": total_answers,
                    "avg_score": round(avg_score, 1),
                    "active_students": active_students,
                    "new_exams": total_new_exams,
                    "old_exams": total_old_exams,
                    "new_active_students": new_active_students,
                    "old_active_students": old_active_students,
                },
            }
        )

    except Exception as e:
        print(f"❌ 获取学生记录统计失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


def ensure_default_api_providers():
    """确保存在默认API提供商配置"""
    import json

    default_providers = [
        {
            "provider_name": "openrouter",
            "display_name": "OpenRouter",
            "api_url": "https://openrouter.ai/api/v1/chat/completions",
            "is_active": False,
            "is_verified": False,
            "default_model": "openai/gpt-4-turbo-preview",
            "supported_models": json.dumps(
                [
                    {"id": "openai/gpt-4-turbo-preview", "name": "GPT-4 Turbo"},
                    {"id": "openai/gpt-4", "name": "GPT-4"},
                    {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                    {"id": "anthropic/claude-3-sonnet", "name": "Claude-3 Sonnet"},
                    {"id": "google/gemini-pro", "name": "Gemini Pro"},
                ]
            ),
            "headers_template": json.dumps(
                {
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://cbit-exam-system.com",
                    "X-Title": "CBIT Exam Question Generator",
                }
            ),
            "request_template": json.dumps(
                {
                    "model": "{model}",
                    "messages": "{messages}",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                }
            ),
        },
        {
            "provider_name": "openai",
            "display_name": "OpenAI",
            "api_url": "https://api.openai.com/v1/chat/completions",
            "is_active": False,
            "is_verified": False,
            "default_model": "gpt-4-turbo-preview",
            "supported_models": json.dumps(
                [
                    {"id": "gpt-4-turbo-preview", "name": "GPT-4 Turbo"},
                    {"id": "gpt-4", "name": "GPT-4"},
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                ]
            ),
            "headers_template": json.dumps(
                {
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json",
                }
            ),
            "request_template": json.dumps(
                {
                    "model": "{model}",
                    "messages": "{messages}",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                }
            ),
        },
        {
            "provider_name": "anthropic",
            "display_name": "Anthropic",
            "api_url": "https://api.anthropic.com/v1/messages",
            "is_active": False,
            "is_verified": False,
            "default_model": "claude-3-sonnet-20240229",
            "supported_models": json.dumps(
                [
                    {"id": "claude-3-sonnet-20240229", "name": "Claude-3 Sonnet"},
                    {"id": "claude-3-haiku-20240307", "name": "Claude-3 Haiku"},
                ]
            ),
            "headers_template": json.dumps(
                {
                    "x-api-key": "{api_key}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                }
            ),
            "request_template": json.dumps(
                {"model": "{model}", "max_tokens": 2000, "messages": "{messages}"}
            ),
        },
    ]

    try:
        for provider_data in default_providers:
            existing = ApiProvider.query.filter_by(
                provider_name=provider_data["provider_name"]
            ).first()
            if not existing:
                new_provider = ApiProvider(**provider_data)
                db.session.add(new_provider)
                print(f"🔧 创建默认API提供商: {provider_data['display_name']}")

        db.session.commit()
        print(f"✅ 默认API提供商配置初始化完成")
    except Exception as e:
        db.session.rollback()
        print(f"❌ 初始化默认API提供商配置失败: {str(e)}")


if __name__ == "__main__":
    # 创建数据库表
    with app.app_context():
        db.create_all()

    # 确保存在默认配置
    ensure_default_config()
    ensure_default_system_config()
    ensure_default_api_providers()

    # 启动考试监控
    start_exam_monitor()

    # 运行应用
    app.run(debug=True, host="0.0.0.0", port=8080)
