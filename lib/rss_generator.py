import PyRSS2Gen as rss
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class RSSItem:
    """RSS feed 中的单个条目"""
    title: str
    link: str
    description: str
    pub_date: Optional[datetime] = None
    guid: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None


@dataclass
class RSSChannel:
    """RSS feed 的频道信息"""
    title: str
    link: str
    description: str
    language: str = "zh-CN"
    pub_date: Optional[datetime] = None
    last_build_date: Optional[datetime] = None
    generator: str = "Prefect RSS Generator"
    ttl: int = 60  # minutes


def generate_rss_feed(channel: RSSChannel, items: List[RSSItem]) -> str:
    """
    生成 RSS 2.0 格式的 XML feed
    
    使用 PyRSS2Gen 简化实现，保持接口兼容性
    """
    # 创建 RSS 条目
    rss_items = []
    for item in items:
        rss_item = rss.RSSItem(
            title=item.title,
            link=item.link,
            description=item.description,
            pubDate=item.pub_date,
            guid=rss.Guid(
                item.guid or item.link,
                isPermaLink=bool(not item.guid)
            ),
            author=item.author,
            categories=[item.category] if item.category else None
        )
        rss_items.append(rss_item)
    
    # 创建 RSS 频道
    feed = rss.RSS2(
        title=channel.title,
        link=channel.link,
        description=channel.description,
        language=channel.language,
        lastBuildDate=channel.last_build_date or datetime.now(),
        pubDate=channel.pub_date or datetime.now(),
        generator=channel.generator,
        ttl=channel.ttl,
        items=rss_items
    )
    
    # 生成 XML
    xml_content = feed.to_xml(encoding='utf-8')
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode('utf-8')
    
    # 添加必要的兼容性处理
    xml_content = _add_compatibility_features(xml_content, channel.link)
    
    return xml_content


def _add_compatibility_features(xml_str: str, channel_link: str) -> str:
    """
    添加关键的兼容性功能
    """
    import re
    import html
    
    # 1. 添加 Atom 命名空间
    xml_str = xml_str.replace(
        '<rss version="2.0">',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
    )
    
    # 2. 移除默认的 docs 元素
    xml_str = re.sub(r'<docs>.*?</docs>', '', xml_str)
    
    # 3. 添加自引用链接
    atom_link = f'<atom:link href="{channel_link}/rss.xml" rel="self" type="application/rss+xml" />'
    xml_str = re.sub(r'(</ttl>\s*)', f'\\1{atom_link}', xml_str)
    
    # 4. 转换日期格式
    xml_str = xml_str.replace(' GMT</', ' +0000</')
    
    # 5. 转换 HTML 内容为 CDATA
    def to_cdata(match):
        content = match.group(1)
        if '&lt;' in content and '&gt;' in content:
            content = html.unescape(content)
            return f'<description><![CDATA[{content}]]></description>'
        return match.group(0)
    
    xml_str = re.sub(r'<description>(.*?)</description>', to_cdata, xml_str, flags=re.DOTALL)
    
    return xml_str


# 保持向后兼容的辅助函数
def format_rss_date(dt: datetime) -> str:
    """将 datetime 对象格式化为 RSS 标准的日期格式 (RFC 822)"""
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def extract_title_from_url(url: str) -> str:
    """从 URL 中提取标题，作为默认标题"""
    path = url.split('//')[-1]
    if '/' in path:
        path = '/'.join(path.split('/')[1:])
    
    if '.' in path.split('/')[-1]:
        path = path.rsplit('.', 1)[0]
    
    title = path.replace('-', ' ').replace('_', ' ').replace('/', ' - ')
    return title.title() if title else "Untitled"


def create_rss_item_from_sitemap_entry(entry, title: Optional[str] = None, description: Optional[str] = None) -> RSSItem:
    """从 sitemap 条目创建 RSS 条目"""
    if not title:
        title = extract_title_from_url(entry.url)
    
    if not description:
        description = f"页面更新于 {entry.lastmod.strftime('%Y-%m-%d %H:%M:%S') if entry.lastmod else '未知时间'}"
    
    return RSSItem(
        title=title,
        link=entry.url,
        description=description,
        pub_date=entry.lastmod,
        guid=entry.url
    )