from dataclasses import dataclass
from datetime import datetime

import PyRSS2Gen as rss


@dataclass
class RSSItem:
    """RSS feed 中的单个条目"""

    title: str
    link: str
    description: str
    pub_date: datetime | None = None
    guid: str | None = None
    author: str | None = None
    category: str | None = None


@dataclass
class RSSChannel:
    """RSS feed 的频道信息"""

    title: str
    link: str
    description: str
    language: str = "zh-CN"
    pub_date: datetime | None = None
    last_build_date: datetime | None = None
    generator: str = "Prefect RSS Generator"
    ttl: int = 60  # minutes


def generate_rss_feed(channel: RSSChannel, items: list[RSSItem]) -> str:
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
            guid=rss.Guid(item.guid or item.link, isPermaLink=bool(not item.guid)),
            author=item.author,
            categories=[item.category] if item.category else None,
        )
        rss_items.append(rss_item)

    # 创建标准RSS频道
    feed = rss.RSS2(
        title=channel.title,
        link=channel.link,
        description=channel.description,
        language=channel.language,
        lastBuildDate=channel.last_build_date or datetime.now(),
        pubDate=channel.pub_date or datetime.now(),
        generator=channel.generator,
        ttl=channel.ttl,
        items=rss_items,
    )

    # 生成 XML
    xml_content = feed.to_xml(encoding="utf-8")
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode("utf-8")

    # 应用必要的后处理
    xml_content = _apply_final_formatting(xml_content, channel.link)

    return xml_content


def _apply_final_formatting(xml_str: str, channel_link: str) -> str:
    """应用最终格式化：Atom命名空间、自引用链接和CDATA处理"""
    import html
    import re

    # 添加Atom命名空间
    xml_str = xml_str.replace('<rss version="2.0">', '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')

    # 日期格式和清理
    xml_str = xml_str.replace(" GMT</", " +0000</")
    xml_str = re.sub(r"<docs>.*?</docs>\s*", "", xml_str)

    # 添加Atom自引用链接
    atom_link = f'<atom:link href="{channel_link}/rss.xml" rel="self" type="application/rss+xml" />'
    insert_pattern = r"(</ttl>\s*)" if "<ttl>" in xml_str else r"(</generator>\s*)"
    xml_str = re.sub(insert_pattern, f"\\1{atom_link}", xml_str)

    # CDATA处理
    def to_cdata(match):
        content = match.group(1)
        if "&lt;" in content and "&gt;" in content:
            return f"<description><![CDATA[{html.unescape(content)}]]></description>"
        return match.group(0)

    return re.sub(r"<description>(.*?)</description>", to_cdata, xml_str, flags=re.DOTALL)


def format_rss_date(dt: datetime) -> str:
    """将datetime对象格式化为RSS标准日期格式(RFC 822)"""
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def extract_title_from_url(url: str) -> str:
    """从URL提取标题"""
    path = url.split("//")[-1]
    if "/" in path:
        path = "/".join(path.split("/")[1:])
    if "." in path.split("/")[-1]:
        path = path.rsplit(".", 1)[0]
    title = path.replace("-", " ").replace("_", " ").replace("/", " - ")
    return title.title() if title else "Untitled"


def create_rss_item_from_sitemap_entry(entry, title: str | None = None, description: str | None = None) -> RSSItem:
    """从sitemap条目创建RSS条目"""
    return RSSItem(
        title=title or extract_title_from_url(entry.url),
        link=entry.url,
        description=description
        or f"页面更新于 {entry.lastmod.strftime('%Y-%m-%d %H:%M:%S') if entry.lastmod else '未知时间'}",
        pub_date=entry.lastmod,
        guid=entry.url,
    )
