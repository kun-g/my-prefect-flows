"""
批量处理工具模块
提供通用的批量分析功能
"""

import asyncio
from collections.abc import Callable
from typing import Any

from .content_analysis import ContentAnalysis
from .content_analyzer import ContentAnalyzer


class BatchProcessor:
    """
    通用批量处理器
    可以用于批量处理各种内容分析任务
    """

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent

    async def batch_analyze_content(
        self, analyzer: ContentAnalyzer, articles: list[dict[str, str]]
    ) -> list[ContentAnalysis]:
        """
        批量分析多篇文章

        Args:
            analyzer: 内容分析器实例
            articles: 文章列表，每个包含 title, content, url

        Returns:
            List[ContentAnalysis]: 分析结果列表
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def analyze_single(article):
            async with semaphore:
                try:
                    return await analyzer.analyze_content(
                        content=article["content"], title=article["title"], url=article["url"]
                    )
                except Exception as e:
                    print(f"❌ 文章分析失败 {article['url']}: {e}")
                    return None

        tasks = [analyze_single(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤掉失败的结果
        successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]

        return successful_results

    async def batch_process(self, items: list[Any], processor_func: Callable, *args, **kwargs) -> list[Any]:
        """
        通用批量处理函数

        Args:
            items: 要处理的项目列表
            processor_func: 处理函数
            *args, **kwargs: 传递给处理函数的额外参数

        Returns:
            List[Any]: 处理结果列表
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_single(item):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(processor_func):
                        return await processor_func(item, *args, **kwargs)
                    else:
                        return processor_func(item, *args, **kwargs)
                except Exception as e:
                    print(f"❌ 处理失败: {e}")
                    return None

        tasks = [process_single(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤掉失败的结果
        successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]

        return successful_results


# 便捷函数
async def batch_analyze_articles(
    articles: list[dict[str, str]], max_concurrent: int = 3, analyzer: ContentAnalyzer | None = None
) -> list[ContentAnalysis]:
    """
    便捷的批量文章分析函数

    Args:
        articles: 文章列表，每个包含 title, content, url
        max_concurrent: 最大并发数
        analyzer: 可选的分析器实例，如果不提供会创建新的

    Returns:
        List[ContentAnalysis]: 分析结果列表
    """
    if analyzer is None:
        analyzer = ContentAnalyzer()

    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.batch_analyze_content(analyzer, articles)
