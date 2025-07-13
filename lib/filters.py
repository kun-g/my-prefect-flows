"""
Content filtering implementations following SOLID principles.
Each filter has a single responsibility and implements ContentFilter interface.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from .interfaces import ContentFilter, ContentEntry, Logger
from .config import FilterConfiguration


class URLPatternFilter(ContentFilter):
    """Filters content entries based on URL patterns"""
    
    def __init__(self, include_patterns: Optional[List[str]] = None,
                 exclude_patterns: Optional[List[str]] = None,
                 logger: Optional[Logger] = None):
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.logger = logger
    
    def filter(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Filter entries based on URL patterns"""
        original_count = len(entries)
        filtered_entries = []
        
        for entry in entries:
            if self._should_include(entry.url):
                filtered_entries.append(entry)
        
        self._log_info(f"URL pattern filter: {original_count} -> {len(filtered_entries)} entries")
        return filtered_entries
    
    def _should_include(self, url: str) -> bool:
        """Check if URL should be included based on patterns"""
        # Check include patterns
        if self.include_patterns:
            if not any(pattern in url for pattern in self.include_patterns):
                return False
        
        # Check exclude patterns
        if self.exclude_patterns:
            if any(pattern in url for pattern in self.exclude_patterns):
                return False
        
        return True
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class DateRangeFilter(ContentFilter):
    """Filters content entries based on date range"""
    
    def __init__(self, days_back: Optional[int] = None,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 logger: Optional[Logger] = None):
        self.days_back = days_back
        self.start_date = start_date
        self.end_date = end_date
        self.logger = logger
    
    def filter(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Filter entries based on date range"""
        if not self._has_date_criteria():
            return entries
        
        original_count = len(entries)
        cutoff_date = self._get_cutoff_date()
        
        filtered_entries = []
        for entry in entries:
            if self._should_include_by_date(entry, cutoff_date):
                filtered_entries.append(entry)
        
        self._log_info(f"Date range filter: {original_count} -> {len(filtered_entries)} entries")
        return filtered_entries
    
    def _has_date_criteria(self) -> bool:
        """Check if any date criteria is set"""
        return bool(self.days_back or self.start_date or self.end_date)
    
    def _get_cutoff_date(self) -> Optional[datetime]:
        """Calculate cutoff date based on criteria"""
        if self.days_back:
            return datetime.now().replace(tzinfo=None) - timedelta(days=self.days_back)
        return self.start_date
    
    def _should_include_by_date(self, entry: ContentEntry, cutoff_date: Optional[datetime]) -> bool:
        """Check if entry should be included based on date"""
        if not entry.last_modified:
            return True  # Include entries without dates
        
        entry_date = entry.last_modified.replace(tzinfo=None)
        
        if cutoff_date and entry_date < cutoff_date:
            return False
        
        if self.end_date and entry_date > self.end_date.replace(tzinfo=None):
            return False
        
        return True
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class LimitFilter(ContentFilter):
    """Limits the number of content entries"""
    
    def __init__(self, max_items: int, logger: Optional[Logger] = None):
        self.max_items = max_items
        self.logger = logger
    
    def filter(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Limit entries to maximum number"""
        original_count = len(entries)
        filtered_entries = entries[:self.max_items]
        
        self._log_info(f"Limit filter: {original_count} -> {len(filtered_entries)} entries")
        return filtered_entries
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)


class CompositeFilter(ContentFilter):
    """Combines multiple filters into a single filter"""
    
    def __init__(self, filters: List[ContentFilter], logger: Optional[Logger] = None):
        self.filters = filters
        self.logger = logger
    
    def filter(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Apply all filters in sequence"""
        current_entries = entries
        
        for content_filter in self.filters:
            current_entries = content_filter.filter(current_entries)
            if not current_entries:  # Short circuit if no entries left
                break
        
        return current_entries


class FilterFactory:
    """Factory for creating filters from configuration"""
    
    @staticmethod
    def create_from_config(config: FilterConfiguration, 
                          logger: Optional[Logger] = None) -> ContentFilter:
        """Create a composite filter from configuration"""
        filters = []
        
        # Add URL pattern filter if configured
        if config.include_patterns or config.exclude_patterns:
            filters.append(URLPatternFilter(
                include_patterns=config.include_patterns,
                exclude_patterns=config.exclude_patterns,
                logger=logger
            ))
        
        # Add date range filter if configured
        if config.days_back:
            filters.append(DateRangeFilter(
                days_back=config.days_back,
                logger=logger
            ))
        
        # Add limit filter if configured
        if config.max_items:
            filters.append(LimitFilter(
                max_items=config.max_items,
                logger=logger
            ))
        
        if not filters:
            # Return a pass-through filter if no filters configured
            return PassThroughFilter()
        
        if len(filters) == 1:
            return filters[0]
        
        return CompositeFilter(filters, logger)


class PassThroughFilter(ContentFilter):
    """A filter that passes all entries through unchanged"""
    
    def filter(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Return entries unchanged"""
        return entries