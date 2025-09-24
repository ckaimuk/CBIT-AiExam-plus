#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动评分系统
支持选择题、简答题和编程题的自动评分
"""

import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Tuple

import requests


class ScoringSystem:
    """评分系统"""

    def __init__(self):
        # 从数据库获取AI API配置
        self.api_key = None
        self.api_url = None
        self.model = None
        self.ai_scoring_enabled = False
        self._load_config_from_db()

        # 关键词权重配置
        self.keyword_weights = {
            "high": 3,  # 高权重关键词
            "medium": 2,  # 中权重关键词
            "low": 1,  # 低权重关键词
        }

    def _load_config_from_db(self):
        """从数据库加载AI配置"""
        try:
            # 导入这里而不是在文件顶部，避免循环导入
            from flask import current_app, has_app_context
            from models import ApiProvider, SystemConfig

            # 检查是否在应用上下文中
            if not has_app_context():
                print("不在Flask应用上下文中，AI评分将使用关键词匹配")
                return

            # 检查AI评分是否启用
            ai_scoring_config = SystemConfig.query.filter_by(
                config_key="aiScoringEnabled"
            ).first()
            if ai_scoring_config:
                self.ai_scoring_enabled = (
                    ai_scoring_config.config_value.lower() == "true"
                )
            else:
                # 如果没有配置，默认启用（向后兼容）
                self.ai_scoring_enabled = True
                print("未找到AI评分配置，默认启用")

            if not self.ai_scoring_enabled:
                print("AI评分已禁用，将使用关键词匹配备用方案")
                return

            # 获取当前激活且验证通过的API提供商
            active_provider = ApiProvider.query.filter_by(
                is_active=True, is_verified=True
            ).first()

            if active_provider:
                self.api_key = active_provider.api_key
                self.api_url = active_provider.api_url
                self.model = active_provider.default_model
                print(
                    f"🤖 AI评分配置加载成功: {active_provider.display_name} - {self.model}"
                )

                # 验证API是否真正可用
                if not self._verify_api_connection():
                    print("⚠️  API连接验证失败，AI评分将使用基本评分结构")
                    self.ai_scoring_enabled = False
                    self.api_key = None
                    self.api_url = None
                    self.model = None
            else:
                print("⚠️  未找到激活且验证的API提供商，AI评分将使用基本评分结构")
                self.ai_scoring_enabled = False

        except Exception as e:
            print(f"❌ 从数据库加载AI配置失败: {str(e)}")
            # 发生错误时默认禁用AI评分，使用关键词匹配
            self.ai_scoring_enabled = False

    def _verify_api_connection(self):
        """验证API连接是否可用"""
        try:
            if not self.api_key or not self.api_url:
                return False

            # 发送一个简单的测试请求
            test_prompt = "测试连接"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 10,
                "temperature": 0.1,
            }

            response = requests.post(
                self.api_url, headers=headers, json=data, timeout=5  # 5秒超时
            )

            if response.status_code == 200:
                print("✅ API连接验证成功")
                return True
            else:
                print(f"❌ API连接验证失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ API连接验证异常: {str(e)}")
            return False

    def calculate_scores_for_instance(
        self, instance_id: int, questions: List[Dict], answers: Dict[str, str]
    ) -> Dict[str, Any]:
        """计算考试实例总分和详细分数"""
        print(f"开始计算考试实例 {instance_id} 的分数，共 {len(questions)} 道题目")
        return self._calculate_scores_internal(
            questions, answers, instance_id, is_instance=True
        )

    def calculate_scores(
        self, exam_id: int, questions: List[Dict], answers: Dict[str, str]
    ) -> Dict[str, Any]:
        """计算考试总分和详细分数"""
        print(f"开始计算考试 {exam_id} 的分数，共 {len(questions)} 道题目")
        return self._calculate_scores_internal(
            questions, answers, exam_id, is_instance=False
        )

    def _calculate_scores_internal(
        self,
        questions: List[Dict],
        answers: Dict[str, str],
        exam_or_instance_id: int,
        is_instance: bool = False,
    ) -> Dict[str, Any]:
        """内部评分方法"""
        total_score = 0
        max_score = 0
        subject_scores = {}
        difficulty_scores = {}
        cognitive_scores = {}
        question_scores = []

        entity_type = "考试实例" if is_instance else "考试"
        print(
            f"开始计算{entity_type} {exam_or_instance_id} 的分数，共 {len(questions)} 道题目"
        )

        for i, question in enumerate(questions):
            # 获取题目ID，尝试多种可能的字段名
            question_id = str(
                question.get("id", question.get("question_id", str(i + 1)))
            )
            student_answer = answers.get(
                question_id, answers.get(str(question.get("id", "")), "")
            )

            print(f"题目 {i+1} (ID: {question_id}): 学生答案长度 {len(student_answer)}")

            # 计算单题分数
            question_score, max_question_score = self._score_single_question(
                question, student_answer
            )

            print(f"题目 {i+1} 得分: {question_score}/{max_question_score}")

            total_score += question_score
            max_score += max_question_score

            # 记录题目分数
            question_scores.append(
                {
                    "question_id": question_id,
                    "score": question_score,
                    "max_score": max_question_score,
                    "percentage": (
                        (question_score / max_question_score * 100)
                        if max_question_score > 0
                        else 0
                    ),
                    "student_answer": (
                        student_answer[:100] + "..."
                        if len(student_answer) > 100
                        else student_answer
                    ),
                    "question_type": question.get(
                        "type_key", question.get("question_type", "unknown")
                    ),
                }
            )

            # 按学科统计
            subject = question.get("subject", question.get("subject_key", "unknown"))
            if subject not in subject_scores:
                subject_scores[subject] = {"score": 0, "max_score": 0}
            subject_scores[subject]["score"] += question_score
            subject_scores[subject]["max_score"] += max_question_score

            # 按难度统计
            difficulty = question.get(
                "difficulty", question.get("difficulty_key", "unknown")
            )
            if difficulty not in difficulty_scores:
                difficulty_scores[difficulty] = {"score": 0, "max_score": 0}
            difficulty_scores[difficulty]["score"] += question_score
            difficulty_scores[difficulty]["max_score"] += max_question_score

            # 按认知层级统计
            cognitive = question.get(
                "cognitive_level", question.get("cognitive_key", "unknown")
            )
            if cognitive not in cognitive_scores:
                cognitive_scores[cognitive] = {"score": 0, "max_score": 0}
            cognitive_scores[cognitive]["score"] += question_score
            cognitive_scores[cognitive]["max_score"] += max_question_score

        # 计算百分比分数
        percentage_score = (total_score / max_score * 100) if max_score > 0 else 0

        # 计算等级
        grade = self._calculate_grade(percentage_score)

        # 计算学科百分比
        subject_percentages = {}
        for subject, scores in subject_scores.items():
            if scores["max_score"] > 0:
                subject_percentages[subject] = (
                    scores["score"] / scores["max_score"] * 100
                )
            else:
                subject_percentages[subject] = 0

        print(f"最终计算结果: 总分 {total_score}/{max_score} ({percentage_score:.2f}%)")

        # 更新数据库中的Answer记录
        self._update_answer_scores(exam_or_instance_id, question_scores, is_instance)

        return {
            "total_score": round(total_score, 2),
            "max_score": round(max_score, 2),
            "percentage_score": round(percentage_score, 2),
            "grade": grade,
            "subject_scores": subject_percentages,
            "difficulty_scores": difficulty_scores,
            "cognitive_scores": cognitive_scores,
            "question_scores": question_scores,
            "summary": self._generate_summary(percentage_score, subject_percentages),
            "debug_info": {
                "questions_count": len(questions),
                "answers_count": len(answers),
                "calculated_questions": len(question_scores),
            },
        }

    def _score_single_question(
        self, question: Dict, student_answer: str
    ) -> Tuple[float, float]:
        """计算单个题目的分数"""
        question_type = question.get("type_key", question.get("question_type", ""))
        max_score = float(question.get("points", 1))

        if not student_answer or not student_answer.strip():
            return 0.0, max_score

        # 标准化题目类型
        if question_type in ["multiple_choice", "选择题"]:
            return self._score_multiple_choice(question, student_answer, max_score)
        elif question_type in ["short_answer", "简答题"]:
            return self._score_short_answer(question, student_answer, max_score)
        elif question_type in ["programming", "编程题"]:
            return self._score_programming(question, student_answer, max_score)
        else:
            # 默认按简答题处理
            return self._score_short_answer(question, student_answer, max_score)

    def _score_multiple_choice(
        self, question: Dict, student_answer: str, max_score: float
    ) -> Tuple[float, float]:
        """评分选择题"""
        correct_answer = question.get("correct_answer", "")

        # 标准化答案格式
        student_clean = student_answer.strip().lower()
        correct_clean = correct_answer.strip().lower()

        # 直接比较
        if student_clean == correct_clean:
            return max_score, max_score

        # 尝试比较选项内容（如果学生答案是选项内容而不是选项字母）
        options = question.get("options", [])
        if options:
            # 查找学生答案对应的选项
            student_option_found = False
            correct_option_found = False

            for i, option in enumerate(options):
                option_clean = option.strip().lower()
                option_letter = chr(65 + i).lower()  # A, B, C, D

                # 检查学生答案是否匹配此选项
                if student_clean == option_clean or student_clean == option_letter:
                    student_option_found = True
                    # 检查这个选项是否是正确答案
                    if correct_clean == option_clean or correct_clean == option_letter:
                        return max_score, max_score

                # 检查正确答案是否匹配此选项
                if correct_clean == option_clean or correct_clean == option_letter:
                    correct_option_found = True

        return 0.0, max_score

    def _score_short_answer(
        self, question: Dict, student_answer: str, max_score: float
    ) -> Tuple[float, float]:
        """评分简答题"""
        correct_answer = question.get("correct_answer", "")

        if not correct_answer.strip():
            # 如果没有标准答案，给予部分分数
            return max_score * 0.5, max_score

        # 检查是否启用AI评分
        if self.ai_scoring_enabled and self.api_key:
            # 使用AI进行语义相似度评分
            ai_similarity = self._calculate_semantic_similarity(
                student_answer, correct_answer
            )
            print(f"🤖 AI语义相似度评分: {ai_similarity:.2f}")

            # 使用关键词匹配作为辅助评分
            keyword_score = self._simple_keyword_similarity(
                student_answer, correct_answer
            )
            print(f"📝 关键词匹配评分: {keyword_score:.2f}")

            # AI评分占80%，关键词匹配占20%
            final_similarity = ai_similarity * 0.8 + keyword_score * 0.2
            print(
                f"✅ 简答题最终评分: AI{ai_similarity:.2f}*0.8 + 关键词{keyword_score:.2f}*0.2 = {final_similarity:.2f}"
            )
        else:
            # AI评分禁用或API不可用，使用基本评分结构
            print("📝 使用基本评分结构（非AI模式）")

            # 基本评分结构：关键词匹配 + 长度评分 + 基本逻辑
            keyword_score = self._simple_keyword_similarity(
                student_answer, correct_answer
            )
            length_score = self._evaluate_answer_length(student_answer, correct_answer)
            basic_logic_score = self._evaluate_basic_logic(student_answer)

            # 基本评分权重：关键词70%，长度20%，逻辑10%
            final_similarity = (
                keyword_score * 0.7 + length_score * 0.2 + basic_logic_score * 0.1
            )
            print(
                f"✅ 基本评分结构: 关键词{keyword_score:.2f}*0.7 + 长度{length_score:.2f}*0.2 + 逻辑{basic_logic_score:.2f}*0.1 = {final_similarity:.2f}"
            )

            # 确保有答案就有基本分数
            if final_similarity < 0.1 and student_answer.strip():
                final_similarity = 0.1  # 有内容就至少给10%相似度
                print(f"🛡️ 基本评分保护：给予最低10%相似度")

        # 基于相似度计算分数，使用更细致的分级
        if final_similarity >= 0.9:
            return max_score, max_score
        elif final_similarity >= 0.8:
            return max_score * 0.9, max_score
        elif final_similarity >= 0.7:
            return max_score * 0.8, max_score
        elif final_similarity >= 0.6:
            return max_score * 0.7, max_score
        elif final_similarity >= 0.5:
            return max_score * 0.5, max_score
        elif final_similarity >= 0.3:
            return max_score * 0.3, max_score
        else:
            return 0.0, max_score

    def _score_programming(
        self, question: Dict, student_answer: str, max_score: float
    ) -> Tuple[float, float]:
        """评分编程题 - 改进的步骤分评估"""
        try:
            if not student_answer.strip():
                return 0.0, max_score

            print(f"📝 开始评分编程题，最大分数: {max_score}")

            # 基本长度检查 - 给更宽松的判断
            if len(student_answer.strip()) < 10:
                print(f"⚠️ 代码过短({len(student_answer.strip())}字符)，给基础分")
                return max_score * 0.1, max_score

            # 1. 基础结构评分（占比30%）
            structure_score = self._check_programming_structure(student_answer)
            print(f"🏗️ 结构评分: {structure_score:.2f}")

            # 2. 语法和基本逻辑评分（占比25%）
            syntax_score = self._check_syntax_and_logic(student_answer)
            print(f"⚙️ 语法逻辑评分: {syntax_score:.2f}")

            # 3. 执行评分（占比20%） - 不强制要求完美运行
            execution_score = 0.3  # 如果有基本代码结构，默认给30%
            try:
                execution_score = self._execute_programming_code(student_answer)
            except Exception as e:
                print(f"⚠️ 代码执行检查失败，使用默认分数: {str(e)}")

            print(f"🚀 执行评分: {execution_score:.2f}")

            # 4. 使用AI评估代码质量和算法思路（如果启用且可用）
            if self.ai_scoring_enabled and self.api_key:
                ai_score = self._evaluate_code_with_ai(question, student_answer)
                print(f"🤖 AI综合评分: {ai_score:.2f}")

                # 综合评分：AI占80%，结构10%，语法5%，执行5%
                final_score = (
                    ai_score * 0.8
                    + structure_score * 0.1
                    + syntax_score * 0.05
                    + execution_score * 0.05
                ) * max_score
                print(
                    f"✅ AI模式最终评分: AI{ai_score:.2f}*0.8 + 结构{structure_score:.2f}*0.1 + 语法{syntax_score:.2f}*0.05 + 执行{execution_score:.2f}*0.05 = {final_score:.2f}/{max_score}"
                )
            else:
                # AI评分禁用，使用基本评分结构
                print("📝 使用基本评分结构（非AI模式）")

                # 基本评分结构：结构40%，语法35%，执行25%
                final_score = (
                    structure_score * 0.4 + syntax_score * 0.35 + execution_score * 0.25
                ) * max_score
                print(
                    f"✅ 基本评分结构最终评分: 结构{structure_score:.2f}*0.4 + 语法{syntax_score:.2f}*0.35 + 执行{execution_score:.2f}*0.25 = {final_score:.2f}/{max_score}"
                )

                # 确保基本评分给予合理分数
                if final_score < max_score * 0.1 and student_answer.strip():
                    final_score = max_score * 0.1  # 有代码内容就至少给10%
                    print(
                        f"🛡️ 基本评分保护：给予最低10%分数 = {final_score:.2f}/{max_score}"
                    )

            return min(final_score, max_score), max_score

        except Exception as e:
            print(f"❌ 编程题评分失败: {str(e)}")
            # 给予基础分数 - 如果有代码就给30%
            base_score = max_score * 0.3 if student_answer.strip() else 0.0
            return base_score, max_score

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """计算语义相似度"""
        try:
            # 检查AI评分是否启用
            if not self.ai_scoring_enabled or not self.api_key:
                return self._simple_keyword_similarity(text1, text2)

            # 使用AI API计算语义相似度
            prompt = f"""
请比较以下两个文本的语义相似度，返回0-1之间的分数（1表示完全相同，0表示完全不同）：

文本1：{text1}
文本2：{text2}

请只返回一个数字分数，不要其他内容。
"""

            response = self._call_ai_api(prompt)
            if response:
                # 尝试提取数字
                import re

                numbers = re.findall(r"0\.\d+|1\.0|0|1", response)
                if numbers:
                    return float(numbers[0])

            # 如果AI调用失败，使用简单的关键词匹配
            return self._simple_keyword_similarity(text1, text2)

        except Exception as e:
            print(f"语义相似度计算失败: {str(e)}")
            return self._simple_keyword_similarity(text1, text2)

    def _simple_keyword_similarity(self, text1: str, text2: str) -> float:
        """简单的关键词相似度计算"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _evaluate_answer_length(
        self, student_answer: str, correct_answer: str
    ) -> float:
        """评估答案长度的合理性"""
        if not student_answer.strip():
            return 0.0

        student_len = len(student_answer.strip())
        correct_len = (
            len(correct_answer.strip()) if correct_answer else 50
        )  # 默认期望长度

        # 长度比例评分
        if correct_len == 0:
            return 0.5 if student_len > 10 else 0.2

        ratio = student_len / correct_len
        if 0.5 <= ratio <= 2.0:  # 长度在标准答案的50%-200%之间
            return 1.0
        elif 0.3 <= ratio < 0.5 or 2.0 < ratio <= 3.0:  # 稍短或稍长
            return 0.7
        elif 0.1 <= ratio < 0.3 or 3.0 < ratio <= 5.0:  # 太短或太长
            return 0.4
        else:
            return 0.2

    def _evaluate_basic_logic(self, student_answer: str) -> float:
        """评估答案的基本逻辑性"""
        if not student_answer.strip():
            return 0.0

        score = 0.0
        text = student_answer.lower()

        # 检查逻辑连接词
        logic_words = [
            "因为",
            "所以",
            "由于",
            "因此",
            "然而",
            "但是",
            "首先",
            "其次",
            "最后",
            "例如",
            "比如",
            "总之",
            "综上",
            "therefore",
            "because",
            "however",
            "first",
        ]

        logic_count = sum(1 for word in logic_words if word in text)
        score += min(logic_count * 0.2, 0.5)  # 逻辑词最多加0.5分

        # 检查句子完整性（是否有标点符号）
        punctuation = ["。", "！", "？", ".", "!", "?"]
        if any(p in student_answer for p in punctuation):
            score += 0.3

        # 检查是否有基本结构（多个句子）
        sentences = len([s for s in student_answer.split("。") if s.strip()]) + len(
            [s for s in student_answer.split(".") if s.strip()]
        )
        if sentences > 1:
            score += 0.2

        return min(score, 1.0)

    def _update_answer_scores(
        self, exam_or_instance_id: int, question_scores: list, is_instance: bool = False
    ):
        """更新数据库中的Answer记录分数"""
        try:
            # 导入这里而不是在文件顶部，避免循环导入
            from flask import has_app_context
            from models import Answer, db

            # 检查是否在应用上下文中
            if not has_app_context():
                print("⚠️ 不在Flask应用上下文中，无法更新答案分数")
                return

            print(f"🔄 开始更新答案分数到数据库...")

            updated_count = 0
            for q_score in question_scores:
                question_id = q_score["question_id"]
                score = q_score["score"]
                max_score = q_score["max_score"]

                # 根据是新系统还是旧系统查找答案记录
                if is_instance:
                    # 新系统：通过exam_instance_id查找
                    answer = Answer.query.filter_by(
                        exam_instance_id=exam_or_instance_id, question_id=question_id
                    ).first()
                else:
                    # 旧系统：通过exam_id查找
                    answer = Answer.query.filter_by(
                        exam_id=exam_or_instance_id, question_id=question_id
                    ).first()

                if answer:
                    # 更新分数和正确性
                    old_score = answer.score
                    answer.score = round(score, 2)
                    answer.is_correct = score >= max_score * 0.8  # 80%以上算正确

                    if old_score != answer.score:
                        print(f"📝 更新题目{question_id}: {old_score} → {answer.score}")
                        updated_count += 1
                else:
                    print(f"⚠️ 未找到题目{question_id}的答案记录")

            # 提交到数据库
            db.session.commit()
            print(f"✅ 成功更新{updated_count}个答案的分数到数据库")

        except Exception as e:
            print(f"❌ 更新答案分数失败: {str(e)}")
            try:
                from models import db

                db.session.rollback()
            except:
                pass

    def _check_programming_structure(self, code: str) -> float:
        """检查编程代码的基本结构"""
        score = 0.0
        code_lower = code.lower()

        # 检查基本Python结构
        structure_checks = [
            ("def ", 0.2),  # 函数定义
            ("class ", 0.1),  # 类定义
            ("if ", 0.15),  # 条件语句
            ("for ", 0.1),  # 循环
            ("while ", 0.1),  # 循环
            ("import ", 0.05),  # 导入
            ("return ", 0.1),  # 返回语句
            ("print(", 0.05),  # 输出语句
            ("=", 0.1),  # 赋值
            (":", 0.05),  # 冒号（结构标志）
        ]

        for pattern, weight in structure_checks:
            if pattern in code_lower:
                score += weight

        # 检查代码缩进（基本格式检查）
        lines = code.split("\n")
        has_indentation = any(
            line.startswith("    ") or line.startswith("\t") for line in lines
        )
        if has_indentation:
            score += 0.1

        return min(score, 1.0)

    def _check_syntax_and_logic(self, code: str) -> float:
        """检查语法和基本逻辑"""
        score = 0.0

        try:
            # 1. 语法检查
            compile(code, "<string>", "exec")
            score += 0.5  # 语法正确给50%
            print("✅ 语法检查通过")
        except SyntaxError as e:
            print(f"⚠️ 语法错误: {str(e)}")
            score += 0.1  # 语法错误但有代码结构给10%
        except Exception as e:
            print(f"⚠️ 编译错误: {str(e)}")
            score += 0.2  # 其他编译问题给20%

        # 2. 基本逻辑结构检查
        code_lower = code.lower()
        logic_patterns = [
            ("if", 0.1),  # 条件判断
            ("else", 0.05),  # 条件分支
            ("for", 0.1),  # 循环
            ("while", 0.1),  # 循环
            ("def", 0.15),  # 函数定义
            ("return", 0.1),  # 返回值
        ]

        for pattern, weight in logic_patterns:
            if pattern in code_lower:
                score += weight
                print(f"✅ 发现逻辑结构: {pattern}")

        return min(score, 1.0)

    def _evaluate_code_with_ai(self, question: Dict, code: str) -> float:
        """使用AI评估代码质量和算法思路"""
        try:
            if not self.ai_scoring_enabled or not self.api_key:
                return 0.5  # 不使用AI时返回中等分数

            question_content = question.get("content", "编程题目")
            correct_answer = question.get("correct_answer", "")

            prompt = f"""
请评估以下Python代码的质量，重点关注步骤分和部分分数：

题目：{question_content}
参考答案：{correct_answer}
学生代码：{code}

评估标准：
1. 算法思路正确性 (40%) - 即使代码不完整，思路对就给分
2. 代码结构合理性 (30%) - 变量命名、函数结构等
3. 核心逻辑实现 (20%) - 关键代码语句是否正确
4. 代码完整性 (10%) - 是否完整实现

特别注意：
- 如果核心算法思路正确，即使代码不能运行也应该给较高分数
- 如果有部分正确的代码语句，应该给对应的部分分数
- 不要因为代码不完整就给很低分数

请返回0-1之间的分数，代表该代码应该得到的百分比分数。
只返回数字，不要其他内容。
"""

            response = self._call_ai_api(prompt)
            if response:
                # 尝试提取数字
                import re

                numbers = re.findall(r"0\.\d+|1\.0|0|1", response)
                if numbers:
                    ai_score = float(numbers[0])
                    print(f"🤖 AI评分详情: {ai_score}")
                    return ai_score

            # 如果AI调用失败，使用基础评分
            return 0.5

        except Exception as e:
            print(f"❌ AI代码评估失败: {str(e)}")
            return 0.5

    def _execute_programming_code(self, code: str) -> float:
        """执行编程代码并评分（安全检查）"""
        try:
            # 安全检查：禁止危险操作
            dangerous_patterns = [
                "import os",
                "import sys",
                "import subprocess",
                "import shutil",
                "open(",
                "file(",
                "exec(",
                "eval(",
                "__import__",
                "getattr",
                "setattr",
                "delattr",
                "globals(",
                "locals(",
                "input(",
                "raw_input(",
            ]

            code_lower = code.lower()
            for pattern in dangerous_patterns:
                if pattern in code_lower:
                    print(f"检测到潜在危险代码: {pattern}")
                    return 0.3  # 给予低分但不是零分

            # 简单的语法检查
            try:
                compile(code, "<string>", "exec")
                syntax_score = 1.0
            except SyntaxError as e:
                print(f"语法错误: {str(e)}")
                syntax_score = 0.2
            except Exception as e:
                print(f"编译错误: {str(e)}")
                syntax_score = 0.4

            # 如果语法正确，尝试有限执行（在沙盒环境中）
            if syntax_score >= 1.0:
                try:
                    # 创建受限的执行环境
                    restricted_globals = {
                        "__builtins__": {
                            "len": len,
                            "str": str,
                            "int": int,
                            "float": float,
                            "list": list,
                            "dict": dict,
                            "tuple": tuple,
                            "range": range,
                            "enumerate": enumerate,
                            "min": min,
                            "max": max,
                            "sum": sum,
                            "abs": abs,
                            "round": round,
                            "print": print,
                        }
                    }

                    # 限制执行时间和输出
                    exec(code, restricted_globals, {})
                    return 1.0  # 执行成功

                except Exception as e:
                    print(f"运行时错误: {str(e)}")
                    return 0.6  # 语法正确但运行失败

            return syntax_score

        except Exception as e:
            print(f"代码评估失败: {str(e)}")
            return 0.5  # 给予中等分数

    def _evaluate_code_quality(self, question: Dict, code: str) -> float:
        """评估代码质量"""
        try:
            # 检查AI评分是否启用
            if not self.ai_scoring_enabled or not self.api_key:
                return 0.5  # 不使用AI时返回中等分数

            prompt = f"""
请评估以下Python代码的质量，考虑以下方面：
1. 代码正确性
2. 代码风格和可读性
3. 算法效率
4. 错误处理

题目要求：{question.get('content', '')}
学生代码：{code}

请返回0-1之间的分数（1表示优秀，0表示很差）。
只返回数字分数，不要其他内容。
"""

            response = self._call_ai_api(prompt)
            if response:
                import re

                numbers = re.findall(r"0\.\d+|1\.0|0|1", response)
                if numbers:
                    return float(numbers[0])

            return 0.5  # 默认中等分数

        except Exception as e:
            print(f"代码质量评估失败: {str(e)}")
            return 0.5

    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的代码评审专家，请严格按照要求返回结果。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 100,
            }

            response = requests.post(
                self.api_url, headers=headers, json=data, timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"AI API调用失败: {response.status_code}")
                return None

        except Exception as e:
            print(f"AI API调用异常: {str(e)}")
            return None

    def _calculate_grade(self, percentage: float) -> str:
        """计算等级"""
        if percentage >= 90:
            return "A+"
        elif percentage >= 85:
            return "A"
        elif percentage >= 80:
            return "A-"
        elif percentage >= 75:
            return "B+"
        elif percentage >= 70:
            return "B"
        elif percentage >= 65:
            return "B-"
        elif percentage >= 60:
            return "C+"
        elif percentage >= 55:
            return "C"
        elif percentage >= 50:
            return "C-"
        else:
            return "F"

    def _generate_summary(
        self, percentage: float, subject_scores: Dict[str, float]
    ) -> str:
        """生成成绩总结"""
        if percentage >= 80:
            performance = "优秀"
        elif percentage >= 70:
            performance = "良好"
        elif percentage >= 60:
            performance = "及格"
        else:
            performance = "需要改进"

        # 找出最强和最弱的学科
        if subject_scores:
            best_subject = max(subject_scores.items(), key=lambda x: x[1])
            worst_subject = min(subject_scores.items(), key=lambda x: x[1])

            return f"总体表现{performance}。在{best_subject[0]}方面表现最佳({best_subject[1]:.1f}%)，在{worst_subject[0]}方面需要加强({worst_subject[1]:.1f}%)。"
        else:
            return f"总体表现{performance}。"
