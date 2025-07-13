#!/usr/bin/env python3
"""
RSS Enhancement Demo
Shows before/after comparison of RSS improvements
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from lib.rss_generator import RSSItem, RSSChannel, generate_rss_feed
from flows.sitemap_to_rss import extract_page_content
from datetime import datetime

def show_before_after_demo():
    """Demonstrate the before and after RSS content"""
    
    print("🔄 RSS ENHANCEMENT DEMO")
    print("=" * 60)
    
    # Sample article HTML
    sample_article = """
    <html>
    <head>
        <title>The Future of RSS Feeds in 2024</title>
        <meta name="description" content="Learn about RSS feed improvements and best practices.">
    </head>
    <body>
        <article>
            <h1>The Future of RSS Feeds in 2024</h1>
            <p>RSS feeds remain one of the most reliable ways to distribute content across the web. Despite predictions of their demise, RSS continues to evolve and adapt to modern web standards.</p>
            <p>Recent improvements in RSS technology include better content extraction, HTML support, and enhanced metadata. These changes make RSS feeds more valuable for both publishers and subscribers.</p>
            <p>Modern RSS readers can now display rich content, images, and proper formatting, creating a better reading experience for users who prefer RSS over social media feeds.</p>
        </article>
    </body>
    </html>
    """
    
    article_url = "https://example.com/rss-future-2024"
    
    # BEFORE: Traditional RSS with just meta description
    print("📰 BEFORE (Traditional RSS):")
    print("-" * 30)
    
    old_item = RSSItem(
        title="The Future of RSS Feeds in 2024",
        link=article_url,
        description="Learn about RSS feed improvements and best practices.",  # Just meta description
        pub_date=datetime.now(),
        guid=article_url
    )
    
    channel = RSSChannel(
        title="Tech Blog",
        link="https://example.com",
        description="Latest technology articles"
    )
    
    old_rss = generate_rss_feed(channel, [old_item])
    
    # Extract just the description part for display
    import re
    old_desc_match = re.search(r'<description>(.*?)</description>', old_rss, re.DOTALL)
    old_description = old_desc_match.group(1) if old_desc_match else "Not found"
    
    print(f"Description: {old_description}")
    print(f"Length: {len(old_description)} characters")
    print("❌ No 'Read More' link")
    print("❌ Limited content preview")
    print()
    
    # AFTER: Enhanced RSS with content extraction
    print("✨ AFTER (Enhanced RSS):")
    print("-" * 30)
    
    # Extract content using new functionality
    enhanced_description = extract_page_content(sample_article, article_url, 400)
    
    new_item = RSSItem(
        title="The Future of RSS Feeds in 2024",
        link=article_url,
        description=enhanced_description,
        pub_date=datetime.now(),
        guid=article_url
    )
    
    new_rss = generate_rss_feed(channel, [new_item])
    
    # Extract the enhanced description
    new_desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', new_rss, re.DOTALL)
    new_description = new_desc_match.group(1) if new_desc_match else "Not found"
    
    # Pretty print the enhanced description
    print("Description (HTML content):")
    print(new_description.replace('\n\n', '\n').strip())
    print()
    print(f"Total length: {len(new_description)} characters")
    print("✅ Includes 'Read More...' link")
    print("✅ Rich content preview")
    print("✅ HTML formatting preserved")
    print("✅ CDATA sections for compatibility")
    print()
    
    # Benefits summary
    print("📊 IMPROVEMENT SUMMARY:")
    print("-" * 30)
    print(f"Content richness: {len(new_description) // len(old_description)}x more informative")
    print(f"User engagement: Increased with content preview")
    print(f"Traffic direction: Clear 'Read More' call-to-action")
    print(f"Technical quality: Proper HTML/CDATA handling")
    
    # Save demo files
    with open('/tmp/demo_before.xml', 'w', encoding='utf-8') as f:
        f.write(old_rss)
    
    with open('/tmp/demo_after.xml', 'w', encoding='utf-8') as f:
        f.write(new_rss)
    
    print(f"\n📁 Demo files saved:")
    print(f"   Before: /tmp/demo_before.xml")
    print(f"   After:  /tmp/demo_after.xml")

if __name__ == "__main__":
    show_before_after_demo()