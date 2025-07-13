"""
Content processing utilities following Single Responsibility Principle.
Each class has a single, well-defined responsibility.
"""
import re
import html
from datetime import datetime
from typing import Optional, List, Dict, Any
from .interfaces import ContentEntry


class URLProcessor:
    """Handles URL-related processing operations"""
    
    @staticmethod
    def extract_title_from_url(url: str) -> str:
        """Extract a title from URL path"""
        # Remove protocol and domain
        path = url.split('//')[-1]
        if '/' in path:
            path = '/'.join(path.split('/')[1:])
        
        # Remove file extension
        if '.' in path.split('/')[-1]:
            path = path.rsplit('.', 1)[0]
        
        # Replace separators with spaces and title case
        title = path.replace('-', ' ').replace('_', ' ').replace('/', ' - ')
        
        return title.title() if title else "Untitled"


class HTMLProcessor:
    """Handles HTML content processing operations"""
    
    @staticmethod
    def extract_title(html_content: str) -> Optional[str]:
        """Extract title from HTML content"""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', 
                               html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        return None
    
    @staticmethod
    def extract_description(html_content: str) -> Optional[str]:
        """Extract meta description from HTML content"""
        desc_match = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html_content, re.IGNORECASE
        )
        if desc_match:
            return desc_match.group(1).strip()
        return None
    
    @staticmethod
    def extract_body_preview(html_content: str, max_length: int = 200) -> Optional[str]:
        """Extract a preview from body content"""
        body_start = html_content.find('<body')
        if body_start == -1:
            return None
        
        body_start = html_content.find('>', body_start) + 1
        body_end = html_content.find('</body>')
        if body_end == -1:
            return None
        
        body_content = html_content[body_start:body_end]
        # Remove HTML tags for preview
        clean_content = re.sub(r'<[^>]+>', '', body_content)
        clean_content = clean_content.strip()
        
        if len(clean_content) > max_length:
            return clean_content[:max_length] + "..."
        return clean_content if clean_content else None
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML entities in text"""
        return html.escape(text)


class DateFormatter:
    """Handles date formatting operations"""
    
    @staticmethod
    def format_rss_date(dt: datetime) -> str:
        """Format datetime for RSS (RFC 822 format)"""
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    @staticmethod
    def parse_iso_date(date_str: str) -> Optional[datetime]:
        """Parse ISO format date string"""
        try:
            # Handle timezone suffix
            clean_date = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(clean_date)
        except (ValueError, AttributeError):
            return None


class ContentEnricher:
    """Enriches content entries with additional data"""
    
    def __init__(self, html_processor: HTMLProcessor = None,
                 url_processor: URLProcessor = None):
        self.html_processor = html_processor or HTMLProcessor()
        self.url_processor = url_processor or URLProcessor()
    
    def enrich_from_html(self, entry: ContentEntry, html_content: str) -> ContentEntry:
        """Enrich content entry from HTML content"""
        # Extract title if not present
        if not entry.title:
            entry.title = self.html_processor.extract_title(html_content)
        
        # Extract description if not present  
        if not entry.content:
            description = self.html_processor.extract_description(html_content)
            if not description:
                description = self.html_processor.extract_body_preview(html_content)
            entry.content = description
        
        return entry
    
    def enrich_from_url(self, entry: ContentEntry) -> ContentEntry:
        """Enrich content entry from URL if no title available"""
        if not entry.title:
            entry.title = self.url_processor.extract_title_from_url(entry.url)
        
        return entry


class ValidationUtils:
    """Utility functions for validation"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        return bool(url and url.startswith(('http://', 'https://')))
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email is valid"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))