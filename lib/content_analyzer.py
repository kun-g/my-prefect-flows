"""
智能内容分析器 - 主控类
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import os

try:
    import litellm
except ImportError as e:
    print(f"请安装必要的依赖: pip install litellm")
    raise e

from .content_analysis import ContentAnalysis, ScoreDimensions, DifficultyLevel, TagCategories
from .content_optimizer import ContentOptimizer


class ContentAnalyzer:
    """
    智能内容分析器主控类
    负责协调各个分析模块，提供完整的内容分析功能
    """
    
    def __init__(
        self, 
        max_tokens: int = 4000,
        models: Optional[Dict[str, str]] = None
    ):
        self.optimizer = ContentOptimizer(max_tokens=max_tokens)
        
        # 配置LiteLLM
        litellm.set_verbose = False
        
        # 配置代理设置（如果提供）
        if os.getenv("LITELLM_PROXY_API_BASE"):
            litellm.api_base = os.getenv("LITELLM_PROXY_API_BASE")
        if os.getenv("LITELLM_PROXY_API_KEY"):
            litellm.api_key = os.getenv("LITELLM_PROXY_API_KEY")
        
        # 模型配置 - 支持环境变量和参数覆盖
        default_models = {
            "summary": os.getenv("SUMMARY_MODEL", "gpt-4o-mini"),
            "tags": os.getenv("TAGS_MODEL", "gpt-4o-mini"), 
            "scoring": os.getenv("SCORING_MODEL", "gpt-4o"),
            "reading_time": os.getenv("READING_TIME_MODEL", "gpt-4o-mini")
        }
        
        if models:
            default_models.update(models)
        
        self.models = default_models
        
        # 系统提示词
        self.system_prompts = {
            "summary": self._get_summary_prompt(),
            "tags": self._get_tags_prompt(),
            "scoring": self._get_scoring_prompt(),
            "reading_time": self._get_reading_time_prompt()
        }
    

    def _get_summary_prompt(self) -> str:
        """获取摘要生成提示词"""
        return """你是一个专业的内容摘要专家。请为给定的技术文章生成一个简洁而全面的摘要。

要求：
1. 摘要长度控制在150-200字
2. 突出文章的核心观点和主要内容
3. 保持技术准确性
4. 使用清晰易懂的语言
5. 避免冗余和无关信息

请直接返回摘要内容，不需要额外解释。"""

    def _get_tags_prompt(self) -> str:
        """获取标签生成提示词"""
        available_tags = list(TagCategories.get_all_tags())
        tags_text = "、".join(available_tags[:50])  # 只显示前50个标签避免过长
        
        return f"""你是一个专业的内容标签专家。请为给定的技术文章选择最合适的标签。

可选标签包括（但不限于）：{tags_text}

要求：
1. 选择3-8个最相关的标签
2. 优先选择技术栈、内容类型、应用场景相关的标签
3. 标签应准确反映文章的核心主题
4. 如果现有标签不够准确，可以提出新的标签

请以JSON格式返回，例如：
{{"tags": ["Python", "Web开发", "最佳实践", "后端开发"]}}"""

    def _get_scoring_prompt(self) -> str:
        """获取评分提示词"""
        dimensions = ScoreDimensions.get_weights()
        dims_text = "\n".join([f"- {dim}（权重{weight*100:.0f}%）" for dim, weight in dimensions.items()])
        
        return f"""你是一个专业的技术内容评估专家。请对给定文章进行多维度评分。

评分维度：
{dims_text}

评分标准：
- 实用性：内容能否直接应用到实际工作中（0-10分）
- 学习价值：能学到新知识/技能的程度（0-10分）
- 时效性：信息新鲜度和当前相关性（0-10分）
- 技术深度：技术含量和复杂度（0-10分）
- 完整性：内容完整性和逻辑性（0-10分）

还需要评估：
- 难度等级：初级、中级、高级
- 置信度：对评分准确性的信心（0-1）

请以JSON格式返回，例如：
{{
    "scores": {{
        "实用性": 8.5,
        "学习价值": 7.2,
        "时效性": 9.0,
        "技术深度": 6.8,
        "完整性": 8.0
    }},
    "difficulty_level": "中级",
    "confidence": 0.85
}}"""

    def _get_reading_time_prompt(self) -> str:
        """获取阅读时间估算提示词"""
        return """你是一个阅读时间估算专家。请根据文章内容估算平均阅读时间。

考虑因素：
1. 文章字数和段落结构
2. 技术复杂度（复杂内容需要更多时间理解）
3. 代码示例数量（代码需要额外时间分析）
4. 图表和链接数量

假设读者具有一定技术背景，正常阅读速度。

请只返回分钟数（整数），例如：5"""

    async def analyze_content(
        self, 
        content: str, 
        title: str, 
        url: str
    ) -> ContentAnalysis:
        """
        分析内容并生成完整的分析结果
        
        Args:
            content: 文章正文内容
            title: 文章标题
            url: 文章URL
            
        Returns:
            ContentAnalysis: 完整的分析结果
        """
        # 优化内容以适合LLM处理
        optimized_content, optimization_meta = self.optimizer.optimize_for_analysis(content, title)
        
        # 并发执行各项分析任务
        results = await self._concurrent_analysis(optimized_content, title)
        
        # 整合分析结果
        analysis = self._build_analysis_result(
            results, title, url, optimization_meta
        )
        
        return analysis
    
    async def _concurrent_analysis(self, content: str, title: str) -> Dict:
        """并发执行所有分析任务"""
        tasks = {
            "summary": self._generate_summary(content, title),
            "tags": self._extract_tags(content, title),
            "scores": self._calculate_scores(content, title),
            "reading_time": self._estimate_reading_time(content)
        }
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # 整理结果
        task_names = list(tasks.keys())
        analysis_results = {}
        
        for i, result in enumerate(results):
            task_name = task_names[i]
            if isinstance(result, Exception):
                print(f"⚠️ 任务 {task_name} 执行失败: {result}")
                analysis_results[task_name] = self._get_fallback_result(task_name)
            else:
                analysis_results[task_name] = result
        
        return analysis_results
    
    async def _generate_summary(self, content: str, title: str) -> str:
        """生成内容摘要"""
        messages = [
            {"role": "system", "content": self.system_prompts["summary"]},
            {"role": "user", "content": f"标题：{title}\n\n内容：{content}"}
        ]
        
        model = self.models.get("summary", "gpt-4o-mini")
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    async def _extract_tags(self, content: str, title: str) -> List[str]:
        """提取内容标签"""
        messages = [
            {"role": "system", "content": self.system_prompts["tags"]},
            {"role": "user", "content": f"标题：{title}\n\n内容：{content[:1500]}"}  # 限制长度
        ]
        
        model = self.models.get("tags", "gpt-4o-mini")
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=200,
            temperature=0.2
        )
        
        # 解析JSON响应
        try:
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result.get("tags", [])
        except:
            # 如果JSON解析失败，尝试简单的文本解析
            return self._parse_tags_from_text(response.choices[0].message.content.strip())
    
    async def _calculate_scores(self, content: str, title: str) -> Dict:
        """计算多维度评分"""
        messages = [
            {"role": "system", "content": self.system_prompts["scoring"]},
            {"role": "user", "content": f"标题：{title}\n\n内容：{content}"}
        ]
        
        model = self.models.get("scoring", "gpt-4o")
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=500,
            temperature=0.1
        )
        
        # 解析JSON响应
        try:
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return {
                "scores": result.get("scores", {}),
                "difficulty_level": result.get("difficulty_level", DifficultyLevel.INTERMEDIATE),
                "confidence": result.get("confidence", 0.5)
            }
        except:
            # 如果解析失败，返回默认值
            return self._get_fallback_result("scores")
    
    async def _estimate_reading_time(self, content: str) -> int:
        """估算阅读时间"""
        # 简单的基于字数的估算作为后备
        char_count = len(content)
        fallback_time = max(1, char_count // 500)  # 假设每分钟500字
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompts["reading_time"]},
                {"role": "user", "content": content[:1000]}  # 只传递开头部分
            ]
            
            model = self.models.get("reading_time", "gpt-4o-mini")
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                max_tokens=50,
                temperature=0.1
            )
            
            # 提取数字
            time_text = response.choices[0].message.content.strip()
            time_match = re.search(r'\d+', time_text)
            
            if time_match:
                return int(time_match.group())
            else:
                return fallback_time
                
        except:
            return fallback_time
    
    def _parse_tags_from_text(self, text: str) -> List[str]:
        """从文本中解析标签（当JSON解析失败时使用）"""
        # 简单的正则表达式解析
        tags = re.findall(r'["\']([^"\']+)["\']', text)
        
        if not tags:
            # 尝试按逗号分割
            tags = [tag.strip() for tag in text.split(',')]
        
        # 过滤和清理标签
        cleaned_tags = []
        for tag in tags:
            tag = tag.strip().strip('"\'')
            if tag and len(tag) > 1:
                cleaned_tags.append(tag)
        
        return cleaned_tags[:8]  # 限制数量
    
    def _get_fallback_result(self, task_name: str):
        """获取任务失败时的后备结果"""
        fallbacks = {
            "summary": "内容摘要生成失败，请查看原文获取详细信息。",
            "tags": TagCategories.suggest_tags_by_content(""),  # 空标签列表
            "scores": {
                "scores": {dim: 5.0 for dim in ScoreDimensions.get_weights().keys()},
                "difficulty_level": DifficultyLevel.INTERMEDIATE,
                "confidence": 0.3
            },
            "reading_time": 5  # 默认5分钟
        }
        return fallbacks.get(task_name, None)
    
    def _build_analysis_result(
        self, 
        results: Dict, 
        title: str, 
        url: str, 
        optimization_meta: Dict
    ) -> ContentAnalysis:
        """构建最终的分析结果"""
        
        # 计算综合评分
        scores = results["scores"]["scores"]
        reading_score = ScoreDimensions.calculate_weighted_score(scores)
        
        # 确定使用的模型
        model_used = "gpt-4o-mini + gpt-4o"  # 多模型组合
        
        return ContentAnalysis(
            url=url,
            title=title,
            summary=results["summary"],
            tags=results["tags"],
            reading_score=reading_score,
            reading_time_minutes=results["reading_time"],
            difficulty_level=results["scores"]["difficulty_level"],
            score_breakdown=scores,
            analyzed_at=datetime.now(),
            model_used=model_used,
            confidence_score=results["scores"]["confidence"]
        )
    
    def get_usage_statistics(self) -> Dict:
        """获取使用统计信息"""
        # LiteLLM 会自动处理统计信息，这里返回简单的占位符
        return {
            "message": "统计信息由 LiteLLM 自动管理"
        }