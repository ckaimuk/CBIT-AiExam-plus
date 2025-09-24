#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题目验证器
验证AI生成的题目质量和正确性
"""

import json
import math
import re
from typing import Any, Dict, List, Tuple


class QuestionValidator:
    """题目验证器"""

    def __init__(self):
        self.min_content_length = 20
        self.max_content_length = 1000
        self.required_fields = ["content", "correct_answer", "explanation"]

    def validate_question(self, question: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证单个题目"""
        errors = []

        # 检查必填字段
        for field in self.required_fields:
            if field not in question or not question[field]:
                errors.append(f"缺少必填字段: {field}")

        # 验证题目内容
        content_errors = self._validate_content(question.get("content", ""))
        errors.extend(content_errors)

        # 验证选项（选择题）
        if question.get("type_key") == "multiple_choice":
            option_errors = self._validate_options(question.get("options", []))
            errors.extend(option_errors)

        # 验证正确答案
        answer_errors = self._validate_answer(question)
        errors.extend(answer_errors)

        # 验证解析
        explanation_errors = self._validate_explanation(question.get("explanation", ""))
        errors.extend(explanation_errors)

        return len(errors) == 0, errors

    def _validate_content(self, content: str) -> List[str]:
        """验证题目内容"""
        errors = []

        if not content or len(content.strip()) < self.min_content_length:
            errors.append("题目内容过短")

        if len(content) > self.max_content_length:
            errors.append("题目内容过长")

        # 检查是否包含数学公式标记
        if "$$" in content or "\\(" in content:
            errors.append("题目包含未处理的数学公式标记")

        # 检查是否包含特殊字符
        if re.search(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,;:!?()\[\]{}"\'`~@#$%^&*+=|\\/<>]', content):
            errors.append("题目包含不支持的字符")

        return errors

    def _validate_options(self, options: List[str]) -> List[str]:
        """验证选择题选项"""
        errors = []

        if not options:
            errors.append("选择题缺少选项")
            return errors

        if len(options) < 2:
            errors.append("选择题选项数量不足")

        if len(options) > 6:
            errors.append("选择题选项数量过多")

        # 检查选项内容
        for i, option in enumerate(options):
            if not option or len(option.strip()) < 1:
                errors.append(f"选项{i+1}内容为空")
            elif len(option) > 200:
                errors.append(f"选项{i+1}内容过长")

        # 检查选项重复
        unique_options = set(option.strip().lower() for option in options if option)
        if len(unique_options) != len(options):
            errors.append("存在重复选项")

        return errors

    def _validate_answer(self, question: Dict[str, Any]) -> List[str]:
        """验证正确答案"""
        errors = []
        correct_answer = question.get("correct_answer", "")
        question_type = question.get("type_key", "")

        if not correct_answer:
            errors.append("缺少正确答案")
            return errors

        if question_type == "multiple_choice":
            options = question.get("options", [])
            if correct_answer not in options:
                errors.append("正确答案不在选项列表中")

        elif question_type == "short_answer":
            if len(correct_answer.strip()) < 2:
                errors.append("简答题答案过短")

        elif question_type == "programming":
            # 编程题答案应该是代码
            if not self._is_valid_code(correct_answer):
                errors.append("编程题答案格式不正确")

        return errors

    def _validate_explanation(self, explanation: str) -> List[str]:
        """验证解析内容"""
        errors = []

        if not explanation or len(explanation.strip()) < 10:
            errors.append("解析内容过短")

        if len(explanation) > 2000:
            errors.append("解析内容过长")

        return errors

    def _is_valid_code(self, code: str) -> bool:
        """检查是否为有效的代码"""
        if not code or len(code.strip()) < 5:
            return False

        # 检查是否包含基本的编程结构
        code_indicators = [
            "def ",
            "function",
            "class ",
            "import ",
            "return ",
            "if ",
            "for ",
            "while ",
            "print(",
            "console.log",
            "SELECT",
            "FROM",
            "WHERE",
            "INSERT",
            "UPDATE",
        ]

        return any(indicator in code for indicator in code_indicators)

    def validate_exam(self, questions: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """验证整个考试"""
        errors = []

        if not questions:
            errors.append("考试题目为空")
            return False, errors

        if len(questions) < 10:
            errors.append("考试题目数量不足")

        if len(questions) > 50:
            errors.append("考试题目数量过多")

        # 验证每个题目
        for i, question in enumerate(questions):
            is_valid, question_errors = self.validate_question(question)
            if not is_valid:
                errors.append(f"题目{i+1}验证失败: {'; '.join(question_errors)}")

        # 检查学科分布
        subject_distribution = self._check_subject_distribution(questions)
        if subject_distribution:
            errors.append(f"学科分布不均: {subject_distribution}")

        # 检查难度分布
        difficulty_distribution = self._check_difficulty_distribution(questions)
        if difficulty_distribution:
            errors.append(f"难度分布不均: {difficulty_distribution}")

        return len(errors) == 0, errors

    def _check_subject_distribution(self, questions: List[Dict[str, Any]]) -> str:
        """检查学科分布"""
        subject_counts = {}
        for question in questions:
            subject = question.get("subject_key", "unknown")
            subject_counts[subject] = subject_counts.get(subject, 0) + 1

        total = len(questions)
        expected_distribution = {
            "statistics": 0.30,
            "calculus": 0.25,
            "linear_algebra": 0.20,
            "probability": 0.20,
            "programming": 0.05,
        }

        for subject, expected_ratio in expected_distribution.items():
            actual_ratio = subject_counts.get(subject, 0) / total
            if abs(actual_ratio - expected_ratio) > 0.1:  # 允许10%的偏差
                return f"{subject}: 期望{expected_ratio:.1%}, 实际{actual_ratio:.1%}"

        return None

    def _check_difficulty_distribution(self, questions: List[Dict[str, Any]]) -> str:
        """检查难度分布"""
        difficulty_counts = {}
        for question in questions:
            difficulty = question.get("difficulty_key", "unknown")
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

        total = len(questions)
        expected_distribution = {"high_school": 0.4, "gre_level": 0.4, "graduate": 0.2}

        for difficulty, expected_ratio in expected_distribution.items():
            actual_ratio = difficulty_counts.get(difficulty, 0) / total
            if abs(actual_ratio - expected_ratio) > 0.15:  # 允许15%的偏差
                return f"{difficulty}: 期望{expected_ratio:.1%}, 实际{actual_ratio:.1%}"

        return None

    def fix_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """修复题目中的常见问题"""
        fixed_question = question.copy()

        # 修复题目内容
        content = fixed_question.get("content", "")
        if content:
            # 移除多余的空白字符
            content = re.sub(r"\s+", " ", content).strip()
            fixed_question["content"] = content

        # 修复选项
        if fixed_question.get("type_key") == "multiple_choice":
            options = fixed_question.get("options", [])
            if options:
                # 清理选项内容
                cleaned_options = []
                for option in options:
                    if option and option.strip():
                        cleaned_options.append(option.strip())
                fixed_question["options"] = cleaned_options

        # 修复正确答案
        correct_answer = fixed_question.get("correct_answer", "")
        if correct_answer:
            fixed_question["correct_answer"] = correct_answer.strip()

        # 修复解析
        explanation = fixed_question.get("explanation", "")
        if explanation:
            explanation = re.sub(r"\s+", " ", explanation).strip()
            fixed_question["explanation"] = explanation

        return fixed_question
