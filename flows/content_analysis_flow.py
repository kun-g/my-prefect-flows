"""
智能内容分析工作流 - Prefect集成
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from prefect import flow, task
from dotenv import load_dotenv
load_dotenv()

# 导入项目库
from lib.sitemap import fetch_sitemap, SitemapEntry
from lib.content_extractor import extract_page_content
from lib.content_analyzer import ContentAnalyzer
from lib.content_analysis import ContentAnalysis


@task(log_prints=True, retries=2)
async def analyze_single_url(url: str, analyzer: ContentAnalyzer) -> Optional[ContentAnalysis]:
    """
    分析单个URL的内容
    """
    try:
        print(f"🔍 开始分析: {url}")
        
        # 获取页面内容
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 提取标题和内容
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "无标题"
        
        # 使用现有的内容提取器
        content = extract_page_content(response.text, url)
        
        # 清理HTML标签获取纯文本
        content_soup = BeautifulSoup(content, 'html.parser')
        clean_content = content_soup.get_text()
        
        if len(clean_content.strip()) < 100:
            print(f"⚠️ 内容太短，跳过分析: {url}")
            return None
        
        # 执行智能分析
        analysis = await analyzer.analyze_content(
            content=clean_content,
            title=title_text,
            url=url
        )
        
        print(f"✅ 分析完成: {url} (评分: {analysis.reading_score:.1f})")
        return analysis
        
    except Exception as e:
        print(f"❌ 分析失败 {url}: {e}")
        return None


@task(log_prints=True)
def save_analysis_results(analyses: List[ContentAnalysis], output_path: str) -> str:
    """
    保存分析结果到文件
    """
    # 过滤掉None结果
    valid_analyses = [a for a in analyses if a is not None]
    
    if not valid_analyses:
        print("⚠️ 没有有效的分析结果")
        return ""
    
    # 转换为字典格式
    results = {
        "analyzed_at": datetime.now().isoformat(),
        "articles": [analysis.to_dict() for analysis in valid_analyses]
    }
    
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存JSON文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 结果已保存到: {output_path}")
    
    return output_path




@flow(name="智能内容分析工作流", description="对指定URL列表进行智能内容分析")
async def content_analysis_flow(
    urls: List[str],
    output_dir: str = "output/content_analysis",
    max_concurrent: int = 3
):
    """
    智能内容分析主工作流
    
    Args:
        urls: 要分析的URL列表
        output_dir: 输出目录
        max_concurrent: 最大并发数
    """
    print(f"🚀 开始智能内容分析工作流")
    print(f"📍 分析URL数量: {len(urls)}")
    print(f"📁 输出目录: {output_dir}")
    
    if not urls:
        print("❌ 没有提供要分析的URL")
        return {"error": "没有提供要分析的URL"}
    
    # 1. 初始化内容分析器
    analyzer = ContentAnalyzer()
    
    # 2. 批量分析内容
    analysis_tasks = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def analyze_with_semaphore(url: str):
        async with semaphore:
            return await analyze_single_url(url, analyzer)
    
    # 创建所有分析任务
    for url in urls:
        task = analyze_with_semaphore(url)
        analysis_tasks.append(task)
    
    # 等待所有分析完成
    print(f"🔄 开始批量分析 (并发数: {max_concurrent})")
    analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
    
    # 处理结果，过滤异常
    valid_analyses = []
    for result in analyses:
        if isinstance(result, Exception):
            print(f"⚠️ 分析任务异常: {result}")
        elif result is not None:
            valid_analyses.append(result)
    
    print(f"✅ 成功分析 {len(valid_analyses)} 篇文章")
    
    # 3. 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"{output_dir}/analysis_results_{timestamp}.json"
    
    saved_path = save_analysis_results(valid_analyses, results_path)
    
    # 4. 打印摘要
    if saved_path:
        return {
            "results_path": saved_path,
            "articles_analyzed": len(valid_analyses),
        }
    
    return {"error": "分析失败，没有保存结果"}


@flow(name="批量URL组内容分析", description="分析多组URL的内容")
async def batch_urls_analysis_flow(
    url_groups: List[Dict[str, any]],
    output_dir: str = "output/batch_analysis"
):
    """
    批量分析多组URL的内容
    
    Args:
        url_groups: URL组配置列表，每个包含 name, urls 字段
        output_dir: 输出目录
    """
    print(f"🚀 开始批量URL组内容分析")
    print(f"📍 待分析URL组数: {len(url_groups)}")
    
    results = {}
    
    for group in url_groups:
        group_name = group["name"]
        urls = group["urls"]
        max_concurrent = group.get("max_concurrent", 2)
        
        print(f"\n🔍 分析URL组: {group_name} ({len(urls)} 个URL)")
        
        group_output_dir = f"{output_dir}/{group_name}"
        
        try:
            result = await content_analysis_flow(
                urls=urls,
                output_dir=group_output_dir,
                max_concurrent=max_concurrent
            )
            results[group_name] = result
            
        except Exception as e:
            print(f"❌ URL组 {group_name} 分析失败: {e}")
            results[group_name] = {"error": str(e)}
    
    # 生成汇总报告
    summary_path = f"{output_dir}/batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 批量分析完成，汇总报告: {summary_path}")
    return results


# 便利函数
def create_url_list_from_text(text: str) -> List[str]:
    """
    从文本中提取URL列表
    支持换行分隔或逗号分隔的URL
    """
    urls = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if line:
            # 处理逗号分隔的URL
            if ',' in line:
                urls.extend([url.strip() for url in line.split(',') if url.strip()])
            else:
                urls.append(line)
    
    # 过滤有效的URL
    valid_urls = []
    for url in urls:
        if url.startswith(('http://', 'https://')):
            valid_urls.append(url)
    
    return valid_urls


def create_url_list_from_file(file_path: str) -> List[str]:
    """
    从文件中读取URL列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return create_url_list_from_text(content)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return []


if __name__ == "__main__":
    # 示例运行
    import asyncio
    
    # 直接URL列表分析示例
    example_urls = [
        "https://www.prefect.io/blog/introducing-prefect-3",
        "https://www.prefect.io/blog/prefect-flows-vs-airflow-dags"
    ]
    
    asyncio.run(content_analysis_flow(urls=example_urls))