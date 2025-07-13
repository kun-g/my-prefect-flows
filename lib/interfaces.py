"""
Abstract interfaces and protocols for the application.
Following SOLID principles, especially Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContentEntry:
    """Generic content entry data structure"""
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    last_modified: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class DataFetcher(ABC):
    """Abstract base class for data fetching operations"""
    
    @abstractmethod
    def fetch(self, source: str) -> List[ContentEntry]:
        """Fetch content entries from a source"""
        pass


class ContentProcessor(ABC):
    """Abstract base class for content processing operations"""
    
    @abstractmethod
    def process(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Process a list of content entries"""
        pass


class ContentFilter(ABC):
    """Abstract base class for content filtering operations"""
    
    @abstractmethod
    def filter(self, entries: List[ContentEntry]) -> List[ContentEntry]:
        """Filter a list of content entries"""
        pass


class ContentTransformer(ABC):
    """Abstract base class for content transformation operations"""
    
    @abstractmethod
    def transform(self, entries: List[ContentEntry]) -> str:
        """Transform content entries to output format"""
        pass


class StorageProvider(ABC):
    """Abstract base class for storage operations"""
    
    @abstractmethod
    def store(self, content: str, key: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Store content and return result information"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if content exists at key"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete content at key"""
        pass


class ConfigurationProvider(Protocol):
    """Protocol for configuration providers"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        ...
    
    def validate(self) -> bool:
        """Validate configuration completeness"""
        ...


class Logger(Protocol):
    """Protocol for logging operations"""
    
    def info(self, message: str) -> None:
        """Log info message"""
        ...
    
    def error(self, message: str) -> None:
        """Log error message"""
        ...
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        ...