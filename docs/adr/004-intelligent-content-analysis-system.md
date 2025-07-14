# ADR-004: 智能内容分析与评价系统架构设计

## 状态
已实现 (Implemented)

## 背景
项目当前已实现从sitemap生成RSS feeds的功能。为了辅助用户快速判断文章的阅读价值，需要实现智能内容分析功能，包括：
1. 自动提取和分析文章内容
2. 生成智能标签和分类
3. 撰写简洁摘要
4. 提供多维度评分
5. 支持用户快速做出阅读决策

这是ADR-001（RSS语义化总结）的前置需求，将为后续的内容聚合和新数据源生成奠定基础。

## 决策

### 架构原则
- **模块化抽象**: LLM提供商抽象层，支持多模型混合使用
- **任务导向**: 面向"是否值得阅读"的决策支持
- **成本控制**: 智能路由和截断，优化API成本
- **可扩展性**: 易于添加新的评分维度和标签类别

### 核心数据结构

#### ContentAnalysis (扩展版)
```python
@dataclass
class ContentAnalysis:
    # 基础信息
    url: str
    title: str
    extracted_content: str
    
    # 智能分析结果
    summary: str                    # 简洁摘要 (150-200字)
    tags: List[str]                 # 智能标签
    reading_score: float            # 综合阅读价值评分 (0-10)
    reading_time_minutes: int       # 预估阅读时间
    difficulty_level: str           # 难度等级
    actionable_insights: List[str]  # 可执行的见解
    
    # 评分细分
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    # {"实用性": 8.5, "学习价值": 7.0, "时效性": 9.0, "技术深度": 6.5, "完整性": 8.0}
    
    # 元数据
    analyzed_at: datetime
    model_used: str
    confidence_score: float         # 分析结果置信度
```

### 评分标准体系

#### 评分维度（第一版）
```python
SCORING_DIMENSIONS = {
    "practical_value": {
        "name": "实用性",
        "description": "能否直接应用到工作中",
        "weight": 0.25,
        "range": "0-10"
    },
    "learning_value": {
        "name": "学习价值", 
        "description": "能学到新知识/技能的程度",
        "weight": 0.25,
        "range": "0-10"
    },
    "timeliness": {
        "name": "时效性",
        "description": "信息新鲜度和当前相关性",
        "weight": 0.2,
        "range": "0-10"
    },
    "technical_depth": {
        "name": "技术深度",
        "description": "技术含量和复杂度",
        "weight": 0.15,
        "range": "0-10"
    },
    "completeness": {
        "name": "完整性",
        "description": "内容完整性和深度",
        "weight": 0.15,
        "range": "0-10"
    }
}
```

#### 标签体系（第一版）
```python
TAG_CATEGORIES = {
    "tech_stack": [
        "Python", "JavaScript", "Go", "Rust", "Java",
        "React", "Vue", "Django", "FastAPI", "Docker",
        "Kubernetes", "AWS", "PostgreSQL", "Redis"
    ],
    "content_type": [
        "教程", "最佳实践", "案例研究", "工具介绍",
        "行业动态", "技术观点", "开源项目", "代码片段"
    ],
    "difficulty": ["入门", "中级", "高级", "专家"],
    "domain": [
        "前端开发", "后端开发", "DevOps", "AI/ML", 
        "数据工程", "系统架构", "产品设计", "创业"
    ],
    "reading_time": ["<5分钟", "5-15分钟", "15-30分钟", ">30分钟"]
}
```

### LLM抽象层架构 (基于LiteLLM)

采用LiteLLM作为模型抽象层，避免重复造轮子。LiteLLM专门解决多LLM提供商统一调用问题。

#### 依赖安装
```bash
pip install litellm
```

#### 模型配置和路由
```python
# lib/llm_manager.py
import litellm
from litellm import Router
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

class TaskType(Enum):
    SUMMARIZE = "summarize"      # 摘要生成
    TAG = "tag"                  # 标签提取  
    SCORE = "score"              # 评分分析
    EXTRACT = "extract"          # 内容提取
    FULL_ANALYSIS = "full"       # 完整分析

@dataclass
class TaskConfig:
    """任务配置，定义不同任务使用的模型策略"""
    model_name: str
    max_tokens: int
    temperature: float
    system_prompt: str

class LLMManager:
    """基于LiteLLM的模型管理器"""
    
    def __init__(self, config: Dict[str, any]):
        self.task_configs = config["task_configs"]
        self.router = self._setup_router(config["model_list"])
    
    def _setup_router(self, model_list: List[Dict]) -> Router:
        """设置LiteLLM路由器"""
        return Router(
            model_list=model_list,
            fallbacks=[
                {"gpt-4o": ["gpt-4o-mini"]},          # GPT-4o失败时降级到mini
                {"claude-3-sonnet": ["gpt-4o-mini"]}   # Claude失败时降级到GPT
            ],
            retry_policy={"max_retries": 2, "base_delay": 1}
        )
    
    async def analyze_content(self, content: str, task_type: TaskType) -> Dict:
        """统一的内容分析接口"""
        task_config = self.task_configs[task_type.value]
        
        messages = [
            {"role": "system", "content": task_config.system_prompt},
            {"role": "user", "content": content}
        ]
        
        try:
            response = await self.router.acompletion(
                model=task_config.model_name,
                messages=messages,
                max_tokens=task_config.max_tokens,
                temperature=task_config.temperature
            )
            
            # 获取成本信息
            cost = litellm.completion_cost(response)
            
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "model_used": response.model,
                "cost": cost,
                "tokens": response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
```

#### 配置文件示例
```python
# configs/llm_config.py
LLM_CONFIG = {
    "model_list": [
        # 高质量模型 - 用于复杂分析
        {
            "model_name": "gpt-4o",
            "litellm_params": {
                "model": "openai/gpt-4o",
                "api_key": "your-openai-key"
            }
        },
        {
            "model_name": "claude-3-sonnet", 
            "litellm_params": {
                "model": "anthropic/claude-3-sonnet-20240229",
                "api_key": "your-anthropic-key"
            }
        },
        # 经济型模型 - 用于简单任务
        {
            "model_name": "gpt-4o-mini",
            "litellm_params": {
                "model": "openai/gpt-4o-mini",
                "api_key": "your-openai-key"
            }
        }
    ],
    "task_configs": {
        "summarize": TaskConfig(
            model_name="gpt-4o-mini",    # 摘要用经济型模型
            max_tokens=300,
            temperature=0.3,
            system_prompt="你是一个专业的内容摘要助手。请为以下文章生成150-200字的简洁摘要..."
        ),
        "score": TaskConfig(
            model_name="gpt-4o",         # 评分用高质量模型
            max_tokens=500,
            temperature=0.1,
            system_prompt="你是内容质量评估专家。请按照实用性、学习价值等维度为文章评分..."
        ),
        "tag": TaskConfig(
            model_name="gpt-4o-mini",    # 标签用经济型模型
            max_tokens=200,
            temperature=0.2,
            system_prompt="你是内容分类专家。请为文章生成相关标签..."
        )
    }
}
```

#### 智能截断模块
```python
# lib/content_optimizer.py
class ContentOptimizer:
    """内容智能优化器，处理过长内容"""
    
    def smart_truncate(self, content: str, max_tokens: int = 4000) -> str:
        """
        智能截断内容，保留最有价值的部分
        """
        # 1. 提取文章结构（标题、段落、代码块）
        # 2. 计算各部分的重要性得分
        # 3. 选择性保留高价值内容
        # 4. 确保语义连贯性
        pass
    
    def extract_key_sections(self, content: str) -> Dict[str, str]:
        """提取关键章节"""
        pass
```

### 核心处理模块

#### 内容分析器
```python
# lib/content_analyzer.py
from .llm_manager import LLMManager, TaskType
from .content_optimizer import ContentOptimizer

class ContentAnalyzer:
    """核心内容分析器"""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.optimizer = ContentOptimizer()
    
    async def full_analysis(self, url: str, content: str) -> ContentAnalysis:
        """
        完整内容分析流程：
        1. 智能截断和优化
        2. 并发调用多个分析任务
        3. 聚合结果
        4. 计算综合评分
        """
        optimized_content = self.optimizer.smart_truncate(content)
        
        # 并发执行多个分析任务
        tasks = [
            self.llm_manager.analyze_content(optimized_content, TaskType.SUMMARIZE),
            self.llm_manager.analyze_content(optimized_content, TaskType.TAG),
            self.llm_manager.analyze_content(optimized_content, TaskType.SCORE)
        ]
        
        results = await asyncio.gather(*tasks)
        
        return self._aggregate_results(url, content, results)
    
    def _aggregate_results(self, url: str, content: str, 
                          results: List[Dict]) -> ContentAnalysis:
        """聚合分析结果"""
        pass
    
    def _calculate_overall_score(self, score_breakdown: Dict[str, float]) -> float:
        """基于权重计算综合评分"""
        total_score = 0
        for dimension, score in score_breakdown.items():
            weight = SCORING_DIMENSIONS.get(dimension, {}).get("weight", 0.2)
            total_score += score * weight
        return round(total_score, 1)
```

### 工作流集成

#### 主工作流
```python
# flows/content_analysis_flow.py
@flow(name="Content Analysis Flow")
async def content_analysis_flow(
    urls: List[str],
    output_file: str = "content_analysis.json",
    batch_size: int = 5,
    model_config: Dict = None
):
    """
    智能内容分析工作流
    
    Steps:
    1. 批量提取内容
    2. 并发分析（控制并发数）
    3. 结果聚合和存储
    4. 生成分析报告
    """
    pass
```

## 后果

### 优势
1. **决策支持**: 帮助用户快速判断文章阅读价值
2. **成本可控**: 智能路由和混合模型使用，优化成本
3. **高度可扩展**: 易于添加新的评分维度和模型提供商
4. **无缝集成**: 为ADR-001的语义总结功能提供基础

### 考虑的挑战
1. **模型成本**: 需要仔细平衡分析质量和API成本
2. **响应时间**: 大批量内容分析的性能优化
3. **质量控制**: 不同模型结果的一致性和准确性
4. **配置复杂性**: 多模型策略的配置管理

### 成本估算
- 单篇文章分析成本: $0.01-0.05 (取决于模型选择)
- 日处理100篇文章: $1-5
- 月成本预估: $30-150

## 实施计划

### Phase 1: 基础架构 (2-3天)
- [x] 实现 LLM 抽象层和路由器
- [x] 实现 ContentAnalyzer 核心逻辑
- [x] 实现智能截断模块
- [x] 单模型集成测试

### Phase 2: 多模型集成 (2天)
- [x] 集成 OpenAI GPT-4o
- [x] 集成 Anthropic Claude
- [x] 实现混合路由策略
- [x] 成本监控和优化

### Phase 3: 评分系统 (1-2天)
- [x] 实现评分标准和权重计算
- [x] 标签体系实现
- [x] 分析结果验证和调优

### Phase 4: 工作流集成 (1天)
- [x] 实现 Prefect 工作流
- [x] 批量处理和并发控制
- [x] 结果存储和导出

### Phase 5: 测试和优化 (1-2天)
- [x] 端到端测试
- [ ] 性能基准测试
- [x] 文档和配置示例

## 相关文档
- [ADR-001: RSS 语义化总结架构设计](./001-rss-semantic-summary-architecture.md)
- [现有内容提取器](../lib/content_extractor.py)
- [项目 README](../README.md)

## 实施总结

### 完成状态
- **总体进度**: 95% 完成
- **实施时间**: 2025-07-13 至 2025-07-14
- **核心功能**: 全部实现并通过测试

### 实际实现的模块
1. **lib/content_analysis.py**: 核心数据结构和评分体系
2. **lib/content_analyzer.py**: 主控分析器，集成 LiteLLM
3. **lib/content_optimizer.py**: 智能内容优化和截断
4. **lib/batch.py**: 批量处理工具
5. **flows/content_analysis_flow.py**: Prefect 工作流集成
6. **example_content_analysis.py**: 使用示例和文档

### 验证结果
- ✅ 端到端测试通过
- ✅ 智能分析功能正常工作
- ✅ 批量处理和并发控制有效
- ✅ 成本优化策略运行良好
- ✅ 结果存储和报告生成正常

### 技术亮点
- 基于 LiteLLM 的多模型抽象层
- 异步并发处理提高性能
- 智能路由优化成本 (gpt-4o + gpt-4o-mini)
- 完整的评分体系和标签分类
- Prefect 工作流无缝集成

### 待改进项
- [ ] 补充单元测试覆盖率
- [ ] 完善类型注解
- [ ] 性能基准测试
- [ ] 长期成本监控

---
**创建日期**: 2025-07-13  
**实施完成**: 2025-07-14  
**作者**: Claude Code  
**状态**: 已实现 (Implemented)