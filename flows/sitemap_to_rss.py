from prefect import flow, task
from datetime import datetime
from typing import List, Dict, Optional
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from lib.sitemap import fetch_sitemap, SitemapEntry
from lib.rss_generator import (
    RSSChannel, RSSItem, generate_rss_feed, 
    create_rss_item_from_sitemap_entry
)


@task(log_prints=True)
def apply_rss_filters(entries: List[SitemapEntry], filter_config: Optional[Dict] = None) -> List[SitemapEntry]:
    """
    为 RSS 生成应用过滤器
    """
    if not filter_config:
        return entries
    
    filtered_entries = []
    
    for entry in entries:
        include = True
        
        # 包含 URL 模式
        if "include_patterns" in filter_config:
            patterns = filter_config["include_patterns"]
            if not any(pattern in entry.url for pattern in patterns):
                include = False
        
        # 排除 URL 模式
        if "exclude_patterns" in filter_config:
            patterns = filter_config["exclude_patterns"]
            if any(pattern in entry.url for pattern in patterns):
                include = False
        
        # 限制条目数量
        if "max_items" in filter_config:
            max_items = filter_config["max_items"]
            if len(filtered_entries) >= max_items:
                break
        
        if include:
            filtered_entries.append(entry)
    
    print(f"过滤后的条目数: {len(entries)} -> {len(filtered_entries)}")
    return filtered_entries


@task(log_prints=True)
def sort_entries_by_date(entries: List[SitemapEntry], reverse: bool = True) -> List[SitemapEntry]:
    """
    按最后修改时间排序条目
    """
    # 将没有 lastmod 的条目放到最后
    def sort_key(entry):
        if entry.lastmod:
            return entry.lastmod
        else:
            return datetime.min
    
    sorted_entries = sorted(entries, key=sort_key, reverse=reverse)
    print(f"按日期排序完成，最新的 {len(sorted_entries)} 个条目")
    return sorted_entries


@task(log_prints=True)
def create_rss_items(entries: List[SitemapEntry], fetch_titles: bool = False) -> List[RSSItem]:
    """
    从 sitemap 条目创建 RSS 条目
    """
    import httpx
    import re
    
    rss_items = []
    
    for entry in entries:
        title = None
        description = None
        
        # 如果需要获取页面标题
        if fetch_titles:
            try:
                print(f"获取页面标题: {entry.url}")
                response = httpx.get(entry.url, timeout=10)
                response.raise_for_status()
                
                # 提取标题
                content = response.text
                title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                
                # 提取描述（meta description）
                desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', content, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip()
                
            except Exception as e:
                print(f"获取页面内容失败 {entry.url}: {e}")
        
        # 创建 RSS 条目
        rss_item = create_rss_item_from_sitemap_entry(entry, title, description)
        rss_items.append(rss_item)
    
    print(f"创建了 {len(rss_items)} 个 RSS 条目")
    return rss_items


@task(log_prints=True)
def generate_rss_xml(
    rss_items: List[RSSItem], 
    channel_config: Dict,
    output_file: str
) -> str:
    """
    生成 RSS XML 并保存到文件
    """
    # 创建频道配置
    channel = RSSChannel(
        title=channel_config.get("title", "Site Updates"),
        link=channel_config.get("link", "https://example.com"),
        description=channel_config.get("description", "Latest updates from the site"),
        language=channel_config.get("language", "zh-CN"),
        ttl=channel_config.get("ttl", 60)
    )
    
    # 生成 RSS XML
    rss_xml = generate_rss_feed(channel, rss_items)
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rss_xml)
    
    print(f"RSS feed 已保存到: {output_file}")
    return output_file


@flow(name="Sitemap to RSS Generator")
def sitemap_to_rss_flow(
    sitemap_url: str,
    channel_config: Dict,
    output_file: str = "rss_feed.xml",
    filter_config: Optional[Dict] = None,
    fetch_titles: bool = False,
    max_items: int = 50,
    sort_by_date: bool = True
):
    """
    完整的 sitemap 到 RSS 转换流程
    
    Args:
        sitemap_url: sitemap URL
        channel_config: RSS 频道配置
        output_file: 输出文件路径
        filter_config: 过滤器配置
        fetch_titles: 是否获取页面标题
        max_items: 最大条目数
        sort_by_date: 是否按日期排序
    """
    print(f"开始 sitemap 到 RSS 转换流程: {sitemap_url}")
    
    # 步骤 1: 获取 sitemap
    sitemap_entries = fetch_sitemap(sitemap_url)
    
    if not sitemap_entries:
        print("未找到 sitemap 条目，退出流程")
        return None
    
    # 步骤 2: 应用过滤器
    if filter_config:
        # 确保最大条目数限制
        if max_items and "max_items" not in filter_config:
            filter_config["max_items"] = max_items
        sitemap_entries = apply_rss_filters(sitemap_entries, filter_config)
    else:
        # 如果没有过滤器，至少应用最大条目数限制
        sitemap_entries = sitemap_entries[:max_items]
    
    if not sitemap_entries:
        print("过滤后无条目，退出流程")
        return None
    
    # 步骤 3: 按日期排序
    if sort_by_date:
        sitemap_entries = sort_entries_by_date(sitemap_entries)
    
    # 步骤 4: 创建 RSS 条目
    rss_items = create_rss_items(sitemap_entries, fetch_titles)
    
    # 步骤 5: 生成并保存 RSS XML
    output_path = generate_rss_xml(rss_items, channel_config, output_file)
    
    print(f"RSS 生成流程完成! 文件保存到: {output_path}")
    return {
        "output_file": output_path,
        "total_items": len(rss_items),
        "channel_title": channel_config.get("title", "Site Updates")
    }


# 示例配置
SAMPLE_CONFIGS = {
    "lennysnewsletter": {
        "sitemap_url": "https://www.lennysnewsletter.com/sitemap.xml",
        "channel_config": {
            "title": "Lenny's Newsletter Updates",
            "link": "https://www.lennysnewsletter.com",
            "description": "Latest updates from Lenny's Newsletter",
            "language": "en"
        },
        "filter_config": {
            "include_patterns": ["/p/"],
            "max_items": 20
        },
        "output_file": "output/lennys_rss.xml"
    },
    
    "pythonweekly": {
        "sitemap_url": "https://www.pythonweekly.com/sitemap.xml",
        "channel_config": {
            "title": "Python Weekly Updates",
            "link": "https://www.pythonweekly.com",
            "description": "Latest Python Weekly newsletters",
            "language": "en"
        },
        "filter_config": {
            "include_patterns": ["/archive/"],
            "max_items": 15
        },
        "output_file": "output/pythonweekly_rss.xml"
    },
    
    "prefect": {
        "sitemap_url": "https://www.prefect.io/sitemap.xml",
        "channel_config": {
            "title": "Prefect Blog Updates",
            "link": "https://www.prefect.io",
            "description": "Latest blog posts from Prefect",
            "language": "en"
        },
        "filter_config": {
            "include_patterns": ["/blog/"],
            "exclude_patterns": ["/blog/tags/", "/blog/page/"],
            "max_items": 25
        },
        "output_file": "output/prefect_rss.xml"
    }
}


# 示例使用
if __name__ == "__main__":
    # 使用预定义配置
    config = SAMPLE_CONFIGS["prefect"]
    
    sitemap_to_rss_flow(
        sitemap_url=config["sitemap_url"],
        channel_config=config["channel_config"],
        output_file=config["output_file"],
        filter_config=config["filter_config"],
        fetch_titles=True,  # 获取真实的页面标题
        max_items=20,
        sort_by_date=True
    )


# 部署为定时任务的示例
def deploy_rss_feeds():
    """部署多个 RSS feed 生成任务"""
    for name, config in SAMPLE_CONFIGS.items():
        sitemap_to_rss_flow.serve(
            name=f"rss-{name}",
            cron="0 */6 * * *",  # 每6小时运行一次
            parameters={
                "sitemap_url": config["sitemap_url"],
                "channel_config": config["channel_config"],
                "output_file": config["output_file"],
                "filter_config": config["filter_config"],
                "fetch_titles": True,
                "max_items": 30
            }
        )