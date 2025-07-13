"""
Content processing implementations following SOLID principles.
Each processor has a single responsibility and implements ContentProcessor interface.
"""
from datetime import datetime
from typing import List, Optional, Callable
from .interfaces import ContentProcessor, ContentEntry, Logger
from .utils import ContentEnricher
from .fetchers import HTTPContentFetcher


class ContentSorter(ContentProcessor):
    """Sorts content entries by specified criteria"""
    
    def __init__(self, sort_key: Callable[[ContentEntry], any] = None,
                 reverse: bool = True, logger: Optional[Logger] = None):
        self.sort_key = sort_key or self._default_sort_key
        self.reverse = reverse
        self.logger = logger
    
    def process(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Sort entries by the specified key"""
        sorted_entries = sorted(entries, key=self.sort_key, reverse=self.reverse)
        
        self._log_info(f"Sorted {len(sorted_entries)} entries by date")
        return sorted_entries
    
    @staticmethod
    def _default_sort_key(entry: ContentEntry) -> datetime:
        """Default sort key - by last_modified date"""
        return entry.last_modified if entry.last_modified else datetime.min
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class TitleEnrichmentProcessor(ContentProcessor):
    """Enriches content entries with titles from their URLs or HTML content"""
    
    def __init__(self, fetch_from_web: bool = False, 
                 content_fetcher: Optional[HTTPContentFetcher] = None,
                 logger: Optional[Logger] = None):
        self.fetch_from_web = fetch_from_web
        self.content_fetcher = content_fetcher or HTTPContentFetcher(logger)
        self.enricher = ContentEnricher()
        self.logger = logger
    
    def process(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Enrich entries with titles"""
        enriched_entries = []
        
        for entry in entries:
            enriched_entry = self._enrich_single_entry(entry)
            enriched_entries.append(enriched_entry)
        
        self._log_info(f"Enriched {len(enriched_entries)} entries with titles")
        return enriched_entries
    
    def _enrich_single_entry(self, entry: ContentEntry) -> ContentEntry:
        """Enrich a single entry with title"""
        # First try to extract from URL if no title
        if not entry.title:
            entry = self.enricher.enrich_from_url(entry)
        
        # If configured, fetch from web for better titles
        if self.fetch_from_web and entry.url:
            html_content = self.content_fetcher.fetch_content(entry.url)
            if html_content:
                entry = self.enricher.enrich_from_html(entry, html_content)
        
        return entry
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class ContentEnrichmentProcessor(ContentProcessor):
    """Enriches content entries with full content from web"""
    
    def __init__(self, content_fetcher: Optional[HTTPContentFetcher] = None,
                 logger: Optional[Logger] = None):
        self.content_fetcher = content_fetcher or HTTPContentFetcher(logger)
        self.enricher = ContentEnricher()
        self.logger = logger
    
    def process(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Enrich entries with content from web"""
        enriched_entries = []
        
        for entry in entries:
            enriched_entry = self._enrich_with_content(entry)
            enriched_entries.append(enriched_entry)
        
        self._log_info(f"Enriched {len(enriched_entries)} entries with web content")
        return enriched_entries
    
    def _enrich_with_content(self, entry: ContentEntry) -> ContentEntry:
        """Enrich entry with content from web"""
        if not entry.url:
            return entry
        
        html_content = self.content_fetcher.fetch_content(entry.url)
        if html_content:
            entry = self.enricher.enrich_from_html(entry, html_content)
        
        return entry
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class MetadataProcessor(ContentProcessor):
    """Processes and enriches metadata for content entries"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger
    
    def process(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Process and enrich metadata for entries"""
        processed_entries = []
        
        for entry in entries:
            processed_entry = self._process_metadata(entry)
            processed_entries.append(processed_entry)
        
        self._log_info(f"Processed metadata for {len(processed_entries)} entries")
        return processed_entries
    
    def _process_metadata(self, entry: ContentEntry) -> ContentEntry:
        """Process metadata for a single entry"""
        if not entry.metadata:
            entry.metadata = {}
        
        # Add processing timestamp
        entry.metadata['processed_at'] = datetime.now().isoformat()
        
        # Add URL domain
        if entry.url:
            domain = self._extract_domain(entry.url)
            if domain:
                entry.metadata['domain'] = domain
        
        return entry
    
    @staticmethod
    def _extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return None
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class ProcessorPipeline(ContentProcessor):
    """Combines multiple processors into a processing pipeline"""
    
    def __init__(self, processors: List[ContentProcessor], 
                 logger: Optional[Logger] = None):
        self.processors = processors
        self.logger = logger
    
    def process(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Process entries through all processors in sequence"""
        current_entries = entries
        
        self._log_info(f"Starting processing pipeline with {len(self.processors)} processors")
        
        for i, processor in enumerate(self.processors):
            self._log_info(f"Running processor {i + 1}/{len(self.processors)}: {type(processor).__name__}")
            current_entries = processor.process(current_entries)
        
        self._log_info(f"Processing pipeline complete: {len(entries)} -> {len(current_entries)} entries")
        return current_entries
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)