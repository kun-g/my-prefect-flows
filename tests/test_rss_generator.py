#!/usr/bin/env python3
"""
RSS Generator单元测试

测试lib/rss_generator.py中的核心功能，包括：
- RSS feed生成
- CDATA处理
- Atom命名空间支持
- 日期格式化
- 数据结构兼容性
"""

import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from lib.rss_generator import (
    RSSChannel, RSSItem, generate_rss_feed,
    format_rss_date, extract_title_from_url,
    create_rss_item_from_sitemap_entry
)


class TestRSSDataStructures(unittest.TestCase):
    """测试RSS数据结构"""
    
    def test_rss_item_with_optional_fields(self):
        """测试RSSItem的可选字段"""
        pub_date = datetime(2025, 7, 14, 12, 0, 0)
        item = RSSItem(
            title="Full Item",
            link="https://example.com/full",
            description="Full description",
            pub_date=pub_date,
            guid="custom-guid",
            author="Test Author",
            category="Test Category"
        )
        
        self.assertEqual(item.pub_date, pub_date)
        self.assertEqual(item.guid, "custom-guid")
        self.assertEqual(item.author, "Test Author")
        self.assertEqual(item.category, "Test Category")


class TestRSSGeneration(unittest.TestCase):
    """测试RSS生成功能"""
    
    def setUp(self):
        """设置测试数据"""
        self.channel = RSSChannel(
            title="Test RSS Feed",
            link="https://example.com",
            description="A test RSS feed for unit testing",
            language="en"
        )
        
        self.items = [
            RSSItem(
                title="Plain Text Item",
                link="https://example.com/plain",
                description="Simple text description",
                pub_date=datetime(2025, 7, 14, 10, 0, 0),
                guid="item-1"
            ),
            RSSItem(
                title="HTML Content Item",
                link="https://example.com/html",
                description="Description with <strong>HTML</strong> and <em>formatting</em>",
                pub_date=datetime(2025, 7, 14, 11, 0, 0),
                author="Test Author",
                category="Test Category"
            )
        ]
    
    def test_basic_rss_generation(self):
        """测试基本RSS生成"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 验证基本结构
        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', rss_xml)
        self.assertIn('<rss version="2.0"', rss_xml)
        self.assertIn('<channel>', rss_xml)
        self.assertIn('</channel>', rss_xml)
        self.assertIn('</rss>', rss_xml)
        
        # 验证频道信息
        self.assertIn('<title>Test RSS Feed</title>', rss_xml)
        self.assertIn('<link>https://example.com</link>', rss_xml)
        self.assertIn('<description>A test RSS feed for unit testing</description>', rss_xml)
        self.assertIn('<language>en</language>', rss_xml)
    
    def test_rss_items_in_feed(self):
        """测试RSS条目是否正确包含在feed中"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 验证条目内容
        self.assertIn('<title>Plain Text Item</title>', rss_xml)
        self.assertIn('<title>HTML Content Item</title>', rss_xml)
        self.assertIn('https://example.com/plain', rss_xml)
        self.assertIn('https://example.com/html', rss_xml)
        self.assertIn('Simple text description', rss_xml)
    
    def test_atom_namespace_support(self):
        """测试Atom命名空间支持"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 验证Atom命名空间
        self.assertIn('xmlns:atom="http://www.w3.org/2005/Atom"', rss_xml)
        self.assertIn('atom:link', rss_xml)
        self.assertIn('rel="self"', rss_xml)
        self.assertIn('type="application/rss+xml"', rss_xml)
    
    def test_cdata_wrapping(self):
        """测试CDATA包装功能"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 验证HTML内容被CDATA包装
        self.assertIn('<![CDATA[', rss_xml)
        self.assertIn(']]>', rss_xml)
        
        # 检查HTML内容是否在CDATA中
        self.assertIn('<![CDATA[Description with <strong>HTML</strong>', rss_xml)
    
    def test_date_formatting(self):
        """测试日期格式"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 验证+0000时区格式
        self.assertIn('+0000', rss_xml)
        
        # 验证日期格式符合RFC 822
        # 应该包含类似"Mon, 14 Jul 2025 10:00:00 +0000"的格式
        import re
        date_pattern = r'\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} \+0000'
        self.assertTrue(re.search(date_pattern, rss_xml))
    
    def test_custom_fields(self):
        """测试自定义字段支持"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 验证作者字段
        self.assertIn('Test Author', rss_xml)
        
        # 验证分类字段
        self.assertIn('Test Category', rss_xml)
        
        # 验证GUID字段
        self.assertIn('item-1', rss_xml)
    
    def test_empty_items_list(self):
        """测试空条目列表"""
        rss_xml = generate_rss_feed(self.channel, [])
        
        # 应该仍然生成有效的RSS结构
        self.assertIn('<rss version="2.0"', rss_xml)
        self.assertIn('<channel>', rss_xml)
        self.assertIn('<title>Test RSS Feed</title>', rss_xml)
        self.assertIn('</channel>', rss_xml)
        self.assertIn('</rss>', rss_xml)
    
    def test_xml_validity(self):
        """测试生成的XML是否有效"""
        rss_xml = generate_rss_feed(self.channel, self.items)
        
        # 尝试解析XML以验证有效性
        try:
            root = ET.fromstring(rss_xml)
            self.assertEqual(root.tag, 'rss')
            self.assertEqual(root.get('version'), '2.0')
            
            # 验证channel元素存在
            channel = root.find('channel')
            self.assertIsNotNone(channel)
            
            # 验证基本元素
            title = channel.find('title')
            self.assertIsNotNone(title)
            self.assertEqual(title.text, 'Test RSS Feed')
            
        except ET.ParseError as e:
            self.fail(f"Generated XML is not valid: {e}")


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""
    
    def test_format_rss_date(self):
        """测试日期格式化"""
        dt = datetime(2025, 7, 14, 15, 30, 45)
        formatted = format_rss_date(dt)
        
        # 验证RFC 822格式
        self.assertEqual(formatted, "Mon, 14 Jul 2025 15:30:45 +0000")
    
    def test_extract_title_from_url(self):
        """测试从URL提取标题"""
        test_cases = [
            ("https://example.com/my-blog-post", "My Blog Post"),
            ("https://blog.example.com/tech/python-tips", "Tech - Python Tips"),
            ("https://example.com/about.html", "About"),
            ("https://example.com/", "Untitled"),
            ("https://example.com/news/2025/tech_update", "News - 2025 - Tech Update")
        ]
        
        for url, expected_title in test_cases:
            with self.subTest(url=url):
                result = extract_title_from_url(url)
                self.assertEqual(result, expected_title)
    
    def test_create_rss_item_from_sitemap_entry(self):
        """测试从sitemap条目创建RSS条目"""
        # 创建模拟的sitemap条目
        class MockSitemapEntry:
            def __init__(self, url, lastmod=None):
                self.url = url
                self.lastmod = lastmod
        
        entry = MockSitemapEntry(
            "https://example.com/blog/test-post",
            datetime(2025, 7, 14, 12, 0, 0)
        )
        
        item = create_rss_item_from_sitemap_entry(entry)
        
        self.assertEqual(item.link, "https://example.com/blog/test-post")
        self.assertEqual(item.title, "Blog - Test Post")
        self.assertEqual(item.pub_date, datetime(2025, 7, 14, 12, 0, 0))
        self.assertEqual(item.guid, "https://example.com/blog/test-post")
        self.assertIn("页面更新于", item.description)
        self.assertIn("2025-07-14 12:00:00", item.description)
    
    def test_create_rss_item_with_custom_title_description(self):
        """测试使用自定义标题和描述创建RSS条目"""
        class MockSitemapEntry:
            def __init__(self, url, lastmod=None):
                self.url = url
                self.lastmod = lastmod
        
        entry = MockSitemapEntry("https://example.com/test")
        
        item = create_rss_item_from_sitemap_entry(
            entry,
            title="Custom Title",
            description="Custom description"
        )
        
        self.assertEqual(item.title, "Custom Title")
        self.assertEqual(item.description, "Custom description")


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def test_special_characters_in_content(self):
        """测试内容中的特殊字符"""
        channel = RSSChannel(
            title="Test & Special Characters",
            link="https://example.com",
            description="Description with <script> and & symbols"
        )
        
        items = [
            RSSItem(
                title="Title with & and < > symbols",
                link="https://example.com/special",
                description="Content with \"quotes\" and 'apostrophes' & <em>HTML</em>"
            )
        ]
        
        rss_xml = generate_rss_feed(channel, items)
        
        # XML应该是有效的
        try:
            ET.fromstring(rss_xml)
        except ET.ParseError as e:
            self.fail(f"Failed to parse XML with special characters: {e}")
    
    def test_very_long_content(self):
        """测试很长的内容"""
        long_description = "A" * 10000 + "<p>HTML content</p>" + "B" * 10000
        
        channel = RSSChannel(
            title="Long Content Test",
            link="https://example.com",
            description="Testing very long content"
        )
        
        items = [
            RSSItem(
                title="Long Content Item",
                link="https://example.com/long",
                description=long_description
            )
        ]
        
        rss_xml = generate_rss_feed(channel, items)
        
        # 验证长内容被正确处理
        self.assertIn(long_description[:100], rss_xml)
        self.assertIn("<![CDATA[", rss_xml)  # 应该被CDATA包装
    
    def test_unicode_content(self):
        """测试Unicode内容"""
        channel = RSSChannel(
            title="Unicode测试频道",
            link="https://example.com",
            description="包含中文、emoji 🚀 和其他Unicode字符的测试"
        )
        
        items = [
            RSSItem(
                title="Unicode标题 🎉",
                link="https://example.com/unicode",
                description="内容包含中文、日文（こんにちは）、emoji 🌟 和 <strong>HTML</strong>"
            )
        ]
        
        rss_xml = generate_rss_feed(channel, items)
        
        # 验证Unicode内容被正确保留
        self.assertIn("Unicode测试频道", rss_xml)
        self.assertIn("🚀", rss_xml)
        self.assertIn("Unicode标题 🎉", rss_xml)
        self.assertIn("こんにちは", rss_xml)
        self.assertIn("🌟", rss_xml)
        
        # XML应该是有效的
        try:
            ET.fromstring(rss_xml)
        except ET.ParseError as e:
            self.fail(f"Failed to parse XML with Unicode content: {e}")


class TestBackwardCompatibility(unittest.TestCase):
    """测试向后兼容性"""
    
    def test_api_compatibility_with_legacy(self):
        """测试API与旧版本的兼容性"""
        # 这个测试确保新实现的API与旧版本完全一致
        channel = RSSChannel(
            title="Compatibility Test",
            link="https://example.com",
            description="Testing backward compatibility"
        )
        
        items = [
            RSSItem(
                title="Compatibility Item",
                link="https://example.com/compat",
                description="Testing compatibility"
            )
        ]
        
        # 这应该能正常工作，因为API没有改变
        try:
            rss_xml = generate_rss_feed(channel, items)
            self.assertIsInstance(rss_xml, str)
            self.assertGreater(len(rss_xml), 0)
        except Exception as e:
            self.fail(f"API compatibility broken: {e}")
    
    def test_output_format_consistency(self):
        """测试输出格式的一致性"""
        channel = RSSChannel(
            title="Format Test",
            link="https://example.com",
            description="Testing output format"
        )
        
        items = [
            RSSItem(
                title="Format Item",
                link="https://example.com/format",
                description="<p>HTML content</p>",
                pub_date=datetime(2025, 7, 14, 12, 0, 0),
                author="Test Author",
                category="Test Category",
                guid="format-guid"
            )
        ]
        
        rss_xml = generate_rss_feed(channel, items)
        
        # 验证关键元素都存在（与旧版本相同）
        required_elements = [
            '<rss version="2.0"',
            'xmlns:atom=',
            '<channel>',
            '<title>Format Test</title>',
            '<description>Testing output format</description>',
            '<language>zh-CN</language>',
            '<generator>Prefect RSS Generator</generator>',
            '<ttl>60</ttl>',
            'atom:link',
            '<![CDATA[<p>HTML content</p>]]>',
            'Test Author',
            'Test Category',
            'format-guid',
            '+0000'
        ]
        
        for element in required_elements:
            with self.subTest(element=element):
                self.assertIn(element, rss_xml, f"Missing required element: {element}")


if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestRSSDataStructures,
        TestRSSGeneration,
        TestUtilityFunctions,
        TestEdgeCases,
        TestBackwardCompatibility
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print(f"\n{'='*50}")
    print(f"测试摘要:")
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    # 退出码：成功为0，失败为1
    exit_code = 0 if result.wasSuccessful() else 1
    print(f"\n退出码: {exit_code}")
    exit(exit_code)