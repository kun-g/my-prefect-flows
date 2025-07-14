#!/usr/bin/env python3
"""
智能内容分析示例脚本
演示如何使用内容分析系统
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from lib.content_analyzer import ContentAnalyzer
from lib.batch import batch_analyze_articles


async def analyze_sample_content():
    """分析示例内容"""
    print("🚀 智能内容分析示例")
    
    # 示例内容
    sample_content = """
    # Python性能优化指南

    Python是一门强大的编程语言，但在某些场景下可能面临性能瓶颈。本文将介绍一些实用的优化技巧。

    ## 1. 选择合适的数据结构

    不同的数据结构在不同场景下有不同的性能表现。例如：
    - 列表（List）：适合频繁添加元素
    - 集合（Set）：适合快速查找
    - 字典（Dict）：适合键值对存储

    ## 2. 使用内置函数

    Python的内置函数通常用C实现，性能更好：

    ```python
    # 推荐
    result = sum(numbers)
    
    # 不推荐
    result = 0
    for num in numbers:
        result += num
    ```

    ## 3. 避免频繁的字符串拼接

    字符串是不可变对象，频繁拼接会创建大量临时对象：

    ```python
    # 推荐
    result = ''.join(strings)
    
    # 不推荐  
    result = ''
    for s in strings:
        result += s
    ```

    ## 4. 使用生成器

    生成器可以节省内存，特别是处理大量数据时：

    ```python
    # 生成器表达式
    squares = (x**2 for x in range(1000000))
    ```

    ## 5. 性能分析工具

    使用cProfile等工具分析代码性能瓶颈：

    ```python
    import cProfile
    cProfile.run('your_function()')
    ```

    ## 总结

    性能优化需要在可读性和效率之间找到平衡。建议先写出清晰的代码，然后针对瓶颈进行优化。

    记住：过早优化是万恶之源。先测量，再优化。
    """

    sample_title = "Python性能优化指南"
    sample_url = "https://example.com/python-performance-guide"

    try:
        # 初始化分析器
        analyzer = ContentAnalyzer()
        print("✅ 内容分析器初始化成功")

        # 执行分析
        print("🔍 开始分析内容...")
        analysis = await analyzer.analyze_content(
            content=sample_content,
            title=sample_title,
            url=sample_url
        )

        # 输出结果
        print("\n📊 分析结果:")
        print(f"📝 标题: {analysis.title}")
        print(f"⭐ 综合评分: {analysis.reading_score:.1f}/10")
        print(f"📅 预估阅读时间: {analysis.reading_time_minutes}分钟")
        print(f"🎯 难度等级: {analysis.difficulty_level}")
        print(f"🏷️ 标签: {', '.join(analysis.tags)}")
        print(f"🤖 使用模型: {analysis.model_used}")
        print(f"📈 置信度: {analysis.confidence_score:.2f}")

        print(f"\n📋 摘要:")
        print(analysis.summary)

        print(f"\n📊 详细评分:")
        for dimension, score in analysis.score_breakdown.items():
            print(f"   {dimension}: {score:.1f}/10")

        # 获取使用统计
        stats = analyzer.get_usage_statistics()
        print(f"\n💰 使用统计:")
        print(f"   请求数: {stats['total_requests']}")
        print(f"   Token数: {stats['total_tokens']}")
        print(f"   预估成本: ${stats['total_cost']:.4f}")

        # 保存结果
        result_path = "output/sample_analysis.json"
        os.makedirs(os.path.dirname(result_path), exist_ok=True)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(analysis.to_json())
        
        print(f"\n💾 结果已保存到: {result_path}")

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        print("💡 提示: 请确保设置了OPENAI_API_KEY环境变量")


async def analyze_from_url():
    """从URL分析内容"""
    print("\n🌐 从URL分析内容示例")
    
    # 这里可以添加真实的URL分析
    # 需要先获取网页内容，然后进行分析
    
    test_urls = [
        "https://docs.python.org/3/tutorial/",
        "https://realpython.com/python-concurrency/",
        "https://fastapi.tiangolo.com/tutorial/"
    ]
    
    print("📋 示例URL列表:")
    for i, url in enumerate(test_urls, 1):
        print(f"   {i}. {url}")
    
    print("💡 要实现URL分析，需要:")
    print("   1. 使用requests获取网页内容")
    print("   2. 使用现有的content_extractor提取正文")
    print("   3. 调用ContentAnalyzer进行分析")


async def batch_analysis_example():
    """批量分析示例"""
    print("\n📦 批量分析示例")
    
    # 模拟批量文章数据
    articles = [
        {
            "title": "Django REST API开发指南",
            "content": "Django REST Framework是开发API的强大工具...",
            "url": "https://example.com/django-api"
        },
        {
            "title": "React Hooks最佳实践",
            "content": "React Hooks改变了我们编写组件的方式...",
            "url": "https://example.com/react-hooks"
        },
        {
            "title": "Docker容器化部署教程",
            "content": "Docker让应用部署变得更加简单和一致...",
            "url": "https://example.com/docker-deploy"
        }
    ]
    
    try:
        analyzer = ContentAnalyzer()
        
        print(f"🔄 开始批量分析 {len(articles)} 篇文章...")
        
        # 批量分析
        results = await batch_analyze_articles(articles, max_concurrent=2)
        
        print(f"✅ 完成分析，成功处理 {len(results)} 篇文章")
        
        # 输出汇总
        if results:
            avg_score = sum(r.reading_score for r in results) / len(results)
            print(f"\n📊 批量分析汇总:")
            print(f"   平均评分: {avg_score:.2f}/10")
            print(f"   文章列表:")
            
            for result in results:
                print(f"   • {result.title}: {result.reading_score:.1f}分")

    except Exception as e:
        print(f"❌ 批量分析失败: {e}")


def main():
    """主函数"""
    print("🎯 智能内容分析系统示例")
    print("=" * 50)
    
    # 检查环境
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ 未检测到OPENAI_API_KEY环境变量")
        print("💡 请设置API密钥以进行真实分析:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("\n🔧 当前将运行模拟示例...")
        
        # 运行不需要API的示例
        asyncio.run(batch_analysis_example())
        return
    
    # 运行完整示例
    print("🔑 检测到API密钥，运行完整示例...")
    
    asyncio.run(analyze_sample_content())
    asyncio.run(analyze_from_url()) 
    asyncio.run(batch_analysis_example())


if __name__ == "__main__":
    main()