"""
内容提取器 - 从HTML页面提取主要内容并添加Read More链接
"""

def extract_page_content(html_content: str, url: str) -> str:
    """
    从 HTML 页面提取主要内容并添加 Read More 链接
    
    Args:
        html_content: HTML 页面内容
        url: 页面 URL
        
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
            
            extracted_paragraphs.append(paragraph_html)
        
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