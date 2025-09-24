#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API管理器 - 统一管理多种API提供商
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import requests


class ApiProvider(Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ApiConfig:
    provider: ApiProvider
    api_key: str
    api_url: str
    default_model: str
    headers_template: Dict[str, str]
    request_template: Dict[str, Any]


class ApiManager:
    """统一API管理器"""

    def __init__(self):
        self.current_provider = None
        self.api_configs = {}
        self._load_default_configs()
        self._load_from_database()

    def _load_default_configs(self):
        """加载默认API配置"""
        self.default_configs = {
            ApiProvider.OPENROUTER: {
                "api_url": "https://openrouter.ai/api/v1/chat/completions",
                "default_model": "openai/gpt-4-turbo-preview",
                "headers_template": {
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://cbit-exam-system.com",
                    "X-Title": "CBIT Exam Question Generator",
                },
                "request_template": {
                    "model": "{model}",
                    "messages": "{messages}",
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "top_p": 0.9,
                },
            },
            ApiProvider.OPENAI: {
                "api_url": "https://api.openai.com/v1/chat/completions",
                "default_model": "gpt-4-turbo-preview",
                "headers_template": {
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                "request_template": {
                    "model": "{model}",
                    "messages": "{messages}",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            },
            ApiProvider.ANTHROPIC: {
                "api_url": "https://api.anthropic.com/v1/messages",
                "default_model": "claude-3-sonnet-20240229",
                "headers_template": {
                    "x-api-key": "{api_key}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                "request_template": {
                    "model": "{model}",
                    "max_tokens": 2000,
                    "messages": "{messages}",
                },
            },
        }

    def _load_from_database(self):
        """从数据库加载API配置"""
        try:
            import os
            import sys

            # 修复导入路径问题
            backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
            if backend_path not in sys.path:
                sys.path.append(backend_path)

            from sqlalchemy import create_engine, text

            db_path = os.path.join(
                os.path.dirname(__file__), "..", "instance", "exam.db"
            )
            if os.path.exists(db_path):
                engine = create_engine(f"sqlite:///{db_path}")
                with engine.connect() as conn:
                    # 查询API提供商配置
                    result = conn.execute(
                        text(
                            """
                        SELECT provider_name, api_url, api_key, is_active, default_model, 
                               headers_template, request_template 
                        FROM api_providers WHERE is_verified = 1
                    """
                        )
                    ).fetchall()

                    print(f"🔍 从数据库查询到 {len(result)} 个API配置")

                    for row in result:
                        try:
                            provider = ApiProvider(row[0])  # provider_name
                            api_config = ApiConfig(
                                provider=provider,
                                api_key=row[2],  # api_key
                                api_url=row[1],  # api_url
                                default_model=row[4],  # default_model
                                headers_template=(
                                    json.loads(row[5]) if row[5] else {}
                                ),  # headers_template
                                request_template=(
                                    json.loads(row[6]) if row[6] else {}
                                ),  # request_template
                            )
                            self.api_configs[provider] = api_config

                            if row[3]:  # is_active
                                self.current_provider = provider
                                print(f"✅ 设置活跃提供商: {provider.value}")
                        except Exception as e:
                            print(f"⚠️ 跳过无效的API配置: {row[0]} - {str(e)}")

                    # 如果没有激活的提供商，尝试从旧的系统配置读取
                    if not self.current_provider:
                        self._load_legacy_config(conn)

        except Exception as e:
            print(f"⚠️  从数据库加载API配置失败: {str(e)}")
            # 尝试从环境变量加载
            self._load_from_env()

    def _load_legacy_config(self, conn):
        """加载旧版本的API配置"""
        try:
            from sqlalchemy import text

            # 查询旧的API配置
            api_key_result = conn.execute(
                text(
                    "SELECT config_value FROM system_configs WHERE config_key = 'openrouterApiKey'"
                )
            ).fetchone()
            model_result = conn.execute(
                text(
                    "SELECT config_value FROM system_configs WHERE config_key = 'aiModel'"
                )
            ).fetchone()

            if api_key_result and api_key_result[0]:
                # 创建OpenRouter配置
                config = self.default_configs[ApiProvider.OPENROUTER].copy()
                api_config = ApiConfig(
                    provider=ApiProvider.OPENROUTER,
                    api_key=api_key_result[0],
                    api_url=config["api_url"],
                    default_model=(
                        model_result[0] if model_result else config["default_model"]
                    ),
                    headers_template=config["headers_template"],
                    request_template=config["request_template"],
                )
                self.api_configs[ApiProvider.OPENROUTER] = api_config
                self.current_provider = ApiProvider.OPENROUTER
                print(f"🔧 从旧配置加载OpenRouter API")

        except Exception as e:
            print(f"⚠️  加载旧配置失败: {str(e)}")

    def _load_from_env(self):
        """从环境变量加载配置"""
        # OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            config = self.default_configs[ApiProvider.OPENROUTER].copy()
            api_config = ApiConfig(
                provider=ApiProvider.OPENROUTER,
                api_key=openrouter_key,
                api_url=config["api_url"],
                default_model=os.getenv("AI_MODEL", config["default_model"]),
                headers_template=config["headers_template"],
                request_template=config["request_template"],
            )
            self.api_configs[ApiProvider.OPENROUTER] = api_config
            if not self.current_provider:
                self.current_provider = ApiProvider.OPENROUTER

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            config = self.default_configs[ApiProvider.OPENAI].copy()
            api_config = ApiConfig(
                provider=ApiProvider.OPENAI,
                api_key=openai_key,
                api_url=config["api_url"],
                default_model=config["default_model"],
                headers_template=config["headers_template"],
                request_template=config["request_template"],
            )
            self.api_configs[ApiProvider.OPENAI] = api_config
            if not self.current_provider:
                self.current_provider = ApiProvider.OPENAI

    def has_valid_api(self) -> bool:
        """检查是否有有效的API配置"""
        if (
            self.current_provider is not None
            and self.current_provider in self.api_configs
        ):
            return True

        # 如果没有激活的API，但有已验证的API，自动激活第一个
        print("🔍 没有激活的API，检查是否有已验证的API可以自动激活...")

        try:
            providers = self.get_available_providers()
            verified_providers = [p for p in providers if p.get("is_verified")]

            if verified_providers:
                provider_name = verified_providers[0]["name"]
                print(f"🔄 自动激活已验证的API: {provider_name}")

                try:
                    provider_enum = ApiProvider(provider_name)
                    if self.activate_provider(provider_enum):
                        print(f"✅ 自动激活成功: {provider_name}")
                        return True
                except ValueError:
                    print(f"❌ 无效的提供商名称: {provider_name}")

        except Exception as e:
            print(f"⚠️ 自动激活失败: {str(e)}")

        return False

    def get_current_config(self) -> Optional[ApiConfig]:
        """获取当前激活的API配置"""
        if self.current_provider and self.current_provider in self.api_configs:
            return self.api_configs[self.current_provider]
        return None

    def set_active_provider(self, provider: ApiProvider) -> bool:
        """设置激活的API提供商"""
        if provider in self.api_configs:
            self.current_provider = provider
            return True
        return False

    def validate_api_key(self, provider: ApiProvider, api_key: str) -> Dict[str, Any]:
        """验证API密钥"""
        try:
            config = self.default_configs[provider]

            # 构建请求头
            headers = {}
            for key, template in config["headers_template"].items():
                headers[key] = template.format(api_key=api_key)

            # 测试请求
            if provider == ApiProvider.OPENROUTER:
                # 获取模型列表
                models_url = "https://openrouter.ai/api/v1/models"
                response = requests.get(models_url, headers=headers, timeout=10)

                if response.status_code == 200:
                    models_data = response.json()
                    print(f"🔍 OpenRouter API响应: {models_data}")

                    # 处理OpenRouter的响应格式
                    raw_models = models_data.get("data", [])
                    if not raw_models:
                        print("⚠️ OpenRouter返回的模型列表为空")
                        return {"success": False, "error": "未获取到可用模型列表"}

                    # 筛选推荐的模型 - 扩大筛选范围
                    recommended_models = []
                    for model in raw_models:
                        model_id = model.get("id", "")
                        model_name = model.get("name", model_id)

                        # 扩大模型筛选范围，包含更多常用模型
                        if any(
                            keyword in model_id.lower()
                            for keyword in [
                                "gpt-4",
                                "gpt-3.5",
                                "gpt-35",
                                "claude-3",
                                "claude-2",
                                "claude",
                                "gemini",
                                "palm",
                                "llama",
                                "mistral",
                                "qwen",
                                "deepseek",
                                "yi-",
                                "chatgpt",
                                "o1-",
                                "sonnet",
                                "haiku",
                                "opus",
                            ]
                        ):
                            recommended_models.append(
                                {
                                    "id": model_id,
                                    "name": model_name,
                                    "context_length": model.get("context_length", 0),
                                    "pricing": model.get("pricing", {}),
                                }
                            )

                    # 如果筛选结果太少，添加更多模型
                    if len(recommended_models) < 10:
                        print("⚠️ 推荐模型数量较少，添加更多模型...")
                        for model in raw_models:
                            model_id = model.get("id", "")
                            model_name = model.get("name", model_id)

                            # 添加OpenAI和Anthropic的所有模型
                            if (
                                "openai/" in model_id
                                or "anthropic/" in model_id
                                or "google/" in model_id
                                or "meta-llama/" in model_id
                            ):
                                if not any(
                                    m["id"] == model_id for m in recommended_models
                                ):
                                    recommended_models.append(
                                        {
                                            "id": model_id,
                                            "name": model_name,
                                            "context_length": model.get(
                                                "context_length", 0
                                            ),
                                            "pricing": model.get("pricing", {}),
                                        }
                                    )

                            if len(recommended_models) >= 20:
                                break

                    print(f"✅ 筛选出 {len(recommended_models)} 个推荐模型")

                    # 按提供商和名称排序
                    recommended_models.sort(
                        key=lambda x: (x["id"].split("/")[0], x["name"])
                    )

                    return {
                        "success": True,
                        "models": recommended_models,
                    }  # 返回所有筛选出的模型，不设上限
                else:
                    error_text = response.text
                    print(
                        f"❌ OpenRouter API调用失败: {response.status_code} - {error_text}"
                    )
                    return {
                        "success": False,
                        "error": f"API验证失败: {response.status_code}",
                    }

            elif provider == ApiProvider.OPENAI:
                # 首先获取可用模型列表
                models_url = "https://api.openai.com/v1/models"
                models_response = requests.get(models_url, headers=headers, timeout=10)

                if models_response.status_code == 200:
                    models_data = models_response.json()
                    raw_models = models_data.get("data", [])

                    print(f"📊 OpenAI API返回 {len(raw_models)} 个原始模型")

                    # 筛选出聊天模型
                    chat_models = []
                    for model in raw_models:
                        model_id = model.get("id", "")

                        # 筛选出主要的聊天模型
                        if any(
                            keyword in model_id
                            for keyword in [
                                "gpt-4",
                                "gpt-3.5",
                                "gpt-4o",
                                "o1-preview",
                                "o1-mini",
                            ]
                        ):
                            # 排除一些不常用的变体
                            if not any(
                                exclude in model_id
                                for exclude in [
                                    "instruct",
                                    "edit",
                                    "search",
                                    "similarity",
                                    "davinci",
                                    "curie",
                                    "babbage",
                                    "ada",
                                ]
                            ):
                                chat_models.append(
                                    {
                                        "id": model_id,
                                        "name": model_id.replace("-", " ").title(),
                                        "owned_by": model.get("owned_by", "openai"),
                                    }
                                )

                    # 按模型名称排序
                    chat_models.sort(key=lambda x: x["id"])

                    print(f"✅ 筛选出 {len(chat_models)} 个OpenAI聊天模型")

                    if not chat_models:
                        # 如果没有筛选出模型，使用默认列表
                        chat_models = [
                            {"id": "gpt-4o", "name": "GPT-4o"},
                            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
                            {"id": "gpt-4", "name": "GPT-4"},
                            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                        ]

                    return {"success": True, "models": chat_models}
                else:
                    print(f"❌ 获取OpenAI模型列表失败: {models_response.status_code}")
                    # 验证API密钥的有效性
                    test_data = {
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 5,
                    }
                    test_response = requests.post(
                        config["api_url"], headers=headers, json=test_data, timeout=10
                    )

                    if test_response.status_code == 200:
                        # API密钥有效，但无法获取模型列表，使用默认列表
                        default_models = [
                            {"id": "gpt-4o", "name": "GPT-4o"},
                            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
                            {"id": "gpt-4", "name": "GPT-4"},
                            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                        ]
                        return {"success": True, "models": default_models}
                    else:
                        return {
                            "success": False,
                            "error": f"API验证失败: {test_response.status_code}",
                        }

            elif provider == ApiProvider.ANTHROPIC:
                # Anthropic API验证逻辑 - 先测试API有效性
                test_data = {
                    "model": "claude-3-haiku-20240307",  # 使用固定的可用模型
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "test"}],
                }
                response = requests.post(
                    config["api_url"], headers=headers, json=test_data, timeout=10
                )

                if response.status_code == 200:
                    # API验证成功，返回完整的Claude模型列表
                    models = [
                        {
                            "id": "claude-3-5-sonnet-20241022",
                            "name": "Claude-3.5 Sonnet (Latest)",
                        },
                        {
                            "id": "claude-3-5-sonnet-20240620",
                            "name": "Claude-3.5 Sonnet",
                        },
                        {"id": "claude-3-5-haiku-20241022", "name": "Claude-3.5 Haiku"},
                        {"id": "claude-3-opus-20240229", "name": "Claude-3 Opus"},
                        {"id": "claude-3-sonnet-20240229", "name": "Claude-3 Sonnet"},
                        {"id": "claude-3-haiku-20240307", "name": "Claude-3 Haiku"},
                    ]
                    print(f"✅ 返回 {len(models)} 个Anthropic模型")
                    return {"success": True, "models": models}
                else:
                    print(f"❌ Anthropic API验证失败: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API验证失败: {response.status_code}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_api(
        self, messages: List[Dict[str, str]], model: str = None
    ) -> Optional[str]:
        """调用当前激活的API"""
        if not self.has_valid_api():
            print("❌ 没有可用的API配置")
            return None

        config = self.get_current_config()

        try:
            # 构建请求头
            headers = {}
            for key, template in config.headers_template.items():
                headers[key] = template.format(api_key=config.api_key)

            # 构建请求数据
            data = config.request_template.copy()

            # 替换模板变量
            actual_model = model or config.default_model
            for key, value in data.items():
                if isinstance(value, str):
                    if value == "{model}":
                        data[key] = actual_model
                    elif value == "{messages}":
                        data[key] = messages

            # 特殊处理Anthropic API格式
            if config.provider == ApiProvider.ANTHROPIC:
                # Anthropic使用不同的消息格式
                if messages and messages[0].get("role") == "system":
                    system_content = messages[0]["content"]
                    user_messages = messages[1:]
                    data["system"] = system_content
                    data["messages"] = user_messages
                else:
                    data["messages"] = messages

            print(f"🌐 发送API请求到: {config.api_url}")
            print(f"🤖 使用模型: {actual_model}")
            print(f"🔧 提供商: {config.provider.value}")

            response = requests.post(
                config.api_url, headers=headers, json=data, timeout=30
            )
            print(f"📊 响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()

                # 根据不同提供商解析响应
                if config.provider == ApiProvider.ANTHROPIC:
                    return result.get("content", [{}])[0].get("text", "")
                else:
                    return result["choices"][0]["message"]["content"]
            else:
                print(f"❌ API调用失败: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ API调用异常: {str(e)}")
            return None

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """获取可用的API提供商列表"""
        import os
        import sys

        from sqlalchemy import create_engine, text

        providers = []

        # 从数据库获取实际配置状态
        db_configs = {}
        try:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "instance", "exam.db"
            )
            if os.path.exists(db_path):
                engine = create_engine(f"sqlite:///{db_path}")
                with engine.connect() as conn:
                    result = conn.execute(
                        text(
                            """
                        SELECT provider_name, is_active, is_verified, default_model 
                        FROM api_providers
                    """
                        )
                    ).fetchall()

                    for row in result:
                        db_configs[row[0]] = {
                            "is_active": bool(row[1]),
                            "is_verified": bool(row[2]),
                            "default_model": row[3],
                        }
        except Exception as e:
            print(f"⚠️ 获取数据库配置失败: {str(e)}")

        for provider in ApiProvider:
            config = self.default_configs[provider]
            provider_name = provider.value

            # 从数据库获取实际状态
            db_info = db_configs.get(provider_name, {})
            has_config = provider in self.api_configs or db_info.get(
                "is_verified", False
            )
            is_active = provider == self.current_provider or db_info.get(
                "is_active", False
            )
            default_model = db_info.get("default_model") or config["default_model"]

            providers.append(
                {
                    "name": provider_name,
                    "display_name": provider.value.title(),
                    "has_config": has_config,
                    "is_active": is_active,
                    "is_verified": db_info.get("is_verified", False),
                    "default_model": default_model,
                    "api_url": config["api_url"],
                }
            )

            print(
                f"📋 提供商 {provider_name}: 有配置={has_config}, 激活={is_active}, 验证={db_info.get('is_verified', False)}"
            )

        return providers

    def save_provider_config(
        self, provider: ApiProvider, api_key: str, model: str = None
    ) -> bool:
        """保存API提供商配置到数据库"""
        try:
            import os
            import sys

            backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
            if backend_path not in sys.path:
                sys.path.append(backend_path)

            # 优先尝试使用Flask应用上下文
            try:
                from flask import current_app
                from models import ApiProvider as ApiProviderModel
                from models import db

                # 检查Flask应用上下文
                if current_app:
                    return self._save_with_flask_context(provider, api_key, model)
            except (ImportError, RuntimeError):
                print("⚠️ Flask上下文不可用，使用直接数据库连接")

            # 回退到直接数据库连接
            from sqlalchemy import create_engine, text

            db_path = os.path.join(
                os.path.dirname(__file__), "..", "instance", "exam.db"
            )
            if not os.path.exists(db_path):
                print(f"❌ 数据库文件不存在: {db_path}")
                return False

            engine = create_engine(f"sqlite:///{db_path}")

            config = self.default_configs[provider]
            default_model = model or config["default_model"]

            print(f"🔍 验证API密钥...")
            # 先验证API
            validation_result = self.validate_api_key(provider, api_key)
            if not validation_result.get("success"):
                print(f"❌ API验证失败: {validation_result.get('error')}")
                return False

            print(f"✅ API验证成功，开始保存配置...")

            with engine.begin() as conn:  # 使用begin()自动处理事务
                # 检查是否已存在
                existing = conn.execute(
                    text(
                        "SELECT id FROM api_providers WHERE provider_name = :provider"
                    ),
                    {"provider": provider.value},
                ).fetchone()

                if existing:
                    # 更新现有配置
                    result = conn.execute(
                        text(
                            """
                        UPDATE api_providers 
                        SET api_key = :api_key, 
                            default_model = :model,
                            is_verified = 1,
                            updated_at = datetime('now')
                        WHERE provider_name = :provider
                    """
                        ),
                        {
                            "api_key": api_key,
                            "model": default_model,
                            "provider": provider.value,
                        },
                    )
                    print(f"✅ 更新API配置，影响行数: {result.rowcount}")
                else:
                    # 插入新配置
                    result = conn.execute(
                        text(
                            """
                        INSERT INTO api_providers 
                        (provider_name, display_name, api_url, api_key, is_active, is_verified, 
                         default_model, supported_models, headers_template, request_template)
                        VALUES (:provider, :display_name, :api_url, :api_key, 0, 1, 
                                :model, :models, :headers, :request)
                    """
                        ),
                        {
                            "provider": provider.value,
                            "display_name": provider.value.title(),
                            "api_url": config["api_url"],
                            "api_key": api_key,
                            "model": default_model,
                            "models": json.dumps(validation_result.get("models", [])),
                            "headers": json.dumps(config["headers_template"]),
                            "request": json.dumps(config["request_template"]),
                        },
                    )
                    print(f"✅ 插入新API配置，影响行数: {result.rowcount}")

                    # 事务会自动提交

                # 更新内存中的配置
                api_config = ApiConfig(
                    provider=provider,
                    api_key=api_key,
                    api_url=config["api_url"],
                    default_model=default_model,
                    headers_template=config["headers_template"],
                    request_template=config["request_template"],
                )
                self.api_configs[provider] = api_config

                return True

        except Exception as e:
            print(f"❌ 保存API配置失败: {str(e)}")
            return False

    def activate_provider(self, provider: ApiProvider) -> bool:
        """激活指定的API提供商"""
        try:
            # 先重新加载配置，确保最新的配置被载入内存
            self._load_from_database()

            if provider not in self.api_configs:
                print(f"❌ 提供商 {provider.value} 未找到配置")
                return False

            import os
            import sys

            backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
            if backend_path not in sys.path:
                sys.path.append(backend_path)

            from sqlalchemy import create_engine, text

            db_path = os.path.join(
                os.path.dirname(__file__), "..", "instance", "exam.db"
            )
            if os.path.exists(db_path):
                engine = create_engine(f"sqlite:///{db_path}")

                with engine.begin() as conn:  # 使用begin()自动处理事务
                    # 检查提供商是否存在
                    check_result = conn.execute(
                        text(
                            "SELECT provider_name FROM api_providers WHERE provider_name = :provider"
                        ),
                        {"provider": provider.value},
                    ).fetchone()

                    if not check_result:
                        print(f"❌ 数据库中未找到提供商 {provider.value}")
                        return False

                    # 先将所有提供商设为非激活
                    conn.execute(text("UPDATE api_providers SET is_active = 0"))

                    # 激活指定提供商
                    result = conn.execute(
                        text(
                            "UPDATE api_providers SET is_active = 1 WHERE provider_name = :provider"
                        ),
                        {"provider": provider.value},
                    )

                    if result.rowcount == 0:
                        return False

                    # 事务会自动提交

                self.current_provider = provider
                return True

        except Exception as e:
            print(f"❌ 激活API提供商失败: {str(e)}")
            return False

    def _save_with_flask_context(
        self, provider: ApiProvider, api_key: str, model: str = None
    ) -> bool:
        """使用Flask上下文保存API配置"""
        try:
            import json

            from models import ApiProvider as ApiProviderModel
            from models import db

            config = self.default_configs[provider]
            default_model = model or config["default_model"]

            # 先验证API
            print(f"🔍 使用Flask上下文验证API密钥...")
            validation_result = self.validate_api_key(provider, api_key)
            if not validation_result.get("success"):
                print(f"❌ API验证失败: {validation_result.get('error')}")
                return False

            print(f"✅ API验证成功，使用Flask ORM保存配置...")

            # 查找或创建API提供商记录
            existing = ApiProviderModel.query.filter_by(
                provider_name=provider.value
            ).first()

            if existing:
                # 更新现有配置
                existing.api_key = api_key
                existing.default_model = default_model
                existing.is_verified = True
                existing.supported_models = json.dumps(
                    validation_result.get("models", [])
                )
                print(f"✅ 更新现有配置: {provider.value}")
            else:
                # 创建新配置
                new_provider = ApiProviderModel(
                    provider_name=provider.value,
                    display_name=provider.value.title(),
                    api_url=config["api_url"],
                    api_key=api_key,
                    is_active=False,
                    is_verified=True,
                    default_model=default_model,
                    supported_models=json.dumps(validation_result.get("models", [])),
                    headers_template=json.dumps(config["headers_template"]),
                    request_template=json.dumps(config["request_template"]),
                )
                db.session.add(new_provider)
                print(f"✅ 创建新配置: {provider.value}")

            # 提交事务
            db.session.commit()

            # 更新内存中的配置
            api_config = ApiConfig(
                provider=provider,
                api_key=api_key,
                api_url=config["api_url"],
                default_model=default_model,
                headers_template=config["headers_template"],
                request_template=config["request_template"],
            )
            self.api_configs[provider] = api_config

            print(f"✅ Flask上下文保存成功: {provider.value}")
            return True

        except Exception as e:
            print(f"❌ Flask上下文保存失败: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False
