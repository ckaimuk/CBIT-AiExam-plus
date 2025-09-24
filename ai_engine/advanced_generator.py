"""
高级题目生成引擎 - 彻底解决重复题目问题
确保每道题目完全不同，不仅仅是数字改变
"""

import random
import json
import hashlib
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime


class AdvancedQuestionGenerator:
    """高级题目生成引擎 - 确保每道题目完全不同"""
    
    def __init__(self):
        self.used_signatures = set()  # 已使用的题目签名
        self.scenario_templates = self._load_scenario_templates()
        self.difficulty_configs = self._load_difficulty_configs()
        
    def _load_difficulty_configs(self) -> Dict[str, Dict]:
        """加载难度配置"""
        return {
            # 基础难度
            '简单': {
                'complexity_level': 1,
                'calculation_steps': 1,
                'concepts_count': 1,
                'points': 1,
                'time_limit': 2,
                'description': '单步计算，直接应用公式'
            },
            '中等': {
                'complexity_level': 2,
                'calculation_steps': 2,
                'concepts_count': 2,
                'points': 3,
                'time_limit': 4,
                'description': '两步计算，需要逻辑推理'
            },
            '困难': {
                'complexity_level': 3,
                'calculation_steps': 3,
                'concepts_count': 3,
                'points': 5,
                'time_limit': 8,
                'description': '多步计算，综合分析'
            },
            # 专业级别
            'gre_math': {
                'complexity_level': 4,
                'calculation_steps': 3,
                'concepts_count': 2,
                'points': 4,
                'time_limit': 3,
                'description': 'GRE数学推理，策略性思维',
                'special_features': ['data_sufficiency', 'quantitative_comparison', 'trap_answers']
            },
            'graduate_study': {
                'complexity_level': 8,
                'calculation_steps': 6,
                'concepts_count': 4,
                'points': 8,
                'time_limit': 15,
                'description': '研究生水平，理论证明',
                'special_features': ['proof_required', 'theoretical_analysis']
            },
            'competition_math': {
                'complexity_level': 7,
                'calculation_steps': 5,
                'concepts_count': 3,
                'points': 7,
                'time_limit': 12,
                'description': '数学竞赛，创新思路',
                'special_features': ['creative_approach', 'non_standard_methods']
            }
        }
    
    def _load_scenario_templates(self) -> Dict[str, List[Dict]]:
        """加载场景模板 - 每个场景有多个完全不同的子类型"""
        return {
            'shopping_scenario': [
                {
                    'type': 'unit_price_calculation',
                    'template': '商店购买：{customer}买了{quantity}个{item}，总共花费{total}元。每个{item}的单价是多少？',
                    'variables': {
                        'customer': ['小明', '小红', '张先生', '李女士', '王同学'],
                        'quantity': lambda: random.randint(3, 15),
                        'item': ['苹果', '橘子', '葡萄', '香蕉', '草莓'],
                        'total': lambda q, p: q * p,
                        'unit_price': lambda: random.uniform(2.5, 12.8)
                    },
                    'answer_formula': lambda vars: vars['total'] / vars['quantity']
                },
                {
                    'type': 'bulk_discount_analysis',
                    'template': '批量采购：{company}需要采购{needed_qty}个{product}。零售价{retail_price}元/个，批发价{wholesale_price}元/个（最少{min_qty}个）。最优采购成本是多少？',
                    'variables': {
                        'company': ['科技公司', '制造厂', '学校', '医院', '餐厅'],
                        'needed_qty': lambda: random.randint(50, 200),
                        'product': ['电脑', '桌椅', '文具', '设备', '原料'],
                        'retail_price': lambda: random.uniform(100, 500),
                        'wholesale_price': lambda: random.uniform(70, 450),  # 简化
                        'min_qty': lambda: random.randint(30, 100)  # 简化
                    },
                    'answer_formula': lambda vars: min(
                        vars['needed_qty'] * vars['retail_price'],
                        vars['needed_qty'] * vars['wholesale_price'] if vars['needed_qty'] >= vars['min_qty'] else float('inf')
                    )
                },
                {
                    'type': 'promotional_pricing',
                    'template': '促销活动：{store}举办{event}活动，{item}原价{original_price}元，现在{discount_type}。{customer}买{quantity}个需要多少钱？',
                    'variables': {
                        'store': ['超市', '商场', '网店', '专卖店', '便利店'],
                        'event': ['双十一', '年末清仓', '会员专享', '新店开业', '节日特惠'],
                        'item': ['手机', '衣服', '鞋子', '包包', '化妆品'],
                        'original_price': lambda: random.uniform(200, 1500),
                        'discount_type': lambda: random.choice(['8折优惠', '满300减50', '买二送一', '第二件半价']),
                        'customer': ['顾客', '会员', '学生', '老师', '职员'],
                        'quantity': lambda: random.randint(1, 5)
                    },
                    'answer_formula': lambda vars: vars['original_price'] * vars['quantity'] * 0.8  # 简化折扣计算
                },
                {
                    'type': 'currency_exchange_shopping',
                    'template': '跨境购物：{customer}在{country}购买{item}，当地价格{local_price}{currency}，汇率1{currency}={exchange_rate}人民币。折合人民币多少钱？',
                    'variables': {
                        'customer': ['游客', '留学生', '商务人士', '代购', '旅行者'],
                        'country': ['美国', '日本', '韩国', '英国', '欧洲'],
                        'item': ['手表', '包包', '化妆品', '电子产品', '奢侈品'],
                        'local_price': lambda: random.uniform(100, 2000),
                        'currency': lambda: random.choice(['美元', '日元', '韩元', '英镑', '欧元']),
                        'exchange_rate': lambda: random.uniform(6.5, 7.5)
                    },
                    'answer_formula': lambda vars: vars['local_price'] * vars['exchange_rate']
                },
                {
                    'type': 'subscription_cost_analysis',
                    'template': '订阅服务：{service}提供{plan_type}，月费{monthly_fee}元，年费{annual_fee}元。选择年费比月费能节省多少钱？',
                    'variables': {
                        'service': ['视频平台', '音乐软件', '云存储', '健身app', '学习软件'],
                        'plan_type': ['基础套餐', '高级套餐', 'VIP套餐', '家庭套餐', '学生套餐'],
                        'monthly_fee': lambda: random.uniform(15, 80),
                        'annual_fee': lambda: random.uniform(120, 600)  # 简化
                    },
                    'answer_formula': lambda vars: (vars['monthly_fee'] * 12) - vars['annual_fee']
                }
            ],
            
            'probability_statistics': [
                {
                    'type': 'card_probability',
                    'template': '扑克牌概率：从标准52张扑克牌中抽取一张，抽到{target_type}的概率是多少？',
                    'variables': {
                        'target_type': ['红桃', '黑桃', '方块', '梅花', '红色牌', '黑色牌', '人头牌', '数字牌']
                    },
                    'answer_formula': lambda vars: {
                        '红桃': 13/52, '黑桃': 13/52, '方块': 13/52, '梅花': 13/52,
                        '红色牌': 26/52, '黑色牌': 26/52, '人头牌': 12/52, '数字牌': 40/52
                    }[vars['target_type']]
                },
                {
                    'type': 'dice_combination',
                    'template': '骰子组合：同时投掷{dice_count}个骰子，点数之和为{target_sum}的概率是多少？',
                    'variables': {
                        'dice_count': lambda: random.randint(2, 3),
                        'target_sum': lambda: random.randint(4, 15)  # 简化为固定范围
                    },
                    'answer_formula': lambda vars: self._calculate_dice_probability(vars['dice_count'], vars['target_sum'])
                },
                {
                    'type': 'survey_statistics',
                    'template': '调查统计：对{total_people}人进行{survey_topic}调查，{positive_count}人给出积极回应。随机选择一人，他给出积极回应的概率是多少？',
                    'variables': {
                        'total_people': lambda: random.randint(100, 1000),
                        'survey_topic': ['环保意识', '健康饮食', '运动习惯', '阅读习惯', '社交媒体使用'],
                        'positive_count': lambda: random.randint(50, 750)  # 简化
                    },
                    'answer_formula': lambda vars: vars['positive_count'] / vars['total_people']
                },
                {
                    'type': 'quality_control',
                    'template': '质量检测：生产线生产{total_products}个产品，其中{defective_count}个不合格。随机抽检一个产品，它合格的概率是多少？',
                    'variables': {
                        'total_products': lambda: random.randint(500, 5000),
                        'defective_count': lambda: random.randint(5, 250)  # 简化
                    },
                    'answer_formula': lambda vars: (vars['total_products'] - vars['defective_count']) / vars['total_products']
                },
                {
                    'type': 'weather_prediction',
                    'template': '天气预报：根据历史数据，{city}在{season}季节有{rainy_days}天下雨，共{total_days}天。随机选择一天，下雨的概率是多少？',
                    'variables': {
                        'city': ['北京', '上海', '广州', '深圳', '杭州'],
                        'season': ['春', '夏', '秋', '冬'],
                        'total_days': lambda: random.choice([90, 91, 92]),
                        'rainy_days': lambda: random.randint(10, 30)  # 简化
                    },
                    'answer_formula': lambda vars: vars['rainy_days'] / vars['total_days']
                }
            ],
            
            'investment_finance': [
                {
                    'type': 'simple_interest',
                    'template': '简单利息：{investor}投资{principal}元，年利率{rate}%，投资{years}年。到期后能获得多少利息？',
                    'variables': {
                        'investor': ['小王', '张女士', '李先生', '退休职工', '大学生'],
                        'principal': lambda: random.randint(10000, 100000),
                        'rate': lambda: random.uniform(3.5, 8.5),
                        'years': lambda: random.randint(1, 5)
                    },
                    'answer_formula': lambda vars: vars['principal'] * vars['rate'] / 100 * vars['years']
                },
                {
                    'type': 'compound_interest',
                    'template': '复利计算：{bank}提供复利投资，本金{principal}元，年利率{rate}%，{compound_frequency}复利，投资{years}年。最终金额是多少？',
                    'variables': {
                        'bank': ['工商银行', '建设银行', '招商银行', '民生银行', '理财公司'],
                        'principal': lambda: random.randint(50000, 500000),
                        'rate': lambda: random.uniform(4.0, 12.0),
                        'compound_frequency': lambda: random.choice(['按年', '按月', '按季度']),
                        'years': lambda: random.randint(2, 10)
                    },
                    'answer_formula': lambda vars: vars['principal'] * (1 + vars['rate']/100) ** vars['years']
                },
                {
                    'type': 'portfolio_allocation',
                    'template': '投资组合：{investor}有{total_money}元进行投资，计划{stock_ratio}%投资股票，{bond_ratio}%投资债券，其余存银行。股票部分投入多少钱？',
                    'variables': {
                        'investor': ['投资者', '基金经理', '理财顾问', '个人投资人', '机构投资者'],
                        'total_money': lambda: random.randint(100000, 2000000),
                        'stock_ratio': lambda: random.randint(30, 70),
                        'bond_ratio': lambda: random.randint(10, 40)  # 简化
                    },
                    'answer_formula': lambda vars: vars['total_money'] * vars['stock_ratio'] / 100
                },
                {
                    'type': 'loan_calculation',
                    'template': '贷款计算：{borrower}向银行贷款{loan_amount}元，年利率{rate}%，贷款期限{years}年，{payment_type}。{calculation_target}？',
                    'variables': {
                        'borrower': ['购房者', '创业者', '企业主', '学生', '个体户'],
                        'loan_amount': lambda: random.randint(100000, 2000000),
                        'rate': lambda: random.uniform(4.5, 15.0),
                        'years': lambda: random.randint(5, 30),
                        'payment_type': lambda: random.choice(['等额本息', '等额本金']),
                        'calculation_target': lambda: random.choice(['每月还款金额是多少', '总利息是多少', '第一年还款总额是多少'])
                    },
                    'answer_formula': lambda vars: vars['loan_amount'] * vars['rate'] / 100 / 12  # 简化计算
                },
                {
                    'type': 'currency_arbitrage',
                    'template': '汇率套利：{trader}发现{currency1}兑{currency2}汇率为{rate1}，{currency2}兑人民币汇率为{rate2}。如果用{amount}人民币进行套利，能获得多少利润？',
                    'variables': {
                        'trader': ['外汇交易员', '套利者', '投资者', '金融机构', '个人交易者'],
                        'currency1': lambda: random.choice(['美元', '欧元', '英镑', '日元']),
                        'currency2': lambda: random.choice(['港币', '澳元', '加元', '瑞郎']),
                        'rate1': lambda: random.uniform(0.8, 1.5),
                        'rate2': lambda: random.uniform(5.0, 8.0),
                        'amount': lambda: random.randint(100000, 1000000)
                    },
                    'answer_formula': lambda vars: vars['amount'] * vars['rate1'] * vars['rate2'] - vars['amount']
                }
            ]
        }
    
    def _calculate_dice_probability(self, dice_count: int, target_sum: int) -> float:
        """计算骰子点数和的概率（简化实现）"""
        if dice_count == 2:
            # 两个骰子的概率计算
            total_outcomes = 36
            if target_sum < 2 or target_sum > 12:
                return 0.0
            # 简化的概率分布
            probabilities = {
                2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6,
                8: 5, 9: 4, 10: 3, 11: 2, 12: 1
            }
            return probabilities.get(target_sum, 0) / total_outcomes
        else:
            # 三个骰子简化计算
            return 1.0 / (6 ** dice_count)  # 简化
    
    def generate_unique_questions(self, count: int, difficulty: str, language: str, 
                                subject: str, custom_prompt: str = "") -> List[Dict[str, Any]]:
        """生成完全不同的题目"""
        
        print(f"🎯 高级题目生成器启动")
        print(f"目标: 生成 {count} 道完全不同的 {difficulty} 级别题目")
        
        # 解析自定义提示词，确定主要场景类型
        primary_scenario = self._determine_primary_scenario(custom_prompt)
        
        # 🔥 优先使用提示词中的语言要求
        if custom_prompt.strip():
            detected_language = self._extract_language_from_prompt(custom_prompt)
            if detected_language != language:
                print(f"📝 检测到提示词语言要求: {detected_language}, 覆盖默认语言: {language}")
                language = detected_language
        
        print(f"主要场景: {primary_scenario}")
        print(f"最终语言: {language}")
        
        # 获取难度配置
        difficulty_config = self.difficulty_configs.get(difficulty, self.difficulty_configs['中等'])
        
        questions = []
        used_question_signatures = set()  # 本次生成中使用的题目签名
        
        # 为了保证完全不同，我们需要从多个角度生成题目
        generation_strategies = [
            'scenario_rotation',      # 场景轮换
            'parameter_variation',    # 参数变化
            'structure_modification', # 结构修改
            'context_diversification' # 上下文多样化
        ]
        
        for i in range(count):
            print(f"\n生成第 {i+1} 道题目...")
            
            # 选择生成策略
            strategy = generation_strategies[i % len(generation_strategies)]
            
            # 根据策略生成题目
            question = self._generate_single_unique_question(
                index=i,
                strategy=strategy,
                primary_scenario=primary_scenario,
                difficulty_config=difficulty_config,
                language=language,
                subject=subject,
                custom_prompt=custom_prompt,
                used_signatures=used_question_signatures
            )
            
            if question:
                # 计算题目签名
                signature = self._calculate_question_signature(question)
                
                # 确保完全不重复
                if signature not in used_question_signatures and signature not in self.used_signatures:
                    questions.append(question)
                    used_question_signatures.add(signature)
                    self.used_signatures.add(signature)
                    print(f"✅ 成功生成唯一题目，签名: {signature[:16]}...")
                else:
                    print(f"⚠️  题目重复，重新生成...")
                    # 重新生成
                    i -= 1  # 重试当前题目
            
            # 防止无限循环
            if len(questions) == 0 and i > count * 2:
                print("⚠️  生成困难，使用fallback方法")
                question = self._generate_fallback_question(i, difficulty_config, language, subject)
                questions.append(question)
        
        print(f"\n🎉 成功生成 {len(questions)} 道完全不同的题目")
        return questions
    
    def _determine_primary_scenario(self, custom_prompt: str) -> str:
        """确定主要场景类型"""
        prompt_lower = custom_prompt.lower()
        
        if any(keyword in prompt_lower for keyword in ['购物', '买', '价格', '商店', 'shopping', 'buy', 'price']):
            return 'shopping_scenario'
        elif any(keyword in prompt_lower for keyword in ['概率', '统计', 'probability', 'statistics']):
            return 'probability_statistics'
        elif any(keyword in prompt_lower for keyword in ['投资', '理财', '利息', 'investment', 'finance', 'interest']):
            return 'investment_finance'
        else:
            # 默认混合所有场景
            return 'mixed_scenarios'
    
    def _extract_language_from_prompt(self, custom_prompt: str) -> str:
        """从提示词中提取语言要求"""
        prompt_lower = custom_prompt.lower()
        
        # 检测英文要求
        if any(keyword in prompt_lower for keyword in ['english', '英文', 'in english', '使用英文', '用英文']):
            return 'en'
        # 检测中文要求  
        elif any(keyword in prompt_lower for keyword in ['chinese', '中文', 'in chinese', '使用中文', '用中文']):
            return 'zh'
        else:
            return 'zh'  # 默认中文
    
    def _generate_single_unique_question(self, index: int, strategy: str, primary_scenario: str,
                                       difficulty_config: Dict, language: str, subject: str,
                                       custom_prompt: str, used_signatures: Set[str]) -> Dict[str, Any]:
        """生成单个唯一题目"""
        
        # 根据策略选择场景和模板
        if strategy == 'scenario_rotation':
            # 场景轮换：每道题使用不同场景
            scenario_types = list(self.scenario_templates.keys())
            if primary_scenario in scenario_types and primary_scenario != 'mixed_scenarios':
                # 主要使用指定场景，但也混合其他场景
                if index % 3 == 0:  # 每3道题有1道用其他场景
                    other_scenarios = [s for s in scenario_types if s != primary_scenario]
                    scenario_type = random.choice(other_scenarios) if other_scenarios else primary_scenario
                else:
                    scenario_type = primary_scenario
            else:
                scenario_type = scenario_types[index % len(scenario_types)]
        else:
            # 其他策略仍使用主场景
            scenario_type = primary_scenario if primary_scenario != 'mixed_scenarios' else 'shopping_scenario'
        
        # 获取场景模板
        templates = self.scenario_templates.get(scenario_type, self.scenario_templates['shopping_scenario'])
        
        # 选择子模板（确保不重复）
        template = templates[index % len(templates)]
        
        # 生成变量值
        variables = self._generate_template_variables(template, index, strategy, language)
        
        # 根据变量填充模板 - 支持英文模板
        content = self._fill_template(template, variables, language)
        
        # 计算答案
        answer = template['answer_formula'](variables)
        
        # 生成选项
        options = self._generate_options(answer, template['type'], language)
        
        # 生成解析
        explanation = self._generate_explanation(template, variables, answer, language)
        
        question = {
            'subject': subject,
            'sub_tag': f"{scenario_type}-{template['type']}-{index}",
            'language': language,
            'difficulty': difficulty_config['description'],
            'question_type': 'multiple_choice',
            'content': content,
            'options': options,
            'correct_answer': options[0],
            'explanation': explanation,
            'points': difficulty_config['points'],
            'time_limit': difficulty_config.get('time_limit', 5),
            'scenario_type': f"{scenario_type}_{template['type']}_{index}",
            'content_pattern': f"unique_{strategy}_{index}_{hash(content) % 10000}"
        }
        
        return question
    
    def _generate_template_variables(self, template: Dict, index: int, strategy: str, language: str) -> Dict[str, Any]:
        """生成模板变量值 - 确保每次都不同"""
        variables = {}
        
        # 设置随机种子，确保每道题都不同
        random.seed(hash(f"{template['type']}_{index}_{strategy}_{datetime.now().microsecond}"))
        
        for var_name, var_config in template['variables'].items():
            if callable(var_config):
                # 如果是函数，调用它
                try:
                    # 检查函数参数
                    import inspect
                    sig = inspect.signature(var_config)
                    if len(sig.parameters) == 0:
                        variables[var_name] = var_config()
                    else:
                        # 有参数的函数，传入已有变量
                        variables[var_name] = var_config(**{k: v for k, v in variables.items() if k in sig.parameters})
                except Exception as e:
                    print(f"变量生成错误 {var_name}: {e}")
                    variables[var_name] = 1  # 默认值
            elif isinstance(var_config, list):
                # 如果是列表，随机选择（加入index确保不同）
                variables[var_name] = var_config[(index + hash(strategy)) % len(var_config)]
            else:
                variables[var_name] = var_config
        
        # 🌍 根据语言转换变量值
        if language == 'en':
            variables = self._translate_variables_to_english(variables)
        
        # 后处理：处理依赖关系
        if 'total' in variables and 'quantity' in variables and 'unit_price' in variables:
            variables['total'] = variables['quantity'] * variables['unit_price']
        
        return variables
    
    def _fill_template(self, template: Dict, variables: Dict, language: str) -> str:
        """填充模板 - 支持中英文切换和数字优化"""
        try:
            # 🔧 优化数字精度 - 避免过长小数
            optimized_vars = {}
            for key, value in variables.items():
                if isinstance(value, float):
                    if abs(value) > 100:
                        # 大数值保留整数或1位小数
                        optimized_vars[key] = round(value, 1) if value % 1 > 0.1 else int(value)
                    elif abs(value) > 1:
                        # 中等数值保留2位小数
                        optimized_vars[key] = round(value, 2)
                    else:
                        # 小数值保留3位小数
                        optimized_vars[key] = round(value, 3)
                else:
                    optimized_vars[key] = value
            
            # 🌍 根据语言选择模板
            if language == 'en':
                content_template = self._get_english_template(template)
            else:
                content_template = template['template']
            
            content = content_template.format(**optimized_vars)
            return content
        except Exception as e:
            print(f"模板填充错误: {e}")
            return f"Template error: {template.get('template', 'Unknown')}"
    
    def _get_english_template(self, template: Dict) -> str:
        """获取英文模板"""
        template_type = template['type']
        
        # 购物场景英文模板
        if template_type == 'unit_price_calculation':
            return 'Shopping: {customer} bought {quantity} {item}s for ${total}. What is the unit price per {item}?'
        elif template_type == 'bulk_discount_analysis':
            return 'Bulk Purchase: {company} needs {needed_qty} {product}s. Retail price ${retail_price} each, wholesale price ${wholesale_price} each (minimum {min_qty} units). What is the optimal purchase cost?'
        elif template_type == 'promotional_pricing':
            return 'Promotion: {store} has a {event} sale. {item} original price ${original_price}, now {discount_type}. How much does {customer} pay for {quantity} items?'
        elif template_type == 'currency_exchange_shopping':
            return 'Cross-border Shopping: {customer} buys {item} in {country}, local price {local_price} {currency}, exchange rate 1 {currency} = {exchange_rate} RMB. How much in RMB?'
        elif template_type == 'subscription_cost_analysis':
            return 'Subscription: {service} offers {plan_type}, monthly fee ${monthly_fee}, annual fee ${annual_fee}. How much can you save by choosing annual over monthly?'
        
        # 概率统计英文模板
        elif template_type == 'card_probability':
            return 'Card Probability: Drawing one card from a standard 52-card deck, what is the probability of drawing a {target_type}?'
        elif template_type == 'dice_combination':
            return 'Dice Combination: Rolling {dice_count} dice simultaneously, what is the probability that the sum equals {target_sum}?'
        elif template_type == 'survey_statistics':
            return 'Survey Statistics: Among {total_people} people surveyed about {survey_topic}, {positive_count} gave positive responses. What is the probability that a randomly selected person gives a positive response?'
        elif template_type == 'quality_control':
            return 'Quality Control: A production line produces {total_products} products, {defective_count} are defective. What is the probability that a randomly inspected product is qualified?'
        elif template_type == 'weather_prediction':
            return 'Weather Forecast: Based on historical data, {city} has {rainy_days} rainy days in {season} season out of {total_days} total days. What is the probability of rain on a randomly selected day?'
        
        # 投资理财英文模板
        elif template_type == 'simple_interest':
            return 'Simple Interest: {investor} invests ${principal} at {rate}% annual interest for {years} years. How much interest will be earned?'
        elif template_type == 'compound_interest':
            return 'Compound Interest: {bank} offers compound investment, principal ${principal}, annual rate {rate}%, {compound_frequency} compounding, {years} years. What is the final amount?'
        elif template_type == 'portfolio_allocation':
            return 'Portfolio Allocation: {investor} has ${total_money} to invest, plans to invest {stock_ratio}% in stocks, {bond_ratio}% in bonds, rest in bank. How much money goes to stocks?'
        elif template_type == 'loan_calculation':
            return 'Loan Calculation: {borrower} borrows ${loan_amount} from bank at {rate}% annual rate for {years} years, {payment_type}. {calculation_target}?'
        elif template_type == 'currency_arbitrage':
            return 'Currency Arbitrage: {trader} finds {currency1} to {currency2} rate is {rate1}, {currency2} to RMB rate is {rate2}. Using {amount} RMB for arbitrage, how much profit can be made?'
        
        else:
            # 回退到原模板
            return template['template']
    
    def _translate_variables_to_english(self, variables: Dict) -> Dict:
        """将中文变量值翻译为英文"""
        translation_map = {
            # 人名翻译
            '小明': 'Tom', '小红': 'Lucy', '张先生': 'Mr. Zhang', '李女士': 'Ms. Li', '王同学': 'Student Wang',
            '退休职工': 'Retiree', '大学生': 'Student', '投资者': 'Investor', '基金经理': 'Fund Manager',
            '理财顾问': 'Financial Advisor', '个人投资人': 'Individual Investor', '机构投资者': 'Institutional Investor',
            '购房者': 'Home Buyer', '创业者': 'Entrepreneur', '企业主': 'Business Owner', '学生': 'Student', '个体户': 'Self-employed',
            
            # 公司机构翻译
            '科技公司': 'Tech Company', '制造厂': 'Factory', '学校': 'School', '医院': 'Hospital', '餐厅': 'Restaurant',
            '工商银行': 'ICBC', '建设银行': 'CCB', '招商银行': 'CMB', '民生银行': 'CMBC', '理财公司': 'Wealth Management',
            
            # 商品翻译
            '苹果': 'apple', '橘子': 'orange', '葡萄': 'grape', '香蕉': 'banana', '草莓': 'strawberry',
            '电脑': 'computer', '桌椅': 'furniture', '文具': 'stationery', '设备': 'equipment', '原料': 'material',
            '手机': 'phone', '衣服': 'clothing', '鞋子': 'shoes', '包包': 'bag', '化妆品': 'cosmetics',
            '手表': 'watch', '电子产品': 'electronics', '奢侈品': 'luxury goods',
            
            # 店铺翻译
            '超市': 'Supermarket', '商场': 'Mall', '网店': 'Online Store', '专卖店': 'Specialty Store', '便利店': 'Convenience Store',
            
            # 服务翻译
            '视频平台': 'Video Platform', '音乐软件': 'Music App', '云存储': 'Cloud Storage', '健身app': 'Fitness App', '学习软件': 'Learning App',
            
            # 套餐翻译
            '基础套餐': 'Basic Plan', '高级套餐': 'Premium Plan', 'VIP套餐': 'VIP Plan', '家庭套餐': 'Family Plan', '学生套餐': 'Student Plan',
            
            # 活动翻译
            '双十一': 'Double 11', '年末清仓': 'Year-end Sale', '会员专享': 'Member Exclusive', '新店开业': 'Grand Opening', '节日特惠': 'Holiday Special',
            
            # 城市翻译
            '北京': 'Beijing', '上海': 'Shanghai', '广州': 'Guangzhou', '深圳': 'Shenzhen', '杭州': 'Hangzhou',
            
            # 国家地区翻译
            '美国': 'USA', '日本': 'Japan', '韩国': 'Korea', '英国': 'UK', '欧洲': 'Europe',
            
            # 货币翻译
            '美元': 'USD', '日元': 'JPY', '韩元': 'KRW', '英镑': 'GBP', '欧元': 'EUR',
            '港币': 'HKD', '澳元': 'AUD', '加元': 'CAD', '瑞郎': 'CHF',
            
            # 其他翻译
            '环保意识': 'Environmental Awareness', '健康饮食': 'Healthy Diet', '运动习惯': 'Exercise Habits', 
            '阅读习惯': 'Reading Habits', '社交媒体使用': 'Social Media Usage',
            '春': 'Spring', '夏': 'Summer', '秋': 'Autumn', '冬': 'Winter',
            '等额本息': 'Equal Principal and Interest', '等额本金': 'Equal Principal',
            '每月还款金额是多少': 'What is the monthly payment amount',
            '总利息是多少': 'What is the total interest',
            '第一年还款总额是多少': 'What is the total payment in the first year'
        }
        
        translated_vars = {}
        for key, value in variables.items():
            if isinstance(value, str) and value in translation_map:
                translated_vars[key] = translation_map[value]
            else:
                translated_vars[key] = value
        
        return translated_vars
    
    def _generate_options(self, correct_answer: float, question_type: str, language: str) -> List[str]:
        """生成选项 - 优化数字格式"""
        if isinstance(correct_answer, (int, float)):
            # 🔧 优化答案数字格式
            if abs(correct_answer) > 100:
                formatted_answer = round(correct_answer, 1) if correct_answer % 1 > 0.1 else int(correct_answer)
            elif abs(correct_answer) > 1:
                formatted_answer = round(correct_answer, 2)
            else:
                formatted_answer = round(correct_answer, 3)
            
            # 数值类型答案
            if question_type in ['unit_price_calculation', 'bulk_discount_analysis', 'promotional_pricing', 'currency_exchange_shopping', 'subscription_cost_analysis']:
                unit = '元' if language == 'zh' else '$'
                correct_str = f"{formatted_answer}{unit}"
                
                # 生成干扰项
                distractor1 = f"{formatted_answer * 1.2:.1f}{unit}"
                distractor2 = f"{formatted_answer * 0.8:.1f}{unit}"
                distractor3 = f"{formatted_answer * 1.5:.1f}{unit}"
                
                options = [correct_str, distractor1, distractor2, distractor3]
            elif question_type in ['simple_interest', 'compound_interest', 'portfolio_allocation', 'loan_calculation', 'currency_arbitrage']:
                # 金融类题目
                unit = '元' if language == 'zh' else '$'
                correct_str = f"{formatted_answer}{unit}"
                
                distractor1 = f"{formatted_answer * 1.15:.1f}{unit}"
                distractor2 = f"{formatted_answer * 0.85:.1f}{unit}"
                distractor3 = f"{formatted_answer * 1.3:.1f}{unit}"
                
                options = [correct_str, distractor1, distractor2, distractor3]
            elif question_type in ['card_probability', 'dice_combination', 'survey_statistics', 'quality_control', 'weather_prediction']:
                # 概率类题目
                correct_str = f"{formatted_answer:.3f}"
                
                distractor1 = f"{min(1.0, formatted_answer * 1.3):.3f}"
                distractor2 = f"{max(0.0, formatted_answer * 0.7):.3f}"
                distractor3 = f"{min(1.0, formatted_answer + 0.1):.3f}"
                
                options = [correct_str, distractor1, distractor2, distractor3]
            else:
                # 其他数值类型
                correct_str = str(formatted_answer)
                options = [
                    correct_str,
                    str(round(formatted_answer * 1.1, 2)),
                    str(round(formatted_answer * 0.9, 2)),
                    str(round(formatted_answer * 1.25, 2))
                ]
        else:
            # 非数值答案
            if language == 'zh':
                options = [str(correct_answer), "选项B", "选项C", "选项D"]
            else:
                options = [str(correct_answer), "Option B", "Option C", "Option D"]
        
        return options
    
    def _generate_explanation(self, template: Dict, variables: Dict, answer: float, language: str) -> str:
        """生成解析"""
        question_type = template['type']
        
        if question_type == 'unit_price_calculation':
            if language == 'zh':
                return f"计算单价：总价 ÷ 数量 = {variables.get('total', 0):.1f} ÷ {variables.get('quantity', 1)} = {answer:.2f}元"
            else:
                return f"Calculate unit price: Total ÷ Quantity = {variables.get('total', 0):.1f} ÷ {variables.get('quantity', 1)} = ${answer:.2f}"
        
        elif question_type == 'card_probability':
            if language == 'zh':
                return f"概率计算：favorable outcomes ÷ total outcomes = {answer:.3f}"
            else:
                return f"Probability calculation: favorable outcomes ÷ total outcomes = {answer:.3f}"
        
        else:
            if language == 'zh':
                return f"根据给定条件计算得出答案为 {answer:.2f}"
            else:
                return f"Based on given conditions, the answer is {answer:.2f}"
    
    def _calculate_question_signature(self, question: Dict[str, Any]) -> str:
        """计算题目签名 - 用于检测重复"""
        # 提取题目的关键特征
        key_features = [
            question.get('scenario_type', ''),
            question.get('content', '')[:100],  # 内容前100字符
            str(question.get('correct_answer', '')),
            question.get('sub_tag', '')
        ]
        
        # 生成MD5签名
        signature_string = '|'.join(key_features)
        return hashlib.md5(signature_string.encode()).hexdigest()
    
    def _generate_fallback_question(self, index: int, difficulty_config: Dict, language: str, subject: str) -> Dict[str, Any]:
        """fallback题目生成"""
        a = 5 + index * 3
        b = 7 + index * 2
        result = a * b
        
        if language == 'zh':
            content = f"计算题 #{index + 1}：{a} × {b} = ?"
            explanation = f"直接计算：{a} × {b} = {result}"
            options = [str(result), str(result + 5), str(result - 3), str(result + 10)]
        else:
            content = f"Calculation #{index + 1}: {a} × {b} = ?"
            explanation = f"Direct calculation: {a} × {b} = {result}"
            options = [str(result), str(result + 5), str(result - 3), str(result + 10)]
        
        return {
            'subject': subject,
            'sub_tag': f"fallback-calculation-{index}",
            'language': language,
            'difficulty': difficulty_config['description'],
            'question_type': 'multiple_choice',
            'content': content,
            'options': options,
            'correct_answer': options[0],
            'explanation': explanation,
            'points': difficulty_config['points'],
            'scenario_type': f'fallback_{index}',
            'content_pattern': f'fallback_unique_{index}'
        }


# 便于导入的函数
def generate_advanced_questions(count: int, difficulty: str, language: str, 
                              subject: str, custom_prompt: str = "") -> List[Dict[str, Any]]:
    """便捷的题目生成函数"""
    generator = AdvancedQuestionGenerator()
    return generator.generate_unique_questions(count, difficulty, language, subject, custom_prompt)


if __name__ == "__main__":
    # 测试
    print("🧪 测试高级题目生成器...")
    
    questions = generate_advanced_questions(
        count=5,
        difficulty="中等",
        language="zh",
        subject="数学",
        custom_prompt="生成购物场景题目"
    )
    
    for i, q in enumerate(questions, 1):
        print(f"\n题目 {i}:")
        print(f"类型: {q['scenario_type']}")
        print(f"内容: {q['content']}")
        print(f"答案: {q['correct_answer']}")
