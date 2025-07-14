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
        "total_articles": len(valid_analyses),
        "average_score": sum(a.reading_score for a in valid_analyses) / len(valid_analyses),
        "articles": [analysis.to_dict() for analysis in valid_analyses]
    }
    
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存JSON文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 结果已保存到: {output_path}")
    print(f"📊 统计信息: {len(valid_analyses)}篇文章，平均评分: {results['average_score']:.2f}")
    
    return output_path


@task(log_prints=True)
def generate_analysis_report(results_path: str) -> str:
    """
    生成分析报告
    """
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get("articles", [])
        if not articles:
            return "没有可用的分析数据"
        
        # 生成统计报告
        scores = [a["reading_score"] for a in articles]
        difficulties = [a["difficulty_level"] for a in articles]
        
        report = f"""
# 智能内容分析报告

## 基本统计
- 分析文章数量: {len(articles)}
- 平均阅读价值评分: {sum(scores)/len(scores):.2f}/10
- 最高评分: {max(scores):.2f}
- 最低评分: {min(scores):.2f}

## 难度分布
- 初级: {difficulties.count('初级')}篇
- 中级: {difficulties.count('中级')}篇  
- 高级: {difficulties.count('高级')}篇

## 高价值文章推荐 (评分>=8.0)
"""
        
        # 筛选高价值文章
        high_value = [a for a in articles if a["reading_score"] >= 8.0]
        high_value.sort(key=lambda x: x["reading_score"], reverse=True)
        
        for i, article in enumerate(high_value[:10], 1):
            report += f"""
### {i}. {article['title']} ({article['reading_score']:.1f}分)
- URL: {article['url']}
- 难度: {article['difficulty_level']}
- 预估阅读时间: {article['reading_time_minutes']}分钟
- 标签: {', '.join(article['tags'])}
- 摘要: {article['summary'][:100]}...

"""
        
        # 保存报告
        report_path = results_path.replace('.json', '_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📋 报告已生成: {report_path}")
        return report_path
        
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        return ""


@flow(name="智能内容分析工作流", description="从sitemap提取URL并进行智能内容分析")
async def content_analysis_flow(
    sitemap_url: str,
    output_dir: str = "output/content_analysis",
    max_articles: int = 20,
    max_concurrent: int = 3,
    llm_config_path: Optional[str] = None
):
    """
    智能内容分析主工作流
    
    Args:
        sitemap_url: sitemap URL
        output_dir: 输出目录
        max_articles: 最大分析文章数
        max_concurrent: 最大并发数
        llm_config_path: LLM配置文件路径
    """
    print(f"🚀 开始智能内容分析工作流")
    print(f"📍 Sitemap URL: {sitemap_url}")
    print(f"📁 输出目录: {output_dir}")
    
    # 1. 获取sitemap条目
    try:
        sitemap_entries = fetch_sitemap(sitemap_url)
        print(f"📄 获取到 {len(sitemap_entries)} 个sitemap条目")
    except Exception as e:
        print(f"❌ 获取sitemap失败: {e}")
        return
    
    # 2. 限制分析数量
    entries_to_analyze = sitemap_entries[:max_articles]
    print(f"🎯 将分析前 {len(entries_to_analyze)} 篇文章")
    
    # 3. 初始化内容分析器
    analyzer = ContentAnalyzer()
    
    # 4. 批量分析内容
    analysis_tasks = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def analyze_with_semaphore(entry: SitemapEntry):
        async with semaphore:
            return await analyze_single_url(entry.url, analyzer)
    
    # 创建所有分析任务
    for entry in entries_to_analyze:
        task = analyze_with_semaphore(entry)
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
    
    # 5. 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"{output_dir}/analysis_results_{timestamp}.json"
    
    saved_path = save_analysis_results(valid_analyses, results_path)
    
    # 6. 生成报告
    if saved_path:
        report_path = generate_analysis_report(saved_path)
        
        return {
            "results_path": saved_path,
            "report_path": report_path,
            "articles_analyzed": len(valid_analyses),
        }
    
    return {"error": "分析失败，没有保存结果"}


@flow(name="批量站点内容分析", description="分析多个站点的内容")
async def batch_site_analysis_flow(
    sites_config: List[Dict[str, str]],
    output_dir: str = "output/batch_analysis",
    max_articles_per_site: int = 10
):
    """
    批量分析多个站点的内容
    
    Args:
        sites_config: 站点配置列表，每个包含 name, sitemap_url
        output_dir: 输出目录
        max_articles_per_site: 每个站点最大分析文章数
    """
    print(f"🚀 开始批量站点内容分析")
    print(f"📍 待分析站点数: {len(sites_config)}")
    
    results = {}
    
    for site in sites_config:
        site_name = site["name"]
        sitemap_url = site["sitemap_url"]
        
        print(f"\n🔍 分析站点: {site_name}")
        
        site_output_dir = f"{output_dir}/{site_name}"
        
        try:
            result = await content_analysis_flow(
                sitemap_url=sitemap_url,
                output_dir=site_output_dir,
                max_articles=max_articles_per_site,
                max_concurrent=2  # 降低并发以避免被限制
            )
            results[site_name] = result
            
        except Exception as e:
            print(f"❌ 站点 {site_name} 分析失败: {e}")
            results[site_name] = {"error": str(e)}
    
    # 生成汇总报告
    summary_path = f"{output_dir}/batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 批量分析完成，汇总报告: {summary_path}")
    return results


if __name__ == "__main__":
    # 示例运行
    import asyncio
    
    # 单站点分析示例
    asyncio.run(content_analysis_flow(
        sitemap_url="https://www.prefect.io/sitemap.xml",
        max_articles=1
    ))