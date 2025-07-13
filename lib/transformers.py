"""
RSS content transformer following SOLID principles.
Implements ContentTransformer interface for RSS feed generation.
"""
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional
from .interfaces import ContentTransformer, ContentEntry, Logger
from .config import RSSConfiguration
from .utils import DateFormatter, HTMLProcessor


class RSSTransformer(ContentTransformer):
    """Transforms content entries into RSS XML format"""
    
    def __init__(self, config: RSSConfiguration, logger: Optional[Logger] = None):
        self.config = config
        self.logger = logger
        self.date_formatter = DateFormatter()
        self.html_processor = HTMLProcessor()
    
    def transform(self, entries: List[ContentEntry]) -> str:
        """Transform content entries to RSS XML"""
        self._log_info(f"Transforming {len(entries)} entries to RSS XML")
        
        # Create RSS root element
        rss = self._create_rss_root()
        
        # Create channel element
        channel = self._create_channel(rss)
        
        # Add items to channel
        self._add_items_to_channel(channel, entries)
        
        # Convert to string
        xml_str = ET.tostring(rss, encoding="unicode", method="xml")
        formatted_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        self._log_info("RSS XML transformation complete")
        return formatted_xml
    
    def _create_rss_root(self) -> ET.Element:
        """Create RSS root element with namespaces"""
        rss = ET.Element("rss")
        rss.set("version", "2.0")
        rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
        return rss
    
    def _create_channel(self, rss: ET.Element) -> ET.Element:
        """Create and populate channel element"""
        channel = ET.SubElement(rss, "channel")
        
        # Basic channel information
        ET.SubElement(channel, "title").text = self.config.title
        ET.SubElement(channel, "link").text = self.config.link
        ET.SubElement(channel, "description").text = self.config.description
        ET.SubElement(channel, "language").text = self.config.language
        ET.SubElement(channel, "generator").text = self.config.generator
        ET.SubElement(channel, "ttl").text = str(self.config.ttl)
        
        # Add atom:link self-reference
        self._add_atom_link(channel)
        
        # Add timestamps
        self._add_channel_timestamps(channel)
        
        return channel
    
    def _add_atom_link(self, channel: ET.Element) -> None:
        """Add atom:link self-reference to channel"""
        atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
        atom_link.set("href", f"{self.config.link}/rss.xml")
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")
    
    def _add_channel_timestamps(self, channel: ET.Element) -> None:
        """Add publication and build date timestamps"""
        now = datetime.now()
        formatted_date = self.date_formatter.format_rss_date(now)
        
        ET.SubElement(channel, "pubDate").text = formatted_date
        ET.SubElement(channel, "lastBuildDate").text = formatted_date
    
    def _add_items_to_channel(self, channel: ET.Element, entries: List[ContentEntry]) -> None:
        """Add content entries as RSS items to channel"""
        for entry in entries:
            item_elem = self._create_item_element(entry)
            channel.append(item_elem)
    
    def _create_item_element(self, entry: ContentEntry) -> ET.Element:
        """Create RSS item element from content entry"""
        item = ET.Element("item")
        
        # Required elements
        self._add_item_title(item, entry)
        self._add_item_link(item, entry)
        self._add_item_description(item, entry)
        self._add_item_guid(item, entry)
        
        # Optional elements
        self._add_item_pub_date(item, entry)
        self._add_item_category(item, entry)
        
        return item
    
    def _add_item_title(self, item: ET.Element, entry: ContentEntry) -> None:
        """Add title element to item"""
        title = entry.title or "Untitled"
        ET.SubElement(item, "title").text = self.html_processor.escape_html(title)
    
    def _add_item_link(self, item: ET.Element, entry: ContentEntry) -> None:
        """Add link element to item"""
        ET.SubElement(item, "link").text = entry.url
    
    def _add_item_description(self, item: ET.Element, entry: ContentEntry) -> None:
        """Add description element to item"""
        description = self._get_item_description(entry)
        ET.SubElement(item, "description").text = self.html_processor.escape_html(description)
    
    def _get_item_description(self, entry: ContentEntry) -> str:
        """Get description for RSS item"""
        if entry.content:
            return entry.content
        
        # Generate default description based on last modified date
        if entry.last_modified:
            date_str = entry.last_modified.strftime('%Y-%m-%d %H:%M:%S')
            return f"页面更新于 {date_str}"
        
        return "内容已更新"
    
    def _add_item_guid(self, item: ET.Element, entry: ContentEntry) -> None:
        """Add GUID element to item"""
        guid_elem = ET.SubElement(item, "guid")
        guid_elem.text = entry.url  # Use URL as GUID
        guid_elem.set("isPermaLink", "true")
    
    def _add_item_pub_date(self, item: ET.Element, entry: ContentEntry) -> None:
        """Add publication date element to item"""
        if entry.last_modified:
            formatted_date = self.date_formatter.format_rss_date(entry.last_modified)
            ET.SubElement(item, "pubDate").text = formatted_date
    
    def _add_item_category(self, item: ET.Element, entry: ContentEntry) -> None:
        """Add category element to item if available"""
        if entry.metadata and 'category' in entry.metadata:
            category = entry.metadata['category']
            ET.SubElement(item, "category").text = self.html_processor.escape_html(str(category))
        elif entry.metadata and 'domain' in entry.metadata:
            # Use domain as category if no explicit category
            domain = entry.metadata['domain']
            ET.SubElement(item, "category").text = self.html_processor.escape_html(domain)
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class JSONTransformer(ContentTransformer):
    """Transforms content entries into JSON format"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger
    
    def transform(self, entries: List[ContentEntry]) -> str:
        """Transform content entries to JSON"""
        import json
        
        self._log_info(f"Transforming {len(entries)} entries to JSON")
        
        json_data = []
        for entry in entries:
            item_data = {
                'url': entry.url,
                'title': entry.title,
                'content': entry.content,
                'last_modified': entry.last_modified.isoformat() if entry.last_modified else None,
                'metadata': entry.metadata
            }
            json_data.append(item_data)
        
        result = json.dumps(json_data, ensure_ascii=False, indent=2)
        self._log_info("JSON transformation complete")
        return result
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)