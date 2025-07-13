import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
import html


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
    """
    # 创建根元素
    rss = ET.Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    # 创建 channel 元素
    channel_elem = ET.SubElement(rss, "channel")
    
    # 添加频道基本信息
    ET.SubElement(channel_elem, "title").text = channel.title
    ET.SubElement(channel_elem, "link").text = channel.link
    ET.SubElement(channel_elem, "description").text = channel.description
    ET.SubElement(channel_elem, "language").text = channel.language
    ET.SubElement(channel_elem, "generator").text = channel.generator
    ET.SubElement(channel_elem, "ttl").text = str(channel.ttl)
    
    # 添加 atom:link 自引用
    atom_link = ET.SubElement(channel_elem, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", f"{channel.link}/rss.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")
    
    # 添加时间信息
    now = datetime.now()
    if channel.pub_date:
        ET.SubElement(channel_elem, "pubDate").text = format_rss_date(channel.pub_date)
    else:
        ET.SubElement(channel_elem, "pubDate").text = format_rss_date(now)
    
    if channel.last_build_date:
        ET.SubElement(channel_elem, "lastBuildDate").text = format_rss_date(channel.last_build_date)
    else:
        ET.SubElement(channel_elem, "lastBuildDate").text = format_rss_date(now)
    
    # 添加条目
    for item in items:
        item_elem = ET.SubElement(channel_elem, "item")
        
        ET.SubElement(item_elem, "title").text = html.escape(item.title)
        ET.SubElement(item_elem, "link").text = item.link
        
        # Handle description with potential HTML content
        create_cdata_element(item_elem, "description", item.description)
        
        # GUID (通常使用链接)
        guid_elem = ET.SubElement(item_elem, "guid")
        guid_elem.text = item.guid or item.link
        guid_elem.set("isPermaLink", "true" if not item.guid else "false")
        
        # 发布日期
        if item.pub_date:
            ET.SubElement(item_elem, "pubDate").text = format_rss_date(item.pub_date)
        
        # 作者
        if item.author:
            ET.SubElement(item_elem, "author").text = html.escape(item.author)
        
        # 分类
        if item.category:
            ET.SubElement(item_elem, "category").text = html.escape(item.category)
    
    # 转换为字符串
    xml_str = ET.tostring(rss, encoding="unicode", method="xml")
    
    # 添加 XML 声明
    formatted_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    
    # Post-process to add CDATA sections for HTML content
    formatted_xml = _add_cdata_to_descriptions(formatted_xml)
    
    return formatted_xml


def _add_cdata_to_descriptions(xml_str: str) -> str:
    """
    Post-process XML to wrap HTML descriptions in CDATA sections
    """
    import re
    
    def replace_html_description(match):
        content = match.group(1)
        # Check if content contains HTML tags (escaped or unescaped)
        if ('&lt;' in content and '&gt;' in content) or ('<' in content and '>' in content):
            # Unescape any entities that ElementTree added and wrap in CDATA
            content = html.unescape(content)
            return f'<description><![CDATA[{content}]]></description>'
        else:
            # Keep plain text as-is
            return match.group(0)
    
    # Find and replace description elements
    pattern = r'<description>(.*?)</description>'
    result = re.sub(pattern, replace_html_description, xml_str, flags=re.DOTALL)
    
    return result


def create_cdata_element(parent, tag_name, content):
    """
    Create an XML element with content (will be post-processed for CDATA if needed)
    """
    elem = ET.SubElement(parent, tag_name)
    elem.text = content if content else ""
    return elem


def format_rss_date(dt: datetime) -> str:
    """
    将 datetime 对象格式化为 RSS 标准的日期格式 (RFC 822)
    例如: Mon, 12 Jul 2025 10:30:00 +0000
    """
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def extract_title_from_url(url: str) -> str:
    """
    从 URL 中提取标题，作为默认标题
    """
    # 移除协议和域名
    path = url.split('//')[-1]
    if '/' in path:
        path = '/'.join(path.split('/')[1:])
    
    # 移除文件扩展名
    if '.' in path.split('/')[-1]:
        path = path.rsplit('.', 1)[0]
    
    # 替换分隔符为空格并标题化
    title = path.replace('-', ' ').replace('_', ' ').replace('/', ' - ')
    
    return title.title() if title else "Untitled"


def create_rss_item_from_sitemap_entry(entry, title: Optional[str] = None, description: Optional[str] = None) -> RSSItem:
    """
    从 sitemap 条目创建 RSS 条目
    """
    # 如果没有提供标题，尝试从 URL 提取
    if not title:
        title = extract_title_from_url(entry.url)
    
    # 如果没有描述，使用默认描述
    if not description:
        description = f"页面更新于 {entry.lastmod.strftime('%Y-%m-%d %H:%M:%S') if entry.lastmod else '未知时间'}"
    
    return RSSItem(
        title=title,
        link=entry.url,
        description=description,
        pub_date=entry.lastmod,
        guid=entry.url
    )