#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能题目生成器 - 完全基于AI参数驱动，摆脱预设框架限制
"""

import hashlib
import json
import os
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import requests


# 导入枚举类
class DifficultyLevel(Enum):
    HIGH_SCHOOL = "high_school"
    UNDERGRADUATE_BASIC = "undergraduate_basic"
    UNDERGRADUATE_ADVANCED = "undergraduate_advanced"
    GRE_LEVEL = "gre_level"
    GRADUATE_STUDY = "graduate_study"
    DOCTORAL_RESEARCH = "doctoral_research"


class QuestionType(Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    PROGRAMMING = "programming"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    ESSAY = "essay"


class Language(Enum):
    CHINESE = "zh"
    ENGLISH = "en"


@dataclass
class GenerationConfig:
    subject: str
    sub_domain: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.UNDERGRADUATE_BASIC
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    language: Language = Language.CHINESE
    use_scenarios: bool = False
    custom_prompt: str = ""
    count: int = 5
    points_per_question: int = 1


class SmartQuestionGenerator:
    """智能题目生成器 - 完全基于AI参数驱动"""

    def __init__(self):
        # 使用新的API管理器
        try:
            print("🔧 初始化智能题目生成器...")
            from .api_manager import ApiManager

            self.api_manager = ApiManager()
            print("✅ API管理器创建成功")

            # 生成历史和去重
            self.generated_signatures = set()

            print("🔧 智能题目生成器初始化完成")

            # 强制重新加载API配置
            try:
                print("🔄 重新加载API配置...")
                self.api_manager._load_api_configs()
                print("✅ API配置重新加载完成")
            except Exception as load_error:
                print(f"⚠️ 重新加载API配置失败: {str(load_error)}")
                # 不抛出异常，继续初始化

            api_status = self.get_api_status()
            print(f"📡 API状态: {api_status}")

            if api_status["available"]:
                print(f"🤖 当前提供商: {api_status['provider']}")
                print(f"🎯 默认模型: {api_status['model']}")
            else:
                print(f"⚠️ {api_status['message']}")

        except Exception as init_error:
            print(f"❌ 智能题目生成器初始化失败: {str(init_error)}")
            import traceback

            traceback.print_exc()
            raise

    def has_valid_api(self) -> bool:
        """检查是否有有效的API配置"""
        return self.api_manager.has_valid_api()

    def get_api_status(self) -> dict:
        """获取API状态信息"""
        if self.api_manager.has_valid_api():
            config = self.api_manager.get_current_config()
            return {
                "available": True,
                "provider": config.provider.value,
                "model": config.default_model,
                "message": f"使用 {config.provider.value} API",
            }
        else:
            return {
                "available": False,
                "provider": None,
                "model": None,
                "message": "未配置有效的API，无法使用AI生题功能",
            }

    def _init_difficulty_configs(self):
        """初始化难度级别配置"""
        if hasattr(self, "difficulty_configs"):
            return

        # 难度级别详细配置
        self.difficulty_configs = {
            DifficultyLevel.HIGH_SCHOOL: {
                "name_zh": "高中水平",
                "name_en": "High School Level",
                "time_limit_minutes": 3,
                "points": 1,
            },
            DifficultyLevel.UNDERGRADUATE_BASIC: {
                "name_zh": "本科基础",
                "name_en": "Undergraduate Basic",
                "time_limit_minutes": 5,
                "points": 2,
            },
            DifficultyLevel.UNDERGRADUATE_ADVANCED: {
                "name_zh": "本科高级",
                "name_en": "Undergraduate Advanced",
                "time_limit_minutes": 8,
                "points": 3,
            },
            DifficultyLevel.GRE_LEVEL: {
                "name_zh": "GRE难度",
                "name_en": "GRE Level",
                "time_limit_minutes": 4,
                "points": 4,
            },
            DifficultyLevel.GRADUATE_STUDY: {
                "name_zh": "研究生水平",
                "name_en": "Graduate Study Level",
                "time_limit_minutes": 15,
                "points": 5,
            },
            DifficultyLevel.DOCTORAL_RESEARCH: {
                "name_zh": "博士研究",
                "name_en": "Doctoral Research",
                "time_limit_minutes": 25,
                "points": 8,
            },
        }

    def generate_questions(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """生成题目主入口"""
        # 确保难度配置已初始化
        self._init_difficulty_configs()

        print(
            f"🎯 开始生成题目 - 学科: {config.subject}, 难度: {config.difficulty.value}, 数量: {config.count}"
        )

        questions = []
        failed_attempts = 0
        max_failed_attempts = config.count * 2  # 允许失败次数为目标数量的2倍

        for i in range(config.count):
            success = False
            retry_count = 0
            max_retries = 3

            while (
                not success
                and retry_count < max_retries
                and failed_attempts < max_failed_attempts
            ):
                try:
                    question = self._generate_ai_driven_question(
                        config, i + retry_count
                    )
                    if question and self._validate_question(question):
                        questions.append(question)
                        print(f"✅ 成功生成第 {i+1} 道题目")
                        success = True
                    else:
                        retry_count += 1
                        failed_attempts += 1
                        print(
                            f"⚠️  第 {i+1} 道题目生成失败，重试 {retry_count}/{max_retries}"
                        )
                except Exception as e:
                    retry_count += 1
                    failed_attempts += 1
                    print(
                        f"❌ 第 {i+1} 道题目生成异常 (重试 {retry_count}/{max_retries}): {str(e)}"
                    )

            if not success:
                print(f"❌ 第 {i+1} 道题目最终生成失败")

        print(
            f"🎉 完成生成，共 {len(questions)} 道有效题目，失败 {failed_attempts} 次尝试"
        )
        return questions

    def _generate_ai_driven_question(
        self, config: GenerationConfig, index: int
    ) -> Optional[Dict[str, Any]]:
        """完全基于AI参数驱动的题目生成"""
        try:
            # 构建详细的AI提示词
            difficulty_config = self.difficulty_configs[config.difficulty]

            # 难度级别描述
            difficulty_descriptions = {
                "zh": {
                    DifficultyLevel.HIGH_SCHOOL: "高中水平 - 基础概念和简单应用",
                    DifficultyLevel.UNDERGRADUATE_BASIC: "本科基础 - 理论理解和标准应用",
                    DifficultyLevel.UNDERGRADUATE_ADVANCED: "本科高级 - 复杂理论和综合应用",
                    DifficultyLevel.GRE_LEVEL: "GRE水平 - 标准化考试推理和分析",
                    DifficultyLevel.GRADUATE_STUDY: "研究生水平 - 高级理论和研究方法",
                    DifficultyLevel.DOCTORAL_RESEARCH: "博士研究 - 前沿理论和创新研究",
                },
                "en": {
                    DifficultyLevel.HIGH_SCHOOL: "High School Level - Basic concepts and simple applications",
                    DifficultyLevel.UNDERGRADUATE_BASIC: "Undergraduate Basic - Theoretical understanding and standard applications",
                    DifficultyLevel.UNDERGRADUATE_ADVANCED: "Undergraduate Advanced - Complex theories and comprehensive applications",
                    DifficultyLevel.GRE_LEVEL: "GRE Level - Standardized test reasoning and analysis",
                    DifficultyLevel.GRADUATE_STUDY: "Graduate Level - Advanced theories and research methods",
                    DifficultyLevel.DOCTORAL_RESEARCH: "Doctoral Research - Cutting-edge theories and innovative research",
                },
            }

            # 题目类型描述
            question_type_descriptions = {
                "zh": {
                    QuestionType.MULTIPLE_CHOICE: "选择题 - 4个选项，1个正确答案",
                    QuestionType.SHORT_ANSWER: "简答题 - 简短文字回答",
                    QuestionType.PROGRAMMING: "编程题 - 代码实现",
                    QuestionType.TRUE_FALSE: "判断题 - 正确或错误",
                    QuestionType.FILL_BLANK: "填空题 - 填入关键词或数值",
                    QuestionType.ESSAY: "论述题 - 详细分析和论证",
                },
                "en": {
                    QuestionType.MULTIPLE_CHOICE: "Multiple Choice - 4 options with 1 correct answer",
                    QuestionType.SHORT_ANSWER: "Short Answer - Brief text response",
                    QuestionType.PROGRAMMING: "Programming - Code implementation",
                    QuestionType.TRUE_FALSE: "True/False - Correct or incorrect",
                    QuestionType.FILL_BLANK: "Fill in the Blank - Keywords or numerical values",
                    QuestionType.ESSAY: "Essay - Detailed analysis and argumentation",
                },
            }

            # 构建AI提示词
            if config.language == Language.CHINESE:
                prompt = f"""
请生成一道高质量的考试题目，要求如下：

【基本信息】
- 学科：{config.subject}
- 子领域：{config.sub_domain or "任意子领域"}
- 难度：{difficulty_descriptions["zh"][config.difficulty]}
- 题型：{question_type_descriptions["zh"][config.question_type]}
- 语言：中文
- 分值：{config.points_per_question}分

【内容要求】
1. 题目必须完全原创，避免常见的模板化内容
2. 难度必须严格符合指定级别，体现相应的认知复杂度
3. 内容要准确、专业，符合学科规范
4. 如果是选择题，干扰项要合理且具有迷惑性
5. **数学公式必须使用LaTeX格式**：行内公式用$公式$，行间公式用$$公式$$
   - 例如：函数$f(x) = x^2 + 3x - 1$，积分$\\int_0^1 x^2 dx$，分数$\\frac{{a}}{{b}}$
   - 复杂公式：$$\\lim_{{x \\to 0}} \\frac{{\\sin x}}{{x}} = 1$$

【场景要求】
{f"请基于真实应用场景出题，提供丰富的背景环境描述，让题目具有实际意义和应用价值。" if config.use_scenarios else "可以是纯理论题目，重点考查概念理解和计算能力。"}

【自定义要求】
{config.custom_prompt if config.custom_prompt else "无特殊要求"}

【创新性要求】
- 避免使用常见的数值组合和标准例题
- 尝试结合当前学科发展趋势和实际应用
- 题目应该具有一定的思维挑战性
- 每道题目都应该是独特的，不重复已有模式

请严格按照以下JSON格式返回：
{{
    "content": "题目内容（详细完整）",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correct_answer": "正确答案",
    "explanation": "详细解析（包含解题步骤和原理说明）",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "difficulty_justification": "为什么这道题符合指定难度级别的说明",
    "innovation_aspects": "这道题的创新点和独特性"
}}
"""
            else:
                prompt = f"""
Please generate a high-quality exam question with the following requirements:

【Basic Information】
- Subject: {config.subject}
- Sub-domain: {config.sub_domain or "Any sub-domain"}
- Difficulty: {difficulty_descriptions["en"][config.difficulty]}
- Question Type: {question_type_descriptions["en"][config.question_type]}
- Language: English
- Points: {config.points_per_question}

【Content Requirements】
1. Question must be completely original, avoiding common template content
2. Difficulty must strictly match the specified level, reflecting appropriate cognitive complexity
3. Content must be accurate, professional, and conform to disciplinary standards
4. For multiple choice, distractors should be reasonable and misleading
5. **Mathematical formulas must use LaTeX format**: inline formulas use $formula$, display formulas use $$formula$$
   - Examples: function $f(x) = x^2 + 3x - 1$, integral $\\int_0^1 x^2 dx$, fraction $\\frac{{a}}{{b}}$
   - Complex formulas: $$\\lim_{{x \\to 0}} \\frac{{\\sin x}}{{x}} = 1$$

【Scenario Requirements】
{f"Please create questions based on real-world application scenarios, providing rich background context to make questions practically meaningful and valuable." if config.use_scenarios else "Can be purely theoretical questions, focusing on concept understanding and computational ability."}

【Custom Requirements】
{config.custom_prompt if config.custom_prompt else "No special requirements"}

【Innovation Requirements】
- Avoid common numerical combinations and standard examples
- Try to incorporate current disciplinary trends and practical applications
- Questions should have intellectual challenge
- Each question should be unique, not repeating existing patterns

Please return strictly in the following JSON format:
{{
    "content": "Question content (detailed and complete)",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Correct answer",
    "explanation": "Detailed explanation (including solution steps and principle explanation)",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "difficulty_justification": "Explanation of why this question matches the specified difficulty level",
    "innovation_aspects": "Innovation points and uniqueness of this question"
}}
"""

            # 调用AI API
            print(f"🤖 构建的AI提示词长度: {len(prompt)} 字符")
            print(f"📝 提示词预览: {prompt[:200]}...")

            ai_response = self._call_ai_api(prompt)

            # 如果API调用失败，抛出异常而不是使用模拟响应
            if not ai_response:
                if not self.api_manager.has_valid_api():
                    raise Exception("未配置有效的API，请前往系统设置配置API密钥")
                else:
                    raise Exception("API调用失败，请检查网络连接和API配置")

            if ai_response and "content" in ai_response:
                # 补充必要字段
                return {
                    "subject": config.subject,
                    "sub_tag": config.sub_domain
                    or f"{config.subject}-{config.difficulty.value}",
                    "language": config.language.value,
                    "difficulty": (
                        difficulty_config["name_zh"]
                        if config.language == Language.CHINESE
                        else difficulty_config["name_en"]
                    ),
                    "cognitive_level": (
                        "综合" if config.language == Language.CHINESE else "Synthesis"
                    ),
                    "question_type": config.question_type.value,
                    "content": ai_response.get("content", ""),
                    "options": ai_response.get("options", []),
                    "correct_answer": ai_response.get("correct_answer", ""),
                    "explanation": ai_response.get("explanation", ""),
                    "keywords": ai_response.get("keywords", ["AI生成"]),
                    "points": config.points_per_question,
                    "scoring_criteria": {
                        "full_credit": (
                            "完全正确"
                            if config.language == Language.CHINESE
                            else "Completely correct"
                        ),
                        "partial_credit": (
                            "部分正确"
                            if config.language == Language.CHINESE
                            else "Partially correct"
                        ),
                        "zero_credit": (
                            "答案错误"
                            if config.language == Language.CHINESE
                            else "Incorrect answer"
                        ),
                    },
                    "time_limit": difficulty_config["time_limit_minutes"],
                    "auto_gradable": True,
                    "ai_generated": True,
                    "difficulty_justification": ai_response.get(
                        "difficulty_justification", ""
                    ),
                    "innovation_aspects": ai_response.get("innovation_aspects", ""),
                }
            else:
                print(f"⚠️  AI API返回格式错误或为空")
                return None

        except Exception as e:
            print(f"❌ AI驱动生成异常: {e}")
            return None

    def _call_ai_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用AI API生成题目"""
        if not self.api_manager.has_valid_api():
            print("❌ 没有可用的API配置")
            return None

        # 构建消息
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的教育测评专家，专门负责生成高质量的考试题目。请确保生成的题目准确、公平、具有适当的难度区分度。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            print(f"📝 Prompt长度: {len(prompt)} 字符")

            # 使用API管理器调用
            content = self.api_manager.call_api(messages)

            if not content:
                print("❌ API调用失败")
                return None

            print(f"✅ API调用成功，返回内容长度: {len(content)} 字符")

            # 解析JSON
            try:
                question_data = json.loads(content)
                return question_data
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON解析失败: {str(e)}")
                print(f"原始内容: {content[:200]}...")

                # 尝试修复常见的JSON问题
                try:
                    # 1. 先移除代码块标记
                    cleaned_content = self._clean_json_response(content)

                    # 2. 修复LaTeX反斜杠转义问题
                    fixed_content = self._fix_latex_escapes_in_json(cleaned_content)

                    question_data = json.loads(fixed_content)
                    print("✅ JSON修复成功")
                    return question_data
                except json.JSONDecodeError as fix_e:
                    print(f"❌ JSON修复失败: {str(fix_e)}")
                    return None

        except Exception as e:
            print(f"API调用失败: {str(e)}")
            return None

    def _clean_json_response(self, content: str) -> str:
        """清理AI响应中的代码块标记和其他格式问题"""
        import re

        # 移除代码块标记
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*$", "", content)
        content = re.sub(r"^```\s*", "", content)

        # 移除开头和结尾的空白字符
        content = content.strip()

        # 如果没有找到JSON对象，尝试提取
        if not content.startswith("{"):
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group()

        # 进一步清理：确保是完整的JSON对象
        # 找到第一个{和最后一个}
        first_brace = content.find("{")
        last_brace = content.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            content = content[first_brace : last_brace + 1]

        return content

    def _fix_latex_escapes_in_json(self, json_string: str) -> str:
        """修复JSON中的LaTeX反斜杠转义问题"""

        # 简单有效的方法：直接替换所有单反斜杠为双反斜杠
        # 这样可以确保LaTeX命令在JSON中正确转义

        # 首先处理已经正确转义的情况，避免重复转义
        # 将已有的双反斜杠临时替换为特殊标记
        temp_marker = "___DOUBLE_BACKSLASH___"
        fixed_string = json_string.replace("\\\\", temp_marker)

        # 将所有单反斜杠替换为双反斜杠
        fixed_string = fixed_string.replace("\\", "\\\\")

        # 恢复原有的双反斜杠
        fixed_string = fixed_string.replace(temp_marker, "\\\\")

        return fixed_string

    def _generate_ai_parameter_driven_response(
        self, config: GenerationConfig, index: int
    ) -> Dict[str, Any]:
        """完全基于AI参数生成题目，摆脱预设框架限制"""

        # 使用index和时间戳作为随机种子，确保每次生成不同的题目
        import random
        import time

        random.seed(
            hash(
                f"{config.subject}_{config.difficulty.value}_{index}_{config.sub_domain}_{config.use_scenarios}_{time.time()}"
            )
        )

        # 根据难度级别定义不同的复杂度要求
        difficulty_complexity = {
            DifficultyLevel.HIGH_SCHOOL: {
                "concepts": ["基础概念", "简单计算", "直观理解"],
                "complexity_level": "基础应用",
                "thinking_depth": "记忆和理解",
                "problem_scope": "单一知识点",
            },
            DifficultyLevel.UNDERGRADUATE_BASIC: {
                "concepts": ["核心理论", "标准方法", "典型应用"],
                "complexity_level": "理论理解",
                "thinking_depth": "分析和应用",
                "problem_scope": "多知识点综合",
            },
            DifficultyLevel.UNDERGRADUATE_ADVANCED: {
                "concepts": ["高级理论", "复杂推导", "深度分析"],
                "complexity_level": "高级应用",
                "thinking_depth": "综合分析",
                "problem_scope": "跨领域整合",
            },
            DifficultyLevel.GRE_LEVEL: {
                "concepts": ["逻辑推理", "问题解决", "数量分析"],
                "complexity_level": "标准化推理",
                "thinking_depth": "批判性思维",
                "problem_scope": "实际问题解决",
            },
            DifficultyLevel.GRADUATE_STUDY: {
                "concepts": ["前沿理论", "研究方法", "创新思维"],
                "complexity_level": "研究水平",
                "thinking_depth": "原创性分析",
                "problem_scope": "学科前沿问题",
            },
            DifficultyLevel.DOCTORAL_RESEARCH: {
                "concepts": ["尖端理论", "原创研究", "学科交叉"],
                "complexity_level": "创新研究",
                "thinking_depth": "开创性思维",
                "problem_scope": "未解决的前沿问题",
            },
        }

        current_difficulty = difficulty_complexity[config.difficulty]

        # 根据学科生成不同的专业术语和概念
        subject_specifics = {
            "数学": {
                "fields": [
                    "代数",
                    "分析",
                    "几何",
                    "拓扑",
                    "数论",
                    "逻辑",
                    "组合",
                    "概率",
                ],
                "advanced_topics": [
                    "范畴论",
                    "代数几何",
                    "微分几何",
                    "调和分析",
                    "表示论",
                    "数理逻辑",
                ],
                "research_areas": [
                    "算术几何",
                    "非交换几何",
                    "高维范畴",
                    "量子代数",
                    "计算复杂性理论",
                ],
                "formulas": [
                    "$f(x) = x^2 + bx + c$",
                    "$\\int_a^b f(x)dx$",
                    "$\\lim_{x \\to 0} \\frac{\\sin x}{x}$",
                    "$\\sum_{i=1}^n i^2$",
                    "$\\frac{dy}{dx}$",
                ],
            },
            "统计学": {
                "fields": [
                    "描述统计",
                    "推断统计",
                    "回归分析",
                    "时间序列",
                    "多元分析",
                    "非参数",
                ],
                "advanced_topics": [
                    "贝叶斯统计",
                    "生存分析",
                    "高维统计",
                    "机器学习统计",
                    "因果推断",
                ],
                "research_areas": [
                    "量子统计",
                    "拓扑数据分析",
                    "深度学习理论",
                    "分布式统计",
                    "隐私保护统计",
                ],
                "formulas": [
                    "$\\bar{x} = \\frac{1}{n}\\sum_{i=1}^n x_i$",
                    "$P(A|B) = \\frac{P(B|A)P(A)}{P(B)}$",
                    "$\\sigma^2 = E[(X-\\mu)^2]$",
                    "$Z = \\frac{X-\\mu}{\\sigma}$",
                    "$r = \\frac{\\sum(x_i-\\bar{x})(y_i-\\bar{y})}{\\sqrt{\\sum(x_i-\\bar{x})^2\\sum(y_i-\\bar{y})^2}}$",
                ],
            },
            "物理": {
                "fields": ["力学", "热学", "电磁学", "光学", "原子物理", "固体物理"],
                "advanced_topics": [
                    "量子力学",
                    "相对论",
                    "统计力学",
                    "凝聚态物理",
                    "粒子物理",
                ],
                "research_areas": [
                    "量子引力",
                    "弦理论",
                    "拓扑量子态",
                    "量子信息",
                    "宇宙学",
                ],
            },
            "计算机科学": {
                "fields": ["算法", "数据结构", "编程", "数据库", "网络", "系统"],
                "advanced_topics": [
                    "机器学习",
                    "人工智能",
                    "分布式系统",
                    "密码学",
                    "计算理论",
                ],
                "research_areas": [
                    "量子计算",
                    "神经符号AI",
                    "联邦学习",
                    "同态加密",
                    "区块链理论",
                ],
            },
            "工程": {
                "fields": ["控制", "信号处理", "系统设计", "优化", "建模", "仿真"],
                "advanced_topics": [
                    "自适应控制",
                    "鲁棒控制",
                    "最优控制",
                    "系统识别",
                    "智能系统",
                ],
                "research_areas": [
                    "自主系统",
                    "人机协作",
                    "边缘计算",
                    "数字孪生",
                    "可持续工程",
                ],
            },
        }

        subject_info = subject_specifics.get(config.subject, subject_specifics["数学"])

        # 根据难度选择合适的主题领域
        if config.difficulty in [
            DifficultyLevel.HIGH_SCHOOL,
            DifficultyLevel.UNDERGRADUATE_BASIC,
        ]:
            topic_pool = subject_info["fields"]
        elif config.difficulty in [
            DifficultyLevel.UNDERGRADUATE_ADVANCED,
            DifficultyLevel.GRE_LEVEL,
            DifficultyLevel.GRADUATE_STUDY,
        ]:
            topic_pool = subject_info["advanced_topics"]
        else:  # DOCTORAL_RESEARCH
            topic_pool = subject_info["research_areas"]

        # 随机选择主题 - 使用index和随机因子增加多样性
        topic_index = (index * 7 + random.randint(0, len(topic_pool) * 2)) % len(
            topic_pool
        )
        selected_topic = topic_pool[topic_index]

        # 生成题目内容
        if config.use_scenarios:
            scenario_context = self._generate_scenario_context(
                config.subject, selected_topic, config.difficulty
            )
            content_prefix = f"在{scenario_context}中，"
        else:
            content_prefix = f"在{config.subject}的{selected_topic}研究中，"

        # 添加数学公式到题目中
        formula = ""
        if config.subject in subject_info and "formulas" in subject_info:
            formula_list = subject_info["formulas"]
            formula = formula_list[index % len(formula_list)]

        # 根据难度生成不同复杂度的问题描述
        problem_descriptors = {
            DifficultyLevel.HIGH_SCHOOL: [
                "请直接计算并给出答案",
                "根据基本公式求解",
                "运用简单概念分析",
                "使用基础方法计算",
                "应用基本定理求解",
            ],
            DifficultyLevel.UNDERGRADUATE_BASIC: [
                "请运用相关理论进行分析",
                "根据标准方法求解",
                "结合多个概念进行综合判断",
                "运用核心理论进行计算",
                "基于基本原理进行推导",
            ],
            DifficultyLevel.UNDERGRADUATE_ADVANCED: [
                "请进行深入的理论分析",
                "运用高级方法进行复杂计算",
                "结合多个领域知识进行综合研究",
                "运用复杂理论进行推导",
                "基于高级概念进行综合分析",
            ],
            DifficultyLevel.GRE_LEVEL: [
                "请运用逻辑推理进行分析",
                "根据给定条件进行策略性思考",
                "运用批判性思维进行判断",
                "基于逻辑分析进行推理",
                "运用分析思维解决问题",
            ],
            DifficultyLevel.GRADUATE_STUDY: [
                "请运用前沿理论进行创新分析",
                "结合最新研究成果进行深度研究",
                "运用创新方法解决复杂问题",
                "基于研究理论进行创新思考",
                "运用学术方法进行深度分析",
            ],
            DifficultyLevel.DOCTORAL_RESEARCH: [
                "请运用原创性理论进行突破性分析",
                "结合前沿交叉领域知识进行创新研究",
                "运用开创性思维解决未解难题",
                "基于前沿理论进行突破性研究",
                "运用创新思维探索未知领域",
            ],
        }

        descriptor = random.choice(problem_descriptors[config.difficulty])

        # 生成数值参数 - 增加更多随机化
        random_offset = random.randint(1, 100)  # 增加随机偏移

        if config.difficulty == DifficultyLevel.DOCTORAL_RESEARCH:
            # 博士级别使用更复杂的参数
            param_options1 = [
                f"λ={random.uniform(0.1 + random_offset * 0.01, 2.5 + random_offset * 0.02):.3f}",
                f"α={random.randint(3 + random_offset % 10, 15 + random_offset % 20)}",
                f"n={random.randint(10 + random_offset % 50, 100 + random_offset % 100)}",
                f"φ={random.uniform(0.5 + random_offset * 0.01, 3.14 + random_offset * 0.001):.3f}",
                f"ε={random.uniform(0.001 + random_offset * 0.0001, 0.1 + random_offset * 0.001):.4f}",
            ]
            param_options2 = [
                f"β={random.uniform(1.2 + random_offset * 0.01, 8.7 + random_offset * 0.02):.2f}",
                f"k={random.randint(5 + random_offset % 20, 50 + random_offset % 30)}",
                f"m={random.randint(20 + random_offset % 80, 200 + random_offset % 150)}",
                f"ω={random.uniform(0.8 + random_offset * 0.01, 5.2 + random_offset * 0.02):.2f}",
                f"δ={random.uniform(0.05 + random_offset * 0.001, 0.95 + random_offset * 0.01):.3f}",
            ]
            param1 = random.choice(param_options1)
            param2 = random.choice(param_options2)
        elif config.difficulty == DifficultyLevel.GRADUATE_STUDY:
            param_options1 = [
                f"p={random.uniform(0.2 + random_offset * 0.005, 0.9 + random_offset * 0.001):.2f}",
                f"n={random.randint(5 + random_offset % 15, 30 + random_offset % 25)}",
                f"σ={random.uniform(1 + random_offset * 0.1, 5 + random_offset * 0.2):.1f}",
                f"λ={random.uniform(0.5 + random_offset * 0.01, 3.0 + random_offset * 0.05):.2f}",
            ]
            param_options2 = [
                f"μ={random.uniform(-2 + random_offset * 0.1, 5 + random_offset * 0.2):.1f}",
                f"t={random.randint(10 + random_offset % 40, 100 + random_offset % 60)}",
                f"r={random.uniform(0.1 + random_offset * 0.01, 1 + random_offset * 0.02):.2f}",
                f"θ={random.uniform(0.1 + random_offset * 0.001, 2.0 + random_offset * 0.01):.2f}",
            ]
            param1 = random.choice(param_options1)
            param2 = random.choice(param_options2)
        else:
            param_options1 = [
                f"x={random.randint(1 + random_offset % 10, 20 + random_offset % 15)}",
                f"n={random.randint(2 + random_offset % 5, 10 + random_offset % 8)}",
                f"p={random.uniform(0.1 + random_offset * 0.01, 0.9 + random_offset * 0.005):.1f}",
                f"a={random.randint(3 + random_offset % 8, 12 + random_offset % 10)}",
            ]
            param_options2 = [
                f"y={random.randint(1 + random_offset % 8, 15 + random_offset % 12)}",
                f"k={random.randint(1 + random_offset % 5, 8 + random_offset % 7)}",
                f"q={random.uniform(0.2 + random_offset * 0.01, 0.8 + random_offset * 0.005):.1f}",
                f"b={random.randint(2 + random_offset % 6, 9 + random_offset % 8)}",
            ]
            param1 = random.choice(param_options1)
            param2 = random.choice(param_options2)

        # 如果有自定义prompt，优先使用自定义prompt生成内容
        if config.custom_prompt and config.custom_prompt.strip():
            # 基于自定义prompt生成更相关的题目内容
            custom_content = self._generate_custom_prompt_content(
                config, selected_topic, current_difficulty
            )
            if custom_content:
                content = custom_content
            else:
                # 在自定义prompt基础上添加困难度体现
                difficulty_hint = self._get_difficulty_hint(
                    config.difficulty, current_difficulty
                )
                content = f"{content_prefix}考虑{selected_topic}问题，设{param1}，{param2}。{difficulty_hint} {descriptor}"
        else:
            # 生成清晰的题目内容，避免prompt泄露
            if formula:
                content = f"已知函数{formula}，求解相关问题。"
            else:
                # 根据学科和主题生成合适的题目内容
                if config.subject == "数学":
                    if selected_topic == "微积分":
                        content = f"计算函数在指定点的导数值。"
                    elif selected_topic == "线性代数":
                        content = f"求解矩阵运算问题。"
                    elif selected_topic == "概率论":
                        content = f"计算概率分布的相关参数。"
                    else:
                        content = f"解决{selected_topic}相关的数学问题。"
                elif config.subject == "统计学":
                    content = f"分析统计数据并计算相关指标。"
                else:
                    content = f"解决{config.subject}领域的{selected_topic}问题。"

        # 生成选项 - 增加多样化的理论标识和描述
        theory_labels = [
            "理论A",
            "方法B",
            "结论C",
            "模型D",
            "定理E",
            "原理F",
            "算法G",
            "策略H",
        ]
        random.shuffle(theory_labels)

        approach_words = [
            "基于",
            "通过",
            "依据",
            "运用",
            "采用",
            "利用",
            "结合",
            "整合",
        ]
        result_words = ["结果", "方法", "分析", "思路", "策略", "途径", "模式", "框架"]

        base_options = []
        for i in range(4):
            theory_label = theory_labels[i % len(theory_labels)]
            approach = random.choice(approach_words)
            concept = current_difficulty["concepts"][
                i % len(current_difficulty["concepts"])
            ]
            result_type = random.choice(result_words)

            option = f"{theory_label}：{approach}{concept}的{result_type}"
            base_options.append(option)

        # 随机化选项顺序
        random.shuffle(base_options)

        # 生成关键词
        keywords = [
            config.subject,
            selected_topic,
            current_difficulty["complexity_level"],
            f"{config.difficulty.value}_level",
        ]

        if config.use_scenarios:
            keywords.append("应用场景")

        # 添加随机化的专业关键词
        extra_keywords = random.sample(topic_pool, min(2, len(topic_pool)))
        keywords.extend(extra_keywords)

        return {
            "content": content,
            "options": base_options,
            "correct_answer": base_options[0],  # 第一个选项作为正确答案
            "explanation": f"根据{config.subject}领域{selected_topic}的{current_difficulty['complexity_level']}理论，结合{current_difficulty['thinking_depth']}，可以得出该结果体现了{current_difficulty['problem_scope']}的特征。",
            "keywords": keywords,
            "difficulty_justification": f"该题目体现了{config.difficulty.value}级别的{current_difficulty['complexity_level']}要求，需要{current_difficulty['thinking_depth']}能力",
            "innovation_aspects": f"采用AI参数驱动生成，完全摆脱预设框架限制，每次生成独特的{selected_topic}相关问题",
        }

    def _generate_scenario_context(
        self, subject: str, topic: str, difficulty: DifficultyLevel
    ) -> str:
        """生成场景上下文"""
        import random

        scenarios = {
            "数学": {
                "basic": [
                    "数学建模实验：某公司需要优化生产流程，建立数学模型分析成本效益",
                    "数据分析项目：某学校分析学生成绩数据，找出影响学习效果的关键因素",
                    "工程计算问题：某建筑公司计算桥梁承重，确保结构安全性",
                ],
                "advanced": [
                    "科学研究计算：某研究所进行数值模拟，预测气候变化对生态系统的影响",
                    "金融数学建模：某投资银行开发风险评估模型，预测市场波动",
                    "机器学习算法优化：某科技公司改进推荐系统，提升用户满意度",
                ],
                "research": [
                    "跨学科研究合作：某国际团队研究数学在生物信息学中的应用",
                    "前沿理论探索：某大学研究代数几何在密码学中的新突破",
                    "国际学术会议：某顶级会议展示数学理论的最新研究成果",
                ],
            },
            "统计学": {
                "basic": [
                    "市场调研分析：某公司调查消费者偏好，制定营销策略",
                    "医学数据研究：某医院分析患者数据，改进治疗方案",
                    "质量控制检验：某工厂统计产品缺陷率，优化生产流程",
                ],
                "advanced": [
                    "大数据挖掘项目：某互联网公司分析用户行为，优化产品功能",
                    "生物信息学研究：某实验室分析基因数据，发现疾病关联",
                    "金融风险评估：某银行建立信用评分模型，控制贷款风险",
                ],
                "research": [
                    "人工智能统计基础：某研究机构探索统计学习理论的新发展",
                    "量子统计理论：某大学研究量子计算中的统计方法",
                    "复杂系统建模：某研究所分析社会网络，预测信息传播",
                ],
            },
            "物理": {
                "basic": [
                    "物理实验设计：某中学设计实验验证牛顿第二定律",
                    "工程应用计算：某工程师计算电路参数，确保设备正常运行",
                    "日常现象解释：某科普工作者解释彩虹形成的物理原理",
                ],
                "advanced": [
                    "高能物理实验：某实验室进行粒子碰撞实验，探索物质基本结构",
                    "材料科学研究：某研究所分析新材料性能，开发先进器件",
                    "量子技术开发：某公司研发量子计算机，突破计算极限",
                ],
                "research": [
                    "基础物理理论验证：某大学验证相对论预言，推进理论发展",
                    "宇宙学模型构建：某天文台建立宇宙演化模型，探索宇宙奥秘",
                    "量子计算硬件：某实验室开发量子比特，实现量子优势",
                ],
            },
            "计算机科学": {
                "basic": [
                    "软件开发项目：某公司开发移动应用，提升用户体验",
                    "系统设计任务：某工程师设计数据库架构，优化查询性能",
                    "算法优化问题：某程序员改进排序算法，提升运行效率",
                ],
                "advanced": [
                    "人工智能应用：某科技公司开发智能客服，提升服务质量",
                    "分布式系统设计：某云服务商构建高可用架构，确保服务稳定",
                    "网络安全防护：某安全公司开发防护系统，抵御网络攻击",
                ],
                "research": [
                    "量子计算算法：某研究机构开发量子算法，解决经典难题",
                    "神经网络理论：某大学研究深度学习理论，推进AI发展",
                    "区块链创新：某实验室探索区块链技术，革新金融系统",
                ],
            },
            "工程": {
                "basic": [
                    "工程设计项目：某建筑公司设计绿色建筑，实现节能减排",
                    "系统控制优化：某工厂优化生产线控制，提升生产效率",
                    "产品性能测试：某汽车公司测试车辆性能，确保安全可靠",
                ],
                "advanced": [
                    "智能制造系统：某制造企业建设智能工厂，实现自动化生产",
                    "自动化控制设计：某工程师设计机器人控制系统，提升精度",
                    "可靠性工程：某航天公司分析系统可靠性，确保任务成功",
                ],
                "research": [
                    "自主系统开发：某研究机构开发无人驾驶技术，革新交通",
                    "可持续工程技术：某大学研究清洁能源，保护环境",
                    "人机协作系统：某实验室开发人机交互技术，提升效率",
                ],
            },
        }

        if difficulty in [
            DifficultyLevel.HIGH_SCHOOL,
            DifficultyLevel.UNDERGRADUATE_BASIC,
        ]:
            level = "basic"
        elif difficulty in [
            DifficultyLevel.UNDERGRADUATE_ADVANCED,
            DifficultyLevel.GRE_LEVEL,
            DifficultyLevel.GRADUATE_STUDY,
        ]:
            level = "advanced"
        else:
            level = "research"

        subject_scenarios = scenarios.get(subject, scenarios["数学"])
        scenario_list = subject_scenarios[level]
        # 使用topic和时间戳增加随机性
        import time

        scenario_index = (
            hash(topic + str(time.time())) + random.randint(0, 100)
        ) % len(scenario_list)
        return scenario_list[scenario_index]

    def _get_difficulty_hint(
        self, difficulty: DifficultyLevel, current_difficulty: dict
    ) -> str:
        """获取困难度提示"""
        difficulty_hints = {
            DifficultyLevel.HIGH_SCHOOL: "这是一道基础题目，",
            DifficultyLevel.UNDERGRADUATE_BASIC: "这是一道标准题目，",
            DifficultyLevel.UNDERGRADUATE_ADVANCED: "这是一道高级题目，",
            DifficultyLevel.GRE_LEVEL: "这是一道推理题目，",
            DifficultyLevel.GRADUATE_STUDY: "这是一道研究题目，",
            DifficultyLevel.DOCTORAL_RESEARCH: "这是一道前沿题目，",
        }

        complexity_hints = {
            DifficultyLevel.HIGH_SCHOOL: "需要运用基础概念和简单计算",
            DifficultyLevel.UNDERGRADUATE_BASIC: "需要理解核心理论和标准方法",
            DifficultyLevel.UNDERGRADUATE_ADVANCED: "需要掌握复杂理论和综合应用",
            DifficultyLevel.GRE_LEVEL: "需要运用逻辑推理和批判性思维",
            DifficultyLevel.GRADUATE_STUDY: "需要运用前沿理论和创新方法",
            DifficultyLevel.DOCTORAL_RESEARCH: "需要运用原创理论和突破性思维",
        }

        hint = difficulty_hints.get(difficulty, "这是一道题目，")
        complexity = complexity_hints.get(difficulty, "需要运用相关理论")

        return f"{hint}{complexity}。"

    def _generate_custom_prompt_content(
        self, config: GenerationConfig, selected_topic: str, current_difficulty: dict
    ) -> str:
        """基于自定义prompt生成题目内容"""
        import random

        # 解析自定义prompt中的关键词
        prompt_lower = config.custom_prompt.lower()

        # 数学相关关键词
        if any(
            keyword in prompt_lower
            for keyword in ["微积分", "极限", "导数", "积分", "ε-δ", "epsilon", "delta"]
        ):
            if (
                "极限" in prompt_lower
                or "ε-δ" in prompt_lower
                or "epsilon" in prompt_lower
            ):
                # 生成极限相关题目
                if config.use_scenarios:
                    scenario = random.choice(["工程计算", "物理建模", "数据分析"])
                    return f"在{scenario}中，需要计算函数f(x) = x² + 3x - 2在x→2时的极限值。根据ε-δ定义，当|x-2| < δ时，|f(x)-8| < ε，求δ与ε的关系。"
                else:
                    return f"根据ε-δ定义，证明函数f(x) = x² + 3x - 2在x→2时的极限为8。设ε = 0.1，求对应的δ值。"

        elif any(
            keyword in prompt_lower
            for keyword in ["线性代数", "矩阵", "向量", "特征值"]
        ):
            if config.use_scenarios:
                scenario = random.choice(["机器学习", "图像处理", "控制系统"])
                return f"在{scenario}中，给定矩阵A = [[2,1],[1,3]]，求其特征值和特征向量，并分析其在系统稳定性中的作用。"
            else:
                return f"对于矩阵A = [[2,1],[1,3]]，计算其特征值λ₁和λ₂，并求对应的特征向量。"

        elif any(
            keyword in prompt_lower for keyword in ["概率", "统计", "分布", "期望"]
        ):
            if config.use_scenarios:
                scenario = random.choice(["质量控制", "金融风险评估", "医学统计"])
                return f"在{scenario}中，某随机变量X服从正态分布N(μ=5, σ²=4)，求P(3<X<7)的概率值。"
            else:
                return f"设随机变量X服从正态分布N(μ=5, σ²=4)，计算P(3<X<7)的概率值。"

        # 物理相关关键词
        elif any(
            keyword in prompt_lower for keyword in ["力学", "电磁学", "量子", "相对论"]
        ):
            if config.use_scenarios:
                scenario = random.choice(["实验设计", "工程应用", "理论研究"])
                return f"在{scenario}中，考虑{selected_topic}问题，根据{current_difficulty['concepts'][0]}理论，分析其物理意义和应用价值。"
            else:
                return f"在{selected_topic}中，根据{current_difficulty['concepts'][0]}原理，分析相关物理现象。"

        # 计算机科学相关关键词
        elif any(
            keyword in prompt_lower
            for keyword in ["算法", "数据结构", "编程", "复杂度"]
        ):
            if config.use_scenarios:
                scenario = random.choice(["软件开发", "系统优化", "性能分析"])
                return f"在{scenario}中，需要实现一个{selected_topic}算法，分析其时间复杂度和空间复杂度。"
            else:
                return f"设计一个{selected_topic}算法，分析其时间复杂度和空间复杂度。"

        # 如果没有匹配到特定关键词，返回基于prompt的通用内容
        difficulty_hint = self._get_difficulty_hint(
            config.difficulty, current_difficulty
        )

        if config.use_scenarios:
            scenario = self._generate_scenario_context(
                config.subject, selected_topic, config.difficulty
            )
            return f"在{scenario}中，{config.custom_prompt}。{difficulty_hint}请基于{selected_topic}知识进行分析。"
        else:
            return f"{config.custom_prompt}。{difficulty_hint}请结合{selected_topic}的相关理论进行解答。"

    def _validate_question(self, question: Dict[str, Any]) -> bool:
        """验证题目质量"""

        # 基本字段检查
        required_fields = ["content", "correct_answer", "explanation"]
        for field in required_fields:
            if not question.get(field):
                print(f"验证失败：缺少必要字段 {field}")
                return False

        # 内容长度检查
        if len(question["content"]) < 10:
            print("验证失败：题目内容过短")
            return False

        # 选择题特殊验证
        if question.get("question_type") == "multiple_choice":
            options = question.get("options", [])
            if len(options) != 4:
                print("验证失败：选择题选项数量不正确")
                return False

            if question["correct_answer"] not in options:
                print("验证失败：正确答案不在选项中")
                return False

        # 防重复检查
        signature = self._calculate_question_signature(question)
        if signature in self.generated_signatures:
            print("验证失败：题目重复")
            return False

        self.generated_signatures.add(signature)
        return True

    def _calculate_question_signature(self, question: Dict[str, Any]) -> str:
        """计算题目签名用于去重"""
        content = question.get("content", "")
        answer = question.get("correct_answer", "")
        # 对于AI生成的题目，加入更多信息以减少误判
        if question.get("ai_generated", False):
            keywords = "|".join(question.get("keywords", []))
            signature_string = f"{content[:150]}|{answer}|{keywords}"
        else:
            signature_string = f"{content[:100]}|{answer}"
        return hashlib.md5(signature_string.encode()).hexdigest()

    def get_available_subjects(self) -> Dict[str, Any]:
        """获取可用学科列表"""
        return {
            "数学": {"name": "数学", "name_en": "Mathematics"},
            "统计学": {"name": "统计学", "name_en": "Statistics"},
            "物理": {"name": "物理", "name_en": "Physics"},
            "计算机科学": {"name": "计算机科学", "name_en": "Computer Science"},
            "工程": {"name": "工程", "name_en": "Engineering"},
            "英语": {"name": "英语", "name_en": "English"},
            "逻辑": {"name": "逻辑", "name_en": "Logic"},
        }

    def get_difficulty_levels(self) -> Dict[str, Any]:
        """获取难度级别列表"""
        return {
            "high_school": {
                "name": "高中水平",
                "name_en": "High School Level",
                "description": "基础概念和简单应用",
                "points": 1,
                "time_limit": 3,
            },
            "undergraduate_basic": {
                "name": "本科基础",
                "name_en": "Undergraduate Basic",
                "description": "理论理解和标准应用",
                "points": 2,
                "time_limit": 5,
            },
            "undergraduate_advanced": {
                "name": "本科高级",
                "name_en": "Undergraduate Advanced",
                "description": "复杂理论和综合应用",
                "points": 3,
                "time_limit": 8,
            },
            "gre_level": {
                "name": "GRE难度",
                "name_en": "GRE Level",
                "description": "标准化考试推理和分析",
                "points": 4,
                "time_limit": 4,
            },
            "graduate_study": {
                "name": "研究生水平",
                "name_en": "Graduate Study Level",
                "description": "高级理论和研究方法",
                "points": 5,
                "time_limit": 15,
            },
            "doctoral_research": {
                "name": "博士研究",
                "name_en": "Doctoral Research",
                "description": "前沿理论和创新研究",
                "points": 8,
                "time_limit": 25,
            },
        }

    def get_question_types(self) -> Dict[str, Any]:
        """获取题目类型列表"""
        return {
            "multiple_choice": {
                "name": "选择题",
                "name_en": "Multiple Choice",
                "description": "4个选项，1个正确答案",
            },
            "short_answer": {
                "name": "简答题",
                "name_en": "Short Answer",
                "description": "简短文字回答",
            },
            "programming": {
                "name": "编程题",
                "name_en": "Programming",
                "description": "代码实现",
            },
            "true_false": {
                "name": "判断题",
                "name_en": "True/False",
                "description": "正确或错误",
            },
            "fill_blank": {
                "name": "填空题",
                "name_en": "Fill in the Blank",
                "description": "填入关键词或数值",
            },
            "essay": {
                "name": "论述题",
                "name_en": "Essay",
                "description": "详细分析和论证",
            },
        }


# 便于导入的函数
def generate_questions_with_config(
    subject: str,
    difficulty: str = "undergraduate_basic",
    question_type: str = "multiple_choice",
    language: str = "zh",
    count: int = 5,
    use_scenarios: bool = False,
    sub_domain: str = None,
    custom_prompt: str = "",
    points_per_question: int = 1,
) -> List[Dict[str, Any]]:
    """便捷的题目生成函数"""

    # 转换枚举值
    difficulty_enum = DifficultyLevel(difficulty)
    question_type_enum = QuestionType(question_type)
    language_enum = Language(language)

    # 创建配置
    config = GenerationConfig(
        subject=subject,
        sub_domain=sub_domain,
        difficulty=difficulty_enum,
        question_type=question_type_enum,
        language=language_enum,
        use_scenarios=use_scenarios,
        custom_prompt=custom_prompt,
        count=count,
        points_per_question=points_per_question,
    )

    # 生成题目
    generator = SmartQuestionGenerator()
    return generator.generate_questions(config)
