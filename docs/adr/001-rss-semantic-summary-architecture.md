# ADR-001: RSS 语义化总结架构设计

## 状态
提议中 (Proposed)

## 背景
当前项目已实现了从 sitemap 生成 RSS feed 的功能。下一步需要实现 RSS 语义化总结功能，即：
1. 解析现有的 RSS feeds
2. 提取文章完整内容
3. 使用 AI 进行语义化分析和总结
4. 生成包含摘要的新 RSS feed

需要确定如何在现有代码基础上扩展新功能，最大化代码复用。

## 决策

### 架构原则
- **模块化设计**：保持现有代码稳定，通过新模块扩展功能
- **最大化复用**：复用现有的 60-70% 代码
- **数据流清晰**：RSS Sources → Parser → Extractor → Analyzer → Aggregator → Generator

### 模块设计

#### 1. 可复用的现有模块 (lib/rss_generator.py)
- ✅ `RSSItem` 数据类 - 表示 RSS 条目
- ✅ `RSSChannel` 数据类 - 表示 RSS 频道
- ✅ `generate_rss_feed()` - 生成 RSS XML
- ✅ `format_rss_date()` - 日期格式化
- ✅ `extract_title_from_url()` - 可扩展为通用工具

#### 2. 新增核心模块

**lib/rss_parser.py**
```python
@dataclass
class ParsedRSSFeed:
    channel_info: RSSChannel
    items: List[RSSItem]
    source_url: str
    
def parse_rss_feed(rss_url: str) -> ParsedRSSFeed
def parse_multiple_feeds(urls: List[str]) -> List[ParsedRSSFeed]
```

**lib/content_extractor.py**
```python
@dataclass
class ExtractedContent:
    url: str
    title: str
    content: str
    summary: str
    metadata: Dict
    
def extract_full_content(url: str) -> ExtractedContent
def batch_extract_content(urls: List[str]) -> List[ExtractedContent]
```

**lib/semantic_analyzer.py**
```python
@dataclass
class SemanticAnalysis:
    summary: str
    key_points: List[str]
    categories: List[str]
    sentiment: str
    relevance_score: float
    
def analyze_content(content: str) -> SemanticAnalysis
def generate_summary(content: str, max_length: int) -> str
def categorize_content(content: str) -> List[str]
```

**lib/content_aggregator.py**
```python
@dataclass
class AggregatedContent:
    grouped_items: Dict[str, List[RSSItem]]
    deduplicated_items: List[RSSItem]
    trending_topics: List[str]
    
def aggregate_by_category(items: List[RSSItem]) -> Dict[str, List[RSSItem]]
def deduplicate_content(items: List[RSSItem]) -> List[RSSItem]
def identify_trending_topics(items: List[RSSItem]) -> List[str]
```

#### 3. 主流程 (flows/rss_semantic_summary.py)

```python
@flow(name="RSS Semantic Summary")
def rss_semantic_summary_flow(
    rss_sources: List[str],
    output_config: Dict,
    ai_config: Dict,
    aggregation_config: Dict
):
    """
    完整的 RSS 语义化总结流程
    
    Steps:
    1. 解析多个 RSS 源
    2. 提取文章完整内容
    3. AI 语义化分析
    4. 内容聚合和去重
    5. 生成总结版 RSS
    """
    pass
```

### 数据流架构

```
RSS Sources (多个RSS链接)
    ↓
RSS Parser (解析RSS feeds)
    ↓
Content Extractor (提取完整文章内容)
    ↓
Semantic Analyzer (AI分析和总结)
    ↓
Content Aggregator (聚合、去重、分类)
    ↓
RSS Generator (生成最终RSS) ← 复用现有代码
```

### 配置管理

创建统一的配置文件结构：
```python
# configs/semantic_summary_config.py
SUMMARY_CONFIGS = {
    "tech_digest": {
        "sources": [
            "https://example.com/rss1.xml",
            "https://example.com/rss2.xml"
        ],
        "ai_config": {
            "provider": "openai",
            "model": "gpt-4",
            "max_summary_length": 200
        },
        "aggregation": {
            "deduplicate": True,
            "max_items": 20,
            "categories": ["tech", "ai", "data"]
        },
        "output": {
            "title": "科技资讯精选摘要",
            "description": "AI生成的科技资讯精选和总结"
        }
    }
}
```

## 后果

### 优势
1. **代码复用率高**：60-70% 的现有代码可直接复用
2. **模块化清晰**：每个模块职责单一，易于测试和维护
3. **扩展性好**：可以轻松添加新的 AI 提供商或内容源
4. **现有功能不受影响**：sitemap 到 RSS 功能保持独立

### 需要考虑的问题
1. **AI API 成本**：需要控制 API 调用频率和内容长度
2. **性能优化**：大量内容提取和分析的并发处理
3. **错误处理**：网络请求、AI API 失败的容错机制
4. **内容质量**：AI 总结质量的评估和优化

## 实施计划

### Phase 1: 基础模块 (1-2天)
- [ ] 实现 `rss_parser.py`
- [ ] 实现 `content_extractor.py`
- [ ] 基础测试

### Phase 2: AI 集成 (2-3天)
- [ ] 实现 `semantic_analyzer.py`
- [ ] 集成 OpenAI API
- [ ] 总结质量测试

### Phase 3: 聚合功能 (1-2天)
- [ ] 实现 `content_aggregator.py`
- [ ] 去重和分类逻辑
- [ ] 性能优化

### Phase 4: 主流程 (1天)
- [ ] 实现 `rss_semantic_summary.py`
- [ ] 端到端测试
- [ ] 配置文件和示例

### Phase 5: 部署和监控 (1天)
- [ ] Prefect 部署配置
- [ ] 错误监控和告警
- [ ] 文档和使用指南

## 相关文档
- [现有 sitemap 到 RSS 实现](../flows/sitemap_to_rss.py)
- [RSS 生成器库](../lib/rss_generator.py)
- [项目 README](../README.md)

---
**创建日期**: 2025-07-12  
**作者**: Claude Code  
**审核**: 待定