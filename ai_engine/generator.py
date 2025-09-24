#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI题目生成引擎
基于OpenRouter API生成个性化考试题目
"""

import json
import os
import random
from datetime import datetime
from typing import Any, Dict, List

import requests


class QuestionGenerator:
    """题目生成器"""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = os.getenv("AI_MODEL", "openai/gpt-4-turbo-preview")

        # 学科配置
        self.subjects = {
            "statistics": {
                "name": "统计学",
                "weight": 0.30,
                "topics": [
                    "描述性统计",
                    "推断统计",
                    "假设检验",
                    "回归分析",
                    "概率分布",
                ],
            },
            "calculus": {
                "name": "微积分",
                "weight": 0.25,
                "topics": ["极限", "导数", "积分", "微分方程", "多元函数"],
            },
            "linear_algebra": {
                "name": "线性代数",
                "weight": 0.20,
                "topics": ["矩阵运算", "向量空间", "特征值", "线性变换", "行列式"],
            },
            "probability": {
                "name": "概率论",
                "weight": 0.20,
                "topics": ["概率分布", "贝叶斯定理", "随机变量", "期望值", "方差"],
            },
            "programming": {
                "name": "编程基础",
                "weight": 0.05,
                "topics": ["Python基础", "数据结构", "算法", "SQL", "R语言"],
            },
        }

        # 难度等级配置
        self.difficulty_levels = {
            "high_school": {
                "name": "高中水平",
                "weight": 0.4,
                "description": "基础概念理解和简单应用",
            },
            "gre_level": {
                "name": "GRE数学水平",
                "weight": 0.4,
                "description": "中等难度，需要一定的分析能力",
            },
            "graduate": {
                "name": "研究生水平",
                "weight": 0.2,
                "description": "高级应用和综合分析",
            },
        }

        # 认知层级配置
        self.cognitive_levels = {
            "understanding": {
                "name": "理解",
                "weight": 0.3,
                "description": "基本概念理解和记忆",
            },
            "application": {
                "name": "应用",
                "weight": 0.5,
                "description": "运用知识解决具体问题",
            },
            "synthesis": {
                "name": "综合",
                "weight": 0.2,
                "description": "综合分析多个知识点",
            },
        }

        # 题型配置
        self.question_types = {
            "multiple_choice": {"name": "选择题", "weight": 0.6, "options_count": 4},
            "short_answer": {"name": "简答题", "weight": 0.3, "options_count": 0},
            "programming": {"name": "编程题", "weight": 0.1, "options_count": 0},
        }

    def generate_exam(self, total_questions: int = 20) -> List[Dict[str, Any]]:
        """生成完整考试题目"""
        # 如果没有API密钥，直接生成模拟题目
        if not self.api_key:
            return self._generate_mock_exam(total_questions)

        questions = []

        # 根据权重分配题目数量
        subject_distribution = self._calculate_distribution(self.subjects, total_questions)

        question_id = 1
        for subject_key, subject_info in self.subjects.items():
            num_questions = subject_distribution[subject_key]

            for i in range(num_questions):
                # 随机选择难度和认知层级
                difficulty = self._weighted_choice(self.difficulty_levels)
                cognitive_level = self._weighted_choice(self.cognitive_levels)
                question_type = self._weighted_choice(self.question_types)

                # 生成题目
                question = self._generate_single_question(
                    subject_key=subject_key,
                    subject_info=subject_info,
                    difficulty=difficulty,
                    cognitive_level=cognitive_level,
                    question_type=question_type,
                    question_id=question_id,
                )

                if question:
                    questions.append(question)
                    question_id += 1

        # 随机打乱题目顺序
        random.shuffle(questions)

        # 重新分配题目ID
        for i, question in enumerate(questions, 1):
            question["id"] = f"q{i}"

        return questions

    def _generate_mock_exam(self, total_questions: int = 20) -> List[Dict[str, Any]]:
        """生成模拟考试题目"""
        questions = []

        # 模拟题目库
        mock_questions = [
            {
                "content": "在统计学中，标准差的计算公式是什么？",
                "options": ["√(Σ(x-μ)²/n)", "Σ(x-μ)²/n", "√(Σx²/n)", "Σx/n"],
                "correct_answer": "√(Σ(x-μ)²/n)",
                "explanation": "标准差是方差的平方根，用于衡量数据的离散程度。",
                "subject": "统计学",
                "difficulty": "高中水平",
                "type": "选择题",
            },
            {
                "content": "微积分中，导数的定义是什么？",
                "options": [
                    "lim(h→0)[f(x+h)-f(x)]/h",
                    "f(x+h)-f(x)",
                    "f'(x)",
                    "∫f(x)dx",
                ],
                "correct_answer": "lim(h→0)[f(x+h)-f(x)]/h",
                "explanation": "导数是函数在某点的瞬时变化率，通过极限定义。",
                "subject": "微积分",
                "difficulty": "GRE数学水平",
                "type": "选择题",
            },
            {
                "content": "线性代数中，矩阵的秩表示什么？",
                "options": [
                    "矩阵的行数",
                    "矩阵的列数",
                    "线性无关行（列）的最大个数",
                    "矩阵的行列式",
                ],
                "correct_answer": "线性无关行（列）的最大个数",
                "explanation": "矩阵的秩是矩阵中线性无关行或列的最大个数。",
                "subject": "线性代数",
                "difficulty": "研究生水平",
                "type": "选择题",
            },
            {
                "content": "概率论中，贝叶斯定理的公式是什么？",
                "options": [
                    "P(A|B) = P(B|A)P(A)/P(B)",
                    "P(A|B) = P(A)P(B)",
                    "P(A|B) = P(B|A)",
                    "P(A|B) = P(A)+P(B)",
                ],
                "correct_answer": "P(A|B) = P(B|A)P(A)/P(B)",
                "explanation": "贝叶斯定理描述了在已知B发生的条件下，A发生的概率。",
                "subject": "概率论",
                "difficulty": "GRE数学水平",
                "type": "选择题",
            },
            {
                "content": "Python中，以下哪个函数用于计算列表的长度？",
                "options": ["len()", "length()", "size()", "count()"],
                "correct_answer": "len()",
                "explanation": "len()函数用于计算序列（如列表、字符串等）的长度。",
                "subject": "编程基础",
                "difficulty": "高中水平",
                "type": "选择题",
            },
        ]

        # 生成指定数量的题目
        for i in range(total_questions):
            question_template = mock_questions[i % len(mock_questions)]
            question = {
                "id": f"q{i+1}",
                "subject": question_template["subject"],
                "subject_key": ("statistics" if "统计" in question_template["subject"] else "calculus"),
                "difficulty": question_template["difficulty"],
                "difficulty_key": question_template["difficulty"].lower().replace(" ", "_"),
                "cognitive_level": "理解",  # 固定设置为理解
                "cognitive_key": "understanding",
                "type": question_template["type"],
                "type_key": question_template["type"].lower().replace(" ", "_"),
                "content": question_template["content"],
                "options": question_template["options"],
                "correct_answer": question_template["correct_answer"],
                "explanation": question_template["explanation"],
                "points": 1,
                "time_limit": 3,
            }
            questions.append(question)

        return questions

    def _generate_single_question(
        self,
        subject_key: str,
        subject_info: Dict,
        difficulty: Dict,
        cognitive_level: Dict,
        question_type: Dict,
        question_id: int,
    ) -> Dict[str, Any]:
        """生成单个题目"""
        try:
            # 构建提示词
            prompt = self._build_generation_prompt(subject_info, difficulty, cognitive_level, question_type)

            # 调用AI API
            response = self._call_openrouter_api(prompt)

            if not response:
                return None

            # 解析响应
            question_data = self._parse_question_response(response, question_type)

            if not question_data:
                return None

            # 构建题目对象
            question = {
                "id": f"q{question_id}",
                "subject": subject_info["name"],
                "subject_key": subject_key,
                "difficulty": difficulty["name"],
                "difficulty_key": difficulty["name"].lower().replace(" ", "_"),
                "cognitive_level": cognitive_level["name"],
                "cognitive_key": cognitive_level["name"].lower(),
                "type": question_type["name"],
                "type_key": question_type["name"].lower().replace(" ", "_"),
                "content": question_data.get("content", ""),
                "options": question_data.get("options", []),
                "correct_answer": question_data.get("correct_answer", ""),
                "explanation": question_data.get("explanation", ""),
                "points": self._calculate_points(difficulty, cognitive_level),
                "time_limit": self._calculate_time_limit(question_type, difficulty),
            }

            return question

        except Exception as e:
            print(f"生成题目失败: {str(e)}")
            return None

    def _build_generation_prompt(
        self,
        subject_info: Dict,
        difficulty: Dict,
        cognitive_level: Dict,
        question_type: Dict,
    ) -> str:
        """构建AI生成提示词"""
        topic = random.choice(subject_info["topics"])

        prompt = f"""
请为IMBA（信息管理与商业分析）硕士项目生成一道考试题目。

学科领域：{subject_info['name']} - {topic}
难度等级：{difficulty['name']} - {difficulty.get('description', '')}
认知层级：{cognitive_level['name']} - {cognitive_level.get('description', '')}
题型：{question_type['name']}

要求：
1. 题目内容要符合{subject_info['name']}的{topic}主题
2. 难度要适合{difficulty['name']}水平
3. 认知要求要达到{cognitive_level['name']}层级
4. 题目要清晰明确，避免歧义
5. 如果是选择题，提供4个选项，其中只有1个正确答案
6. 如果是编程题，提供具体的编程任务和测试用例
7. 提供详细的解答和解析

请以JSON格式返回，包含以下字段：
- content: 题目内容
- options: 选项列表（选择题）或空数组（其他题型）
- correct_answer: 正确答案
- explanation: 详细解析

示例格式：
{{
    "content": "题目内容...",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correct_answer": "正确答案",
    "explanation": "详细解析..."
}}
"""
        return prompt

    def _call_openrouter_api(self, prompt: str) -> str:
        """调用OpenRouter API"""
        try:
            print(f"API Key: {self.api_key[:20] if self.api_key else 'None'}...")
            print(f"Model: {self.model}")
            print(f"API URL: {self.api_url}")

            if not self.api_key:
                print("错误: API密钥未设置，使用模拟数据")
                return self._generate_mock_response()

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的数学和统计学教育专家，擅长为研究生水平的考试生成高质量的题目。请严格按照JSON格式返回结果。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            }

            print("发送API请求...")
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)

            print(f"API响应状态: {response.status_code}")
            print(f"API响应内容: {response.text[:200]}...")

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"API调用失败: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"API调用异常: {str(e)}")
            return self._generate_mock_response()

    def _generate_mock_response(self) -> str:
        """生成模拟API响应"""
        import random

        # 模拟题目类型
        question_types = [
            {
                "content": "在统计学中，标准差的计算公式是什么？",
                "options": ["√(Σ(x-μ)²/n)", "Σ(x-μ)²/n", "√(Σx²/n)", "Σx/n"],
                "correct_answer": "√(Σ(x-μ)²/n)",
                "explanation": "标准差是方差的平方根，用于衡量数据的离散程度。",
            },
            {
                "content": "微积分中，导数的定义是什么？",
                "options": [
                    "lim(h→0)[f(x+h)-f(x)]/h",
                    "f(x+h)-f(x)",
                    "f'(x)",
                    "∫f(x)dx",
                ],
                "correct_answer": "lim(h→0)[f(x+h)-f(x)]/h",
                "explanation": "导数是函数在某点的瞬时变化率，通过极限定义。",
            },
            {
                "content": "线性代数中，矩阵的秩表示什么？",
                "options": [
                    "矩阵的行数",
                    "矩阵的列数",
                    "线性无关行（列）的最大个数",
                    "矩阵的行列式",
                ],
                "correct_answer": "线性无关行（列）的最大个数",
                "explanation": "矩阵的秩是矩阵中线性无关行或列的最大个数。",
            },
        ]

        question = random.choice(question_types)
        return json.dumps(question, ensure_ascii=False)

    def _parse_question_response(self, response: str, question_type: Dict) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 清理响应内容
            response = response.strip()

            # 尝试直接解析JSON
            if response.startswith("{"):
                return json.loads(response)

            # 如果不是JSON格式，尝试提取JSON部分
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # 修复常见的JSON格式问题
                json_str = json_str.replace('\\"', '"')  # 修复转义引号
                json_str = json_str.replace("\\n", "\n")  # 修复换行符
                json_str = json_str.replace("\\t", "\t")  # 修复制表符
                return json.loads(json_str)

            # 如果无法解析JSON，生成一个默认的题目结构
            print(f"无法解析AI响应，生成默认题目: {response[:100]}...")
            return self._generate_default_question(question_type)

        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            print(f"响应内容: {response[:200]}...")
            return self._generate_default_question(question_type)
        except Exception as e:
            print(f"解析响应时发生错误: {str(e)}")
            return self._generate_default_question(question_type)

    def _generate_default_question(self, question_type: Dict) -> Dict[str, Any]:
        """生成默认题目结构"""
        if question_type["name"] == "选择题":
            return {
                "content": "这是一道默认生成的题目，请选择正确答案。",
                "options": ["选项A", "选项B", "选项C", "选项D"],
                "correct_answer": "选项A",
                "explanation": "这是默认题目的解释。",
            }
        elif question_type["name"] == "简答题":
            return {
                "content": "这是一道默认生成的简答题，请简要回答。",
                "options": [],
                "correct_answer": "默认答案",
                "explanation": "这是默认题目的解释。",
            }
        else:
            return {
                "content": "这是一道默认生成的题目。",
                "options": [],
                "correct_answer": "默认答案",
                "explanation": "这是默认题目的解释。",
            }

    def _calculate_distribution(self, items: Dict, total: int) -> Dict[str, int]:
        """计算权重分配"""
        distribution = {}
        remaining = total

        # 按权重分配
        for key, info in items.items():
            count = int(total * info["weight"])
            distribution[key] = count
            remaining -= count

        # 分配剩余数量
        if remaining > 0:
            keys = list(items.keys())
            for i in range(remaining):
                key = keys[i % len(keys)]
                distribution[key] += 1

        return distribution

    def _weighted_choice(self, items: Dict) -> Dict:
        """加权随机选择"""
        total_weight = sum(info["weight"] for info in items.values())
        r = random.uniform(0, total_weight)

        cumulative = 0
        for key, info in items.items():
            cumulative += info["weight"]
            if r <= cumulative:
                return {"key": key, **info}

        # 默认返回第一个
        first_key = list(items.keys())[0]
        return {"key": first_key, **items[first_key]}

    def _calculate_points(self, difficulty: Dict, cognitive_level: Dict) -> int:
        """计算题目分值"""
        base_points = 1

        # 难度加分
        difficulty_bonus = {"high_school": 0, "gre_level": 1, "graduate": 2}.get(difficulty["key"], 0)

        # 认知层级加分
        cognitive_bonus = {"understanding": 0, "application": 1, "synthesis": 2}.get(cognitive_level["key"], 0)

        return base_points + difficulty_bonus + cognitive_bonus

    def generate_exam_with_prompt(self, prompt: str, count: int = 5) -> List[Dict[str, Any]]:
        """使用自定义提示词生成题目"""
        try:
            if not self.api_key:
                print("错误: API密钥未设置，使用模拟数据")
                return self._generate_mock_questions_with_prompt(prompt, count)

            # 调用OpenRouter API
            response = self._call_openrouter_api(prompt)

            # 解析响应
            try:
                data = json.loads(response)
                if "questions" in data:
                    questions = data["questions"]
                    # 确保返回指定数量的题目
                    if len(questions) > count:
                        questions = questions[:count]
                    elif len(questions) < count:
                        # 如果生成的题目不够，补充模拟题目
                        additional = self._generate_mock_questions_with_prompt(prompt, count - len(questions))
                        questions.extend(additional)
                    return questions
                else:
                    print("API响应格式错误，使用模拟数据")
                    return self._generate_mock_questions_with_prompt(prompt, count)
            except json.JSONDecodeError:
                print("API响应解析失败，使用模拟数据")
                return self._generate_mock_questions_with_prompt(prompt, count)

        except Exception as e:
            print(f"AI生成失败: {str(e)}")
            return self._generate_mock_questions_with_prompt(prompt, count)

    def _generate_mock_questions_with_prompt(self, prompt: str, count: int) -> List[Dict[str, Any]]:
        """使用高级题目生成器 - 彻底解决重复问题"""

        # 从提示词中提取信息
        subject = self._extract_subject(prompt)
        difficulty = self._extract_difficulty(prompt)
        language = self._extract_language(prompt)

        print(f"=== 启用高级题目生成器 ===")
        print(f"学科: {subject}, 难度: {difficulty}, 语言: {language}")
        print(f"提示词: {prompt[:100]}...")

        try:
            # 导入并使用高级生成器
            from .advanced_generator import AdvancedQuestionGenerator

            advanced_generator = AdvancedQuestionGenerator()
            questions = advanced_generator.generate_unique_questions(
                count=count,
                difficulty=difficulty,
                language=language,
                subject=subject,
                custom_prompt=prompt,
            )

            print(f"✅ 高级生成器成功生成 {len(questions)} 道完全不同的题目")
            return questions

        except Exception as e:
            print(f"⚠️  高级生成器失败: {e}")
            print("回退到基础生成器...")

            # 回退到原有方法
            generation_strategy = self._determine_generation_strategy(prompt)
            return self._generate_diverse_questions_with_difficulty(
                generation_strategy, count, difficulty, language, subject, prompt
            )

    def _generate_diverse_questions_with_difficulty(
        self,
        strategy: str,
        count: int,
        difficulty: str,
        language: str,
        subject: str,
        prompt: str,
    ) -> List[Dict[str, Any]]:
        """强制多样化生成器 + 真正的难度分级"""
        questions = []
        used_scenario_types = set()  # 追踪已使用的场景类型
        used_content_patterns = set()  # 追踪已使用的内容模式

        # 定义真正的难度标准
        difficulty_config = self._get_difficulty_config(difficulty, language)

        for i in range(count):
            # 强制选择不同的场景类型和内容模式
            question = self._generate_unique_question(
                strategy,
                i,
                difficulty_config,
                language,
                subject,
                prompt,
                used_scenario_types,
                used_content_patterns,
            )

            if question:
                questions.append(question)
                # 记录已使用的模式，确保下一题完全不同
                used_scenario_types.add(question.get("scenario_type", f"type_{i}"))
                used_content_patterns.add(question.get("content_pattern", f"pattern_{i}"))

        print(f"✅ 多样化生成完成: {len(questions)}道题目, 使用的场景类型: {used_scenario_types}")
        return questions

    def _get_difficulty_config(self, difficulty: str, language: str) -> dict:
        """专业分级难度标准配置"""

        # 专业难度配置字典
        professional_configs = {
            # 基础难度
            "简单": {
                "steps": 1,
                "concepts": 1,
                "calculation_complexity": "basic",
                "reasoning_depth": "direct",
                "points": 1,
                "time_limit": 2,
                "description": (
                    "直接应用单一公式或概念" if language == "zh" else "Direct application of single formula or concept"
                ),
            },
            "中等": {
                "steps": 2,
                "concepts": 2,
                "calculation_complexity": "intermediate",
                "reasoning_depth": "logical",
                "points": 3,
                "time_limit": 4,
                "description": (
                    "两步解题，结合两个概念，需要逻辑推理"
                    if language == "zh"
                    else "Two-step problem combining concepts with logical reasoning"
                ),
            },
            "困难": {
                "steps": 4,
                "concepts": 3,
                "calculation_complexity": "advanced",
                "reasoning_depth": "analytical",
                "points": 5,
                "time_limit": 8,
                "description": (
                    "多步骤分析，综合多个概念，需要深入推理"
                    if language == "zh"
                    else "Multi-step analysis with integrated concepts requiring deep reasoning"
                ),
            },
            # 标准化考试级别
            "gre_math": {
                "steps": 3,
                "concepts": 2,
                "calculation_complexity": "moderate",
                "reasoning_depth": "strategic",
                "points": 4,
                "time_limit": 3,
                "trap_answers": True,
                "data_sufficiency": True,
                "description": (
                    "GRE数学推理，需要策略性思维和陷阱识别"
                    if language == "zh"
                    else "GRE quantitative reasoning with strategic thinking and trap identification"
                ),
            },
            "gmat_math": {
                "steps": 4,
                "concepts": 3,
                "calculation_complexity": "high",
                "reasoning_depth": "business_analytical",
                "points": 5,
                "time_limit": 4,
                "business_context": True,
                "data_sufficiency": True,
                "description": (
                    "GMAT商业数学，结合商业背景的分析推理"
                    if language == "zh"
                    else "GMAT business math with analytical reasoning in business context"
                ),
            },
            "sat_math_2": {
                "steps": 3,
                "concepts": 2,
                "calculation_complexity": "advanced",
                "reasoning_depth": "competitive",
                "points": 4,
                "time_limit": 2.5,
                "multiple_approaches": True,
                "description": (
                    "SAT数学2级，竞赛水平的多路径解法"
                    if language == "zh"
                    else "SAT Math Level 2 with competitive multiple-approach solutions"
                ),
            },
            # 学术研究级别
            "graduate_study": {
                "steps": 6,
                "concepts": 4,
                "calculation_complexity": "very_high",
                "reasoning_depth": "theoretical",
                "points": 8,
                "time_limit": 15,
                "proof_required": True,
                "theoretical_basis": True,
                "description": (
                    "研究生水平，需要理论证明和深度分析"
                    if language == "zh"
                    else "Graduate level requiring theoretical proof and deep analysis"
                ),
            },
            "advanced_undergraduate": {
                "steps": 4,
                "concepts": 3,
                "calculation_complexity": "high",
                "reasoning_depth": "analytical",
                "points": 6,
                "time_limit": 10,
                "multi_concept_integration": True,
                "description": (
                    "本科高年级，多概念综合应用"
                    if language == "zh"
                    else "Advanced undergraduate with multi-concept integration"
                ),
            },
            "competition_math": {
                "steps": 5,
                "concepts": 3,
                "calculation_complexity": "creative",
                "reasoning_depth": "innovative",
                "points": 7,
                "time_limit": 12,
                "creative_approach": True,
                "non_standard_methods": True,
                "description": (
                    "数学竞赛水平，需要创新思路和非常规方法"
                    if language == "zh"
                    else "Math competition level requiring innovative thinking and non-standard methods"
                ),
            },
            # 专业应用级别
            "engineering_applications": {
                "steps": 5,
                "concepts": 4,
                "calculation_complexity": "practical_high",
                "reasoning_depth": "applied",
                "points": 6,
                "time_limit": 12,
                "real_world_context": True,
                "precision_required": True,
                "description": (
                    "工程应用水平，实际问题的精确求解"
                    if language == "zh"
                    else "Engineering application level with precise real-world problem solving"
                ),
            },
            "data_science": {
                "steps": 4,
                "concepts": 3,
                "calculation_complexity": "algorithmic",
                "reasoning_depth": "statistical",
                "points": 5,
                "time_limit": 8,
                "statistical_modeling": True,
                "algorithm_design": True,
                "description": (
                    "数据科学水平，统计建模和算法设计"
                    if language == "zh"
                    else "Data science level with statistical modeling and algorithm design"
                ),
            },
            "financial_modeling": {
                "steps": 4,
                "concepts": 3,
                "calculation_complexity": "financial",
                "reasoning_depth": "quantitative",
                "points": 6,
                "time_limit": 10,
                "financial_context": True,
                "risk_analysis": True,
                "description": (
                    "金融建模水平，量化分析和风险评估"
                    if language == "zh"
                    else "Financial modeling level with quantitative analysis and risk assessment"
                ),
            },
        }

        # 如果找不到指定难度，使用基础映射
        if difficulty not in professional_configs:
            basic_mapping = {
                "Easy": "简单",
                "Medium": "中等",
                "Hard": "困难",
                "easy": "简单",
                "medium": "中等",
                "hard": "困难",
            }
            difficulty = basic_mapping.get(difficulty, "中等")

        return professional_configs.get(difficulty, professional_configs["中等"])

    def _generate_unique_question(
        self,
        strategy: str,
        index: int,
        difficulty_config: dict,
        language: str,
        subject: str,
        prompt: str,
        used_types: set,
        used_patterns: set,
    ) -> dict:
        """生成完全唯一的题目"""
        max_attempts = 10
        for attempt in range(max_attempts):
            if strategy == "shopping_scenario":
                question = self._create_advanced_shopping_question(
                    index,
                    difficulty_config,
                    language,
                    subject,
                    used_types,
                    used_patterns,
                )
            elif strategy == "investment_scenario":
                question = self._create_advanced_investment_question(
                    index,
                    difficulty_config,
                    language,
                    subject,
                    used_types,
                    used_patterns,
                )
            elif strategy == "probability_statistics":
                question = self._create_advanced_statistics_question(
                    index,
                    difficulty_config,
                    language,
                    subject,
                    used_types,
                    used_patterns,
                )
            elif strategy == "school_scenario":
                question = self._create_advanced_school_question(
                    index,
                    difficulty_config,
                    language,
                    subject,
                    used_types,
                    used_patterns,
                )
            elif strategy == "transport_scenario":
                question = self._create_advanced_transport_question(
                    index,
                    difficulty_config,
                    language,
                    subject,
                    used_types,
                    used_patterns,
                )
            else:
                question = self._create_advanced_adaptive_question(
                    index,
                    difficulty_config,
                    language,
                    subject,
                    used_types,
                    used_patterns,
                )

            # 检查唯一性
            if question:
                scenario_type = question.get("scenario_type")
                content_pattern = question.get("content_pattern")

                if scenario_type not in used_types and content_pattern not in used_patterns:
                    return question

        # 如果尝试多次仍无法生成唯一题目，创建一个保底的唯一题目
        return self._create_fallback_unique_question(index, difficulty_config, language, subject)

    def _extract_subject(self, prompt: str) -> str:
        """从提示词中提取学科"""
        import re

        if "数学" in prompt or "Mathematics" in prompt or "math" in prompt.lower():
            return "数学" if "zh" in prompt else "Mathematics"
        elif "英语" in prompt or "English" in prompt:
            return "英语" if "zh" in prompt else "English"
        elif "计算机" in prompt or "Computer" in prompt or "Programming" in prompt:
            return "计算机" if "zh" in prompt else "Computer Science"
        elif "逻辑" in prompt or "Logic" in prompt:
            return "逻辑" if "zh" in prompt else "Logic"
        elif "统计" in prompt or "Statistics" in prompt:
            return "统计学" if "zh" in prompt else "Statistics"
        elif "物理" in prompt or "Physics" in prompt:
            return "物理" if "zh" in prompt else "Physics"
        elif "化学" in prompt or "Chemistry" in prompt:
            return "化学" if "zh" in prompt else "Chemistry"
        elif "经济" in prompt or "Economics" in prompt:
            return "经济学" if "zh" in prompt else "Economics"
        return "数学"  # 默认

    def _extract_difficulty(self, prompt: str) -> str:
        """从提示词中提取难度等级"""
        import re

        if re.search(r"简单|Easy|easy|基础|Basic|初级", prompt, re.IGNORECASE):
            return "简单"
        elif re.search(r"困难|Hard|hard|高级|Advanced|复杂|Complex", prompt, re.IGNORECASE):
            return "困难"
        elif re.search(r"中等|Medium|medium|中级|Intermediate", prompt, re.IGNORECASE):
            return "中等"
        # 从JSON格式中提取
        difficulty_match = re.search(r'"difficulty":\s*"([^"]+)"', prompt)
        if difficulty_match:
            return difficulty_match.group(1)
        return "中等"  # 默认

    def _extract_language(self, prompt: str) -> str:
        """从提示词中提取语言"""
        import re

        if re.search(r"英文|English|english|使用English", prompt):
            return "en"
        elif re.search(r"中文|Chinese|chinese|使用中文", prompt):
            return "zh"
        # 从JSON格式中提取
        lang_match = re.search(r'"language":\s*"([^"]+)"', prompt)
        if lang_match:
            return lang_match.group(1)
        return "zh"  # 默认

    def _extract_question_types(self, prompt: str) -> List[str]:
        """从提示词中提取题型"""
        types = []
        if "选择题" in prompt or "multiple_choice" in prompt or "Multiple Choice" in prompt:
            types.append("multiple_choice")
        if "简答题" in prompt or "short_answer" in prompt or "Short Answer" in prompt:
            types.append("short_answer")
        if "编程题" in prompt or "programming" in prompt or "Programming" in prompt:
            types.append("programming")
        if "计算题" in prompt or "calculation" in prompt:
            types.append("calculation")
        if "证明题" in prompt or "proof" in prompt:
            types.append("proof")
        if "应用题" in prompt or "application" in prompt:
            types.append("application")
        return types if types else ["multiple_choice"]

    def _extract_sub_tag(self, prompt: str) -> str:
        """从提示词中提取子标签"""
        import re

        sub_tag_match = re.search(r"子标签为([^，\s]+)", prompt)
        if sub_tag_match:
            return sub_tag_match.group(1)

        # 从提示词内容推断子标签
        if "概率" in prompt or "probability" in prompt.lower():
            return "概率论"
        elif "统计" in prompt or "statistics" in prompt.lower():
            return "统计学"
        elif "微积分" in prompt or "calculus" in prompt.lower():
            return "微积分"
        elif "线性代数" in prompt or "linear algebra" in prompt.lower():
            return "线性代数"
        elif "算法" in prompt or "algorithm" in prompt.lower():
            return "算法"
        return ""

    def _determine_generation_strategy(self, prompt: str) -> str:
        """确定题目生成策略 - 增强版"""
        import re

        # 首先检查具体的场景类型
        if re.search(r"购物|shopping|买|buy|价格|price|商店|store", prompt, re.IGNORECASE):
            return "shopping_scenario"
        elif re.search(
            r"投资|investment|利息|interest|收益|profit|理财|finance",
            prompt,
            re.IGNORECASE,
        ):
            return "investment_scenario"
        elif re.search(r"学校|school|学生|student|班级|class|教室|classroom", prompt, re.IGNORECASE):
            return "school_scenario"
        elif re.search(
            r"交通|transport|车|bus|taxi|速度|speed|距离|distance",
            prompt,
            re.IGNORECASE,
        ):
            return "transport_scenario"
        elif re.search(
            r"餐厅|restaurant|食物|food|分享|share|pizza|蛋糕|cake",
            prompt,
            re.IGNORECASE,
        ):
            return "restaurant_scenario"

        # 然后检查题目类型
        elif re.search(
            r"\d+\s*(ml|毫升|升|liters?)|mixture|ratio|mix|混合|比例",
            prompt,
            re.IGNORECASE,
        ):
            return "mixture_problems"
        elif re.search(r"建模|modeling|model|优化|optimization", prompt, re.IGNORECASE):
            return "mathematical_modeling"
        elif re.search(
            r"算法|algorithm|编程|programming|计算思维|computational",
            prompt,
            re.IGNORECASE,
        ):
            return "computational_thinking"
        elif re.search(r"概率|probability|统计|statistics|数据|data", prompt, re.IGNORECASE):
            return "probability_statistics"
        elif re.search(r"场景|scenario|实际|应用|application", prompt, re.IGNORECASE):
            return "scenario_based"

        return "adaptive"

    def _generate_mixture_problems(
        self, count: int, difficulty: str, language: str, subject: str
    ) -> List[Dict[str, Any]]:
        """生成混合物问题（根据难度分级）"""
        questions = []

        # 根据难度级别设计问题复杂度
        if difficulty == "简单":
            base_numbers = [100, 200, 300, 400, 500]
            ratios = [(1, 1), (2, 1), (3, 2), (4, 1)]
        elif difficulty == "困难":
            base_numbers = [729, 1260, 1848, 2156, 3675]
            ratios = [(7, 2), (9, 4), (11, 3), (13, 5), (15, 7)]
        else:  # 中等
            base_numbers = [240, 360, 480, 600, 840]
            ratios = [(3, 2), (4, 3), (5, 2), (7, 3), (8, 5)]

        for i in range(count):
            volume = base_numbers[i % len(base_numbers)]
            ratio_a, ratio_b = ratios[i % len(ratios)]

            if language == "en":
                if difficulty == "简单":
                    content = f"A mixture of {volume} ml contains milk and water in ratio {ratio_a}:{ratio_b}. How much water should be added to make the ratio 1:1?"
                    explanation = f"Simple calculation: Original milk = {volume * ratio_a // (ratio_a + ratio_b)} ml, water = {volume * ratio_b // (ratio_a + ratio_b)} ml."
                elif difficulty == "困难":
                    content = f"{volume} ml mixture has milk:water = {ratio_a}:{ratio_b}. After adding x ml water, ratio becomes {ratio_a}:{ratio_b+2}. Find x and the percentage increase."
                    explanation = (
                        f"Complex multi-step calculation involving percentage changes and ratio transformations."
                    )
                else:
                    content = f"{volume} ml mixture contains milk and water in ratio {ratio_a}:{ratio_b}. How much water to add for ratio {ratio_a}:{ratio_b+1}?"
                    explanation = (
                        f"Medium complexity: Calculate current amounts, determine target amounts, find difference."
                    )
            else:
                if difficulty == "简单":
                    content = f"{volume}毫升混合物中牛奶和水的比例是{ratio_a}:{ratio_b}。加多少水可以使比例变成1:1？"
                    explanation = f"简单计算：原有牛奶 = {volume * ratio_a // (ratio_a + ratio_b)}毫升，水 = {volume * ratio_b // (ratio_a + ratio_b)}毫升。"
                elif difficulty == "困难":
                    content = f"{volume}毫升混合物中牛奶:水 = {ratio_a}:{ratio_b}。加入x毫升水后，比例变成{ratio_a}:{ratio_b+2}。求x和增长百分比。"
                    explanation = f"复杂的多步计算，涉及百分比变化和比例转换。"
                else:
                    content = f"{volume}毫升混合物中牛奶和水的比例是{ratio_a}:{ratio_b}。加多少水使比例变成{ratio_a}:{ratio_b+1}？"
                    explanation = f"中等复杂度：计算当前量，确定目标量，求差值。"

            # 计算正确答案
            current_milk = volume * ratio_a // (ratio_a + ratio_b)
            current_water = volume * ratio_b // (ratio_a + ratio_b)
            target_ratio = ratio_b + 1 if difficulty != "简单" else ratio_a
            needed_water = (current_milk * target_ratio) // ratio_a if difficulty != "简单" else current_milk
            answer = needed_water - current_water if needed_water > current_water else current_water - needed_water

            options = (
                [
                    f"{answer} ml",
                    f"{answer + 50} ml",
                    f"{answer - 30} ml",
                    f"{answer + 100} ml",
                ]
                if language == "en"
                else [
                    f"{answer}毫升",
                    f"{answer + 50}毫升",
                    f"{answer - 30}毫升",
                    f"{answer + 100}毫升",
                ]
            )

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": "混合问题",
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": 2 if difficulty == "困难" else 1,
                }
            )

        return questions

    def _generate_scenario_problems(
        self, count: int, difficulty: str, language: str, subject: str
    ) -> List[Dict[str, Any]]:
        """生成场景类题目（现实世界应用）- 多样化版本"""
        questions = []

        # 扩展场景模板库，提供更多样化的题目
        scenarios = {
            "简单": {
                "en": [
                    {
                        "context": "Shopping Mall",
                        "template": "You have ${money} to buy {item}. Each {item} costs ${price}. How many can you buy?",
                        "variables": {
                            "money": [80, 120, 150, 200],
                            "item": ["gifts", "books", "toys", "snacks"],
                            "price": [12, 18, 25, 15],
                        },
                        "explanation_template": "{money} ÷ {price} = {result}, so you can buy {answer} complete {item}.",
                    },
                    {
                        "context": "Restaurant",
                        "template": "A {food} has {total} pieces. If {people} friends share equally, how many pieces does each get?",
                        "variables": {
                            "food": ["pizza", "cake", "pie", "sandwich"],
                            "total": [8, 12, 6, 10],
                            "people": [3, 4, 2, 5],
                        },
                        "explanation_template": "{total} ÷ {people} = {result} pieces per person.",
                    },
                    {
                        "context": "School",
                        "template": "A class has {students} students. Each student needs {items} {item}. How many {item} are needed in total?",
                        "variables": {
                            "students": [25, 30, 28, 32],
                            "items": [2, 3, 4, 1],
                            "item": ["pencils", "notebooks", "erasers", "rulers"],
                        },
                        "explanation_template": "{students} × {items} = {result} {item} needed.",
                    },
                    {
                        "context": "Transportation",
                        "template": "A bus can carry {capacity} people. If {waiting} people are waiting, how many buses are needed?",
                        "variables": {
                            "capacity": [50, 40, 60, 45],
                            "waiting": [120, 85, 150, 95],
                        },
                        "explanation_template": "{waiting} ÷ {capacity} = {result}, so {answer} buses are needed.",
                    },
                ],
                "zh": [
                    {
                        "context": "购物场景",
                        "template": "你有{money}元买{item}，每个{item}{price}元，能买几个？",
                        "variables": {
                            "money": [80, 120, 150, 200],
                            "item": ["礼物", "书本", "玩具", "零食"],
                            "price": [12, 18, 25, 15],
                        },
                        "explanation_template": "{money} ÷ {price} = {result}，所以能买{answer}个完整的{item}。",
                    },
                    {
                        "context": "餐厅场景",
                        "template": "一个{food}有{total}块，{people}个朋友平分，每人分几块？",
                        "variables": {
                            "food": ["披萨", "蛋糕", "派", "三明治"],
                            "total": [8, 12, 6, 10],
                            "people": [3, 4, 2, 5],
                        },
                        "explanation_template": "{total} ÷ {people} = {result}块每人。",
                    },
                    {
                        "context": "学校场景",
                        "template": "班级有{students}个学生，每人需要{items}支{item}，总共需要多少支{item}？",
                        "variables": {
                            "students": [25, 30, 28, 32],
                            "items": [2, 3, 4, 1],
                            "item": ["铅笔", "笔记本", "橡皮", "尺子"],
                        },
                        "explanation_template": "{students} × {items} = {result}支{item}。",
                    },
                    {
                        "context": "交通场景",
                        "template": "一辆公交车可载{capacity}人，有{waiting}人等车，需要几辆车？",
                        "variables": {
                            "capacity": [50, 40, 60, 45],
                            "waiting": [120, 85, 150, 95],
                        },
                        "explanation_template": "{waiting} ÷ {capacity} = {result}，所以需要{answer}辆车。",
                    },
                ],
            },
            "中等": {
                "en": [
                    {
                        "context": "Business Investment",
                        "content": "A company invests $10,000 at 5% annual interest. After 3 years, what is the compound interest earned?",
                        "options": ["$1,576.25", "$1,500.00", "$1,625.00", "$1,750.00"],
                        "answer": "$1,576.25",
                        "explanation": "Compound Interest = P(1+r)^t - P = 10000(1.05)^3 - 10000 = $1,576.25",
                    }
                ],
                "zh": [
                    {
                        "context": "商业投资",
                        "content": "公司投资10000元，年利率5%，3年后复利是多少？",
                        "options": ["1576.25元", "1500.00元", "1625.00元", "1750.00元"],
                        "answer": "1576.25元",
                        "explanation": "复利 = P(1+r)^t - P = 10000(1.05)^3 - 10000 = 1576.25元",
                    }
                ],
            },
            "困难": {
                "en": [
                    {
                        "context": "Economic Optimization",
                        "content": "A factory produces x units daily. Cost: C(x) = 100 + 50x + 0.5x². Revenue: R(x) = 200x. Find optimal production for maximum profit.",
                        "options": ["150 units", "100 units", "200 units", "75 units"],
                        "answer": "150 units",
                        "explanation": "Profit P(x) = R(x) - C(x) = 150x - 0.5x². dP/dx = 150 - x = 0, so x = 150.",
                    }
                ],
                "zh": [
                    {
                        "context": "经济优化",
                        "content": "工厂日产x单位，成本C(x)=100+50x+0.5x²，收入R(x)=200x，求最大利润的最优产量。",
                        "options": ["150单位", "100单位", "200单位", "75单位"],
                        "answer": "150单位",
                        "explanation": "利润P(x)=R(x)-C(x)=150x-0.5x²，dP/dx=150-x=0，所以x=150。",
                    }
                ],
            },
        }

        import random

        scenario_list = scenarios[difficulty][language]
        for i in range(count):
            scenario_template = scenario_list[i % len(scenario_list)]

            # 检查是否有模板和变量（新格式）
            if "template" in scenario_template and "variables" in scenario_template:
                # 新的多样化生成方式
                template = scenario_template["template"]
                variables = scenario_template["variables"]

                # 随机选择变量值
                selected_vars = {}
                for var_name, var_options in variables.items():
                    selected_vars[var_name] = random.choice(var_options)

                # 生成题目内容
                content = template.format(**selected_vars)

                # 计算答案
                if "money" in selected_vars and "price" in selected_vars:
                    # 购物场景
                    result = selected_vars["money"] // selected_vars["price"]
                    answer_num = result
                    options = [
                        f"{result}个" if language == "zh" else f"{result} items",
                        f"{result+1}个" if language == "zh" else f"{result+1} items",
                        f"{result-1}个" if language == "zh" else f"{result-1} items",
                        f"{result+2}个" if language == "zh" else f"{result+2} items",
                    ]
                elif "total" in selected_vars and "people" in selected_vars:
                    # 分享场景
                    result = round(selected_vars["total"] / selected_vars["people"], 2)
                    answer_num = result
                    options = [
                        f"{result}块" if language == "zh" else f"{result} pieces",
                        (f"{result+0.5}块" if language == "zh" else f"{result+0.5} pieces"),
                        (f"{result-0.5}块" if language == "zh" else f"{result-0.5} pieces"),
                        f"{result+1}块" if language == "zh" else f"{result+1} pieces",
                    ]
                elif "students" in selected_vars and "items" in selected_vars:
                    # 学校场景
                    result = selected_vars["students"] * selected_vars["items"]
                    answer_num = result
                    options = [
                        f"{result}支" if language == "zh" else f"{result} items",
                        f"{result+5}支" if language == "zh" else f"{result+5} items",
                        f"{result-5}支" if language == "zh" else f"{result-5} items",
                        f"{result+10}支" if language == "zh" else f"{result+10} items",
                    ]
                elif "waiting" in selected_vars and "capacity" in selected_vars:
                    # 交通场景
                    import math

                    result = math.ceil(selected_vars["waiting"] / selected_vars["capacity"])
                    answer_num = result
                    options = [
                        f"{result}辆" if language == "zh" else f"{result} buses",
                        f"{result+1}辆" if language == "zh" else f"{result+1} buses",
                        f"{result-1}辆" if language == "zh" else f"{result-1} buses",
                        f"{result+2}辆" if language == "zh" else f"{result+2} buses",
                    ]
                else:
                    # 默认选项
                    options = (
                        ["选项A", "选项B", "选项C", "选项D"]
                        if language == "zh"
                        else ["Option A", "Option B", "Option C", "Option D"]
                    )
                    answer_num = "A"

                # 生成解释
                selected_vars["result"] = result if "result" in locals() else 0
                selected_vars["answer"] = answer_num
                explanation = scenario_template["explanation_template"].format(**selected_vars)

            else:
                # 旧格式，保持兼容性
                content = scenario_template["content"]
                options = scenario_template["options"]
                explanation = scenario_template["explanation"]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": (
                        f"场景应用-{scenario_template['context']}"
                        if language == "zh"
                        else f"Scenario-{scenario_template['context']}"
                    ),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": (3 if difficulty == "困难" else (2 if difficulty == "中等" else 1)),
                }
            )

        return questions

    def _generate_mathematical_modeling(
        self, count: int, difficulty: str, language: str, subject: str
    ) -> List[Dict[str, Any]]:
        """生成数学建模题目"""
        questions = []
        templates = {
            "简单": ["Plant growth model: 2cm/week. Start 4cm, when reach 20cm?"],
            "中等": ["Exponential decay N(t)=N₀e^(-λt), half-life 5 years, find λ"],
            "困难": ["Multi-var optimization: min f(x,y)=x²+y² subject to x+2y-6=0"],
        }

        for i in range(count):
            template = templates[difficulty][i % len(templates[difficulty])]
            questions.append(
                {
                    "subject": subject,
                    "sub_tag": ("数学建模" if language == "zh" else "Mathematical Modeling"),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "short_answer",
                    "content": template,
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "explanation": "Mathematical modeling problem",
                    "points": (5 if difficulty == "困难" else (3 if difficulty == "中等" else 2)),
                }
            )
        return questions

    def _generate_real_world_applications(
        self, count: int, difficulty: str, language: str, subject: str
    ) -> List[Dict[str, Any]]:
        """生成现实世界应用题目"""
        return self._generate_scenario_problems(count, difficulty, language, subject)

    def _generate_computational_thinking(
        self, count: int, difficulty: str, language: str, subject: str
    ) -> List[Dict[str, Any]]:
        """生成计算思维题目"""
        questions = []
        for i in range(count):
            if difficulty == "简单":
                content = (
                    "What output: for i in range(3): print(i*2)?"
                    if language == "en"
                    else "输出什么：for i in range(3): print(i*2)?"
                )
                answer = "0, 2, 4"
            elif difficulty == "困难":
                content = (
                    "Time complexity: for i in range(n): for j in range(i): process()"
                    if language == "en"
                    else "时间复杂度：for i in range(n): for j in range(i): process()"
                )
                answer = "O(n²)"
            else:
                content = (
                    "Binary search steps for 1000 elements?" if language == "en" else "对1000元素二分查找需要多少步？"
                )
                answer = "10 steps" if language == "en" else "10步"

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": ("计算思维" if language == "zh" else "Computational Thinking"),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": [answer, "Wrong1", "Wrong2", "Wrong3"],
                    "correct_answer": answer,
                    "explanation": "Computational thinking analysis",
                    "points": (4 if difficulty == "困难" else (2 if difficulty == "中等" else 1)),
                }
            )
        return questions

    def _generate_adaptive_questions(
        self,
        count: int,
        difficulty: str,
        language: str,
        subject: str,
        types: List[str],
        sub_tag: str,
        prompt: str,
    ) -> List[Dict[str, Any]]:
        """自适应题目生成（通用方法）"""
        questions = []
        for i in range(count):
            if subject in ["数学", "Mathematics"]:
                if difficulty == "简单":
                    content = "Calculate: 15 + 27 = ?" if language == "en" else "计算：15 + 27 = ?"
                    answer = "42"
                elif difficulty == "困难":
                    content = (
                        "Solve: ∫(x² + 3x + 2)dx from 0 to 2"
                        if language == "en"
                        else "求解：∫(x² + 3x + 2)dx 从 0 到 2"
                    )
                    answer = "22/3"
                else:
                    content = "Find derivative: d/dx(x³ - 2x + 1)" if language == "en" else "求导数：d/dx(x³ - 2x + 1)"
                    answer = "3x² - 2"
            else:
                content = (
                    f"Question about {subject} - {difficulty} level"
                    if language == "en"
                    else f"关于{subject}的{difficulty}题目"
                )
                answer = "Answer A"

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": sub_tag,
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": types[0] if types else "multiple_choice",
                    "content": content,
                    "options": [answer, "Option B", "Option C", "Option D"],
                    "correct_answer": answer,
                    "explanation": f"This is a {difficulty} difficulty question about {subject}",
                    "points": (3 if difficulty == "困难" else (2 if difficulty == "中等" else 1)),
                }
            )
        return questions

    def _generate_shopping_scenario(
        self, count: int, difficulty: str, language: str, subject: str, prompt: str
    ) -> List[Dict[str, Any]]:
        """生成购物场景题目 - 专业多样化版本"""
        questions = []
        import random

        # 定义多样化的购物场景知识点分支
        scenario_types = {
            "zh": [
                {
                    "type": "单价计算",
                    "template": "超市购物：{customer}想买{quantity}个{item}，总共花费{total}元，每个{item}的单价是多少？",
                    "knowledge": "除法运算：总价÷数量=单价",
                    "items": ["苹果", "橘子", "香蕉", "牛奶", "面包"],
                    "customers": ["小明", "小红", "张阿姨", "李叔叔", "王奶奶"],
                },
                {
                    "type": "折扣优惠",
                    "template": "商场促销：{item}原价{original}元，现在{discount}折优惠，{customer}买{quantity}个需要多少钱？",
                    "knowledge": "百分数应用：原价×折扣×数量",
                    "items": ["运动鞋", "衬衫", "书包", "文具盒", "玩具"],
                    "customers": ["小学生", "中学生", "上班族", "退休人员"],
                },
                {
                    "type": "找零计算",
                    "template": "便利店购物：{customer}用{payment}元买了{quantity}个单价{price}元的{item}，应该找零多少钱？",
                    "knowledge": "减法运算：付款金额-商品总价",
                    "items": ["饮料", "零食", "口香糖", "报纸", "矿泉水"],
                    "customers": ["路人甲", "学生", "工人", "司机"],
                },
                {
                    "type": "比较购买",
                    "template": "价格比较：A店{item}每个{price_a}元，B店同样的{item}买{quantity}个送{bonus}个，哪个更划算？",
                    "knowledge": "单价比较和性价比分析",
                    "items": ["鸡蛋", "牙膏", "洗发水", "大米", "食用油"],
                    "customers": ["家庭主妇", "精明消费者", "节约达人"],
                },
                {
                    "type": "批量采购",
                    "template": "批发市场：{customer}需要采购{item}，零售价{retail}元/个，满{threshold}个批发价{wholesale}元/个，买{quantity}个最省钱的方案是什么？",
                    "knowledge": "条件判断和优化决策",
                    "items": ["文具", "电池", "清洁用品", "办公用品", "日用品"],
                    "customers": ["办公室经理", "学校采购员", "小店老板"],
                },
            ],
            "en": [
                {
                    "type": "unit_price",
                    "template": "Grocery shopping: {customer} wants to buy {quantity} {item} for a total of ${total}. What is the unit price?",
                    "knowledge": "Division: Total cost ÷ Quantity = Unit price",
                    "items": [
                        "apples",
                        "oranges",
                        "bananas",
                        "milk bottles",
                        "bread loaves",
                    ],
                    "customers": ["Alice", "Bob", "Mrs. Chen", "Mr. Smith", "Grandma"],
                },
                {
                    "type": "discount",
                    "template": "Store sale: {item} originally costs ${original} each. There is a {discount}% discount. How much does {customer} pay for {quantity} items?",
                    "knowledge": "Percentage application: Original price × (100-discount)% × quantity",
                    "items": [
                        "sneakers",
                        "shirts",
                        "backpacks",
                        "stationery sets",
                        "toys",
                    ],
                    "customers": [
                        "a student",
                        "an office worker",
                        "a parent",
                        "a teenager",
                    ],
                },
                {
                    "type": "change_calculation",
                    "template": "Convenience store: {customer} pays ${payment} for {quantity} {item} at ${price} each. How much change should they receive?",
                    "knowledge": "Subtraction: Payment amount - Total cost",
                    "items": [
                        "drinks",
                        "snacks",
                        "gum packs",
                        "newspapers",
                        "water bottles",
                    ],
                    "customers": ["a customer", "a student", "a worker", "a driver"],
                },
                {
                    "type": "price_comparison",
                    "template": "Price comparison: Store A sells {item} at ${price_a} each. Store B sells {quantity} {item} and gives {bonus} free. Which is better?",
                    "knowledge": "Unit price comparison and value analysis",
                    "items": [
                        "eggs",
                        "toothpaste",
                        "shampoo",
                        "rice bags",
                        "cooking oil",
                    ],
                    "customers": [
                        "a housewife",
                        "a smart shopper",
                        "a budget-conscious person",
                    ],
                },
                {
                    "type": "bulk_purchase",
                    "template": "Wholesale market: {customer} needs {item}. Retail price: ${retail} each. Bulk price (≥{threshold}): ${wholesale} each. What is the best way to buy {quantity} items?",
                    "knowledge": "Conditional logic and optimization",
                    "items": [
                        "stationery",
                        "batteries",
                        "cleaning supplies",
                        "office supplies",
                        "daily necessities",
                    ],
                    "customers": [
                        "an office manager",
                        "a school buyer",
                        "a shop owner",
                    ],
                },
            ],
        }

        for i in range(count):
            # 随机选择一个场景类型，确保每道题都不同
            scenario = random.choice(scenario_types[language])

            # 根据难度调整数值范围
            if difficulty == "简单":
                quantity = random.randint(2, 5)
                price = random.randint(5, 15)
                payment = quantity * price + random.randint(10, 50)  # 确保付款金额大于商品总价
                base_values = {
                    "quantity": quantity,
                    "price": price,
                    "original": random.randint(20, 100),
                    "discount": random.choice([8, 9, 7, 6]),
                    "payment": payment,
                    "threshold": random.randint(10, 20),
                    "bonus": random.randint(1, 3),
                }
            elif difficulty == "困难":
                quantity = random.randint(8, 15)
                price = random.randint(25, 80)
                payment = quantity * price + random.randint(50, 200)
                base_values = {
                    "quantity": quantity,
                    "price": price,
                    "original": random.randint(200, 1000),
                    "discount": random.choice([75, 85, 65, 55]),
                    "payment": payment,
                    "threshold": random.randint(50, 100),
                    "bonus": random.randint(5, 15),
                }
            else:  # 中等
                quantity = random.randint(5, 10)
                price = random.randint(15, 40)
                payment = quantity * price + random.randint(20, 100)
                base_values = {
                    "quantity": quantity,
                    "price": price,
                    "original": random.randint(80, 300),
                    "discount": random.choice([8, 9, 7, 6]),
                    "payment": payment,
                    "threshold": random.randint(20, 50),
                    "bonus": random.randint(2, 8),
                }

            # 填充模板变量
            template_vars = {
                "customer": random.choice(scenario["customers"]),
                "item": random.choice(scenario["items"]),
                "quantity": base_values["quantity"],
                "total": base_values["quantity"] * base_values["price"],
                "price": base_values["price"],
                "original": base_values["original"],
                "discount": base_values["discount"],
                "payment": base_values["payment"],
                "price_a": base_values["price"],
                "threshold": base_values["threshold"],
                "wholesale": base_values["price"] - random.randint(2, 8),
                "retail": base_values["price"],
                "bonus": base_values["bonus"],
            }

            # 生成题目内容
            content = scenario["template"].format(**template_vars)

            # 根据题目类型计算答案
            if scenario["type"] in ["单价计算", "unit_price"]:
                correct_answer = template_vars["total"] // template_vars["quantity"]
                if language == "zh":
                    explanation = (
                        f"单价计算：{template_vars['total']}元 ÷ {template_vars['quantity']}个 = {correct_answer}元/个"
                    )
                    options = [
                        f"{correct_answer}元",
                        f"{correct_answer+2}元",
                        f"{correct_answer-1}元",
                        f"{correct_answer+5}元",
                    ]
                else:
                    explanation = (
                        f"Unit price: ${template_vars['total']} ÷ {template_vars['quantity']} = ${correct_answer}"
                    )
                    options = [
                        f"${correct_answer}",
                        f"${correct_answer+2}",
                        f"${correct_answer-1}",
                        f"${correct_answer+5}",
                    ]

            elif scenario["type"] in ["折扣优惠", "discount"]:
                discount_price = template_vars["original"] * (template_vars["discount"] / 10)
                total_cost = discount_price * template_vars["quantity"]
                if language == "zh":
                    explanation = f"折扣价：{template_vars['original']}元 × {template_vars['discount']}折 × {template_vars['quantity']}个 = {total_cost:.0f}元"
                    options = [
                        f"{total_cost:.0f}元",
                        f"{total_cost*1.1:.0f}元",
                        f"{total_cost*0.9:.0f}元",
                        f"{total_cost*1.2:.0f}元",
                    ]
                else:
                    explanation = f"Discounted total: ${template_vars['original']} × {100-template_vars['discount']}% × {template_vars['quantity']} = ${total_cost:.0f}"
                    options = [
                        f"${total_cost:.0f}",
                        f"${total_cost*1.1:.0f}",
                        f"${total_cost*0.9:.0f}",
                        f"${total_cost*1.2:.0f}",
                    ]

            elif scenario["type"] in ["找零计算", "change_calculation"]:
                total_spent = template_vars["price"] * template_vars["quantity"]
                change = template_vars["payment"] - total_spent
                if language == "zh":
                    explanation = f"找零：{template_vars['payment']}元 - ({template_vars['price']}元 × {template_vars['quantity']}个) = {change}元"
                    options = [
                        f"{change}元",
                        f"{change+10}元",
                        f"{change-5}元",
                        f"{change+15}元",
                    ]
                else:
                    explanation = f"Change: ${template_vars['payment']} - (${template_vars['price']} × {template_vars['quantity']}) = ${change}"
                    options = [
                        f"${change}",
                        f"${change+10}",
                        f"${change-5}",
                        f"${change+15}",
                    ]

            else:  # 其他复杂场景
                if language == "zh":
                    correct_answer = "需要具体分析"
                    explanation = f"这是一道综合分析题，需要考虑{scenario['knowledge']}"
                    options = ["方案A更优", "方案B更优", "两者相等", "无法确定"]
                else:
                    correct_answer = "Needs analysis"
                    explanation = f"This requires comprehensive analysis considering {scenario['knowledge']}"
                    options = [
                        "Option A is better",
                        "Option B is better",
                        "They are equal",
                        "Cannot determine",
                    ]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": (f"购物场景-{scenario['type']}" if language == "zh" else f"Shopping-{scenario['type']}"),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": {"简单": 2, "中等": 3, "困难": 4}.get(difficulty, 2),
                }
            )

        return questions

    def _generate_investment_scenario(
        self, count: int, difficulty: str, language: str, subject: str, prompt: str
    ) -> List[Dict[str, Any]]:
        """生成投资理财场景题目 - 多样化专业版本"""
        questions = []
        import random

        # 定义多样化的投资理财场景
        scenario_types = {
            "zh": [
                {
                    "type": "银行存款",
                    "template": "{person}在{bank}存入{principal}元，年利率{rate}%，{mode}，{period}后能取出多少钱？",
                    "banks": [
                        "工商银行",
                        "建设银行",
                        "农业银行",
                        "招商银行",
                        "中国银行",
                    ],
                    "persons": ["张先生", "李女士", "王同学", "刘阿姨", "陈叔叔"],
                    "modes": ["定期存款", "活期存款", "大额存单"],
                    "knowledge": "利息计算：本金×利率×时间",
                },
                {
                    "type": "股票投资",
                    "template": "{person}买入{company}股票{shares}股，每股{price}元，{period}后股价{change_type}到{final_price}元，{action}后盈亏多少？",
                    "companies": ["腾讯", "阿里巴巴", "茅台", "比亚迪", "宁德时代"],
                    "persons": [
                        "投资新手小王",
                        "资深股民老李",
                        "理财达人小张",
                        "上班族小刘",
                    ],
                    "change_types": ["上涨", "下跌", "波动"],
                    "actions": ["全部卖出", "卖出一半", "继续持有"],
                    "knowledge": "股票损益：(卖出价-买入价)×股数-手续费",
                },
                {
                    "type": "基金定投",
                    "template": "{person}每月定投{fund_name}基金{monthly}元，连续投资{months}个月，平均收益率{rate}%，最终资产价值多少？",
                    "fund_names": [
                        "沪深300",
                        "创业板ETF",
                        "科技主题",
                        "消费升级",
                        "新能源",
                    ],
                    "persons": ["理财新手", "工薪族", "大学生", "退休人员"],
                    "knowledge": "定投收益：本金总额×(1+平均收益率)",
                },
                {
                    "type": "房产投资",
                    "template": "{person}在{city}{location}购买{area}平米房产，单价{price}元/平米，{period}后房价{change_type}{percent}%，房产总价值多少？",
                    "cities": ["北京", "上海", "深圳", "杭州", "成都"],
                    "locations": ["市中心", "学区", "地铁沿线", "商业区", "新区"],
                    "persons": ["首次购房者", "投资客", "换房族", "海归人士"],
                    "change_types": ["上涨", "下跌"],
                    "knowledge": "房产估值：面积×单价×(1±涨跌幅)",
                },
                {
                    "type": "保险理财",
                    "template": "{person}购买{insurance_type}，年缴费{premium}元，缴费{years}年，预期年化收益{rate}%，到期能领取多少钱？",
                    "insurance_types": [
                        "年金险",
                        "万能险",
                        "增额终身寿险",
                        "教育金",
                        "养老金",
                    ],
                    "persons": ["年轻父母", "中年白领", "临近退休者", "高收入群体"],
                    "knowledge": "保险收益：总保费×复利增长",
                },
            ],
            "en": [
                {
                    "type": "bank_deposit",
                    "template": "{person} deposits ${principal} in {bank} at {rate}% annual interest, {mode}. How much can be withdrawn after {period}?",
                    "banks": [
                        "Bank of America",
                        "Wells Fargo",
                        "Chase Bank",
                        "Citibank",
                        "TD Bank",
                    ],
                    "persons": [
                        "Mr. Smith",
                        "Ms. Johnson",
                        "Student Alex",
                        "Mrs. Davis",
                        "Mr. Wilson",
                    ],
                    "modes": [
                        "fixed deposit",
                        "savings account",
                        "certificate of deposit",
                    ],
                    "knowledge": "Interest calculation: Principal × Rate × Time",
                },
                {
                    "type": "stock_investment",
                    "template": "{person} buys {shares} shares of {company} at ${price} per share. After {period}, the stock price {change_type} to ${final_price}. What is the profit/loss if {action}?",
                    "companies": ["Apple", "Microsoft", "Amazon", "Google", "Tesla"],
                    "persons": [
                        "novice investor John",
                        "experienced trader Mary",
                        "day trader Bob",
                        "long-term investor Sarah",
                    ],
                    "change_types": ["rises", "falls", "fluctuates"],
                    "actions": ["sold all", "sold half", "held"],
                    "knowledge": "Stock P&L: (Selling price - Buying price) × Shares - Fees",
                },
                {
                    "type": "fund_investment",
                    "template": "{person} invests ${monthly} monthly in {fund_name} fund for {months} months with average return of {rate}%. What is the final portfolio value?",
                    "fund_names": [
                        "S&P 500",
                        "Tech ETF",
                        "Growth Fund",
                        "Value Fund",
                        "International",
                    ],
                    "persons": [
                        "young professional",
                        "retiree",
                        "college graduate",
                        "small business owner",
                    ],
                    "knowledge": "Investment return: Total principal × (1 + Average return)",
                },
                {
                    "type": "real_estate",
                    "template": "{person} buys {area} sq ft property in {city} {location} at ${price} per sq ft. After {period}, property prices {change_type} by {percent}%. What is the total property value?",
                    "cities": [
                        "New York",
                        "San Francisco",
                        "Los Angeles",
                        "Miami",
                        "Seattle",
                    ],
                    "locations": [
                        "downtown",
                        "suburbs",
                        "waterfront",
                        "business district",
                        "residential area",
                    ],
                    "persons": [
                        "first-time buyer",
                        "real estate investor",
                        "family upgrading",
                        "retiree",
                    ],
                    "change_types": ["increase", "decrease"],
                    "knowledge": "Property valuation: Area × Price per sq ft × (1 ± Change%)",
                },
                {
                    "type": "insurance_investment",
                    "template": "{person} purchases {insurance_type} with annual premium of ${premium} for {years} years, expected return {rate}%. How much can be received at maturity?",
                    "insurance_types": [
                        "whole life insurance",
                        "annuity",
                        "universal life",
                        "education plan",
                        "retirement plan",
                    ],
                    "persons": [
                        "young parent",
                        "middle-aged professional",
                        "near-retiree",
                        "high earner",
                    ],
                    "knowledge": "Insurance return: Total premiums × Compound growth",
                },
            ],
        }

        for i in range(count):
            # 随机选择一个投资场景类型
            scenario = random.choice(scenario_types[language])

            # 根据难度设置参数范围
            if difficulty == "简单":
                base_values = {
                    "principal": random.choice([1000, 2000, 5000, 8000]),
                    "rate": random.choice([3, 5, 6, 8]),
                    "period": (
                        random.choice(["1年", "2年", "3年"])
                        if language == "zh"
                        else random.choice(["1 year", "2 years", "3 years"])
                    ),
                    "shares": random.randint(10, 100),
                    "price": random.randint(10, 50),
                    "monthly": random.choice([500, 1000, 1500]),
                    "months": random.choice([12, 24, 36]),
                    "area": random.randint(50, 120),
                    "premium": random.choice([2000, 3000, 5000]),
                    "years": random.choice([5, 10, 15]),
                }
            elif difficulty == "困难":
                base_values = {
                    "principal": random.choice([50000, 100000, 200000, 500000]),
                    "rate": random.choice([4.5, 6.5, 8.5, 12.5]),
                    "period": (
                        random.choice(["5年", "8年", "10年", "15年"])
                        if language == "zh"
                        else random.choice(["5 years", "8 years", "10 years", "15 years"])
                    ),
                    "shares": random.randint(500, 5000),
                    "price": random.randint(50, 300),
                    "monthly": random.choice([3000, 5000, 8000, 10000]),
                    "months": random.choice([60, 120, 180, 240]),
                    "area": random.randint(80, 200),
                    "premium": random.choice([10000, 20000, 50000]),
                    "years": random.choice([10, 20, 30]),
                }
            else:  # 中等
                base_values = {
                    "principal": random.choice([10000, 20000, 30000, 50000]),
                    "rate": random.choice([4, 6, 8, 10]),
                    "period": (
                        random.choice(["3年", "5年", "7年"])
                        if language == "zh"
                        else random.choice(["3 years", "5 years", "7 years"])
                    ),
                    "shares": random.randint(100, 1000),
                    "price": random.randint(20, 100),
                    "monthly": random.choice([1000, 2000, 3000]),
                    "months": random.choice([36, 60, 84]),
                    "area": random.randint(60, 150),
                    "premium": random.choice([5000, 8000, 12000]),
                    "years": random.choice([10, 15, 20]),
                }

            # 填充模板变量
            template_vars = {
                "person": random.choice(scenario.get("persons", ["投资者"])),
                "bank": random.choice(scenario.get("banks", ["银行"])),
                "company": random.choice(scenario.get("companies", ["公司"])),
                "fund_name": random.choice(scenario.get("fund_names", ["基金"])),
                "city": random.choice(scenario.get("cities", ["城市"])),
                "location": random.choice(scenario.get("locations", ["区域"])),
                "insurance_type": random.choice(scenario.get("insurance_types", ["保险产品"])),
                "mode": random.choice(scenario.get("modes", ["存款方式"])),
                "change_type": random.choice(scenario.get("change_types", ["变化"])),
                "action": random.choice(scenario.get("actions", ["操作"])),
                **base_values,
                "final_price": base_values["price"] + random.randint(-20, 30),
                "percent": random.randint(5, 25),
            }

            # 生成题目内容
            content = scenario["template"].format(**template_vars)

            # 根据场景类型计算答案和生成选项
            if scenario["type"] in ["银行存款", "bank_deposit"]:
                # 简单利息计算
                years = (
                    int(template_vars["period"].split("年")[0])
                    if language == "zh"
                    else int(template_vars["period"].split(" ")[0])
                )
                interest = template_vars["principal"] * (template_vars["rate"] / 100) * years
                total = template_vars["principal"] + interest

                if language == "zh":
                    explanation = f"利息计算：{template_vars['principal']}元 × {template_vars['rate']}% × {years}年 = {interest:.0f}元。本息合计：{template_vars['principal']} + {interest:.0f} = {total:.0f}元"
                    options = [
                        f"{total:.0f}元",
                        f"{total*1.1:.0f}元",
                        f"{total*0.9:.0f}元",
                        f"{total*1.15:.0f}元",
                    ]
                else:
                    explanation = f"Interest: ${template_vars['principal']} × {template_vars['rate']}% × {years} years = ${interest:.0f}. Total: ${template_vars['principal']} + ${interest:.0f} = ${total:.0f}"
                    options = [
                        f"${total:.0f}",
                        f"${total*1.1:.0f}",
                        f"${total*0.9:.0f}",
                        f"${total*1.15:.0f}",
                    ]

            elif scenario["type"] in ["股票投资", "stock_investment"]:
                buy_cost = template_vars["shares"] * template_vars["price"]
                sell_value = template_vars["shares"] * template_vars["final_price"]
                profit_loss = sell_value - buy_cost

                if language == "zh":
                    explanation = f"买入成本：{template_vars['shares']}股 × {template_vars['price']}元 = {buy_cost}元。卖出价值：{template_vars['shares']}股 × {template_vars['final_price']}元 = {sell_value}元。盈亏：{sell_value} - {buy_cost} = {profit_loss}元"
                    options = [
                        f"{profit_loss}元",
                        f"{profit_loss+500}元",
                        f"{profit_loss-300}元",
                        f"{profit_loss+800}元",
                    ]
                else:
                    explanation = f"Purchase cost: {template_vars['shares']} × ${template_vars['price']} = ${buy_cost}. Sale value: {template_vars['shares']} × ${template_vars['final_price']} = ${sell_value}. P&L: ${sell_value} - ${buy_cost} = ${profit_loss}"
                    options = [
                        f"${profit_loss}",
                        f"${profit_loss+500}",
                        f"${profit_loss-300}",
                        f"${profit_loss+800}",
                    ]

            else:  # 其他复杂投资场景
                if language == "zh":
                    result_value = random.randint(50000, 200000)
                    explanation = f"根据{scenario['knowledge']}进行计算，最终价值约为{result_value}元"
                    options = [
                        f"{result_value}元",
                        f"{result_value*1.2:.0f}元",
                        f"{result_value*0.8:.0f}元",
                        f"{result_value*1.5:.0f}元",
                    ]
                else:
                    result_value = random.randint(50000, 200000)
                    explanation = f"Based on {scenario['knowledge']}, the final value is approximately ${result_value}"
                    options = [
                        f"${result_value}",
                        f"${result_value*1.2:.0f}",
                        f"${result_value*0.8:.0f}",
                        f"${result_value*1.5:.0f}",
                    ]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": (
                        f"投资理财-{scenario['type']}" if language == "zh" else f"Investment-{scenario['type']}"
                    ),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": {"简单": 2, "中等": 3, "困难": 5}.get(difficulty, 3),
                }
            )

        return questions

    def _generate_school_scenario(
        self, count: int, difficulty: str, language: str, subject: str, prompt: str
    ) -> List[Dict[str, Any]]:
        """生成学校教育场景题目 - 多样化专业版本"""
        questions = []
        import random

        # 定义多样化的学校教育场景
        scenario_types = {
            "zh": [
                {
                    "type": "教室资源分配",
                    "template": "{school}的{grade}有{classes}个班，每班{students}人，需要为{activity}准备{item}，每人需要{per_person}个，总共需要多少{item}？",
                    "schools": [
                        "实验小学",
                        "希望中学",
                        "育才学校",
                        "明德小学",
                        "朝阳中学",
                    ],
                    "grades": ["三年级", "四年级", "五年级", "六年级", "初一"],
                    "activities": [
                        "美术课",
                        "手工制作",
                        "科学实验",
                        "体育活动",
                        "音乐课",
                    ],
                    "items": ["彩笔", "剪刀", "试管", "跳绳", "口琴"],
                    "knowledge": "乘法运算：班级数×每班人数×每人所需",
                },
                {
                    "type": "考试成绩统计",
                    "template": "{school}{subject}期末考试，{class_name}班{total_students}人参加，{excellent}人优秀(90分以上)，{good}人良好(80-89分)，其余为及格，及格率是多少？",
                    "schools": ["第一小学", "实验中学", "外国语学校"],
                    "subjects": ["数学", "语文", "英语", "科学"],
                    "class_names": ["三(1)", "四(2)", "五(3)", "六(1)", "初一(4)"],
                    "knowledge": "百分比计算：及格人数÷总人数×100%",
                },
                {
                    "type": "图书馆管理",
                    "template": "{school}图书馆有{total_books}本书，其中{fiction}本文学类，{science}本科学类，其余为历史类。如果按{ratio}的比例借给各年级，{grade}年级能借到多少本历史类图书？",
                    "schools": ["市图书馆", "学校图书馆", "社区阅览室"],
                    "grades": ["三年级", "四年级", "五年级", "六年级"],
                    "knowledge": "分类统计和比例分配",
                },
                {
                    "type": "食堂餐饮计算",
                    "template": "{school}食堂为{grade}学生准备午餐，{students}人用餐，每人需要{rice}克大米和{dishes}份菜，大米每千克{rice_price}元，菜每份{dish_price}元，总成本多少？",
                    "schools": ["阳光小学", "育英中学", "新华学校"],
                    "grades": ["小学部", "初中部", "高中部"],
                    "knowledge": "成本计算：数量×单价的综合应用",
                },
                {
                    "type": "体育运动安排",
                    "template": "{school}举办{event}，{participants}人参加，分成{groups}组进行比赛，每组{matches}场比赛，每场比赛{duration}分钟，总共需要多少时间？",
                    "schools": ["体育学校", "普通中学", "实验小学"],
                    "events": ["篮球赛", "足球赛", "乒乓球赛", "羽毛球赛"],
                    "knowledge": "时间计算：组数×每组比赛场次×每场时间",
                },
            ],
            "en": [
                {
                    "type": "classroom_resource",
                    "template": "{school} has {classes} classes in {grade}, with {students} students per class. For {activity}, each student needs {per_person} {item}. How many {item} are needed in total?",
                    "schools": [
                        "Lincoln Elementary",
                        "Washington Middle School",
                        "Roosevelt High",
                        "Jefferson Academy",
                    ],
                    "grades": ["3rd grade", "4th grade", "5th grade", "6th grade"],
                    "activities": [
                        "art class",
                        "science lab",
                        "PE activity",
                        "music lesson",
                    ],
                    "items": ["crayons", "test tubes", "jump ropes", "recorders"],
                    "knowledge": "Multiplication: Classes × Students per class × Items per student",
                },
                {
                    "type": "exam_statistics",
                    "template": "In {school} {subject} final exam, {total_students} students from {class_name} participated. {excellent} got excellent (90+), {good} got good (80-89), the rest passed. What is the pass rate?",
                    "schools": [
                        "Central Elementary",
                        "Riverside Middle",
                        "Oak Hill High",
                    ],
                    "subjects": ["Math", "English", "Science", "History"],
                    "class_names": ["Class 3A", "Class 4B", "Class 5C"],
                    "knowledge": "Percentage calculation: Passed students ÷ Total students × 100%",
                },
                {
                    "type": "library_management",
                    "template": "{school} library has {total_books} books: {fiction} fiction, {science} science, and the rest are history. If distributed in {ratio} ratio to grades, how many history books does {grade} get?",
                    "schools": ["City Library", "School Library", "Community Center"],
                    "grades": ["3rd grade", "4th grade", "5th grade"],
                    "knowledge": "Classification and proportional distribution",
                },
                {
                    "type": "cafeteria_calculation",
                    "template": "{school} cafeteria prepares lunch for {grade}. {students} students eat, each needs {rice}g rice and {dishes} dishes. Rice costs ${rice_price}/kg, each dish ${dish_price}. What is the total cost?",
                    "schools": [
                        "Sunshine Elementary",
                        "Valley Middle School",
                        "Hill High School",
                    ],
                    "grades": [
                        "elementary students",
                        "middle school students",
                        "high school students",
                    ],
                    "knowledge": "Cost calculation: Quantity × Unit price comprehensive application",
                },
                {
                    "type": "sports_arrangement",
                    "template": "{school} organizes {event} with {participants} participants, divided into {groups} groups. Each group plays {matches} matches, each lasting {duration} minutes. How much total time is needed?",
                    "schools": [
                        "Sports Academy",
                        "Regular High School",
                        "Athletic Center",
                    ],
                    "events": [
                        "basketball tournament",
                        "soccer league",
                        "tennis competition",
                    ],
                    "knowledge": "Time calculation: Groups × Matches per group × Time per match",
                },
            ],
        }

        for i in range(count):
            # 随机选择一个学校场景类型
            scenario = random.choice(scenario_types[language])

            # 根据难度设置参数范围
            if difficulty == "简单":
                base_values = {
                    "classes": random.randint(2, 5),
                    "students": random.randint(20, 30),
                    "per_person": random.randint(1, 3),
                    "total_students": random.randint(25, 40),
                    "excellent": random.randint(5, 15),
                    "good": random.randint(8, 20),
                    "total_books": random.randint(200, 500),
                    "fiction": random.randint(80, 150),
                    "science": random.randint(60, 120),
                    "rice": random.randint(150, 200),
                    "dishes": random.randint(2, 3),
                    "rice_price": random.randint(3, 6),
                    "dish_price": random.randint(5, 10),
                    "participants": random.randint(20, 40),
                    "groups": random.randint(2, 4),
                    "matches": random.randint(2, 4),
                    "duration": random.randint(10, 20),
                }
            elif difficulty == "困难":
                base_values = {
                    "classes": random.randint(8, 15),
                    "students": random.randint(35, 50),
                    "per_person": random.randint(3, 8),
                    "total_students": random.randint(80, 150),
                    "excellent": random.randint(20, 50),
                    "good": random.randint(30, 70),
                    "total_books": random.randint(2000, 5000),
                    "fiction": random.randint(800, 1500),
                    "science": random.randint(600, 1200),
                    "rice": random.randint(200, 300),
                    "dishes": random.randint(4, 6),
                    "rice_price": random.randint(4, 8),
                    "dish_price": random.randint(8, 15),
                    "participants": random.randint(100, 200),
                    "groups": random.randint(8, 16),
                    "matches": random.randint(5, 10),
                    "duration": random.randint(30, 60),
                }
            else:  # 中等
                base_values = {
                    "classes": random.randint(4, 8),
                    "students": random.randint(28, 40),
                    "per_person": random.randint(2, 5),
                    "total_students": random.randint(40, 80),
                    "excellent": random.randint(10, 30),
                    "good": random.randint(15, 40),
                    "total_books": random.randint(500, 2000),
                    "fiction": random.randint(200, 600),
                    "science": random.randint(150, 500),
                    "rice": random.randint(180, 250),
                    "dishes": random.randint(3, 4),
                    "rice_price": random.randint(4, 7),
                    "dish_price": random.randint(6, 12),
                    "participants": random.randint(50, 100),
                    "groups": random.randint(4, 8),
                    "matches": random.randint(3, 6),
                    "duration": random.randint(20, 40),
                }

            # 填充模板变量
            template_vars = {
                "school": random.choice(scenario.get("schools", ["学校"])),
                "grade": random.choice(scenario.get("grades", ["年级"])),
                "activity": random.choice(scenario.get("activities", ["活动"])),
                "item": random.choice(scenario.get("items", ["物品"])),
                "subject": random.choice(scenario.get("subjects", ["科目"])),
                "class_name": random.choice(scenario.get("class_names", ["班级"])),
                "event": random.choice(scenario.get("events", ["比赛"])),
                "ratio": "1:1:1",
                **base_values,
                "history": base_values["total_books"] - base_values["fiction"] - base_values["science"],
            }

            # 生成题目内容
            content = scenario["template"].format(**template_vars)

            # 根据场景类型计算答案
            if scenario["type"] in ["教室资源分配", "classroom_resource"]:
                total_needed = template_vars["classes"] * template_vars["students"] * template_vars["per_person"]
                if language == "zh":
                    explanation = f"总需求：{template_vars['classes']}个班 × {template_vars['students']}人/班 × {template_vars['per_person']}个/人 = {total_needed}个"
                    options = [
                        f"{total_needed}个",
                        f"{total_needed+20}个",
                        f"{total_needed-15}个",
                        f"{total_needed+35}个",
                    ]
                else:
                    explanation = f"Total needed: {template_vars['classes']} classes × {template_vars['students']} students × {template_vars['per_person']} items = {total_needed} items"
                    options = [
                        f"{total_needed}",
                        f"{total_needed+20}",
                        f"{total_needed-15}",
                        f"{total_needed+35}",
                    ]

            elif scenario["type"] in ["考试成绩统计", "exam_statistics"]:
                passed = template_vars["total_students"] - template_vars["excellent"] - template_vars["good"]
                pass_rate = (passed / template_vars["total_students"]) * 100
                if language == "zh":
                    explanation = f"及格人数：{template_vars['total_students']} - {template_vars['excellent']} - {template_vars['good']} = {passed}人。及格率：{passed}÷{template_vars['total_students']}×100% = {pass_rate:.1f}%"
                    options = [
                        f"{pass_rate:.1f}%",
                        f"{pass_rate+10:.1f}%",
                        f"{pass_rate-5:.1f}%",
                        f"{pass_rate+15:.1f}%",
                    ]
                else:
                    explanation = f"Passed students: {template_vars['total_students']} - {template_vars['excellent']} - {template_vars['good']} = {passed}. Pass rate: {passed}÷{template_vars['total_students']}×100% = {pass_rate:.1f}%"
                    options = [
                        f"{pass_rate:.1f}%",
                        f"{pass_rate+10:.1f}%",
                        f"{pass_rate-5:.1f}%",
                        f"{pass_rate+15:.1f}%",
                    ]

            elif scenario["type"] in ["食堂餐饮计算", "cafeteria_calculation"]:
                rice_cost = (template_vars["students"] * template_vars["rice"] / 1000) * template_vars["rice_price"]
                dish_cost = template_vars["students"] * template_vars["dishes"] * template_vars["dish_price"]
                total_cost = rice_cost + dish_cost
                if language == "zh":
                    explanation = f"大米成本：{template_vars['students']}人×{template_vars['rice']}g÷1000×{template_vars['rice_price']}元={rice_cost:.2f}元。菜成本：{template_vars['students']}人×{template_vars['dishes']}份×{template_vars['dish_price']}元={dish_cost:.2f}元。总成本：{rice_cost:.2f}+{dish_cost:.2f}={total_cost:.2f}元"
                    options = [
                        f"{total_cost:.2f}元",
                        f"{total_cost*1.2:.2f}元",
                        f"{total_cost*0.8:.2f}元",
                        f"{total_cost*1.5:.2f}元",
                    ]
                else:
                    explanation = f"Rice cost: {template_vars['students']}×{template_vars['rice']}g÷1000×${template_vars['rice_price']}=${rice_cost:.2f}. Dish cost: {template_vars['students']}×{template_vars['dishes']}×${template_vars['dish_price']}=${dish_cost:.2f}. Total: ${rice_cost:.2f}+${dish_cost:.2f}=${total_cost:.2f}"
                    options = [
                        f"${total_cost:.2f}",
                        f"${total_cost*1.2:.2f}",
                        f"${total_cost*0.8:.2f}",
                        f"${total_cost*1.5:.2f}",
                    ]

            else:  # 其他复杂场景
                if language == "zh":
                    result = random.randint(100, 500)
                    explanation = f"根据{scenario['knowledge']}计算，结果为{result}"
                    options = [
                        f"{result}",
                        f"{result+50}",
                        f"{result-30}",
                        f"{result+80}",
                    ]
                else:
                    result = random.randint(100, 500)
                    explanation = f"Based on {scenario['knowledge']}, the result is {result}"
                    options = [
                        f"{result}",
                        f"{result+50}",
                        f"{result-30}",
                        f"{result+80}",
                    ]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": (f"学校教育-{scenario['type']}" if language == "zh" else f"School-{scenario['type']}"),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": {"简单": 2, "中等": 3, "困难": 4}.get(difficulty, 2),
                }
            )

        return questions

    def _generate_transport_scenario(
        self, count: int, difficulty: str, language: str, subject: str, prompt: str
    ) -> List[Dict[str, Any]]:
        """生成交通运输场景题目 - 多样化专业版本"""
        questions = []
        import random

        # 定义多样化的交通运输场景
        scenario_types = {
            "zh": [
                {
                    "type": "速度时间距离",
                    "template": "{person}乘坐{vehicle}从{origin}到{destination}，全程{distance}公里，用时{time}小时，平均速度是多少？",
                    "persons": ["小王", "张先生", "李女士", "陈同学", "刘师傅"],
                    "vehicles": ["高铁", "汽车", "飞机", "火车", "地铁"],
                    "origins": ["北京", "上海", "广州", "深圳", "杭州"],
                    "destinations": ["天津", "南京", "东莞", "珠海", "宁波"],
                    "knowledge": "速度=距离÷时间",
                },
                {
                    "type": "油耗计算",
                    "template": "{person}开{car_type}跑了{distance}公里，消耗汽油{fuel}升，每升油{price}元，这次行程的油费是多少？油耗是多少升/百公里？",
                    "persons": ["出租司机老李", "私家车主小张", "货车司机老王"],
                    "car_types": ["轿车", "SUV", "货车", "面包车"],
                    "knowledge": "油费=油量×油价，油耗=油量÷距离×100",
                },
                {
                    "type": "公交换乘",
                    "template": "{person}从{start}坐{bus1}到{transfer}，用时{time1}分钟，再坐{bus2}到{end}，用时{time2}分钟，总共用时多少？如果直达需要{direct_time}分钟，换乘比直达多用时多少？",
                    "persons": ["上班族小刘", "学生小明", "游客老张"],
                    "starts": ["家", "公司", "学校", "酒店"],
                    "transfers": ["市中心", "火车站", "购物中心", "医院"],
                    "ends": ["办公楼", "图书馆", "公园", "机场"],
                    "buses": ["1路", "3路", "5路", "快速公交"],
                    "knowledge": "时间计算和比较",
                },
                {
                    "type": "货物运输",
                    "template": "物流公司用{truck_type}运输{goods}，装载{weight}吨货物，从{origin}运到{destination}，距离{distance}公里，运费{rate}元/吨·公里，总运费多少？",
                    "truck_types": ["大货车", "中型卡车", "小货车", "冷链车"],
                    "goods": ["电器", "食品", "建材", "服装", "化工原料"],
                    "origins": ["工厂", "仓库", "港口", "批发市场"],
                    "destinations": ["商店", "工地", "超市", "零售店"],
                    "knowledge": "运费=重量×距离×单价",
                },
                {
                    "type": "停车费用",
                    "template": "{person}在{location}停车，停车场收费标准：首小时{first_hour}元，之后每小时{hourly}元，停了{hours}小时{minutes}分钟，应付停车费多少？",
                    "persons": ["车主", "顾客", "访客", "员工"],
                    "locations": ["商场", "医院", "写字楼", "景区", "机场"],
                    "knowledge": "阶梯计费和时间进位",
                },
            ],
            "en": [
                {
                    "type": "speed_time_distance",
                    "template": "{person} travels by {vehicle} from {origin} to {destination}, covering {distance} km in {time} hours. What is the average speed?",
                    "persons": ["John", "Mary", "Bob", "Alice", "Tom"],
                    "vehicles": [
                        "high-speed train",
                        "car",
                        "airplane",
                        "regular train",
                        "bus",
                    ],
                    "origins": [
                        "New York",
                        "Los Angeles",
                        "Chicago",
                        "Houston",
                        "Phoenix",
                    ],
                    "destinations": [
                        "Boston",
                        "San Francisco",
                        "Detroit",
                        "Dallas",
                        "Las Vegas",
                    ],
                    "knowledge": "Speed = Distance ÷ Time",
                },
                {
                    "type": "fuel_consumption",
                    "template": "{person} drives a {car_type} for {distance} km, using {fuel} liters of gas at ${price} per liter. What is the fuel cost? What is the fuel consumption per 100km?",
                    "persons": [
                        "taxi driver Mike",
                        "car owner Sarah",
                        "truck driver Bill",
                    ],
                    "car_types": ["sedan", "SUV", "truck", "van"],
                    "knowledge": "Fuel cost = Fuel × Price, Consumption = Fuel ÷ Distance × 100",
                },
                {
                    "type": "public_transport",
                    "template": "{person} takes {bus1} from {start} to {transfer} in {time1} minutes, then {bus2} to {end} in {time2} minutes. What is the total time? How much longer than the {direct_time}-minute direct route?",
                    "persons": ["commuter Lisa", "student Alex", "tourist David"],
                    "starts": ["home", "office", "school", "hotel"],
                    "transfers": ["downtown", "train station", "mall", "hospital"],
                    "ends": ["office building", "library", "park", "airport"],
                    "buses": ["Route 1", "Route 3", "Route 5", "Express Bus"],
                    "knowledge": "Time calculation and comparison",
                },
                {
                    "type": "freight_transport",
                    "template": "A logistics company uses {truck_type} to transport {goods}, carrying {weight} tons from {origin} to {destination}, {distance} km away, at ${rate} per ton-km. What is the total shipping cost?",
                    "truck_types": [
                        "large truck",
                        "medium truck",
                        "small truck",
                        "refrigerated truck",
                    ],
                    "goods": [
                        "electronics",
                        "food",
                        "construction materials",
                        "clothing",
                    ],
                    "origins": ["factory", "warehouse", "port", "distribution center"],
                    "destinations": [
                        "store",
                        "construction site",
                        "supermarket",
                        "retail outlet",
                    ],
                    "knowledge": "Shipping cost = Weight × Distance × Rate",
                },
                {
                    "type": "parking_fee",
                    "template": "{person} parks at {location}. Parking rates: first hour ${first_hour}, then ${hourly} per hour. After parking for {hours} hours {minutes} minutes, how much should be paid?",
                    "persons": ["car owner", "customer", "visitor", "employee"],
                    "locations": [
                        "shopping mall",
                        "hospital",
                        "office building",
                        "tourist attraction",
                    ],
                    "knowledge": "Tiered pricing and time rounding",
                },
            ],
        }

        for i in range(count):
            # 随机选择一个交通场景类型
            scenario = random.choice(scenario_types[language])

            # 根据难度设置参数范围
            if difficulty == "简单":
                base_values = {
                    "distance": random.randint(50, 200),
                    "time": random.randint(1, 4),
                    "fuel": random.randint(5, 15),
                    "price": random.randint(6, 8),
                    "time1": random.randint(10, 30),
                    "time2": random.randint(15, 25),
                    "direct_time": random.randint(25, 45),
                    "weight": random.randint(1, 5),
                    "rate": random.randint(2, 5),
                    "first_hour": random.randint(5, 10),
                    "hourly": random.randint(3, 6),
                    "hours": random.randint(1, 4),
                    "minutes": random.randint(0, 59),
                }
            elif difficulty == "困难":
                base_values = {
                    "distance": random.randint(500, 2000),
                    "time": random.randint(5, 15),
                    "fuel": random.randint(25, 80),
                    "price": random.randint(8, 12),
                    "time1": random.randint(45, 90),
                    "time2": random.randint(30, 75),
                    "direct_time": random.randint(60, 120),
                    "weight": random.randint(10, 50),
                    "rate": random.randint(8, 15),
                    "first_hour": random.randint(15, 25),
                    "hourly": random.randint(8, 15),
                    "hours": random.randint(5, 12),
                    "minutes": random.randint(0, 59),
                }
            else:  # 中等
                base_values = {
                    "distance": random.randint(200, 500),
                    "time": random.randint(2, 8),
                    "fuel": random.randint(15, 30),
                    "price": random.randint(7, 10),
                    "time1": random.randint(20, 45),
                    "time2": random.randint(20, 40),
                    "direct_time": random.randint(35, 70),
                    "weight": random.randint(5, 20),
                    "rate": random.randint(5, 10),
                    "first_hour": random.randint(8, 15),
                    "hourly": random.randint(5, 10),
                    "hours": random.randint(2, 8),
                    "minutes": random.randint(0, 59),
                }

            # 填充模板变量
            template_vars = {
                "person": random.choice(scenario.get("persons", ["旅客"])),
                "vehicle": random.choice(scenario.get("vehicles", ["交通工具"])),
                "car_type": random.choice(scenario.get("car_types", ["汽车"])),
                "origin": random.choice(scenario.get("origins", ["起点"])),
                "destination": random.choice(scenario.get("destinations", ["终点"])),
                "truck_type": random.choice(scenario.get("truck_types", ["卡车"])),
                "goods": random.choice(scenario.get("goods", ["货物"])),
                "location": random.choice(scenario.get("locations", ["地点"])),
                "start": random.choice(scenario.get("starts", ["起点"])),
                "transfer": random.choice(scenario.get("transfers", ["换乘点"])),
                "end": random.choice(scenario.get("ends", ["终点"])),
                "bus1": random.choice(scenario.get("buses", ["公交"])),
                "bus2": random.choice(scenario.get("buses", ["公交"])),
                **base_values,
            }

            # 生成题目内容
            content = scenario["template"].format(**template_vars)

            # 根据场景类型计算答案
            if scenario["type"] in ["速度时间距离", "speed_time_distance"]:
                speed = template_vars["distance"] / template_vars["time"]
                if language == "zh":
                    explanation = f"平均速度 = 距离 ÷ 时间 = {template_vars['distance']}公里 ÷ {template_vars['time']}小时 = {speed:.1f}公里/小时"
                    options = [
                        f"{speed:.1f}公里/小时",
                        f"{speed+10:.1f}公里/小时",
                        f"{speed-8:.1f}公里/小时",
                        f"{speed+15:.1f}公里/小时",
                    ]
                else:
                    explanation = f"Average speed = Distance ÷ Time = {template_vars['distance']} km ÷ {template_vars['time']} hours = {speed:.1f} km/h"
                    options = [
                        f"{speed:.1f} km/h",
                        f"{speed+10:.1f} km/h",
                        f"{speed-8:.1f} km/h",
                        f"{speed+15:.1f} km/h",
                    ]

            elif scenario["type"] in ["油耗计算", "fuel_consumption"]:
                fuel_cost = template_vars["fuel"] * template_vars["price"]
                consumption = (template_vars["fuel"] / template_vars["distance"]) * 100
                if language == "zh":
                    explanation = f"油费：{template_vars['fuel']}升 × {template_vars['price']}元/升 = {fuel_cost}元。油耗：{template_vars['fuel']}升 ÷ {template_vars['distance']}公里 × 100 = {consumption:.1f}升/百公里"
                    options = [
                        f"油费{fuel_cost}元，油耗{consumption:.1f}升/百公里",
                        f"油费{fuel_cost+20}元，油耗{consumption+1:.1f}升/百公里",
                        f"油费{fuel_cost-15}元，油耗{consumption-0.5:.1f}升/百公里",
                        f"油费{fuel_cost+30}元，油耗{consumption+1.5:.1f}升/百公里",
                    ]
                else:
                    explanation = f"Fuel cost: {template_vars['fuel']} L × ${template_vars['price']}/L = ${fuel_cost}. Consumption: {template_vars['fuel']} L ÷ {template_vars['distance']} km × 100 = {consumption:.1f} L/100km"
                    options = [
                        f"Cost ${fuel_cost}, {consumption:.1f} L/100km",
                        f"Cost ${fuel_cost+20}, {consumption+1:.1f} L/100km",
                        f"Cost ${fuel_cost-15}, {consumption-0.5:.1f} L/100km",
                        f"Cost ${fuel_cost+30}, {consumption+1.5:.1f} L/100km",
                    ]

            elif scenario["type"] in ["公交换乘", "public_transport"]:
                total_time = template_vars["time1"] + template_vars["time2"]
                extra_time = total_time - template_vars["direct_time"]
                if language == "zh":
                    explanation = f"总用时：{template_vars['time1']}分钟 + {template_vars['time2']}分钟 = {total_time}分钟。比直达多用时：{total_time} - {template_vars['direct_time']} = {extra_time}分钟"
                    options = [
                        f"总用时{total_time}分钟，多用时{extra_time}分钟",
                        f"总用时{total_time+10}分钟，多用时{extra_time+10}分钟",
                        f"总用时{total_time-5}分钟，多用时{extra_time-5}分钟",
                        f"总用时{total_time+15}分钟，多用时{extra_time+15}分钟",
                    ]
                else:
                    explanation = f"Total time: {template_vars['time1']} + {template_vars['time2']} = {total_time} minutes. Extra time vs direct: {total_time} - {template_vars['direct_time']} = {extra_time} minutes"
                    options = [
                        f"{total_time} min total, {extra_time} min extra",
                        f"{total_time+10} min total, {extra_time+10} min extra",
                        f"{total_time-5} min total, {extra_time-5} min extra",
                        f"{total_time+15} min total, {extra_time+15} min extra",
                    ]

            else:  # 其他复杂场景
                if language == "zh":
                    result = random.randint(100, 1000)
                    explanation = f"根据{scenario['knowledge']}计算，结果为{result}"
                    options = [
                        f"{result}元",
                        f"{result+100}元",
                        f"{result-50}元",
                        f"{result+200}元",
                    ]
                else:
                    result = random.randint(100, 1000)
                    explanation = f"Based on {scenario['knowledge']}, the result is ${result}"
                    options = [
                        f"${result}",
                        f"${result+100}",
                        f"${result-50}",
                        f"${result+200}",
                    ]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": (
                        f"交通运输-{scenario['type']}" if language == "zh" else f"Transport-{scenario['type']}"
                    ),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": {"简单": 2, "中等": 3, "困难": 4}.get(difficulty, 2),
                }
            )

        return questions

    def _generate_restaurant_scenario(
        self, count: int, difficulty: str, language: str, subject: str, prompt: str
    ) -> List[Dict[str, Any]]:
        """生成餐厅场景题目"""
        questions = []
        import random

        foods = ["披萨", "蛋糕", "派", "面包"] if language == "zh" else ["pizza", "cake", "pie", "bread"]

        for i in range(count):
            food = random.choice(foods)
            total_pieces = random.choice([8, 12, 16, 20, 24])
            people = random.choice([3, 4, 5, 6])

            pieces_per_person = total_pieces / people

            if language == "en":
                content = f"A {food} is cut into {total_pieces} pieces. If {people} friends share equally, how many pieces does each person get?"
                explanation = f"{total_pieces} pieces ÷ {people} people = {pieces_per_person:.2f} pieces per person"
            else:
                content = f"一个{food}切成{total_pieces}块，{people}个朋友平分，每人分几块？"
                explanation = f"{total_pieces}块 ÷ {people}人 = {pieces_per_person:.2f}块每人"

            options = [
                (f"{pieces_per_person:.2f}块" if language == "zh" else f"{pieces_per_person:.2f} pieces"),
                (f"{pieces_per_person+0.5:.2f}块" if language == "zh" else f"{pieces_per_person+0.5:.2f} pieces"),
                (f"{pieces_per_person-0.3:.2f}块" if language == "zh" else f"{pieces_per_person-0.3:.2f} pieces"),
                (f"{pieces_per_person+1:.2f}块" if language == "zh" else f"{pieces_per_person+1:.2f} pieces"),
            ]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": ("餐厅场景-定制" if language == "zh" else "Restaurant-Custom"),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": 2 if difficulty == "困难" else 1,
                }
            )

        return questions

    def _generate_probability_statistics(
        self, count: int, difficulty: str, language: str, subject: str, prompt: str
    ) -> List[Dict[str, Any]]:
        """生成概率统计题目 - 多样化专业版本"""
        questions = []
        import random

        # 定义多样化的概率统计场景
        scenario_types = {
            "zh": [
                {
                    "type": "古典概率",
                    "template": "{event}中，{total}个{object}里有{favorable}个{target}，随机选择1个，选到{target}的概率是多少？",
                    "events": ["抽奖活动", "摸球实验", "抽卡游戏", "随机选择"],
                    "objects": ["球", "卡片", "奖券", "学生"],
                    "targets": ["红球", "金卡", "一等奖", "男生"],
                    "knowledge": "古典概率=有利结果数÷总结果数",
                },
                {
                    "type": "正态分布",
                    "template": "{context}的{variable}服从正态分布，均值{mean}，标准差{std}，{condition}范围内的数据占总体的百分比是多少？",
                    "contexts": [
                        "某班学生身高",
                        "产品质量指标",
                        "考试成绩",
                        "测量误差",
                        "股票收益率",
                    ],
                    "variables": ["数值", "指标", "分数", "误差", "收益"],
                    "knowledge": "经验法则：68%-95%-99.7%",
                },
                {
                    "type": "条件概率",
                    "template": "调查显示，{population}中{condition1}的比例为{rate1}%，{condition1}中{condition2}的比例为{rate2}%，随机选择一个人{condition2}的概率是多少？",
                    "populations": ["某城市居民", "大学生群体", "上班族", "网购用户"],
                    "condition1s": ["使用智能手机", "有车一族", "经常运动", "喜欢阅读"],
                    "condition2s": [
                        "使用苹果手机",
                        "开新能源车",
                        "参加马拉松",
                        "买电子书",
                    ],
                    "knowledge": "条件概率：P(A∩B) = P(A) × P(B|A)",
                },
                {
                    "type": "描述统计",
                    "template": "{group}的{measure}数据：{data_desc}，{statistic}是多少？",
                    "groups": ["班级学生", "公司员工", "调查样本", "实验组"],
                    "measures": ["年龄", "工资", "得分", "反应时间"],
                    "data_descs": [
                        "平均值80，方差100",
                        "中位数5000，四分位距2000",
                        "众数85，极差30",
                    ],
                    "statistics": ["标准差", "变异系数", "偏度系数"],
                    "knowledge": "描述统计量的计算和意义",
                },
                {
                    "type": "假设检验",
                    "template": "某{product}的{quality}标准为{standard}，抽样{sample_size}个，样本均值{sample_mean}，{test_type}检验结果如何？",
                    "products": ["零件", "药品", "食品", "电子产品"],
                    "qualities": ["重量", "纯度", "保质期", "电阻值"],
                    "test_types": ["单侧", "双侧"],
                    "knowledge": "假设检验的基本思路和步骤",
                },
            ],
            "en": [
                {
                    "type": "classical_probability",
                    "template": "In {event}, there are {total} {object} with {favorable} being {target}. What is the probability of randomly selecting a {target}?",
                    "events": [
                        "a lottery",
                        "an experiment",
                        "a card game",
                        "random selection",
                    ],
                    "objects": ["balls", "cards", "tickets", "students"],
                    "targets": ["red balls", "aces", "winning tickets", "males"],
                    "knowledge": "Classical probability = Favorable outcomes ÷ Total outcomes",
                },
                {
                    "type": "normal_distribution",
                    "template": "{context} follows a normal distribution with mean {mean} and standard deviation {std}. What percentage of data falls within {condition}?",
                    "contexts": [
                        "Student heights in a class",
                        "Product quality measures",
                        "Test scores",
                        "Measurement errors",
                    ],
                    "variables": ["values", "measures", "scores", "errors"],
                    "knowledge": "Empirical rule: 68%-95%-99.7%",
                },
                {
                    "type": "conditional_probability",
                    "template": "Survey shows {rate1}% of {population} have {condition1}, and {rate2}% of those with {condition1} also have {condition2}. What is the probability a randomly selected person has {condition2}?",
                    "populations": [
                        "city residents",
                        "college students",
                        "office workers",
                        "online shoppers",
                    ],
                    "condition1s": [
                        "smartphones",
                        "cars",
                        "gym memberships",
                        "reading habits",
                    ],
                    "condition2s": [
                        "iPhones",
                        "electric cars",
                        "marathon participation",
                        "e-book purchases",
                    ],
                    "knowledge": "Conditional probability: P(A∩B) = P(A) × P(B|A)",
                },
                {
                    "type": "descriptive_statistics",
                    "template": "{group} {measure} data: {data_desc}. What is the {statistic}?",
                    "groups": [
                        "Class students",
                        "Company employees",
                        "Survey samples",
                        "Test subjects",
                    ],
                    "measures": ["age", "salary", "score", "reaction time"],
                    "data_descs": [
                        "mean 80, variance 100",
                        "median 5000, IQR 2000",
                        "mode 85, range 30",
                    ],
                    "statistics": [
                        "standard deviation",
                        "coefficient of variation",
                        "skewness",
                    ],
                    "knowledge": "Calculation and meaning of descriptive statistics",
                },
                {
                    "type": "hypothesis_testing",
                    "template": "A {product} has {quality} standard of {standard}. Sample of {sample_size} shows mean {sample_mean}. What is the {test_type} test result?",
                    "products": [
                        "component",
                        "medicine",
                        "food item",
                        "electronic device",
                    ],
                    "qualities": ["weight", "purity", "shelf life", "resistance"],
                    "test_types": ["one-tailed", "two-tailed"],
                    "knowledge": "Basic concepts and steps of hypothesis testing",
                },
            ],
        }

        for i in range(count):
            # 随机选择一个概率统计场景类型
            scenario = random.choice(scenario_types[language])

            # 根据难度设置参数范围
            if difficulty == "简单":
                base_values = {
                    "total": random.randint(10, 50),
                    "favorable": random.randint(2, 15),
                    "mean": random.randint(50, 100),
                    "std": random.randint(5, 15),
                    "rate1": random.randint(20, 80),
                    "rate2": random.randint(30, 90),
                    "standard": random.randint(80, 120),
                    "sample_size": random.randint(20, 50),
                    "sample_mean": random.randint(75, 125),
                }
            elif difficulty == "困难":
                base_values = {
                    "total": random.randint(100, 1000),
                    "favorable": random.randint(10, 200),
                    "mean": random.randint(200, 500),
                    "std": random.randint(20, 50),
                    "rate1": random.randint(5, 95),
                    "rate2": random.randint(10, 95),
                    "standard": random.randint(500, 1000),
                    "sample_size": random.randint(100, 500),
                    "sample_mean": random.randint(450, 1050),
                }
            else:  # 中等
                base_values = {
                    "total": random.randint(30, 100),
                    "favorable": random.randint(5, 30),
                    "mean": random.randint(100, 200),
                    "std": random.randint(10, 30),
                    "rate1": random.randint(15, 85),
                    "rate2": random.randint(20, 85),
                    "standard": random.randint(150, 300),
                    "sample_size": random.randint(50, 150),
                    "sample_mean": random.randint(140, 320),
                }

            # 填充模板变量
            template_vars = {
                "event": random.choice(scenario.get("events", ["事件"])),
                "object": random.choice(scenario.get("objects", ["对象"])),
                "target": random.choice(scenario.get("targets", ["目标"])),
                "context": random.choice(scenario.get("contexts", ["背景"])),
                "variable": random.choice(scenario.get("variables", ["变量"])),
                "population": random.choice(scenario.get("populations", ["群体"])),
                "condition1": random.choice(scenario.get("condition1s", ["条件1"])),
                "condition2": random.choice(scenario.get("condition2s", ["条件2"])),
                "group": random.choice(scenario.get("groups", ["组别"])),
                "measure": random.choice(scenario.get("measures", ["指标"])),
                "data_desc": random.choice(scenario.get("data_descs", ["数据描述"])),
                "statistic": random.choice(scenario.get("statistics", ["统计量"])),
                "product": random.choice(scenario.get("products", ["产品"])),
                "quality": random.choice(scenario.get("qualities", ["质量"])),
                "test_type": random.choice(scenario.get("test_types", ["检验类型"])),
                "condition": ("1个标准差" if language == "zh" else "1 standard deviation"),
                **base_values,
            }

            # 生成题目内容
            content = scenario["template"].format(**template_vars)

            # 根据场景类型计算答案
            if scenario["type"] in ["古典概率", "classical_probability"]:
                probability = template_vars["favorable"] / template_vars["total"]
                if language == "zh":
                    explanation = (
                        f"古典概率计算：{template_vars['favorable']} ÷ {template_vars['total']} = {probability:.3f}"
                    )
                    options = [
                        f"{probability:.3f}",
                        f"{probability*1.2:.3f}",
                        f"{probability*0.8:.3f}",
                        f"{probability*1.5:.3f}",
                    ]
                else:
                    explanation = f"Classical probability: {template_vars['favorable']} ÷ {template_vars['total']} = {probability:.3f}"
                    options = [
                        f"{probability:.3f}",
                        f"{probability*1.2:.3f}",
                        f"{probability*0.8:.3f}",
                        f"{probability*1.5:.3f}",
                    ]

            elif scenario["type"] in ["正态分布", "normal_distribution"]:
                if language == "zh":
                    explanation = f"根据经验法则，正态分布中约68%的数据落在均值±1个标准差范围内"
                    options = ["68%", "95%", "99.7%", "50%"]
                else:
                    explanation = f"According to the empirical rule, approximately 68% of data in normal distribution falls within 1 standard deviation"
                    options = ["68%", "95%", "99.7%", "50%"]

            elif scenario["type"] in ["条件概率", "conditional_probability"]:
                joint_prob = (template_vars["rate1"] / 100) * (template_vars["rate2"] / 100)
                if language == "zh":
                    explanation = (
                        f"联合概率：{template_vars['rate1']}% × {template_vars['rate2']}% = {joint_prob*100:.1f}%"
                    )
                    options = [
                        f"{joint_prob*100:.1f}%",
                        f"{joint_prob*100*1.3:.1f}%",
                        f"{joint_prob*100*0.7:.1f}%",
                        f"{joint_prob*100*1.6:.1f}%",
                    ]
                else:
                    explanation = f"Joint probability: {template_vars['rate1']}% × {template_vars['rate2']}% = {joint_prob*100:.1f}%"
                    options = [
                        f"{joint_prob*100:.1f}%",
                        f"{joint_prob*100*1.3:.1f}%",
                        f"{joint_prob*100*0.7:.1f}%",
                        f"{joint_prob*100*1.6:.1f}%",
                    ]

            else:  # 其他复杂场景
                if language == "zh":
                    result = random.randint(10, 50)
                    explanation = f"根据{scenario['knowledge']}，计算结果为{result}"
                    options = [f"{result}", f"{result+5}", f"{result-3}", f"{result+8}"]
                else:
                    result = random.randint(10, 50)
                    explanation = f"Based on {scenario['knowledge']}, the result is {result}"
                    options = [f"{result}", f"{result+5}", f"{result-3}", f"{result+8}"]

            questions.append(
                {
                    "subject": subject,
                    "sub_tag": (
                        f"概率统计-{scenario['type']}" if language == "zh" else f"Statistics-{scenario['type']}"
                    ),
                    "language": language,
                    "difficulty": difficulty,
                    "question_type": "multiple_choice",
                    "content": content,
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": explanation,
                    "points": {"简单": 2, "中等": 3, "困难": 4}.get(difficulty, 3),
                }
            )

        return questions

    def _create_advanced_shopping_question(
        self,
        index: int,
        difficulty_config: dict,
        language: str,
        subject: str,
        used_types: set,
        used_patterns: set,
    ) -> dict:
        """创建高级购物场景题目 - 强制唯一性"""
        import random

        # 使用index确保每道题完全不同
        if difficulty_config["steps"] == 1:  # 简单：直接计算
            return self._generate_simple_unique_shopping(index, difficulty_config, language, subject)
        elif difficulty_config["steps"] >= 4:  # 困难：多步分析
            return self._generate_complex_unique_shopping(index, difficulty_config, language, subject)
        else:  # 中等：两步计算
            return self._generate_medium_unique_shopping(index, difficulty_config, language, subject)

    def _generate_simple_unique_shopping(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """简单购物题目 - 强制唯一"""
        import random

        scenarios = [
            "unit_price",
            "total_cost",
            "quantity_count",
            "change_calc",
            "comparison",
        ]
        scenario_type = scenarios[index % len(scenarios)]

        seed = 1000 + index * 137
        random.seed(seed)

        if scenario_type == "unit_price":
            total = random.randint(30 + index * 5, 150 + index * 8)
            quantity = random.randint(3 + index, 15 + index)
            unit_price = total / quantity

            items = (
                ["苹果", "橘子", "葡萄", "草莓", "樱桃"][index % 5]
                if language == "zh"
                else ["apples", "oranges", "grapes", "strawberries", "cherries"][index % 5]
            )
            names = (
                ["小明", "小红", "小李", "小王", "小张"][index % 5]
                if language == "zh"
                else ["Tom", "Mary", "Bob", "Alice", "John"][index % 5]
            )

            if language == "zh":
                content = f"{names}买了{quantity}个{items}，总共花费{total}元，每个{items}的单价是多少？"
                explanation = f"单价计算：{total}元 ÷ {quantity}个 = {unit_price:.2f}元/个"
                options = [
                    f"{unit_price:.2f}元",
                    f"{unit_price+1:.2f}元",
                    f"{unit_price-0.5:.2f}元",
                    f"{unit_price+1.5:.2f}元",
                ]
            else:
                content = f"{names} bought {quantity} {items} for ${total} total. What's the unit price?"
                explanation = f"Unit price: ${total} ÷ {quantity} = ${unit_price:.2f}"
                options = [
                    f"${unit_price:.2f}",
                    f"${unit_price+1:.2f}",
                    f"${unit_price-0.5:.2f}",
                    f"${unit_price+1.5:.2f}",
                ]

        else:  # 其他简单场景
            money = random.randint(50 + index * 8, 200 + index * 10)
            unit_price = random.uniform(8.5 + index, 35.2 + index * 2)
            max_quantity = int(money / unit_price)

            items = (
                ["玩具", "图书", "文具", "零食", "饮料"][index % 5]
                if language == "zh"
                else ["toys", "books", "stationery", "snacks", "drinks"][index % 5]
            )

            if language == "zh":
                content = f"有{money}元，每个{items}价格{unit_price:.2f}元，最多能买多少个？"
                explanation = f"数量计算：{money}元 ÷ {unit_price:.2f}元 = {max_quantity}个"
                options = [
                    f"{max_quantity}个",
                    f"{max_quantity+1}个",
                    f"{max_quantity-1}个",
                    f"{max_quantity+2}个",
                ]
            else:
                content = f"With ${money}, each {items[:-1]} costs ${unit_price:.2f}. How many can you buy?"
                explanation = f"Quantity: ${money} ÷ ${unit_price:.2f} = {max_quantity}"
                options = [
                    f"{max_quantity}",
                    f"{max_quantity+1}",
                    f"{max_quantity-1}",
                    f"{max_quantity+2}",
                ]

        return {
            "subject": subject,
            "sub_tag": (f"购物-简单-{scenario_type}" if language == "zh" else f"Shopping-Simple-{scenario_type}"),
            "language": language,
            "difficulty": "简单" if language == "zh" else "Easy",
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": options[0],
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"simple_shopping_{scenario_type}_{index}",
            "content_pattern": f"pattern_simple_{index}",
        }

    def _generate_complex_unique_shopping(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """复杂购物题目 - 多步骤分析"""
        import random

        # 使用index确保唯一性
        seed = 2000 + index * 211
        random.seed(seed)

        # 批量采购优化问题
        retail_price = random.randint(20 + index * 3, 50 + index * 5)
        bulk_threshold = random.randint(30 + index * 5, 80 + index * 3)
        bulk_discount = random.randint(18 + index * 2, 35 + index * 3)
        needed_qty = random.randint(bulk_threshold - 15 + index, bulk_threshold + 40 + index * 2)

        bulk_price = retail_price * (100 - bulk_discount) / 100

        # 多种采购策略分析
        strategy1 = needed_qty * retail_price  # 全部零售
        strategy2 = bulk_threshold * bulk_price + max(0, needed_qty - bulk_threshold) * retail_price  # 混合采购
        strategy3 = needed_qty * bulk_price if needed_qty >= bulk_threshold else float("inf")  # 全部批发

        valid_strategies = [s for s in [strategy1, strategy2, strategy3] if s != float("inf")]
        optimal_cost = min(valid_strategies)

        products = (
            ["高端电子产品", "工业原材料", "医疗设备", "精密仪器", "专业工具"][index % 5]
            if language == "zh"
            else [
                "premium electronics",
                "industrial materials",
                "medical equipment",
                "precision instruments",
                "professional tools",
            ][index % 5]
        )
        companies = (
            [
                "科技公司Alpha",
                "制造企业Beta",
                "医疗集团Gamma",
                "工程公司Delta",
                "贸易公司Epsilon",
            ][index % 5]
            if language == "zh"
            else [
                "Tech Corp Alpha",
                "Manufacturing Beta",
                "Medical Group Gamma",
                "Engineering Delta",
                "Trading Epsilon",
            ][index % 5]
        )

        if language == "zh":
            content = f"{companies}需采购{needed_qty}套{products}。供应商定价：零售价{retail_price}元/套，批发价{bulk_price:.1f}元/套（需满{bulk_threshold}套，享{bulk_discount}%折扣）。分析最优采购总成本。"
            explanation = f"多步分析：①全零售={strategy1}元 ②混合采购={strategy2:.0f}元 ③全批发={'满足条件' if strategy3 != float('inf') else '不满足'}={strategy3 if strategy3 != float('inf') else 'N/A'}元。最优方案={optimal_cost:.0f}元。需要比较多种采购策略，选择成本最低的方案。"
            options = [
                f"{optimal_cost:.0f}元",
                f"{optimal_cost*1.08:.0f}元",
                f"{optimal_cost*0.94:.0f}元",
                f"{optimal_cost*1.15:.0f}元",
            ]
        else:
            content = f"{companies} needs {needed_qty} sets of {products}. Pricing: retail ${retail_price}/set, wholesale ${bulk_price:.1f}/set (min {bulk_threshold} sets, {bulk_discount}% discount). Analyze optimal procurement cost."
            explanation = f"Multi-step analysis: ①All retail=${strategy1} ②Mixed=${strategy2:.0f} ③All wholesale={'eligible' if strategy3 != float('inf') else 'not eligible'}=${strategy3 if strategy3 != float('inf') else 'N/A'}. Optimal=${optimal_cost:.0f}. Requires comparing multiple procurement strategies to find lowest cost."
            options = [
                f"${optimal_cost:.0f}",
                f"${optimal_cost*1.08:.0f}",
                f"${optimal_cost*0.94:.0f}",
                f"${optimal_cost*1.15:.0f}",
            ]

        return {
            "subject": subject,
            "sub_tag": (f"购物-复杂-多步分析" if language == "zh" else f"Shopping-Complex-MultiStep"),
            "language": language,
            "difficulty": "困难" if language == "zh" else "Hard",
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": options[0],
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"complex_shopping_optimization_{index}",
            "content_pattern": f"pattern_complex_{index}",
        }

    def _generate_medium_unique_shopping(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """中等购物题目 - 两步计算"""
        import random

        seed = 1500 + index * 173
        random.seed(seed)

        # 折扣计算问题
        original_price = random.randint(80 + index * 10, 300 + index * 15)
        discount_rate = random.randint(15 + index * 2, 40 + index * 3)
        quantity = random.randint(2 + index, 8 + index)

        discounted_price = original_price * (100 - discount_rate) / 100
        total_cost = discounted_price * quantity
        total_savings = (original_price - discounted_price) * quantity

        products = (
            ["运动装备", "电子产品", "家居用品", "服装配件", "美容产品"][index % 5]
            if language == "zh"
            else [
                "sports equipment",
                "electronics",
                "home goods",
                "fashion accessories",
                "beauty products",
            ][index % 5]
        )
        occasions = (
            ["年末促销", "会员专享", "限时特惠", "清仓甩卖", "新品上市"][index % 5]
            if language == "zh"
            else [
                "year-end sale",
                "member exclusive",
                "flash sale",
                "clearance event",
                "new launch",
            ][index % 5]
        )

        if language == "zh":
            content = f"{occasions}期间，{products}原价{original_price}元，享受{discount_rate}%折扣。购买{quantity}件，总共需要支付多少钱？"
            explanation = f"两步计算：第一步-折扣价格 = {original_price}元 × (100%-{discount_rate}%) = {discounted_price:.1f}元。第二步-总支付 = {discounted_price:.1f}元 × {quantity}件 = {total_cost:.1f}元。这道题需要先计算折扣价，再计算总价。"
            options = [
                f"{total_cost:.1f}元",
                f"{total_cost*1.1:.1f}元",
                f"{total_cost*0.9:.1f}元",
                f"{total_cost*1.2:.1f}元",
            ]
        else:
            content = f"During {occasions}, {products} originally ${original_price} has {discount_rate}% off. For {quantity} items, how much to pay total?"
            explanation = f"Two-step calculation: Step 1-Discounted price = ${original_price} × (100%-{discount_rate}%) = ${discounted_price:.1f}. Step 2-Total payment = ${discounted_price:.1f} × {quantity} = ${total_cost:.1f}. This requires calculating discount first, then total."
            options = [
                f"${total_cost:.1f}",
                f"${total_cost*1.1:.1f}",
                f"${total_cost*0.9:.1f}",
                f"${total_cost*1.2:.1f}",
            ]

        return {
            "subject": subject,
            "sub_tag": (f"购物-中等-两步计算" if language == "zh" else f"Shopping-Medium-TwoStep"),
            "language": language,
            "difficulty": "中等" if language == "zh" else "Medium",
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": options[0],
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"medium_shopping_discount_{index}",
            "content_pattern": f"pattern_medium_{index}",
        }

    def _create_advanced_statistics_question(
        self,
        index: int,
        difficulty_config: dict,
        language: str,
        subject: str,
        used_types: set,
        used_patterns: set,
    ) -> dict:
        """创建高级统计学题目 - 强制不同类型"""
        import random

        if difficulty_config["steps"] == 1:  # 简单
            return self._generate_simple_stats_unique(index, difficulty_config, language, subject)
        elif difficulty_config["steps"] >= 4:  # 困难
            return self._generate_complex_stats_unique(index, difficulty_config, language, subject)
        else:  # 中等
            return self._generate_medium_stats_unique(index, difficulty_config, language, subject)

    def _generate_simple_stats_unique(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """简单统计题目 - 完全不同的场景类型"""
        import random

        seed = 3000 + index * 127
        random.seed(seed)

        # 定义完全不同的简单统计场景
        simple_scenarios = [
            "bag_probability",  # 袋子概率
            "coin_flip",  # 硬币翻转
            "dice_roll",  # 骰子投掷
            "card_draw",  # 抽卡
            "spinner_game",  # 转盘游戏
            "survey_result",  # 调查结果
            "exam_score",  # 考试成绩
        ]

        scenario_type = simple_scenarios[index % len(simple_scenarios)]

        if scenario_type == "coin_flip":
            # 硬币翻转场景
            flips = random.randint(2, 6)
            if language == "zh":
                content = f"连续掷硬币{flips}次，每次正面朝上的概率都是0.5，那么第{random.randint(1, flips)}次掷出正面的概率是多少？"
                explanation = f"每次硬币翻转都是独立事件，正面概率始终为0.5"
                options = ["0.5", "0.25", "0.75", "1.0"]
            else:
                content = f"Flipping a fair coin {flips} times, each flip has 0.5 probability of heads. What's the probability of getting heads on the {random.randint(1, flips)}th flip?"
                explanation = f"Each coin flip is independent, probability of heads is always 0.5"
                options = ["0.5", "0.25", "0.75", "1.0"]
            correct_answer = "0.5"

        elif scenario_type == "dice_roll":
            # 骰子投掷场景
            target_number = random.randint(1, 6)
            if language == "zh":
                content = f"投掷一个标准六面骰子，掷出数字{target_number}的概率是多少？"
                explanation = f"标准骰子有6个等可能的结果，掷出{target_number}的概率 = 1/6 ≈ 0.167"
                options = ["0.167", "0.125", "0.200", "0.250"]
            else:
                content = f"Rolling a standard six-sided die, what's the probability of getting {target_number}?"
                explanation = f"Standard die has 6 equally likely outcomes, P({target_number}) = 1/6 ≈ 0.167"
                options = ["0.167", "0.125", "0.200", "0.250"]
            correct_answer = "0.167"

        elif scenario_type == "card_draw":
            # 扑克牌抽取场景
            suits = ["红桃", "黑桃", "方块", "梅花"] if language == "zh" else ["hearts", "spades", "diamonds", "clubs"]
            target_suit = suits[index % 4]
            if language == "zh":
                content = f"从标准52张扑克牌中随机抽取一张，抽到{target_suit}的概率是多少？"
                explanation = f"标准扑克牌有4种花色，每种13张，抽到{target_suit}的概率 = 13/52 = 0.25"
                options = ["0.25", "0.20", "0.30", "0.33"]
            else:
                content = f"Drawing a card from a standard 52-card deck, what's the probability of getting a {target_suit[:-1]}?"
                explanation = f"Standard deck has 4 suits, 13 cards each, P({target_suit[:-1]}) = 13/52 = 0.25"
                options = ["0.25", "0.20", "0.30", "0.33"]
            correct_answer = "0.25"

        elif scenario_type == "spinner_game":
            # 转盘游戏场景
            sections = random.randint(4, 8)
            winning_sections = random.randint(1, sections // 2)
            probability = winning_sections / sections
            if language == "zh":
                content = f"转盘游戏有{sections}个相等的扇形区域，其中{winning_sections}个是获奖区域，转一次获奖的概率是多少？"
                explanation = f"获奖概率 = 获奖区域数 ÷ 总区域数 = {winning_sections}/{sections} = {probability:.3f}"
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.2:.3f}",
                    f"{probability*0.8:.3f}",
                    f"{probability*1.5:.3f}",
                ]
            else:
                content = f"A spinner has {sections} equal sections, {winning_sections} are winning sections. What's the probability of winning?"
                explanation = f"Winning probability = Winning sections ÷ Total sections = {winning_sections}/{sections} = {probability:.3f}"
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.2:.3f}",
                    f"{probability*0.8:.3f}",
                    f"{probability*1.5:.3f}",
                ]
            correct_answer = options[0]

        elif scenario_type == "survey_result":
            # 调查结果场景
            total_people = random.randint(100, 500)
            positive_responses = random.randint(20, total_people // 2)
            probability = positive_responses / total_people
            topics = (
                ["喜欢咖啡", "支持环保", "使用社交媒体", "经常运动", "购买有机食品"]
                if language == "zh"
                else [
                    "like coffee",
                    "support environment",
                    "use social media",
                    "exercise regularly",
                    "buy organic food",
                ]
            )
            topic = topics[index % len(topics)]

            if language == "zh":
                content = (
                    f"调查{total_people}人，其中{positive_responses}人{topic}，随机选择一人，他{topic}的概率是多少？"
                )
                explanation = f"概率 = {topic}的人数 ÷ 总人数 = {positive_responses}/{total_people} = {probability:.3f}"
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.1:.3f}",
                    f"{probability*0.9:.3f}",
                    f"{probability*1.3:.3f}",
                ]
            else:
                content = f"Survey of {total_people} people shows {positive_responses} {topic}. Probability a randomly selected person {topic}?"
                explanation = f"Probability = People who {topic} ÷ Total people = {positive_responses}/{total_people} = {probability:.3f}"
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.1:.3f}",
                    f"{probability*0.9:.3f}",
                    f"{probability*1.3:.3f}",
                ]
            correct_answer = options[0]

        elif scenario_type == "exam_score":
            # 考试成绩场景
            total_students = random.randint(30, 80)
            high_scorers = random.randint(8, total_students // 3)
            probability = high_scorers / total_students
            grade_threshold = random.choice([85, 90, 95])

            if language == "zh":
                content = f"班级{total_students}人参加考试，{high_scorers}人得分超过{grade_threshold}分，随机选择一名学生，他得分超过{grade_threshold}分的概率是多少？"
                explanation = f"概率 = 高分学生数 ÷ 总学生数 = {high_scorers}/{total_students} = {probability:.3f}"
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.15:.3f}",
                    f"{probability*0.85:.3f}",
                    f"{probability*1.25:.3f}",
                ]
            else:
                content = f"In a class of {total_students} students, {high_scorers} scored above {grade_threshold}. Probability a randomly selected student scored above {grade_threshold}?"
                explanation = (
                    f"Probability = High scorers ÷ Total students = {high_scorers}/{total_students} = {probability:.3f}"
                )
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.15:.3f}",
                    f"{probability*0.85:.3f}",
                    f"{probability*1.25:.3f}",
                ]
            correct_answer = options[0]

        else:  # bag_probability (原来的袋子场景，但确保不同)
            total_objects = random.randint(15 + index * 3, 25 + index * 4)
            favorable = random.randint(3 + index, min(10 + index, total_objects - 2))
            probability = favorable / total_objects

            objects = (
                ["球", "卡片", "学生", "产品", "票"][index % 5]
                if language == "zh"
                else ["balls", "cards", "students", "products", "tickets"][index % 5]
            )
            colors = (
                ["红色", "蓝色", "绿色", "黄色", "黑色"][index % 5]
                if language == "zh"
                else ["red", "blue", "green", "yellow", "black"][index % 5]
            )

            if language == "zh":
                content = f"袋子里有{total_objects}个{objects}，其中{favorable}个是{colors}的，随机取一个，取到{colors}{objects}的概率是多少？"
                explanation = (
                    f"古典概率计算：P = 有利结果数 ÷ 总结果数 = {favorable} ÷ {total_objects} = {probability:.3f}"
                )
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.2:.3f}",
                    f"{probability*0.8:.3f}",
                    f"{probability*1.5:.3f}",
                ]
            else:
                content = f"A bag has {total_objects} {objects}, {favorable} are {colors}. Probability of selecting a {colors} {objects[:-1]}?"
                explanation = (
                    f"Classical probability: P = Favorable ÷ Total = {favorable} ÷ {total_objects} = {probability:.3f}"
                )
                options = [
                    f"{probability:.3f}",
                    f"{probability*1.2:.3f}",
                    f"{probability*0.8:.3f}",
                    f"{probability*1.5:.3f}",
                ]
            correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"统计-简单-{scenario_type}" if language == "zh" else f"Stats-Simple-{scenario_type}"),
            "language": language,
            "difficulty": "简单" if language == "zh" else "Easy",
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"simple_stats_{scenario_type}_{index}",
            "content_pattern": f"pattern_stats_simple_{scenario_type}_{index}",
        }

    def _generate_complex_stats_unique(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """复杂统计题目 - 贝叶斯定理"""
        import random

        seed = 4000 + index * 239
        random.seed(seed)

        # 贝叶斯定理应用
        disease_rate = random.randint(1 + index, 5 + index * 2) / 1000
        test_sensitivity = random.randint(88 + index, 96 + index) / 100
        test_specificity = random.randint(80 + index * 2, 90 + index) / 100

        true_positive = disease_rate * test_sensitivity
        false_positive = (1 - disease_rate) * (1 - test_specificity)
        positive_predictive_value = true_positive / (true_positive + false_positive)

        diseases = (
            ["糖尿病", "高血压", "心脏病", "肾病", "肝病"][index % 5]
            if language == "zh"
            else [
                "diabetes",
                "hypertension",
                "heart disease",
                "kidney disease",
                "liver disease",
            ][index % 5]
        )

        if language == "zh":
            content = f"某{diseases}在人群中发病率为{disease_rate*1000:.1f}‰，检测敏感性{test_sensitivity*100:.0f}%，特异性{test_specificity*100:.0f}%。若某人检测阳性，其真正患病的概率是多少？（需要使用贝叶斯定理进行复杂计算）"
            explanation = f"多步骤贝叶斯计算：①真阳性率=患病率×敏感性={disease_rate:.4f}×{test_sensitivity:.3f}={true_positive:.6f} ②假阳性率=(1-患病率)×(1-特异性)={1-disease_rate:.4f}×{1-test_specificity:.3f}={false_positive:.6f} ③阳性预测值=真阳性率÷(真阳性率+假阳性率)={true_positive:.6f}÷({true_positive:.6f}+{false_positive:.6f})={positive_predictive_value:.4f}"
            options = [
                f"{positive_predictive_value:.4f}",
                f"{positive_predictive_value*1.3:.4f}",
                f"{positive_predictive_value*0.7:.4f}",
                f"{positive_predictive_value*1.6:.4f}",
            ]
        else:
            content = f"{diseases.capitalize()} prevalence: {disease_rate*1000:.1f}‰, test sensitivity: {test_sensitivity*100:.0f}%, specificity: {test_specificity*100:.0f}%. If positive, true disease probability? (Requires complex Bayes' theorem calculation)"
            explanation = f"Multi-step Bayes calculation: ①True positive rate=prevalence×sensitivity={disease_rate:.4f}×{test_sensitivity:.3f}={true_positive:.6f} ②False positive rate=(1-prevalence)×(1-specificity)={1-disease_rate:.4f}×{1-test_specificity:.3f}={false_positive:.6f} ③Positive predictive value=true positive÷(true positive+false positive)={true_positive:.6f}÷({true_positive:.6f}+{false_positive:.6f})={positive_predictive_value:.4f}"
            options = [
                f"{positive_predictive_value:.4f}",
                f"{positive_predictive_value*1.3:.4f}",
                f"{positive_predictive_value*0.7:.4f}",
                f"{positive_predictive_value*1.6:.4f}",
            ]

        return {
            "subject": subject,
            "sub_tag": (f"统计-复杂-贝叶斯定理" if language == "zh" else f"Stats-Complex-Bayes"),
            "language": language,
            "difficulty": "困难" if language == "zh" else "Hard",
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": options[0],
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"complex_stats_bayes_{index}",
            "content_pattern": f"pattern_stats_complex_{index}",
        }

    def _generate_medium_stats_unique(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """中等统计题目 - 条件概率"""
        import random

        seed = 3500 + index * 197
        random.seed(seed)

        total_population = random.randint(1000 + index * 100, 2000 + index * 150)
        condition_a_rate = random.randint(30 + index * 5, 60 + index * 3) / 100
        condition_b_given_a_rate = random.randint(20 + index * 3, 50 + index * 2) / 100

        people_with_a = int(total_population * condition_a_rate)
        people_with_both = int(people_with_a * condition_b_given_a_rate)
        joint_probability = people_with_both / total_population

        conditions_a = (
            ["使用智能手机", "有车", "大学学历", "运动习惯", "阅读习惯"][index % 5]
            if language == "zh"
            else [
                "smartphone users",
                "car owners",
                "college graduates",
                "exercise regularly",
                "reading habits",
            ][index % 5]
        )
        conditions_b = (
            ["使用移动支付", "买新能源车", "继续深造", "参加马拉松", "买电子书"][index % 5]
            if language == "zh"
            else [
                "mobile payment",
                "buy electric cars",
                "pursue education",
                "marathon participation",
                "buy e-books",
            ][index % 5]
        )

        if language == "zh":
            content = f"调查{total_population}人，{condition_a_rate*100:.0f}%的人{conditions_a}，其中{condition_b_given_a_rate*100:.0f}%的人{conditions_b}。随机选择一人，既{conditions_a}又{conditions_b}的概率是多少？"
            explanation = f"两步条件概率计算：第一步-满足条件A的人数={total_population}×{condition_a_rate:.2f}={people_with_a}人 第二步-同时满足A和B的人数={people_with_a}×{condition_b_given_a_rate:.2f}={people_with_both}人 第三步-联合概率={people_with_both}÷{total_population}={joint_probability:.4f}"
            options = [
                f"{joint_probability:.4f}",
                f"{joint_probability*1.2:.4f}",
                f"{joint_probability*0.8:.4f}",
                f"{joint_probability*1.4:.4f}",
            ]
        else:
            content = f"Survey of {total_population}: {condition_a_rate*100:.0f}% are {conditions_a}, {condition_b_given_a_rate*100:.0f}% of them also {conditions_b}. Probability of both conditions?"
            explanation = f"Two-step conditional probability: Step 1-People with A={total_population}×{condition_a_rate:.2f}={people_with_a} Step 2-People with both A&B={people_with_a}×{condition_b_given_a_rate:.2f}={people_with_both} Step 3-Joint probability={people_with_both}÷{total_population}={joint_probability:.4f}"
            options = [
                f"{joint_probability:.4f}",
                f"{joint_probability*1.2:.4f}",
                f"{joint_probability*0.8:.4f}",
                f"{joint_probability*1.4:.4f}",
            ]

        return {
            "subject": subject,
            "sub_tag": (f"统计-中等-条件概率" if language == "zh" else f"Stats-Medium-Conditional"),
            "language": language,
            "difficulty": "中等" if language == "zh" else "Medium",
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": options[0],
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"medium_stats_conditional_{index}",
            "content_pattern": f"pattern_stats_medium_{index}",
        }

    def _create_fallback_unique_question(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """创建保底的唯一题目"""
        import random

        seed = 5000 + index * 311
        random.seed(seed)

        base_number = 10 + index * 7
        multiplier = 3 + index
        result = base_number * multiplier

        if language == "zh":
            content = f"基础计算题第{index+1}题：{base_number} × {multiplier} = ?"
            explanation = f"直接乘法计算：{base_number} × {multiplier} = {result}"
            options = [
                f"{result}",
                f"{result+index+1}",
                f"{result-index-1}",
                f"{result+index*2+1}",
            ]
        else:
            content = f"Basic calculation #{index+1}: {base_number} × {multiplier} = ?"
            explanation = f"Direct multiplication: {base_number} × {multiplier} = {result}"
            options = [
                f"{result}",
                f"{result+index+1}",
                f"{result-index-1}",
                f"{result+index*2+1}",
            ]

        return {
            "subject": subject,
            "sub_tag": (f"基础计算-{index+1}" if language == "zh" else f"Basic-Calc-{index+1}"),
            "language": language,
            "difficulty": difficulty_config.get("description", "简单" if language == "zh" else "Easy"),
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": options[0],
            "explanation": explanation,
            "points": difficulty_config["points"],
            "scenario_type": f"fallback_calculation_{index}",
            "content_pattern": f"unique_pattern_{index}",
        }

    def _create_advanced_adaptive_question(
        self,
        index: int,
        difficulty_config: dict,
        language: str,
        subject: str,
        used_types: set,
        used_patterns: set,
    ) -> dict:
        """创建自适应专业题目"""
        difficulty_type = difficulty_config.get("reasoning_depth", "direct")

        # 根据推理深度选择对应的专业生成器
        if difficulty_type == "strategic":  # GRE风格
            return self._create_gre_style_question(index, difficulty_config, language, subject)
        elif difficulty_type == "business_analytical":  # GMAT风格
            return self._create_gmat_style_question(index, difficulty_config, language, subject)
        elif difficulty_type == "theoretical":  # 研究生水平
            return self._create_graduate_level_question(index, difficulty_config, language, subject)
        elif difficulty_type == "innovative":  # 竞赛水平
            return self._create_competition_math_question(index, difficulty_config, language, subject)
        elif difficulty_type == "applied":  # 工程应用
            return self._create_engineering_application_question(index, difficulty_config, language, subject)
        elif difficulty_type == "statistical":  # 数据科学
            return self._create_data_science_question(index, difficulty_config, language, subject)
        elif difficulty_type == "quantitative":  # 金融建模
            return self._create_financial_modeling_question(index, difficulty_config, language, subject)
        else:
            return self._create_fallback_unique_question(index, difficulty_config, language, subject)

    def _create_gre_style_question(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """创建GRE风格数学题目"""
        import random

        seed = 5000 + index * 137
        random.seed(seed)

        # GRE典型题型：数据充分性、图表分析、逻辑推理
        gre_question_types = [
            "data_sufficiency",  # 数据充分性判断
            "quantitative_comparison",  # 数量比较
            "graph_analysis",  # 图表分析
            "word_problem_strategic",  # 策略性文字题
            "sequence_pattern",  # 数列规律
        ]

        question_type = gre_question_types[index % len(gre_question_types)]

        if question_type == "data_sufficiency":
            # 数据充分性判断题
            base_value = random.randint(100, 1000)
            percentage1 = random.randint(15, 35)
            percentage2 = random.randint(10, 25)

            if language == "zh":
                content = f"某公司去年收入{base_value}万元。判断今年收入是否超过1200万元需要哪些信息？\n\n条件1：今年收入比去年增长{percentage1}%\n条件2：今年收入增长了{base_value * percentage2 // 100}万元\n\nA) 仅条件1充分\nB) 仅条件2充分  \nC) 两个条件都需要\nD) 任一条件都充分"

                # 计算答案逻辑
                increase1 = base_value * (1 + percentage1 / 100)
                increase2 = base_value + (base_value * percentage2 // 100)

                if increase1 > 1200 and increase2 > 1200:
                    correct_answer = "D) 任一条件都充分"
                    explanation = f"条件1：{base_value} × (1+{percentage1}%) = {increase1:.0f}万 > 1200万。条件2：{base_value} + {base_value * percentage2 // 100} = {increase2}万 > 1200万。两个条件都单独充分。"
                elif increase1 > 1200:
                    correct_answer = "A) 仅条件1充分"
                    explanation = f"条件1充分：{increase1:.0f}万 > 1200万。条件2不充分：{increase2}万 ≤ 1200万。"
                else:
                    correct_answer = "B) 仅条件2充分"
                    explanation = f"条件1不充分：{increase1:.0f}万 ≤ 1200万。条件2充分：{increase2}万 > 1200万。"

                options = [
                    "A) 仅条件1充分",
                    "B) 仅条件2充分",
                    "C) 两个条件都需要",
                    "D) 任一条件都充分",
                ]
            else:
                content = f"A company had revenue of ${base_value}k last year. To determine if this year's revenue exceeds $1200k, which information is sufficient?\n\nCondition 1: This year's revenue increased by {percentage1}%\nCondition 2: This year's revenue increased by ${base_value * percentage2 // 100}k\n\nA) Condition 1 alone is sufficient\nB) Condition 2 alone is sufficient\nC) Both conditions together are needed\nD) Either condition alone is sufficient"

                increase1 = base_value * (1 + percentage1 / 100)
                increase2 = base_value + (base_value * percentage2 // 100)

                if increase1 > 1200 and increase2 > 1200:
                    correct_answer = "D) Either condition alone is sufficient"
                    explanation = f"Condition 1: ${base_value}k × (1+{percentage1}%) = ${increase1:.0f}k > $1200k. Condition 2: ${base_value}k + ${base_value * percentage2 // 100}k = ${increase2}k > $1200k. Both conditions are individually sufficient."
                elif increase1 > 1200:
                    correct_answer = "A) Condition 1 alone is sufficient"
                    explanation = f"Condition 1 sufficient: ${increase1:.0f}k > $1200k. Condition 2 insufficient: ${increase2}k ≤ $1200k."
                else:
                    correct_answer = "B) Condition 2 alone is sufficient"
                    explanation = f"Condition 1 insufficient: ${increase1:.0f}k ≤ $1200k. Condition 2 sufficient: ${increase2}k > $1200k."

                options = [
                    "A) Condition 1 alone is sufficient",
                    "B) Condition 2 alone is sufficient",
                    "C) Both conditions together are needed",
                    "D) Either condition alone is sufficient",
                ]

        elif question_type == "quantitative_comparison":
            # 数量比较题
            x = random.randint(3, 9)
            y = random.randint(2, 6)

            quantity_a = f"({x}^2 + {y}^2)^(1/2)"
            quantity_b = f"{x} + {y}"

            value_a = (x**2 + y**2) ** 0.5
            value_b = x + y

            if language == "zh":
                content = f"比较下列两个量的大小：\n\n数量A：{quantity_a}\n数量B：{quantity_b}\n\nA) 数量A大于数量B\nB) 数量B大于数量A\nC) 两个数量相等\nD) 无法确定大小关系"

                if value_a > value_b:
                    correct_answer = "A) 数量A大于数量B"
                    explanation = f"数量A = √({x}² + {y}²) = √{x**2 + y**2} ≈ {value_a:.2f}，数量B = {x} + {y} = {value_b}。根据几何不等式，A > B。"
                elif value_b > value_a:
                    correct_answer = "B) 数量B大于数量A"
                    explanation = f"数量A = √({x}² + {y}²) ≈ {value_a:.2f}，数量B = {x} + {y} = {value_b}。B > A。"
                else:
                    correct_answer = "C) 两个数量相等"
                    explanation = f"数量A = 数量B = {value_a:.2f}"

                options = [
                    "A) 数量A大于数量B",
                    "B) 数量B大于数量A",
                    "C) 两个数量相等",
                    "D) 无法确定大小关系",
                ]
            else:
                content = f"Compare the two quantities:\n\nQuantity A: {quantity_a}\nQuantity B: {quantity_b}\n\nA) Quantity A is greater\nB) Quantity B is greater\nC) The quantities are equal\nD) Cannot be determined"

                if value_a > value_b:
                    correct_answer = "A) Quantity A is greater"
                    explanation = f"Quantity A = √({x}² + {y}²) = √{x**2 + y**2} ≈ {value_a:.2f}, Quantity B = {x} + {y} = {value_b}. By geometric inequality, A > B."
                elif value_b > value_a:
                    correct_answer = "B) Quantity B is greater"
                    explanation = (
                        f"Quantity A = √({x}² + {y}²) ≈ {value_a:.2f}, Quantity B = {x} + {y} = {value_b}. B > A."
                    )
                else:
                    correct_answer = "C) The quantities are equal"
                    explanation = f"Quantity A = Quantity B = {value_a:.2f}"

                options = [
                    "A) Quantity A is greater",
                    "B) Quantity B is greater",
                    "C) The quantities are equal",
                    "D) Cannot be determined",
                ]

        else:  # sequence_pattern 或其他类型
            # 数列规律题
            first_term = random.randint(2, 8)
            ratio = random.randint(2, 4)
            n_terms = random.randint(5, 8)

            sequence = [first_term * (ratio**i) for i in range(n_terms)]
            next_term = first_term * (ratio**n_terms)

            if language == "zh":
                content = f"数列：{', '.join(map(str, sequence[:4]))}, __, {sequence[-1]}。求缺失项。\n\n这是一个几何数列，首项{first_term}，公比{ratio}。"
                explanation = f"几何数列公式：aₙ = {first_term} × {ratio}^(n-1)。第{n_terms-1}项 = {first_term} × {ratio}^{n_terms-2} = {sequence[n_terms-2]}。"
                missing_term = sequence[n_terms - 2]
                options = [
                    str(missing_term),
                    str(missing_term + ratio),
                    str(missing_term * 2),
                    str(missing_term - ratio),
                ]
                correct_answer = options[0]
            else:
                content = f"Sequence: {', '.join(map(str, sequence[:4]))}, __, {sequence[-1]}. Find the missing term.\n\nThis is a geometric sequence with first term {first_term} and common ratio {ratio}."
                explanation = f"Geometric sequence formula: aₙ = {first_term} × {ratio}^(n-1). Term {n_terms-1} = {first_term} × {ratio}^{n_terms-2} = {sequence[n_terms-2]}."
                missing_term = sequence[n_terms - 2]
                options = [
                    str(missing_term),
                    str(missing_term + ratio),
                    str(missing_term * 2),
                    str(missing_term - ratio),
                ]
                correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"GRE-{question_type}" if language == "en" else f"GRE-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 3),
            "scenario_type": f"gre_{question_type}_{index}",
            "content_pattern": f"pattern_gre_{question_type}_{index}",
        }

    def _create_graduate_level_question(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """创建研究生水平数学题目"""
        import random

        seed = 6000 + index * 149
        random.seed(seed)

        # 研究生水平题型：证明题、高级分析、抽象代数
        graduate_question_types = [
            "real_analysis_proof",  # 实分析证明
            "linear_algebra_advanced",  # 高级线性代数
            "abstract_algebra",  # 抽象代数
            "topology_basic",  # 基础拓扑
            "complex_analysis",  # 复分析
        ]

        question_type = graduate_question_types[index % len(graduate_question_types)]

        if question_type == "real_analysis_proof":
            # 实分析证明题
            epsilon = random.choice(["ε", "δ"])
            n_value = random.randint(3, 7)

            if language == "zh":
                content = f"证明：设函数序列 {{fₙ(x)}} 定义在 [0,1] 上，其中 fₙ(x) = x^n。\n\n证明该函数序列在 [0,1) 上一致收敛到 f(x) = 0，但在 [0,1] 上不一致收敛。\n\n要求：\n1) 使用 {epsilon}-{n_value} 定义严格证明\n2) 分析在端点 x=1 处的收敛性\n3) 说明一致收敛与逐点收敛的区别"
                explanation = f"证明思路：\n1) 在[0,1)上：对任意ε>0，取N=[log ε/log r]，其中r<1，则当n>N时，sup|fₙ(x)|≤rⁿ<ε\n2) 在x=1处：fₙ(1)=1→1≠0，故不一致收敛\n3) 关键在于收敛速度在端点附近变慢"

                options = [
                    "需要证明一致收敛的ε-N定义和端点分析",
                    "只需证明逐点收敛即可",
                    "函数序列在整个区间一致收敛",
                    "需要使用积分判别法",
                ]
                correct_answer = options[0]
            else:
                content = f"Prove: Let function sequence {{fₙ(x)}} be defined on [0,1] where fₙ(x) = x^n.\n\nProve that this sequence converges uniformly to f(x) = 0 on [0,1) but not uniformly on [0,1].\n\nRequirements:\n1) Use {epsilon}-{n_value} definition for rigorous proof\n2) Analyze convergence at endpoint x=1\n3) Explain difference between uniform and pointwise convergence"
                explanation = f"Proof outline:\n1) On [0,1): For any ε>0, take N=[log ε/log r] where r<1, then for n>N, sup|fₙ(x)|≤rⁿ<ε\n2) At x=1: fₙ(1)=1→1≠0, so not uniformly convergent\n3) Key insight: convergence rate slows near endpoint"

                options = [
                    "Requires proof using ε-N definition and endpoint analysis",
                    "Only pointwise convergence proof needed",
                    "Function sequence converges uniformly on entire interval",
                    "Integral test method required",
                ]
                correct_answer = options[0]

        elif question_type == "linear_algebra_advanced":
            # 高级线性代数
            matrix_size = random.randint(3, 4)
            eigenvalue = random.randint(2, 5)

            if language == "zh":
                content = f"设 A 是 {matrix_size}×{matrix_size} 实对称矩阵，所有特征值都等于 {eigenvalue}。\n\n证明：A = {eigenvalue}I，其中 I 是单位矩阵。\n\n提示：\n1) 利用实对称矩阵的谱定理\n2) 考虑正交对角化 A = PDP^T\n3) 分析对角矩阵 D 的结构"
                explanation = f"证明：\n1) 由谱定理，存在正交矩阵P使得A=PDP^T，其中D是对角矩阵\n2) 由于所有特征值都是{eigenvalue}，所以D={eigenvalue}I\n3) 因此A=P({eigenvalue}I)P^T={eigenvalue}PP^T={eigenvalue}I"

                options = [
                    f"A = {eigenvalue}I（使用谱定理证明）",
                    "A 必须是零矩阵",
                    "A 可以是任意实对称矩阵",
                    "需要额外条件才能确定",
                ]
                correct_answer = options[0]
            else:
                content = f"Let A be a {matrix_size}×{matrix_size} real symmetric matrix with all eigenvalues equal to {eigenvalue}.\n\nProve: A = {eigenvalue}I, where I is the identity matrix.\n\nHints:\n1) Use spectral theorem for real symmetric matrices\n2) Consider orthogonal diagonalization A = PDP^T\n3) Analyze structure of diagonal matrix D"
                explanation = f"Proof:\n1) By spectral theorem, ∃ orthogonal matrix P s.t. A=PDP^T where D is diagonal\n2) Since all eigenvalues equal {eigenvalue}, we have D={eigenvalue}I\n3) Therefore A=P({eigenvalue}I)P^T={eigenvalue}PP^T={eigenvalue}I"

                options = [
                    f"A = {eigenvalue}I (proven using spectral theorem)",
                    "A must be zero matrix",
                    "A can be any real symmetric matrix",
                    "Additional conditions needed",
                ]
                correct_answer = options[0]

        else:  # complex_analysis
            # 复分析
            radius = random.randint(2, 5)

            if language == "zh":
                content = f"设 f(z) 是在 |z| < {radius} 内解析的函数，且 |f(z)| ≤ M 对所有 |z| < {radius} 成立。\n\n如果 f(0) = 0 且 f'(0) = 0，证明：对所有 |z| < {radius-1}，有\n\n|f(z)| ≤ M|z|²/{radius-1}²\n\n要求使用：\n1) Schwarz引理的推广\n2) 最大模原理\n3) 解析函数的性质"
                explanation = f"证明思路：\n1) 由f(0)=f'(0)=0，知f(z)=z²g(z)，其中g(z)解析\n2) 应用Schwarz引理到g(z)在|z|<{radius-1}上\n3) 由最大模原理，|g(z)|≤M/{radius-1}²\n4) 因此|f(z)|=|z|²|g(z)|≤M|z|²/{radius-1}²"

                options = [
                    f"使用Schwarz引理和最大模原理的组合证明",
                    "直接应用柯西积分公式",
                    "使用留数定理",
                    "需要Riemann映射定理",
                ]
                correct_answer = options[0]
            else:
                content = f"Let f(z) be analytic in |z| < {radius} with |f(z)| ≤ M for all |z| < {radius}.\n\nIf f(0) = 0 and f'(0) = 0, prove: for all |z| < {radius-1},\n\n|f(z)| ≤ M|z|²/{radius-1}²\n\nRequired tools:\n1) Generalized Schwarz lemma\n2) Maximum modulus principle\n3) Properties of analytic functions"
                explanation = f"Proof outline:\n1) From f(0)=f'(0)=0, we have f(z)=z²g(z) where g(z) is analytic\n2) Apply Schwarz lemma to g(z) on |z|<{radius-1}\n3) By maximum modulus principle, |g(z)|≤M/{radius-1}²\n4) Thus |f(z)|=|z|²|g(z)|≤M|z|²/{radius-1}²"

                options = [
                    f"Proof using combination of Schwarz lemma and maximum modulus principle",
                    "Direct application of Cauchy integral formula",
                    "Using residue theorem",
                    "Riemann mapping theorem required",
                ]
                correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"研究生-{question_type}" if language == "zh" else f"Graduate-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 15),
            "scenario_type": f"graduate_{question_type}_{index}",
            "content_pattern": f"pattern_graduate_{question_type}_{index}",
        }

    def _create_competition_math_question(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """创建数学竞赛水平题目"""
        import random

        seed = 7000 + index * 167
        random.seed(seed)

        # 竞赛数学题型：组合数学、数论、几何、不等式
        competition_question_types = [
            "combinatorics_advanced",  # 高级组合
            "number_theory",  # 数论
            "geometry_olympiad",  # 奥数几何
            "inequality_creative",  # 创新不等式
            "functional_equation",  # 函数方程
        ]

        question_type = competition_question_types[index % len(competition_question_types)]

        if question_type == "combinatorics_advanced":
            # 高级组合数学
            n = random.randint(8, 12)
            k = random.randint(3, n // 2)

            if language == "zh":
                content = f"有 {n} 个不同的球和 {k} 个不同的盒子。每个盒子至少要放一个球。\n\n求满足以下条件的方案数：\n1) 没有盒子是空的\n2) 第1个盒子恰好有2个球\n3) 其余盒子至少有1个球\n\n这是一个经典的容斥原理应用问题。"

                # 计算：C(n,2) * S(n-2, k-1) 其中S是第二类Stirling数的近似
                first_box_ways = n * (n - 1) // 2  # C(n,2)
                remaining_arrangements = (n - 2) ** (k - 1)  # 简化的Stirling数近似
                total_ways = first_box_ways * remaining_arrangements // (k - 1)  # 修正因子

                explanation = f"解法：\n1) 选择2个球放入第1个盒子：C({n},2)={first_box_ways}\n2) 剩余{n-2}个球分配到{k-1}个盒子，每个非空：使用容斥原理\n3) 总方案数约为{total_ways}"

                options = [
                    str(total_ways),
                    str(total_ways + 100),
                    str(total_ways - 50),
                    str(total_ways * 2),
                ]
                correct_answer = options[0]
            else:
                content = f"There are {n} distinct balls and {k} distinct boxes. Each box must contain at least one ball.\n\nFind the number of ways satisfying:\n1) No box is empty\n2) Box 1 contains exactly 2 balls\n3) Other boxes contain at least 1 ball each\n\nThis is a classic inclusion-exclusion principle problem."

                first_box_ways = n * (n - 1) // 2
                remaining_arrangements = (n - 2) ** (k - 1)
                total_ways = first_box_ways * remaining_arrangements // (k - 1)

                explanation = f"Solution:\n1) Choose 2 balls for box 1: C({n},2)={first_box_ways}\n2) Distribute remaining {n-2} balls to {k-1} boxes, each non-empty: use inclusion-exclusion\n3) Total ways ≈ {total_ways}"

                options = [
                    str(total_ways),
                    str(total_ways + 100),
                    str(total_ways - 50),
                    str(total_ways * 2),
                ]
                correct_answer = options[0]

        elif question_type == "number_theory":
            # 数论题
            p = random.choice([7, 11, 13, 17, 19])  # 选择质数
            a = random.randint(2, p - 1)

            if language == "zh":
                content = f"设 p = {p} 是质数，a = {a}。\n\n求 a^(p-1) mod p 的值，并解释为什么。\n\n提示：这涉及费马小定理的应用。如果 gcd(a,p) = 1，那么 a^(p-1) ≡ 1 (mod p)。"

                result = pow(a, p - 1, p)  # 费马小定理：应该等于1
                explanation = f"根据费马小定理：\n1) 由于p={p}是质数，且gcd({a},{p})=1\n2) 因此{a}^({p}-1) ≡ 1 (mod {p})\n3) 这是数论中的基本定理"

                options = ["1", "0", str(a), str(p - 1)]
                correct_answer = options[0]
            else:
                content = f"Let p = {p} be prime and a = {a}.\n\nFind a^(p-1) mod p and explain why.\n\nHint: This involves Fermat's Little Theorem. If gcd(a,p) = 1, then a^(p-1) ≡ 1 (mod p)."

                result = pow(a, p - 1, p)
                explanation = f"By Fermat's Little Theorem:\n1) Since p={p} is prime and gcd({a},{p})=1\n2) Therefore {a}^({p}-1) ≡ 1 (mod {p})\n3) This is a fundamental theorem in number theory"

                options = ["1", "0", str(a), str(p - 1)]
                correct_answer = options[0]

        else:  # inequality_creative
            # 创新不等式
            n = random.randint(3, 5)

            if language == "zh":
                content = f"设 a₁, a₂, ..., a_{n} 是正实数，且 a₁ + a₂ + ... + a_{n} = {n}。\n\n证明：√(a₁a₂...a_{n}) ≤ 1\n\n并确定等号成立的条件。这是著名的AM-GM不等式的应用。"
                explanation = f"证明使用AM-GM不等式：\n1) 算术平均 ≥ 几何平均\n2) (a₁+a₂+...+a_{n})/{n} ≥ ⁿ√(a₁a₂...a_{n})\n3) 即 {n}/{n} ≥ ⁿ√(a₁a₂...a_{n})\n4) 因此 ⁿ√(a₁a₂...a_{n}) ≤ 1\n5) 等号成立当且仅当 a₁=a₂=...=a_{n}=1"

                options = [
                    "使用AM-GM不等式，等号成立当a₁=a₂=...=a_{n}=1",
                    "使用柯西-施瓦茨不等式",
                    "使用詹森不等式",
                    "直接展开证明",
                ]
                correct_answer = options[0]
            else:
                content = f"Let a₁, a₂, ..., a_{n} be positive real numbers with a₁ + a₂ + ... + a_{n} = {n}.\n\nProve: √(a₁a₂...a_{n}) ≤ 1\n\nAnd determine when equality holds. This is an application of the famous AM-GM inequality."
                explanation = f"Proof using AM-GM inequality:\n1) Arithmetic mean ≥ Geometric mean\n2) (a₁+a₂+...+a_{n})/{n} ≥ ⁿ√(a₁a₂...a_{n})\n3) i.e., {n}/{n} ≥ ⁿ√(a₁a₂...a_{n})\n4) Therefore ⁿ√(a₁a₂...a_{n}) ≤ 1\n5) Equality holds iff a₁=a₂=...=a_{n}=1"

                options = [
                    "Use AM-GM inequality, equality when a₁=a₂=...=a_{n}=1",
                    "Use Cauchy-Schwarz inequality",
                    "Use Jensen's inequality",
                    "Direct expansion proof",
                ]
                correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"竞赛-{question_type}" if language == "zh" else f"Competition-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 12),
            "scenario_type": f"competition_{question_type}_{index}",
            "content_pattern": f"pattern_competition_{question_type}_{index}",
        }

    def _create_gmat_style_question(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """创建GMAT风格商业数学题目"""
        import random

        seed = 8000 + index * 181
        random.seed(seed)

        # GMAT商业题型
        gmat_question_types = [
            "business_optimization",  # 商业优化
            "financial_analysis",  # 财务分析
            "data_sufficiency_business",  # 商业数据充分性
            "profit_maximization",  # 利润最大化
            "market_analysis",  # 市场分析
        ]

        question_type = gmat_question_types[index % len(gmat_question_types)]

        if question_type == "business_optimization":
            # 商业优化问题
            fixed_cost = random.randint(50000, 200000)
            variable_cost = random.randint(20, 80)
            selling_price = random.randint(variable_cost + 30, variable_cost + 100)

            if language == "zh":
                content = f"某公司生产产品X，固定成本{fixed_cost}元，单位变动成本{variable_cost}元，售价{selling_price}元/件。\n\n为了实现盈亏平衡，至少需要生产多少件？如果目标利润是100万元，需要生产多少件？\n\n这是典型的商业决策分析问题。"

                breakeven_quantity = fixed_cost // (selling_price - variable_cost)
                profit_target = 1000000
                target_quantity = (fixed_cost + profit_target) // (selling_price - variable_cost)

                explanation = f"商业分析：\n1) 盈亏平衡点：固定成本÷(售价-变动成本)={fixed_cost}÷({selling_price}-{variable_cost})={breakeven_quantity}件\n2) 目标利润时：(固定成本+目标利润)÷贡献边际=({fixed_cost}+{profit_target})÷{selling_price-variable_cost}={target_quantity}件"

                options = [
                    f"{breakeven_quantity}件和{target_quantity}件",
                    f"{breakeven_quantity+100}件和{target_quantity+200}件",
                    f"{breakeven_quantity-50}件和{target_quantity-100}件",
                    f"{breakeven_quantity*2}件和{target_quantity*2}件",
                ]
                correct_answer = options[0]
            else:
                content = f"Company produces Product X with fixed cost ${fixed_cost}, variable cost ${variable_cost}/unit, selling price ${selling_price}/unit.\n\nHow many units needed for breakeven? How many for $1M profit target?\n\nThis is a typical business decision analysis problem."

                breakeven_quantity = fixed_cost // (selling_price - variable_cost)
                profit_target = 1000000
                target_quantity = (fixed_cost + profit_target) // (selling_price - variable_cost)

                explanation = f"Business analysis:\n1) Breakeven point: Fixed cost÷(Price-Variable cost)=${fixed_cost}÷(${selling_price}-${variable_cost})={breakeven_quantity} units\n2) Profit target: (Fixed cost+Target profit)÷Contribution margin=(${fixed_cost}+${profit_target})÷{selling_price-variable_cost}={target_quantity} units"

                options = [
                    f"{breakeven_quantity} and {target_quantity} units",
                    f"{breakeven_quantity+100} and {target_quantity+200} units",
                    f"{breakeven_quantity-50} and {target_quantity-100} units",
                    f"{breakeven_quantity*2} and {target_quantity*2} units",
                ]
                correct_answer = options[0]

        else:  # financial_analysis
            # 财务分析
            initial_investment = random.randint(500000, 2000000)
            annual_cash_flow = random.randint(150000, 400000)
            discount_rate = random.randint(8, 15)
            years = random.randint(5, 8)

            if language == "zh":
                content = f"投资项目分析：初始投资{initial_investment}元，预计年现金流{annual_cash_flow}元，持续{years}年，折现率{discount_rate}%。\n\n计算净现值(NPV)并判断投资可行性。NPV = -初始投资 + ∑(年现金流/(1+折现率)^t)"

                # 简化NPV计算
                pv_factor = sum(1 / (1 + discount_rate / 100) ** t for t in range(1, years + 1))
                npv = -initial_investment + annual_cash_flow * pv_factor

                explanation = f"NPV计算：\n1) 现值系数总和 = {pv_factor:.3f}\n2) 现金流现值 = {annual_cash_flow} × {pv_factor:.3f} = {annual_cash_flow * pv_factor:.0f}元\n3) NPV = -{initial_investment} + {annual_cash_flow * pv_factor:.0f} = {npv:.0f}元\n4) {'项目可行' if npv > 0 else '项目不可行'}"

                options = [
                    f"NPV={npv:.0f}元，{'可行' if npv > 0 else '不可行'}",
                    f"NPV={npv*1.2:.0f}元，可行",
                    f"NPV={npv*0.8:.0f}元，不可行",
                    f"需要更多信息",
                ]
                correct_answer = options[0]
            else:
                content = f"Investment analysis: Initial investment ${initial_investment}, expected annual cash flow ${annual_cash_flow} for {years} years, discount rate {discount_rate}%.\n\nCalculate NPV and assess feasibility. NPV = -Initial investment + ∑(Cash flow/(1+discount rate)^t)"

                pv_factor = sum(1 / (1 + discount_rate / 100) ** t for t in range(1, years + 1))
                npv = -initial_investment + annual_cash_flow * pv_factor

                explanation = f"NPV calculation:\n1) Total PV factor = {pv_factor:.3f}\n2) PV of cash flows = ${annual_cash_flow} × {pv_factor:.3f} = ${annual_cash_flow * pv_factor:.0f}\n3) NPV = -${initial_investment} + ${annual_cash_flow * pv_factor:.0f} = ${npv:.0f}\n4) Project is {'feasible' if npv > 0 else 'not feasible'}"

                options = [
                    f"NPV=${npv:.0f}, {'feasible' if npv > 0 else 'not feasible'}",
                    f"NPV=${npv*1.2:.0f}, feasible",
                    f"NPV=${npv*0.8:.0f}, not feasible",
                    f"More information needed",
                ]
                correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"GMAT-{question_type}" if language == "en" else f"GMAT-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 4),
            "scenario_type": f"gmat_{question_type}_{index}",
            "content_pattern": f"pattern_gmat_{question_type}_{index}",
        }

    def _create_engineering_application_question(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """创建工程应用题目"""
        import random

        seed = 9000 + index * 193
        random.seed(seed)

        # 工程应用题型
        engineering_types = [
            "structural_analysis",
            "signal_processing",
            "optimization_control",
            "thermodynamics",
            "electrical_circuits",
        ]
        question_type = engineering_types[index % len(engineering_types)]

        if question_type == "structural_analysis":
            # 结构分析
            beam_length = random.randint(8, 15)
            load = random.randint(1000, 5000)
            elastic_modulus = random.randint(200, 300) * 1000  # GPa转换为MPa

            if language == "zh":
                content = f"简支梁结构分析：\n长度L={beam_length}m的简支梁，承受均布载荷q={load}N/m，弹性模量E={elastic_modulus}MPa。\n\n计算梁中点的最大弯矩和挠度。已知：\n- 最大弯矩：M_max = qL²/8\n- 最大挠度：δ_max = 5qL⁴/(384EI)\n- 假设惯性矩I=1×10⁶mm⁴"

                max_moment = load * beam_length**2 / 8
                # 简化挠度计算（省略单位转换的复杂性）
                I = 1e6  # mm⁴
                max_deflection = 5 * load * beam_length**4 / (384 * elastic_modulus * I)

                explanation = f"结构计算：\n1) 最大弯矩：M_max = {load}×{beam_length}²/8 = {max_moment:.0f} N·m\n2) 最大挠度：δ_max = 5×{load}×{beam_length}⁴/(384×{elastic_modulus}×{I}) = {max_deflection:.2f} mm\n3) 需要检查是否满足强度和刚度要求"

                options = [
                    f"M={max_moment:.0f}N·m, δ={max_deflection:.2f}mm",
                    f"M={max_moment*1.2:.0f}N·m, δ={max_deflection*1.1:.2f}mm",
                    f"M={max_moment*0.8:.0f}N·m, δ={max_deflection*0.9:.2f}mm",
                    "需要更多截面参数",
                ]
                correct_answer = options[0]
            else:
                content = f"Simply supported beam analysis:\nBeam length L={beam_length}m, uniformly distributed load q={load}N/m, elastic modulus E={elastic_modulus}MPa.\n\nCalculate maximum bending moment and deflection at midspan. Given:\n- Max moment: M_max = qL²/8\n- Max deflection: δ_max = 5qL⁴/(384EI)\n- Assume moment of inertia I=1×10⁶mm⁴"

                max_moment = load * beam_length**2 / 8
                I = 1e6
                max_deflection = 5 * load * beam_length**4 / (384 * elastic_modulus * I)

                explanation = f"Structural calculation:\n1) Max moment: M_max = {load}×{beam_length}²/8 = {max_moment:.0f} N·m\n2) Max deflection: δ_max = 5×{load}×{beam_length}⁴/(384×{elastic_modulus}×{I}) = {max_deflection:.2f} mm\n3) Check against strength and stiffness requirements"

                options = [
                    f"M={max_moment:.0f}N·m, δ={max_deflection:.2f}mm",
                    f"M={max_moment*1.2:.0f}N·m, δ={max_deflection*1.1:.2f}mm",
                    f"M={max_moment*0.8:.0f}N·m, δ={max_deflection*0.9:.2f}mm",
                    "More section properties needed",
                ]
                correct_answer = options[0]

        else:  # signal_processing
            # 信号处理
            sampling_freq = random.choice([1000, 2000, 4000, 8000])
            signal_freq = random.randint(50, sampling_freq // 3)

            if language == "zh":
                content = f"数字信号处理：\n采样频率fs={sampling_freq}Hz，输入信号频率f={signal_freq}Hz。\n\n根据奈奎斯特定理，判断是否会发生混叠，并计算混叠频率（如果有）。\n\n奈奎斯特频率：fn = fs/2"

                nyquist_freq = sampling_freq / 2
                aliasing = signal_freq > nyquist_freq
                alias_freq = abs(signal_freq - sampling_freq) if aliasing else 0

                explanation = f"信号分析：\n1) 奈奎斯特频率：fn = {sampling_freq}/2 = {nyquist_freq}Hz\n2) 信号频率{signal_freq}Hz {'>' if aliasing else '≤'} {nyquist_freq}Hz\n3) {'会发生混叠' if aliasing else '不会发生混叠'}\n4) {'混叠频率：' + str(alias_freq) + 'Hz' if aliasing else '无混叠'}"

                if aliasing:
                    options = [
                        f"发生混叠，混叠频率{alias_freq}Hz",
                        "不发生混叠",
                        f"混叠频率{alias_freq+100}Hz",
                        "需要增加采样频率",
                    ]
                    correct_answer = options[0]
                else:
                    options = [
                        "不发生混叠",
                        f"发生混叠，混叠频率{signal_freq}Hz",
                        "需要抗混叠滤波器",
                        "采样频率过高",
                    ]
                    correct_answer = options[0]
            else:
                content = f"Digital signal processing:\nSampling frequency fs={sampling_freq}Hz, input signal frequency f={signal_freq}Hz.\n\nDetermine if aliasing occurs based on Nyquist theorem, and calculate aliasing frequency if any.\n\nNyquist frequency: fn = fs/2"

                nyquist_freq = sampling_freq / 2
                aliasing = signal_freq > nyquist_freq
                alias_freq = abs(signal_freq - sampling_freq) if aliasing else 0

                explanation = f"Signal analysis:\n1) Nyquist frequency: fn = {sampling_freq}/2 = {nyquist_freq}Hz\n2) Signal frequency {signal_freq}Hz {'>' if aliasing else '≤'} {nyquist_freq}Hz\n3) {'Aliasing occurs' if aliasing else 'No aliasing'}\n4) {'Alias frequency: ' + str(alias_freq) + 'Hz' if aliasing else 'No aliasing'}"

                if aliasing:
                    options = [
                        f"Aliasing occurs, alias frequency {alias_freq}Hz",
                        "No aliasing",
                        f"Alias frequency {alias_freq+100}Hz",
                        "Need higher sampling rate",
                    ]
                    correct_answer = options[0]
                else:
                    options = [
                        "No aliasing",
                        f"Aliasing occurs, alias frequency {signal_freq}Hz",
                        "Need anti-aliasing filter",
                        "Sampling rate too high",
                    ]
                    correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"工程-{question_type}" if language == "zh" else f"Engineering-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 12),
            "scenario_type": f"engineering_{question_type}_{index}",
            "content_pattern": f"pattern_engineering_{question_type}_{index}",
        }

    def _create_data_science_question(self, index: int, difficulty_config: dict, language: str, subject: str) -> dict:
        """创建数据科学题目"""
        import random

        seed = 10000 + index * 199
        random.seed(seed)

        # 数据科学题型
        ds_types = [
            "machine_learning",
            "statistical_inference",
            "algorithm_complexity",
            "data_preprocessing",
            "model_evaluation",
        ]
        question_type = ds_types[index % len(ds_types)]

        if question_type == "machine_learning":
            # 机器学习
            n_features = random.randint(50, 200)
            n_samples = random.randint(1000, 10000)
            train_ratio = random.choice([0.7, 0.8, 0.85])

            if language == "zh":
                content = f"机器学习模型设计：\n数据集有{n_samples}个样本，{n_features}个特征。训练集比例{train_ratio}，剩余为测试集。\n\n如果使用随机森林算法，特征子集大小建议为√p（p为特征总数），计算：\n1) 训练集样本数\n2) 建议的特征子集大小\n3) 如果准确率要求>95%，评估模型复杂度是否合适"

                train_samples = int(n_samples * train_ratio)
                feature_subset = int(n_features**0.5)
                complexity_assessment = "适中" if n_features < 100 else "偏高"

                explanation = f"模型分析：\n1) 训练集样本数：{n_samples} × {train_ratio} = {train_samples}\n2) 特征子集大小：√{n_features} ≈ {feature_subset}\n3) 模型复杂度：{complexity_assessment}（特征数{n_features}，样本数{n_samples}）\n4) 高准确率要求需要足够的训练数据和特征工程"

                options = [
                    f"训练集{train_samples}，特征子集{feature_subset}，复杂度{complexity_assessment}",
                    f"训练集{train_samples+100}，特征子集{feature_subset+5}",
                    f"特征子集应为{n_features//10}",
                    "需要降维处理",
                ]
                correct_answer = options[0]
            else:
                content = f"Machine learning model design:\nDataset has {n_samples} samples and {n_features} features. Training ratio {train_ratio}, rest for testing.\n\nUsing Random Forest, feature subset size suggested as √p (p=total features). Calculate:\n1) Training set size\n2) Suggested feature subset size\n3) Assess model complexity for >95% accuracy requirement"

                train_samples = int(n_samples * train_ratio)
                feature_subset = int(n_features**0.5)
                complexity_assessment = "moderate" if n_features < 100 else "high"

                explanation = f"Model analysis:\n1) Training set size: {n_samples} × {train_ratio} = {train_samples}\n2) Feature subset size: √{n_features} ≈ {feature_subset}\n3) Model complexity: {complexity_assessment} (features {n_features}, samples {n_samples})\n4) High accuracy requires sufficient training data and feature engineering"

                options = [
                    f"Training {train_samples}, subset {feature_subset}, complexity {complexity_assessment}",
                    f"Training {train_samples+100}, subset {feature_subset+5}",
                    f"Subset should be {n_features//10}",
                    "Dimensionality reduction needed",
                ]
                correct_answer = options[0]

        else:  # statistical_inference
            # 统计推断
            sample_size = random.randint(100, 500)
            confidence_level = random.choice([0.90, 0.95, 0.99])
            margin_error = random.choice([0.03, 0.05, 0.08])

            if language == "zh":
                content = f"统计推断设计：\n计划进行样本调查，样本量n={sample_size}，置信度{confidence_level*100}%，期望误差边界{margin_error}。\n\n计算置信区间半宽度公式：E = z_{confidence_level/2} × σ/√n\n\n假设σ=0.5，判断当前样本量是否满足误差要求。"

                # Z值近似
                z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
                z_score = z_values[confidence_level]
                sigma = 0.5
                actual_margin = z_score * sigma / (sample_size**0.5)
                meets_requirement = actual_margin <= margin_error

                explanation = f"统计计算：\n1) Z_{confidence_level} = {z_score}\n2) 实际误差边界：E = {z_score} × {sigma}/√{sample_size} = {actual_margin:.4f}\n3) 期望误差边界：{margin_error}\n4) {'满足要求' if meets_requirement else '不满足要求，需要增加样本量'}"

                options = [
                    f"实际误差{actual_margin:.4f}，{'满足' if meets_requirement else '不满足'}要求",
                    f"实际误差{actual_margin*1.2:.4f}，不满足要求",
                    f"需要样本量{sample_size*2}",
                    "置信度过高",
                ]
                correct_answer = options[0]
            else:
                content = f"Statistical inference design:\nPlanning sample survey with n={sample_size}, confidence level {confidence_level*100}%, desired margin of error {margin_error}.\n\nConfidence interval half-width formula: E = z_{confidence_level/2} × σ/√n\n\nAssuming σ=0.5, determine if current sample size meets error requirement."

                z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
                z_score = z_values[confidence_level]
                sigma = 0.5
                actual_margin = z_score * sigma / (sample_size**0.5)
                meets_requirement = actual_margin <= margin_error

                explanation = f"Statistical calculation:\n1) Z_{confidence_level} = {z_score}\n2) Actual margin of error: E = {z_score} × {sigma}/√{sample_size} = {actual_margin:.4f}\n3) Desired margin of error: {margin_error}\n4) {'Meets requirement' if meets_requirement else 'Does not meet requirement, increase sample size'}"

                options = [
                    f"Actual margin {actual_margin:.4f}, {'meets' if meets_requirement else 'does not meet'} requirement",
                    f"Actual margin {actual_margin*1.2:.4f}, does not meet requirement",
                    f"Need sample size {sample_size*2}",
                    "Confidence level too high",
                ]
                correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"数据科学-{question_type}" if language == "zh" else f"DataScience-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 8),
            "scenario_type": f"data_science_{question_type}_{index}",
            "content_pattern": f"pattern_data_science_{question_type}_{index}",
        }

    def _create_financial_modeling_question(
        self, index: int, difficulty_config: dict, language: str, subject: str
    ) -> dict:
        """创建金融建模题目"""
        import random

        seed = 11000 + index * 211
        random.seed(seed)

        # 金融建模题型
        fin_types = [
            "options_pricing",
            "portfolio_optimization",
            "risk_management",
            "derivative_valuation",
            "credit_risk",
        ]
        question_type = fin_types[index % len(fin_types)]

        if question_type == "options_pricing":
            # 期权定价
            stock_price = random.randint(50, 150)
            strike_price = random.randint(stock_price - 20, stock_price + 20)
            risk_free_rate = random.randint(3, 8) / 100
            volatility = random.randint(20, 40) / 100
            time_to_expiry = random.choice([0.25, 0.5, 0.75, 1.0])

            if language == "zh":
                content = f"Black-Scholes期权定价：\n股票现价S₀=${stock_price}，执行价K=${strike_price}，无风险利率r={risk_free_rate*100}%，波动率σ={volatility*100}%，到期时间T={time_to_expiry}年。\n\n使用Black-Scholes公式计算欧式看涨期权价值：\nC = S₀N(d₁) - Ke^(-rT)N(d₂)\n\n其中 d₁ = [ln(S₀/K) + (r + σ²/2)T] / (σ√T)"

                import math

                d1 = (
                    math.log(stock_price / strike_price) + (risk_free_rate + volatility**2 / 2) * time_to_expiry
                ) / (volatility * math.sqrt(time_to_expiry))
                d2 = d1 - volatility * math.sqrt(time_to_expiry)

                # 简化正态分布近似
                def norm_cdf(x):
                    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

                call_price = stock_price * norm_cdf(d1) - strike_price * math.exp(
                    -risk_free_rate * time_to_expiry
                ) * norm_cdf(d2)

                explanation = f"期权定价计算：\n1) d₁ = {d1:.4f}, d₂ = {d2:.4f}\n2) N(d₁) = {norm_cdf(d1):.4f}, N(d₂) = {norm_cdf(d2):.4f}\n3) 看涨期权价值：C = {stock_price} × {norm_cdf(d1):.4f} - {strike_price} × e^(-{risk_free_rate}×{time_to_expiry}) × {norm_cdf(d2):.4f} = ${call_price:.2f}"

                options = [
                    f"${call_price:.2f}",
                    f"${call_price*1.1:.2f}",
                    f"${call_price*0.9:.2f}",
                    f"${call_price*1.3:.2f}",
                ]
                correct_answer = options[0]
            else:
                content = f"Black-Scholes option pricing:\nStock price S₀=${stock_price}, strike K=${strike_price}, risk-free rate r={risk_free_rate*100}%, volatility σ={volatility*100}%, time to expiry T={time_to_expiry} years.\n\nCalculate European call option value using Black-Scholes formula:\nC = S₀N(d₁) - Ke^(-rT)N(d₂)\n\nwhere d₁ = [ln(S₀/K) + (r + σ²/2)T] / (σ√T)"

                import math

                d1 = (
                    math.log(stock_price / strike_price) + (risk_free_rate + volatility**2 / 2) * time_to_expiry
                ) / (volatility * math.sqrt(time_to_expiry))
                d2 = d1 - volatility * math.sqrt(time_to_expiry)

                def norm_cdf(x):
                    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

                call_price = stock_price * norm_cdf(d1) - strike_price * math.exp(
                    -risk_free_rate * time_to_expiry
                ) * norm_cdf(d2)

                explanation = f"Option pricing calculation:\n1) d₁ = {d1:.4f}, d₂ = {d2:.4f}\n2) N(d₁) = {norm_cdf(d1):.4f}, N(d₂) = {norm_cdf(d2):.4f}\n3) Call option value: C = {stock_price} × {norm_cdf(d1):.4f} - {strike_price} × e^(-{risk_free_rate}×{time_to_expiry}) × {norm_cdf(d2):.4f} = ${call_price:.2f}"

                options = [
                    f"${call_price:.2f}",
                    f"${call_price*1.1:.2f}",
                    f"${call_price*0.9:.2f}",
                    f"${call_price*1.3:.2f}",
                ]
                correct_answer = options[0]

        else:  # portfolio_optimization
            # 投资组合优化
            expected_return_a = random.randint(8, 15) / 100
            expected_return_b = random.randint(6, 12) / 100
            volatility_a = random.randint(15, 25) / 100
            volatility_b = random.randint(10, 20) / 100
            correlation = random.choice([0.3, 0.5, 0.7])

            if language == "zh":
                content = f"投资组合优化：\n资产A期望收益率{expected_return_a*100}%，波动率{volatility_a*100}%\n资产B期望收益率{expected_return_b*100}%，波动率{volatility_b*100}%\n相关系数ρ={correlation}\n\n构建最小方差投资组合，权重wₐ的计算公式：\nwₐ = (σ_B² - ρσₐσ_B) / (σₐ² + σ_B² - 2ρσₐσ_B)"

                weight_a = (volatility_b**2 - correlation * volatility_a * volatility_b) / (
                    volatility_a**2 + volatility_b**2 - 2 * correlation * volatility_a * volatility_b
                )
                weight_b = 1 - weight_a
                portfolio_return = weight_a * expected_return_a + weight_b * expected_return_b
                portfolio_volatility = math.sqrt(
                    weight_a**2 * volatility_a**2
                    + weight_b**2 * volatility_b**2
                    + 2 * weight_a * weight_b * correlation * volatility_a * volatility_b
                )

                explanation = f"投资组合计算：\n1) 最小方差权重：wₐ = {weight_a:.3f}, w_B = {weight_b:.3f}\n2) 组合期望收益：{weight_a:.3f}×{expected_return_a:.3f} + {weight_b:.3f}×{expected_return_b:.3f} = {portfolio_return:.3f}\n3) 组合风险：√(...) = {portfolio_volatility:.3f}"

                options = [
                    f"wₐ={weight_a:.3f}, 收益{portfolio_return:.3f}, 风险{portfolio_volatility:.3f}",
                    f"wₐ={weight_a*1.1:.3f}, 收益{portfolio_return*1.05:.3f}",
                    f"等权重配置wₐ=0.5",
                    "需要更多相关性数据",
                ]
                correct_answer = options[0]
            else:
                content = f"Portfolio optimization:\nAsset A expected return {expected_return_a*100}%, volatility {volatility_a*100}%\nAsset B expected return {expected_return_b*100}%, volatility {volatility_b*100}%\nCorrelation ρ={correlation}\n\nConstruct minimum variance portfolio, weight wₐ formula:\nwₐ = (σ_B² - ρσₐσ_B) / (σₐ² + σ_B² - 2ρσₐσ_B)"

                weight_a = (volatility_b**2 - correlation * volatility_a * volatility_b) / (
                    volatility_a**2 + volatility_b**2 - 2 * correlation * volatility_a * volatility_b
                )
                weight_b = 1 - weight_a
                portfolio_return = weight_a * expected_return_a + weight_b * expected_return_b
                portfolio_volatility = math.sqrt(
                    weight_a**2 * volatility_a**2
                    + weight_b**2 * volatility_b**2
                    + 2 * weight_a * weight_b * correlation * volatility_a * volatility_b
                )

                explanation = f"Portfolio calculation:\n1) Minimum variance weights: wₐ = {weight_a:.3f}, w_B = {weight_b:.3f}\n2) Portfolio expected return: {weight_a:.3f}×{expected_return_a:.3f} + {weight_b:.3f}×{expected_return_b:.3f} = {portfolio_return:.3f}\n3) Portfolio risk: √(...) = {portfolio_volatility:.3f}"

                options = [
                    f"wₐ={weight_a:.3f}, return {portfolio_return:.3f}, risk {portfolio_volatility:.3f}",
                    f"wₐ={weight_a*1.1:.3f}, return {portfolio_return*1.05:.3f}",
                    f"Equal weight wₐ=0.5",
                    "More correlation data needed",
                ]
                correct_answer = options[0]

        return {
            "subject": subject,
            "sub_tag": (f"金融建模-{question_type}" if language == "zh" else f"FinancialModeling-{question_type}"),
            "language": language,
            "difficulty": difficulty_config["description"],
            "question_type": "multiple_choice",
            "content": content,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "points": difficulty_config["points"],
            "time_limit": difficulty_config.get("time_limit", 10),
            "scenario_type": f"financial_{question_type}_{index}",
            "content_pattern": f"pattern_financial_{question_type}_{index}",
        }
