"""
LLM管理器 - 基于LiteLLM的多模型管理和路由
"""

import os
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
import time
from datetime import datetime

try:
    import litellm
    from litellm import Router, completion
    import tiktoken
except ImportError as e:
    print(f"请安装必要的依赖: pip install litellm tiktoken")
    raise e


@dataclass
class UsageStats:
    """使用统计数据"""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_updated: datetime = None

    def to_dict(self) -> Dict:
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens, 
            'total_cost': self.total_cost,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'average_response_time': self.average_response_time,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class LLMManager:
    """
    LLM模型管理器
    支持多模型路由、降级策略、成本跟踪
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.router = None
        self.usage_stats = UsageStats()
        self._initialize_router()
        
        # 设置LiteLLM日志级别
        litellm.set_verbose = False
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """加载LLM配置"""
        default_config = {
            "models": [
                {
                    "model_name": "gpt-4o-mini",
                    "litellm_params": {
                        "model": "gpt-4o-mini",
                        "api_key": os.getenv("OPENAI_API_KEY"),
                        "timeout": 30
                    },
                    "tpm": 200000,  # tokens per minute
                    "rpm": 1000,    # requests per minute
                    "cost_per_1k_tokens": 0.0001
                },
                {
                    "model_name": "gpt-4o",
                    "litellm_params": {
                        "model": "gpt-4o",
                        "api_key": os.getenv("OPENAI_API_KEY"),
                        "timeout": 60
                    },
                    "tpm": 100000,
                    "rpm": 500,
                    "cost_per_1k_tokens": 0.005
                }
            ],
            "fallback_strategy": "gpt-4o-mini",
            "default_model": "gpt-4o-mini"
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                custom_config = json.load(f)
                # 合并配置
                default_config.update(custom_config)
        
        return default_config
    
    def _initialize_router(self):
        """初始化LiteLLM Router"""
        try:
            self.router = Router(
                model_list=self.config["models"],
                fallbacks=[{"gpt-4o": ["gpt-4o-mini"]}],
                context_window_fallbacks=[{"gpt-4o": ["gpt-4o-mini"]}],
                set_verbose=False
            )
            print("✅ LLM Router初始化成功")
        except Exception as e:
            print(f"❌ LLM Router初始化失败: {e}")
            self.router = None
    
    def count_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """计算文本的token数量"""
        try:
            # 对于OpenAI模型，使用tiktoken
            if "gpt" in model.lower():
                encoding = tiktoken.encoding_for_model(model.replace("gpt-", "gpt-"))
                return len(encoding.encode(text))
            else:
                # 对于其他模型，使用估算（约4字符=1token）
                return len(text) // 4
        except Exception:
            # 如果出错，使用简单估算
            return len(text) // 4
    
    async def completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步完成聊天请求
        """
        if not self.router:
            raise Exception("LLM Router未初始化")
        
        model = model or self.config["default_model"]
        start_time = time.time()
        
        try:
            # 计算输入tokens
            input_text = " ".join([msg["content"] for msg in messages])
            input_tokens = self.count_tokens(input_text, model)
            
            # 调用LiteLLM
            response = await self.router.acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # 更新统计
            response_time = time.time() - start_time
            output_tokens = self.count_tokens(response.choices[0].message.content, model)
            total_tokens = input_tokens + output_tokens
            
            self._update_stats(
                success=True,
                tokens=total_tokens,
                response_time=response_time,
                model=model
            )
            
            return {
                "content": response.choices[0].message.content,
                "model_used": response.model,
                "usage": {
                    "total_tokens": total_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                },
                "response_time": response_time
            }
            
        except Exception as e:
            self._update_stats(success=False, response_time=time.time() - start_time)
            
            # 尝试降级模型
            if model != self.config["fallback_strategy"]:
                print(f"⚠️ 模型 {model} 失败，尝试降级到 {self.config['fallback_strategy']}")
                return await self.completion(
                    messages, 
                    model=self.config["fallback_strategy"],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            
            raise Exception(f"LLM请求失败: {e}")
    
    def _update_stats(
        self, 
        success: bool, 
        tokens: int = 0, 
        response_time: float = 0,
        model: str = None
    ):
        """更新使用统计"""
        self.usage_stats.total_requests += 1
        
        if success:
            self.usage_stats.successful_requests += 1
            self.usage_stats.total_tokens += tokens
            
            # 计算成本
            cost_per_1k = self._get_model_cost(model)
            self.usage_stats.total_cost += (tokens / 1000) * cost_per_1k
        else:
            self.usage_stats.failed_requests += 1
        
        # 更新平均响应时间
        total_responses = self.usage_stats.successful_requests + self.usage_stats.failed_requests
        self.usage_stats.average_response_time = (
            (self.usage_stats.average_response_time * (total_responses - 1) + response_time) 
            / total_responses
        )
        
        self.usage_stats.last_updated = datetime.now()
    
    def _get_model_cost(self, model: str) -> float:
        """获取模型的成本（每1000 tokens）"""
        for model_config in self.config["models"]:
            if model_config["model_name"] == model:
                return model_config.get("cost_per_1k_tokens", 0.0)
        return 0.0
    
    def get_usage_stats(self) -> Dict:
        """获取使用统计"""
        return self.usage_stats.to_dict()
    
    def reset_stats(self):
        """重置统计数据"""
        self.usage_stats = UsageStats()
    
    async def batch_completion(
        self,
        batch_messages: List[List[Dict[str, str]]],
        model: Optional[str] = None,
        max_concurrent: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量处理多个请求
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(messages):
            async with semaphore:
                return await self.completion(messages, model=model, **kwargs)
        
        tasks = [process_single(messages) for messages in batch_messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "error": str(result),
                    "content": None,
                    "model_used": None
                })
            else:
                processed_results.append(result)
        
        return processed_results


# 单例模式的全局LLM管理器
_llm_manager = None

def get_llm_manager(config_path: Optional[str] = None) -> LLMManager:
    """获取全局LLM管理器实例"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager(config_path)
    return _llm_manager