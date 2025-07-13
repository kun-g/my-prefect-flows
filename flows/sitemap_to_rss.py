from prefect import flow, task
from datetime import datetime
from typing import List, Dict, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from lib.sitemap import fetch_sitemap, SitemapEntry
from lib.rss_generator import (
    RSSChannel, RSSItem, generate_rss_feed, 
    create_rss_item_from_sitemap_entry
)
from lib.r2 import R2Client, R2Config


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
def create_rss_items(entries: List[SitemapEntry], fetch_titles: bool = False, extract_content: bool = False, content_length: int = 500) -> List[RSSItem]:
    """
    从 sitemap 条目创建 RSS 条目
    
    Args:
        entries: sitemap 条目列表
        fetch_titles: 是否获取页面标题
        extract_content: 是否提取页面内容
        content_length: 内容提取的最大长度（字符数）
    """
    import httpx
    import re
    from bs4 import BeautifulSoup
    
    rss_items = []
    
    for entry in entries:
        title = None
        description = None
        content = ""
        
        # 如果需要获取页面标题或内容
        if fetch_titles or extract_content:
            try:
                print(f"获取页面内容: {entry.url}")
                response = httpx.get(entry.url, timeout=10)
                response.raise_for_status()
                
                page_content = response.text
                
                # 提取标题
                if fetch_titles:
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', page_content, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        title = title_match.group(1).strip()
                
                # 提取内容
                if extract_content:
                    description = extract_page_content(page_content, entry.url, content_length)
                else:
                    # 仅提取描述（meta description）
                    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', page_content, re.IGNORECASE)
                    if desc_match:
                        description = desc_match.group(1).strip()
                
            except Exception as e:
                print(f"获取页面内容失败 {entry.url}: {e}")
        
        # 创建 RSS 条目
        rss_item = create_rss_item_from_sitemap_entry(entry, title, description)
        rss_items.append(rss_item)
    
    print(f"创建了 {len(rss_items)} 个 RSS 条目")
    return rss_items


def extract_page_content(html_content: str, url: str, max_length: int = 500) -> str:
    """
    从 HTML 页面提取主要内容并添加 Read More 链接
    
    Args:
        html_content: HTML 页面内容
        url: 页面 URL
        max_length: 最大内容长度
        
    Returns:
        包含内容摘录和 Read More 链接的 HTML 字符串
    """
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'meta', 'link']):
            element.decompose()
        
        # 尝试找到主要内容区域
        content_selectors = [
            'article',
            '[role="main"]',
            '.content',
            '.main-content', 
            '.post-content',
            '.entry-content',
            '.article-content',
            'main',
            '#content',
            '#main'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # 如果没有找到主要内容区域，使用 body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # 提取文本内容，专注于段落
        paragraphs = main_content.find_all('p', recursive=True)
        
        # 如果没有足够的段落，也查找其他可能包含内容的元素
        if len(paragraphs) < 2:
            additional_elements = main_content.find_all(['div', 'article', 'section'], recursive=True)
            # 过滤掉明显的非内容元素
            for elem in additional_elements:
                elem_text = elem.get_text(strip=True)
                elem_class = ' '.join(elem.get('class', []))
                elem_id = elem.get('id', '')
                
                # 跳过明显的非内容元素
                skip_classes = ['sidebar', 'navigation', 'nav', 'menu', 'footer', 'header', 'ad', 'advertisement', 'social']
                if any(skip_class in elem_class.lower() or skip_class in elem_id.lower() for skip_class in skip_classes):
                    continue
                    
                if len(elem_text) >= 50:  # 只包含有足够文本的元素
                    paragraphs.append(elem)
        
        extracted_paragraphs = []
        total_length = 0
        
        for p in paragraphs:
            # 跳过空段落或只包含链接的段落
            text = p.get_text(strip=True)
            if len(text) < 20:  # 跳过太短的段落
                continue
            
            # 检查是否是不需要的内容
            p_class = ' '.join(p.get('class', []))
            p_id = p.get('id', '')
            skip_classes = ['sidebar', 'navigation', 'nav', 'menu', 'footer', 'header', 'ad', 'advertisement', 'social', 'comment']
            
            if any(skip_class in p_class.lower() or skip_class in p_id.lower() for skip_class in skip_classes):
                continue
                
            # 保留段落的 HTML 结构，但清理内容
            p_copy = BeautifulSoup(str(p), 'html.parser')
            
            # 移除嵌套的不需要元素
            for unwanted in p_copy(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                unwanted.decompose()
            
            # 简化为 <p> 标签以保持一致性
            paragraph_text = p_copy.get_text(strip=True)
            paragraph_html = f"<p>{paragraph_text}</p>"
            
            if total_length + len(paragraph_text) > max_length:
                # 截断到最大长度
                remaining_length = max_length - total_length
                if remaining_length > 50:  # 至少保留 50 个字符
                    truncated_text = paragraph_text[:remaining_length] + "..."
                    paragraph_html = f"<p>{truncated_text}</p>"
                    extracted_paragraphs.append(paragraph_html)
                break
            
            extracted_paragraphs.append(paragraph_html)
            total_length += len(paragraph_text)
            
            if total_length >= max_length:
                break
        
        # 如果没有提取到有效内容，使用 meta description 作为后备
        if not extracted_paragraphs:
            import re
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
            if desc_match:
                meta_desc = desc_match.group(1).strip()
                if meta_desc:
                    extracted_paragraphs = [f"<p>{meta_desc}</p>"]
        
        # 组合内容和 Read More 链接
        if extracted_paragraphs:
            content_html = '\n\n'.join(extracted_paragraphs)
            read_more_link = f'<p><a href="{url}">Read More...</a></p>'
            return f"{content_html}\n\n{read_more_link}"
        else:
            # 如果没有内容，只返回 Read More 链接
            return f'<p><a href="{url}">Read More...</a></p>'
            
    except Exception as e:
        print(f"内容提取失败: {e}")
        # 返回简单的 Read More 链接作为后备
        return f'<p><a href="{url}">Read More...</a></p>'


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
        config = R2Config(**r2_config if r2_config else {})
        uploader = R2Client(config)

        # 使用统一的 upload 方法，自动处理内容和文件路径
        uploader.upload(
            content=content,
            local_path=file_path,
            key=object_key,
            ContentType='application/rss+xml'
        )
        
        result = {"success": True, "file_url": uploader.get_url(object_key)}
        print(f"RSS已成功上传到 R2: {result['file_url']}")
        
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
    extract_content: bool = False,
    content_length: int = 500,
    max_items: int = 50,
    sort_by_date: bool = True,
    r2_object_key: Optional[str] = None,
    r2_config: Optional[Dict] = None,
    upload_method: str = "direct"
):
    """
    完整的 sitemap 到 RSS 转换流程，支持可选的 R2 上传
    
    Args:
        sitemap_url: sitemap URL
        channel_config: RSS 频道配置
        output_file: 输出文件路径
        filter_config: 过滤器配置
        fetch_titles: 是否获取页面标题
        extract_content: 是否提取页面内容
        content_length: 内容提取的最大长度（字符数）
        max_items: 最大条目数
        sort_by_date: 是否按日期排序
        r2_object_key: R2 存储的对象键（文件名），提供此参数则自动上传到 R2
        r2_config: R2 配置字典
        upload_method: 上传方式 ("direct" 直接上传内容, "file" 上传文件)
    """
    upload_to_r2 = r2_object_key is not None
    action_desc = "并上传到 R2" if upload_to_r2 else ""
    print(f"开始 sitemap 到 RSS 转换{action_desc}流程: {sitemap_url}")
    
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
    rss_items = create_rss_items(sitemap_entries, fetch_titles, extract_content, content_length)
    
    # 步骤 5: 生成 RSS XML
    channel = RSSChannel(
        title=channel_config.get("title", "Site Updates"),
        link=channel_config.get("link", "https://example.com"),
        description=channel_config.get("description", "Latest updates from the site"),
        language=channel_config.get("language", "zh-CN"),
        ttl=channel_config.get("ttl", 60)
    )
    rss_xml_content = generate_rss_feed(channel, rss_items)
    
    # 构建基础结果
    result = {
        "rss_generation": {
            "output_file": output_file,
            "total_items": len(rss_items),
            "channel_title": channel_config.get("title", "Site Updates")
        }
    }
    
    # 步骤 6: 处理输出
    if upload_to_r2:
        # 上传到 R2
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
        
        # 添加上传结果
        result["r2_upload"] = upload_result
        
        if upload_result and upload_result.get("success"):
            print(f"RSS 生成并上传到 R2 流程完成! 访问URL: {upload_result.get('file_url')}")
        else:
            print(f"RSS 生成完成，但上传到 R2 失败: {upload_result.get('error', 'Unknown error') if upload_result else 'No upload result'}")
    else:
        # 仅保存到本地文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rss_xml_content)
        print(f"RSS 生成流程完成! 文件保存到: {output_file}")
    
    return result


# 示例使用
if __name__ == "__main__":
    # 测试单个网站的 RSS 生成
    test_config = {
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
            "max_items": 5
        },
        "output_file": "output/prefect-blog.xml",
        "r2_object_key": "feeds/prefect-blog.xml"
    }
    
    print("测试 RSS 生成流程（包含内容提取和 Read More 链接）...")
    print("如需部署多个网站，请使用: python deployments/deploy_rss_feeds.py")
    print("-" * 50)
    
    # 仅生成 RSS 到本地文件，启用内容提取功能
    result = sitemap_to_rss_flow(
        sitemap_url=test_config["sitemap_url"],
        channel_config=test_config["channel_config"],
        output_file=test_config["output_file"],
        filter_config=test_config["filter_config"],
        fetch_titles=True,
        extract_content=True,  # 启用内容提取
        content_length=400,    # 提取400字符内容
        max_items=5,
        sort_by_date=True
    )
    
    if result:
        print(f"\n测试结果: {result}")
    else:
        print("\n测试失败")