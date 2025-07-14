#!/usr/bin/env python3
"""
智能内容分析系统测试脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from lib.content_analysis import ContentAnalysis, ScoreDimensions, TagCategories
from lib.content_optimizer import ContentOptimizer
from lib.content_analyzer import ContentAnalyzer


def test_data_structures():
    """测试数据结构"""
    print("🧪 测试数据结构...")
    
    # 测试ScoreDimensions
    weights = ScoreDimensions.get_weights()
    print(f"✅ 评分维度权重: {weights}")
    
    # 测试权重计算
    test_scores = {
        "实用性": 8.0,
        "学习价值": 7.5,
        "时效性": 9.0,
        "技术深度": 6.0,
        "完整性": 8.5
    }
    weighted_score = ScoreDimensions.calculate_weighted_score(test_scores)
    print(f"✅ 加权评分计算: {weighted_score}")
    
    # 测试TagCategories
    all_tags = TagCategories.get_all_tags()
    print(f"✅ 可用标签数量: {len(all_tags)}")
    
    suggested_tags = TagCategories.suggest_tags_by_content("这是一篇关于Python Web开发的文章")
    print(f"✅ 建议标签: {suggested_tags}")


def test_content_optimizer():
    """测试内容优化器"""
    print("\n🧪 测试内容优化器...")
    
    # 测试文本
    test_content = """
    # Python Web开发最佳实践
    
    在现代Web开发中，Python是一个非常流行的选择。本文将介绍一些重要的最佳实践。
    
    ## 框架选择
    
    Django和Flask是两个主要的Python Web框架。Django提供了完整的功能，而Flask更加轻量级。
    
    ## 代码示例
    
    ```python
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def hello():
        return 'Hello World!'
    ```
    
    ## 性能优化
    
    对于高并发应用，可以考虑使用异步编程。异步编程能够显著提升性能。
    
    ## 总结
    
    选择合适的框架和优化策略对于成功的Web开发项目至关重要。
    """
    
    optimizer = ContentOptimizer(max_tokens=200)
    
    # 测试token计算
    tokens = optimizer.estimate_tokens(test_content)
    print(f"✅ Token估算: {tokens}")
    
    # 测试智能截断
    truncated, metadata = optimizer.optimize_for_analysis(test_content, "Python Web开发最佳实践")
    print(f"✅ 截断后长度: {len(truncated)}")
    print(f"✅ 元数据: {metadata}")
    
    # 测试摘要候选提取
    candidates = optimizer.extract_summary_candidates(test_content)
    print(f"✅ 摘要候选: {len(candidates)}个")


async def test_content_analyzer_offline():
    """测试内容分析器离线功能"""
    print("\n🧪 测试内容分析器离线功能...")
    
    try:
        analyzer = ContentAnalyzer()
        print("✅ 内容分析器初始化成功")
        
        # 测试后备结果
        fallback_summary = analyzer._get_fallback_result("summary")
        fallback_tags = analyzer._get_fallback_result("tags")
        fallback_scores = analyzer._get_fallback_result("scores")
        
        print(f"✅ 后备摘要: {fallback_summary[:50]}...")
        print(f"✅ 后备标签: {fallback_tags}")
        print(f"✅ 后备评分: {fallback_scores}")
        
    except Exception as e:
        print(f"❌ 内容分析器测试失败: {e}")


def test_environment_setup():
    """测试环境设置"""
    print("\n🧪 测试环境设置...")
    
    # 检查Python版本
    print(f"✅ Python版本: {sys.version}")
    
    # 检查必要的包
    required_packages = ['litellm', 'tiktoken', 'prefect', 'beautifulsoup4']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            print(f"❌ {package}: 未安装")
    
    # 检查环境变量
    env_vars = ['OPENAI_API_KEY']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: 已设置")
        else:
            print(f"⚠️ {var}: 未设置 (可选)")


def run_integration_test():
    """运行集成测试"""
    print("\n🧪 运行集成测试...")
    
    # 测试完整的分析流程（使用模拟数据）
    test_article = {
        "title": "Python异步编程指南",
        "content": """
        Python异步编程是现代Web开发中的重要技术。本文将深入探讨asyncio库的使用方法。
        
        ## 基本概念
        
        异步编程允许程序在等待I/O操作时执行其他任务，从而提高效率。
        
        ## 实际应用
        
        在Web开发中，异步编程特别适用于处理大量并发请求。
        
        ```python
        import asyncio
        
        async def fetch_data():
            await asyncio.sleep(1)
            return "data"
        ```
        
        ## 最佳实践
        
        1. 合理使用async/await
        2. 避免阻塞操作
        3. 正确处理异常
        """,
        "url": "https://example.com/python-async-guide"
    }
    
    # 模拟分析结果
    from datetime import datetime
    
    mock_analysis = ContentAnalysis(
        url=test_article["url"],
        title=test_article["title"],
        summary="本文介绍了Python异步编程的基本概念和实际应用方法。",
        tags=["Python", "异步编程", "Web开发", "性能优化"],
        reading_score=8.2,
        reading_time_minutes=6,
        difficulty_level="中级",
        score_breakdown={
            "实用性": 8.5,
            "学习价值": 8.0,
            "时效性": 7.8,
            "技术深度": 8.0,
            "完整性": 8.2
        },
        analyzed_at=datetime.now(),
        model_used="test-model",
        confidence_score=0.85
    )
    
    print("✅ 模拟分析结果:")
    print(f"   标题: {mock_analysis.title}")
    print(f"   评分: {mock_analysis.reading_score}")
    print(f"   标签: {mock_analysis.tags}")
    print(f"   难度: {mock_analysis.difficulty_level}")
    
    # 测试JSON序列化
    json_str = mock_analysis.to_json()
    print(f"✅ JSON序列化成功, 长度: {len(json_str)}")
    
    # 测试从字典恢复
    recovered = ContentAnalysis.from_dict(mock_analysis.to_dict())
    print(f"✅ 从字典恢复成功: {recovered.title}")


async def main():
    """主测试函数"""
    print("🚀 开始智能内容分析系统测试\n")
    
    # 基本功能测试
    test_environment_setup()
    test_data_structures()
    test_content_optimizer()
    await test_content_analyzer_offline()
    run_integration_test()
    
    print("\n✅ 所有基本测试完成!")
    print("\n📝 下一步:")
    print("1. 设置API密钥 (OPENAI_API_KEY)")
    print("2. 运行真实的内容分析测试")
    print("3. 集成到Prefect工作流中")


if __name__ == "__main__":
    asyncio.run(main())