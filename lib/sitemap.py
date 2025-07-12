import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class SitemapEntry:
    """Represents a single entry from sitemap"""
    url: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


def fetch_sitemap(sitemap_url: str) -> List[SitemapEntry]:
    """
    Fetch and parse sitemap XML to extract URLs and metadata
    """
    print(f"Fetching sitemap from: {sitemap_url}")
    
    try:
        response = httpx.get(sitemap_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Handle namespace
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        entries = []
        for url_elem in root.findall('.//ns:url', namespace):
            loc = url_elem.find('ns:loc', namespace)
            lastmod = url_elem.find('ns:lastmod', namespace)
            changefreq = url_elem.find('ns:changefreq', namespace)
            priority = url_elem.find('ns:priority', namespace)
            
            if loc is not None:
                entry = SitemapEntry(
                    url=loc.text,
                    lastmod=datetime.fromisoformat(lastmod.text.replace('Z', '+00:00')) if lastmod is not None else None,
                    changefreq=changefreq.text if changefreq is not None else None,
                    priority=float(priority.text) if priority is not None else None
                )
                entries.append(entry)
        
        print(f"Found {len(entries)} URLs in sitemap")
        return entries
        
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []