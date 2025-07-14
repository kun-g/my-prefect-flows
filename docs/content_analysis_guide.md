# 智能内容分析与评价系统 (ADR-004)

## 📋 系统概述

智能内容分析系统是一个基于LLM的内容评价工具，能够自动分析技术文章并提供多维度评分、标签分类和摘要生成功能。

## 🏗️ 架构设计

### 核心组件

1. **ContentAnalysis** - 内容分析结果数据结构
2. **ContentOptimizer** - 智能文本优化器
3. **ContentAnalyzer** - 主分析控制器（直接集成LiteLLM）
4. **Prefect工作流** - 批量处理和任务管理

### 技术栈

- **LiteLLM**: 多模型抽象层，提供统一的API接口
- **OpenAI GPT-4o/4o-mini**: 主要分析模型
- **Anthropic Claude-3-Sonnet**: 备选模型（可选）
- **Prefect**: 工作流编排

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用uv（推荐）
uv sync

# 或使用pip
pip install litellm openai prefect beautifulsoup4
```

### 2. 配置API密钥

```bash
# 设置OpenAI API密钥
export OPENAI_API_KEY="your-openai-api-key"

# 可选：设置Anthropic API密钥
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 3. 基本使用

```python
import asyncio
from lib.content_analyzer import ContentAnalyzer

async def analyze_content():
    analyzer = ContentAnalyzer()
    
    analysis = await analyzer.analyze_content(
        content="你的文章内容...",
        title="文章标题",
        url="https://example.com/article"
    )
    
    print(f"评分: {analysis.reading_score:.1f}/10")
    print(f"标签: {analysis.tags}")
    print(f"摘要: {analysis.summary}")

# 运行分析
asyncio.run(analyze_content())
```

### 4. 运行示例

```bash
# 运行基本测试
python test_content_analysis.py

# 运行示例分析
python example_content_analysis.py

# 运行Prefect工作流
python flows/content_analysis_flow.py
```

## 📊 评分体系

### 五维度评分

| 维度 | 权重 | 说明 |
|------|------|------|
| 实用性 | 25% | 能否直接应用到工作中 |
| 学习价值 | 25% | 能学到新知识/技能的程度 |
| 时效性 | 20% | 信息新鲜度和当前相关性 |
| 技术深度 | 15% | 技术含量和复杂度 |
| 完整性 | 15% | 内容完整性和逻辑性 |

### 难度等级

- **初级**: 适合初学者，基础概念介绍
- **中级**: 需要一定基础，实际应用场景
- **高级**: 需要深厚基础，复杂技术实现

## 🏷️ 标签体系

### 技术栈标签
Python, JavaScript, Java, Go, React, Vue, Docker, Kubernetes, AWS等

### 内容类型标签
教程, 指南, 最佳实践, 案例研究, 工具介绍等

### 应用场景标签
Web开发, 移动开发, 后端开发, DevOps, 数据科学等

### 行业领域标签
电商, 金融, 医疗, 教育, 游戏等

## ⚙️ 配置说明

### LLM配置文件

复制并修改配置模板：

```bash
cp config/llm_config.json.example config/llm_config.json
```

配置文件结构：

```json
{
  "models": [
    {
      "model_name": "gpt-4o-mini",
      "litellm_params": {
        "model": "gpt-4o-mini",
        "api_key": "your-api-key",
        "timeout": 30
      },
      "cost_per_1k_tokens": 0.000150
    }
  ],
  "default_model": "gpt-4o-mini",
  "fallback_strategy": "gpt-4o-mini"
}
```

### 环境变量

```bash
# 必需
OPENAI_API_KEY=your-openai-api-key

# 可选
ANTHROPIC_API_KEY=your-anthropic-api-key
LLM_CONFIG_PATH=config/llm_config.json
MAX_CONCURRENT_REQUESTS=5
```

## 🔄 Prefect工作流

### 单站点内容分析

```python
from flows.content_analysis_flow import content_analysis_flow

# 运行工作流
await content_analysis_flow(
    sitemap_url="https://example.com/sitemap.xml",
    max_articles=20,
    output_dir="output/analysis"
)
```

### 批量站点分析

```python
from flows.content_analysis_flow import batch_site_analysis_flow

sites = [
    {"name": "site1", "sitemap_url": "https://site1.com/sitemap.xml"},
    {"name": "site2", "sitemap_url": "https://site2.com/sitemap.xml"}
]

await batch_site_analysis_flow(
    sites_config=sites,
    max_articles_per_site=10
)
```

## 📈 性能优化

### 并发控制

```python
# 调整并发数
analyzer = ContentAnalyzer()
results = await analyzer.batch_analyze(
    articles=articles,
    max_concurrent=3  # 控制并发请求数
)
```

### 内容优化

```python
# 智能截断长文本
optimizer = ContentOptimizer(max_tokens=4000)
optimized_content, metadata = optimizer.optimize_for_analysis(content)
```

### 成本控制

- 摘要和标签使用`gpt-4o-mini`（便宜）
- 评分使用`gpt-4o`（更准确）
- 自动降级机制
- 成本跟踪和预算控制

## 💰 成本估算

| 任务类型 | 模型 | 预估Token | 单次成本 |
|----------|------|-----------|----------|
| 摘要生成 | gpt-4o-mini | 1000 | $0.0002 |
| 标签提取 | gpt-4o-mini | 800 | $0.0001 |
| 评分计算 | gpt-4o | 1500 | $0.0075 |
| **总计** | - | **3300** | **$0.0078** |

日处理100篇文章成本约：**$0.78**

## 🧪 测试和验证

### 运行测试套件

```bash
# 基础功能测试
python test_content_analysis.py

# 性能测试
python -m pytest tests/ -v

# 覆盖率测试
coverage run -m pytest && coverage report
```

### 验证分析质量

1. **一致性测试**: 同一文章多次分析的评分差异应<0.5分
2. **准确性测试**: 标签准确率应>85%
3. **摘要质量**: 摘要应包含核心信息，长度150-200字

## 📁 输出格式

### 分析结果JSON

```json
{
  "analyzed_at": "2024-01-15T10:30:00",
  "total_articles": 10,
  "average_score": 7.8,
  "articles": [
    {
      "url": "https://example.com/article",
      "title": "文章标题",
      "summary": "文章摘要...",
      "tags": ["Python", "Web开发"],
      "reading_score": 8.2,
      "reading_time_minutes": 6,
      "difficulty_level": "中级",
      "score_breakdown": {
        "实用性": 8.5,
        "学习价值": 8.0,
        "时效性": 7.8,
        "技术深度": 8.0,
        "完整性": 8.2
      },
      "confidence_score": 0.85
    }
  ]
}
```

### 分析报告Markdown

自动生成包含统计信息和高价值文章推荐的Markdown报告。

## 🔧 故障排除

### 常见问题

1. **API密钥错误**
   ```bash
   export OPENAI_API_KEY="your-correct-api-key"
   ```

2. **请求超时**
   - 增加timeout配置
   - 降低并发数
   - 检查网络连接

3. **成本过高**
   - 使用更多mini模型
   - 减少最大token数
   - 优化内容截断策略

4. **分析质量差**
   - 调整system prompts
   - 增加context信息
   - 使用更强的模型

### 调试模式

```python
# 启用详细日志
import litellm
litellm.set_verbose = True

# 查看使用统计
stats = analyzer.get_usage_statistics()
print(stats)
```

## 🚀 扩展开发

### 添加新模型

在配置文件中添加新模型：

```json
{
  "model_name": "claude-3-sonnet",
  "litellm_params": {
    "model": "anthropic/claude-3-sonnet-20240229",
    "api_key": "your-anthropic-key"
  }
}
```

### 自定义评分维度

修改`ScoreDimensions`类：

```python
class ScoreDimensions:
    NEW_DIMENSION = "新维度"
    
    @classmethod
    def get_weights(cls):
        return {
            cls.PRACTICALITY: 0.20,
            cls.LEARNING_VALUE: 0.20,
            cls.NEW_DIMENSION: 0.15,
            # ... 其他维度
        }
```

### 自定义标签

扩展`TagCategories`类：

```python
class TagCategories:
    CUSTOM_TAGS = {"自定义标签1", "自定义标签2"}
    
    @classmethod
    def get_all_tags(cls):
        return cls.TECH_STACK | cls.CONTENT_TYPE | cls.CUSTOM_TAGS
```

## 📚 相关文档

- [ADR-004: 智能内容分析系统架构设计](docs/adr/004-intelligent-content-analysis-system.md)
- [LiteLLM文档](https://docs.litellm.ai/)
- [OpenAI API文档](https://platform.openai.com/docs/)
- [Prefect文档](https://docs.prefect.io/)

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 运行测试
5. 创建Pull Request

## 📄 许可证

MIT License - 详见LICENSE文件