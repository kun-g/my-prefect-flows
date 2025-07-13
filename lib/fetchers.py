"""
Sitemap data fetcher implementation following SOLID principles.
Implements DataFetcher interface for fetching sitemap data.
"""
import httpx
import xml.etree.ElementTree as ET
from typing import List, Optional
from .interfaces import DataFetcher, ContentEntry, Logger
from .utils import DateFormatter, ValidationUtils


class SitemapDataFetcher(DataFetcher):
    """Fetches content entries from sitemap XML"""
    
    def __init__(self, logger: Optional[Logger] = None, timeout: int = 30):
        self.logger = logger
        self.timeout = timeout
        self.date_formatter = DateFormatter()
        self.validator = ValidationUtils()
    
    def fetch(self, sitemap_url: str) -> List[ContentEntry]:
        """Fetch content entries from sitemap URL"""
        if not self.validator.is_valid_url(sitemap_url):
            self._log_error(f"Invalid sitemap URL: {sitemap_url}")
            return []
        
        self._log_info(f"Fetching sitemap from: {sitemap_url}")
        
        try:
            response = httpx.get(sitemap_url, timeout=self.timeout)
            response.raise_for_status()
            
            return self._parse_sitemap_xml(response.content)
            
        except Exception as e:
            self._log_error(f"Error fetching sitemap: {e}")
            return []
    
    def _parse_sitemap_xml(self, xml_content: bytes) -> List[ContentEntry]:
        """Parse sitemap XML content into ContentEntry objects"""
        try:
            root = ET.fromstring(xml_content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            entries = []
            for url_elem in root.findall('.//ns:url', namespace):
                entry = self._parse_url_element(url_elem, namespace)
                if entry:
                    entries.append(entry)
            
            self._log_info(f"Found {len(entries)} URLs in sitemap")
            return entries
            
        except Exception as e:
            self._log_error(f"Error parsing sitemap XML: {e}")
            return []
    
    def _parse_url_element(self, url_elem, namespace: dict) -> Optional[ContentEntry]:
        """Parse a single URL element from sitemap"""
        loc_elem = url_elem.find('ns:loc', namespace)
        if loc_elem is None or not loc_elem.text:
            return None
        
        url = loc_elem.text.strip()
        if not self.validator.is_valid_url(url):
            return None
        
        # Extract optional metadata
        lastmod_elem = url_elem.find('ns:lastmod', namespace)
        changefreq_elem = url_elem.find('ns:changefreq', namespace)
        priority_elem = url_elem.find('ns:priority', namespace)
        
        # Parse last modified date
        last_modified = None
        if lastmod_elem is not None and lastmod_elem.text:
            last_modified = self.date_formatter.parse_iso_date(lastmod_elem.text)
        
        # Build metadata dictionary
        metadata = {}
        if changefreq_elem is not None and changefreq_elem.text:
            metadata['changefreq'] = changefreq_elem.text
        if priority_elem is not None and priority_elem.text:
            try:
                metadata['priority'] = float(priority_elem.text)
            except ValueError:
                pass
        
        return ContentEntry(
            url=url,
            last_modified=last_modified,
            metadata=metadata if metadata else None
        )
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def _log_error(self, message: str) -> None:
        """Log error message if logger available"""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"ERROR: {message}")


class HTTPContentFetcher:
    """Fetches additional content from HTTP URLs"""
    
    def __init__(self, logger: Optional[Logger] = None, timeout: int = 10):
        self.logger = logger
        self.timeout = timeout
        self.validator = ValidationUtils()
    
    def fetch_content(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        if not self.validator.is_valid_url(url):
            self._log_error(f"Invalid URL: {url}")
            return None
        
        try:
            self._log_info(f"Fetching content from: {url}")
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            self._log_error(f"Error fetching content from {url}: {e}")
            return None
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
    
    def _log_error(self, message: str) -> None:
        """Log error message if logger available"""
        if self.logger:
            self.logger.error(message)