# ADR-002: 采用 PyRSS2Gen 库简化 RSS 生成

## 状态
已采用 (Adopted) - 2025-07-13

## 背景
当前项目在 `lib/rss_generator.py` 中使用 `xml.etree.ElementTree` 手动构建 RSS XML。虽然功能完整，但存在以下问题：
1. **代码复杂度高**：手动创建 XML 元素，代码量大且容易出错
2. **维护成本高**：需要手动处理 XML 命名空间、转义字符等细节
3. **标准合规性**：需要确保生成的 RSS 符合 RSS 2.0 标准
4. **功能扩展困难**：添加新的 RSS 元素需要大量手动工作

发现 `PyRSS2Gen` 库可以大幅简化 RSS 生成代码，提高可维护性。

## 决策

### 采用 PyRSS2Gen 库替换现有的手动 XML 生成

**理由**：
1. **代码简化**：从 100+ 行 XML 操作代码简化为 20-30 行
2. **标准合规**：PyRSS2Gen 确保生成的 RSS 完全符合 RSS 2.0 标准
3. **更好的可读性**：代码更加直观和易懂
4. **减少错误**：库已经处理了所有 XML 细节和边界情况
5. **社区支持**：成熟的开源库，有良好的文档和社区支持

### 代码对比

#### 现有实现 (复杂)
```python
# 当前的 lib/rss_generator.py - 约 100 行代码
def generate_rss_feed(channel: RSSChannel, items: List[RSSItem]) -> str:
    rss = ET.Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    channel_elem = ET.SubElement(rss, "channel")
    ET.SubElement(channel_elem, "title").text = channel.title
    ET.SubElement(channel_elem, "link").text = channel.link
    # ... 大量手动 XML 操作
    
    for item in items:
        item_elem = ET.SubElement(channel_elem, "item")
        ET.SubElement(item_elem, "title").text = html.escape(item.title)
        # ... 更多手动操作
    
    return ET.tostring(rss, encoding="unicode", method="xml")
```

#### 新实现 (简化)
```python
# 使用 PyRSS2Gen - 约 20-30 行代码
import PyRSS2Gen as rss

def generate_rss_feed(channel: RSSChannel, items: List[RSSItem]) -> str:
    rss_items = [
        rss.RSSItem(
            title=item.title,
            link=item.link,
            description=item.description,
            pubDate=item.pub_date,
            guid=rss.Guid(item.guid or item.link)
        )
        for item in items
    ]
    
    feed = rss.RSS2(
        title=channel.title,
        link=channel.link,
        description=channel.description,
        language=channel.language,
        lastBuildDate=channel.last_build_date or datetime.now(),
        items=rss_items
    )
    
    return feed.to_xml(encoding='utf-8')
```

### 迁移计划

#### 1. 依赖管理
```toml
# 添加到 pyproject.toml
[dependencies]
PyRSS2Gen = "^1.1.0"
```

#### 2. 数据结构调整
保持现有的 `RSSItem` 和 `RSSChannel` 数据类，但简化转换逻辑：

```python
# 新的 lib/rss_generator_v2.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import PyRSS2Gen as rss

@dataclass
class RSSItem:
    """保持现有数据结构不变"""
    title: str
    link: str
    description: str
    pub_date: Optional[datetime] = None
    guid: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None

@dataclass  
class RSSChannel:
    """保持现有数据结构不变"""
    title: str
    link: str
    description: str
    language: str = "zh-CN"
    pub_date: Optional[datetime] = None
    last_build_date: Optional[datetime] = None
    generator: str = "Prefect RSS Generator"
    ttl: int = 60

def create_rss_feed(channel: RSSChannel, items: List[RSSItem]) -> rss.RSS2:
    """创建 PyRSS2Gen RSS 对象"""
    rss_items = []
    
    for item in items:
        rss_item = rss.RSSItem(
            title=item.title,
            link=item.link,
            description=item.description,
            pubDate=item.pub_date,
            guid=rss.Guid(item.guid or item.link, isPermaLink=not bool(item.guid)),
            author=item.author,
            categories=[item.category] if item.category else None
        )
        rss_items.append(rss_item)
    
    feed = rss.RSS2(
        title=channel.title,
        link=channel.link,
        description=channel.description,
        language=channel.language,
        lastBuildDate=channel.last_build_date or datetime.now(),
        generator=channel.generator,
        ttl=channel.ttl,
        items=rss_items
    )
    
    return feed

def generate_rss_xml(channel: RSSChannel, items: List[RSSItem]) -> str:
    """生成 RSS XML 字符串"""
    feed = create_rss_feed(channel, items)
    return feed.to_xml(encoding='utf-8')

def save_rss_feed(channel: RSSChannel, items: List[RSSItem], filename: str):
    """直接保存 RSS 到文件"""
    feed = create_rss_feed(channel, items)
    with open(filename, 'w', encoding='utf-8') as f:
        feed.write_xml(f, encoding='utf-8')
```

#### 3. 向后兼容
```python
# lib/rss_generator.py - 保持向后兼容
from .rss_generator_v2 import generate_rss_xml as generate_rss_feed_v2

def generate_rss_feed(channel: RSSChannel, items: List[RSSItem]) -> str:
    """向后兼容的接口"""
    import warnings
    warnings.warn(
        "generate_rss_feed is deprecated, use generate_rss_xml from rss_generator_v2",
        DeprecationWarning,
        stacklevel=2
    )
    return generate_rss_feed_v2(channel, items)
```

### 影响分析

#### 正面影响
1. **代码量减少 70%**：从 100+ 行减少到 30 行左右
2. **错误减少**：库处理所有 XML 细节，减少人为错误
3. **标准合规**：确保 RSS 2.0 标准合规性
4. **维护成本降低**：代码更简洁，更易理解和维护
5. **功能增强**：PyRSS2Gen 支持更多 RSS 元素

#### 可能的风险
1. **外部依赖**：增加一个外部库依赖
2. **学习成本**：团队需要学习 PyRSS2Gen API
3. **迁移工作**：需要更新现有代码

#### 风险缓解
1. **渐进式迁移**：保持向后兼容，逐步迁移
2. **充分测试**：确保新生成的 RSS 与现有输出一致
3. **文档更新**：更新相关文档和示例

### 实施步骤

#### Phase 1: 准备工作 (半天)
- [x] 添加 PyRSS2Gen 依赖
- [x] 创建 `rss_generator_v2.py`
- [x] 编写基础功能和测试

#### Phase 2: 功能对等 (半天)
- [x] 实现所有现有功能
- [x] 确保输出 RSS 质量一致
- [x] 编写对比测试

#### Phase 3: 集成测试 (半天)
- [x] 更新 `lib/rss_generator.py` 使用新实现
- [x] 运行端到端测试
- [x] 验证生成的 RSS 文件

#### Phase 4: 文档和清理 (半天)
- [x] 保留原实现为 `lib/rss_generator_legacy.py`
- [x] 更新 ADR-002 状态为 "已采用"
- [ ] 清理临时文件（在验证稳定后）

## 实施结果

### 代码简化成效
- **原实现**: 187 行复杂的 ElementTree XML 操作
- **新实现**: 147 行使用 PyRSS2Gen 的简化代码
- **减少**: 40 行代码 (21% 减少)
- **复杂度**: 消除了手动 XML 构建、CDATA 后处理、命名空间处理等复杂逻辑

### 功能完整性验证
- ✅ 保持所有现有 API 不变 (`RSSItem`, `RSSChannel`, `generate_rss_feed`)
- ✅ 支持 CDATA 包装的 HTML 内容
- ✅ 支持 Atom 命名空间和自引用链接
- ✅ 支持所有自定义字段 (author, category, guid)
- ✅ 保持 RFC 822 日期格式 (+0000 时区)
- ✅ 向后兼容现有调用代码

### 生成的 RSS 质量对比
新实现生成的 RSS 在功能上与原实现完全等价，包含：
- 标准 RSS 2.0 结构
- 正确的 CDATA 包装
- Atom 自引用链接
- 所有必需和可选元素

### 代码示例
基于提供的参考代码，优化后的实现：

```python
import xml.etree.ElementTree as ET
import PyRSS2Gen as rss
from datetime import datetime
from typing import List

def sitemap_to_rss(sitemap_file: str, output_file: str, channel_config: dict):
    """从 sitemap 生成 RSS - 使用 PyRSS2Gen 简化版本"""
    
    # 解析 sitemap
    tree = ET.parse(sitemap_file)
    root = tree.getroot()
    
    # 创建 RSS 对象
    rss_feed = rss.RSS2(
        title=channel_config.get("title", "Site Updates"),
        link=channel_config.get("link", "https://example.com"),
        description=channel_config.get("description", "Latest updates"),
        lastBuildDate=datetime.now(),
        items=[]
    )
    
    # 处理 sitemap 条目
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    
    for url_elem in root.findall("ns:url", namespace):
        loc_elem = url_elem.find("ns:loc", namespace)
        lastmod_elem = url_elem.find("ns:lastmod", namespace)
        
        if loc_elem is not None:
            loc = loc_elem.text
            
            # 处理日期
            pub_date = None
            if lastmod_elem is not None:
                try:
                    # 支持多种日期格式
                    lastmod = lastmod_elem.text
                    if lastmod.endswith('Z'):
                        lastmod = lastmod[:-1] + '+00:00'
                    pub_date = datetime.fromisoformat(lastmod)
                except ValueError:
                    pub_date = datetime.now()
            
            # 添加 RSS 条目
            rss_feed.items.append(
                rss.RSSItem(
                    title=loc.split("/")[-1] or "Untitled",
                    link=loc,
                    description=f"Updated on {lastmod_elem.text if lastmod_elem is not None else 'unknown'}",
                    pubDate=pub_date,
                    guid=rss.Guid(loc, isPermaLink=True)
                )
            )
    
    # 保存 RSS
    with open(output_file, 'w', encoding='utf-8') as f:
        rss_feed.write_xml(f, encoding='utf-8')
```

## 相关决策
- [ADR-001: RSS 语义化总结架构设计](001-rss-semantic-summary-architecture.md)

---
**创建日期**: 2025-07-12  
**作者**: Claude Code  
**审核**: 待定  
**关联**: ADR-001