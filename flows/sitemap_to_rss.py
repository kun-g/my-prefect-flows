from prefect import flow, task
from datetime import datetime
from typing import List, Dict, Optional
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from lib.sitemap import fetch_sitemap, SitemapEntry
from lib.rss_generator import (
    RSSChannel, RSSItem, generate_rss_feed, 
    create_rss_item_from_sitemap_entry
)
from lib.r2_uploader import create_r2_uploader, R2Config


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


@task(log_prints=True)
def upload_rss_to_r2(
    object_key: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    r2_config: Optional[Dict] = None
) -> Dict:
    """
    上传 RSS 到 Cloudflare R2
    
    Args:
        object_key: R2 存储的对象键
        content: RSS XML 内容字符串（与 file_path 二选一）
        file_path: 本地 RSS 文件路径（与 content 二选一）
        r2_config: R2 配置字典，如果不提供则从环境变量读取
        
    Returns:
        上传结果字典
        
    Raises:
        ValueError: 当 content 和 file_path 都提供或都不提供时
    """
    # 参数互斥验证
    if (content is None) == (file_path is None):
        raise ValueError("必须提供 content 或 file_path 其中一个参数，不能同时提供或都不提供")
    
    try:
        # 创建 R2 配置
        if r2_config:
            config = R2Config(**r2_config)
        else:
            config = R2Config.from_env()
        
        # 创建上传器
        uploader = create_r2_uploader(config)
        
        # 根据参数选择上传方式
        if content is not None:
            # 上传字符串内容
            result = uploader.upload_string(
                content=content,
                object_key=object_key,
                content_type='application/rss+xml'
            )
            upload_type = "内容"
        else:
            # 上传文件
            result = uploader.upload_file(
                local_file_path=file_path,
                object_key=object_key,
                content_type='application/rss+xml'
            )
            upload_type = "文件"
        
        # 处理结果
        if result["success"]:
            print(f"RSS {upload_type}已成功上传到 R2: {result['file_url']}")
        else:
            print(f"上传 RSS {upload_type}到 R2 失败: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        error_msg = f"上传 RSS 到 R2 时发生错误: {e}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "object_key": object_key
        }


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


@flow(name="Sitemap to RSS with R2 Upload")
def sitemap_to_rss_with_r2_flow(
    sitemap_url: str,
    channel_config: Dict,
    r2_object_key: str,
    output_file: str = "rss_feed.xml",
    filter_config: Optional[Dict] = None,
    fetch_titles: bool = False,
    max_items: int = 50,
    sort_by_date: bool = True,
    r2_config: Optional[Dict] = None,
    upload_method: str = "direct"
):
    """
    完整的 sitemap 到 RSS 转换并上传到 R2 的流程
    
    Args:
        sitemap_url: sitemap URL
        channel_config: RSS 频道配置
        r2_object_key: R2 存储的对象键（文件名）
        output_file: 本地输出文件路径
        filter_config: 过滤器配置
        fetch_titles: 是否获取页面标题
        max_items: 最大条目数
        sort_by_date: 是否按日期排序
        r2_config: R2 配置字典
        upload_method: 上传方式 ("direct" 直接上传内容, "file" 上传文件)
    """
    print(f"开始 sitemap 到 RSS 转换并上传到 R2 的流程: {sitemap_url}")
    
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
    
    # 步骤 5: 生成 RSS XML
    channel = RSSChannel(
        title=channel_config.get("title", "Site Updates"),
        link=channel_config.get("link", "https://example.com"),
        description=channel_config.get("description", "Latest updates from the site"),
        language=channel_config.get("language", "zh-CN"),
        ttl=channel_config.get("ttl", 60)
    )
    rss_xml_content = generate_rss_feed(channel, rss_items)
    
    # 步骤 6: 上传到 R2
    upload_result = None
    if upload_method == "direct":
        # 直接上传 RSS 内容
        upload_result = upload_rss_to_r2(r2_object_key, content=rss_xml_content, r2_config=r2_config)
    else:
        # 先保存到本地文件，然后上传文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rss_xml_content)
        print(f"RSS feed 已保存到本地: {output_file}")
        
        upload_result = upload_rss_to_r2(r2_object_key, file_path=output_file, r2_config=r2_config)
    
    # 构建最终结果
    result = {
        "rss_generation": {
            "output_file": output_file,
            "total_items": len(rss_items),
            "channel_title": channel_config.get("title", "Site Updates")
        },
        "r2_upload": upload_result
    }
    
    if upload_result and upload_result.get("success"):
        print(f"RSS 生成并上传到 R2 流程完成! 访问URL: {upload_result.get('file_url')}")
    else:
        print(f"RSS 生成完成，但上传到 R2 失败: {upload_result.get('error', 'Unknown error') if upload_result else 'No upload result'}")
    
    return result


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
        "output_file": "output/lennys_rss.xml",
        "r2_object_key": "feeds/lennys-newsletter.xml"
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
        "output_file": "output/pythonweekly_rss.xml",
        "r2_object_key": "feeds/python-weekly.xml"
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
            "max_items": 7
        },
        "output_file": "output/prefect_rss.xml",
        "r2_object_key": "feeds/prefect-blog.xml"
    }
}


# 示例使用
if __name__ == "__main__":
    # 使用预定义配置 - 仅生成 RSS
    config = SAMPLE_CONFIGS["prefect"]
    
    # 选择流程类型
    use_r2_upload = True  # 设置为 True 启用 R2 上传
    
    if use_r2_upload:
        # 生成 RSS 并上传到 R2
        result = sitemap_to_rss_with_r2_flow(
            sitemap_url=config["sitemap_url"],
            channel_config=config["channel_config"],
            r2_object_key=config["r2_object_key"],
            output_file=config["output_file"],
            filter_config=config["filter_config"],
            fetch_titles=True,  # 获取真实的页面标题
            max_items=20,
            sort_by_date=True,
            upload_method="direct"  # 直接上传内容，不保存本地文件
        )
        
        if result:
            print(f"\n流程执行结果:")
            print(f"RSS 生成: {result['rss_generation']}")
            print(f"R2 上传: {result['r2_upload']}")
    else:
        # 仅生成 RSS 到本地文件
        result = sitemap_to_rss_flow(
            sitemap_url=config["sitemap_url"],
            channel_config=config["channel_config"],
            output_file=config["output_file"],
            filter_config=config["filter_config"],
            fetch_titles=True,  # 获取真实的页面标题
            max_items=20,
            sort_by_date=True
        )
        
        if result:
            print(f"\n流程执行结果: {result}")


# 部署为定时任务的示例
def deploy_rss_feeds():
    """部署多个 RSS feed 生成任务（仅本地保存）"""
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


def deploy_rss_feeds_with_r2():
    """部署多个 RSS feed 生成并上传到 R2 的任务"""
    for name, config in SAMPLE_CONFIGS.items():
        sitemap_to_rss_with_r2_flow.serve(
            name=f"rss-r2-{name}",
            cron="0 */6 * * *",  # 每6小时运行一次
            parameters={
                "sitemap_url": config["sitemap_url"],
                "channel_config": config["channel_config"],
                "r2_object_key": config["r2_object_key"],
                "output_file": config["output_file"],
                "filter_config": config["filter_config"],
                "fetch_titles": True,
                "max_items": 30,
                "upload_method": "direct"
            }
        )