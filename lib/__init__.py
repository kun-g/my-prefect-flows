"""
Library package following SOLID principles.
Exposes main interfaces and factory functions for easy usage.
"""

# Core interfaces
from .interfaces import (
    ContentEntry,
    DataFetcher,
    ContentProcessor, 
    ContentFilter,
    ContentTransformer,
    StorageProvider,
    ConfigurationProvider,
    Logger
)

# Configuration management
from .config import (
    ConfigurationManager,
    R2Config,
    RSSConfiguration,
    FilterConfiguration
)

# Main service container
from .container import get_container, get_service_builder

# Factory classes for easy instantiation
from .storage import StorageFactory
from .logging import LoggerFactory
from .filters import FilterFactory

__all__ = [
    # Interfaces
    'ContentEntry',
    'DataFetcher', 
    'ContentProcessor',
    'ContentFilter',
    'ContentTransformer',
    'StorageProvider',
    'ConfigurationProvider',
    'Logger',
    
    # Configuration
    'ConfigurationManager',
    'R2Config', 
    'RSSConfiguration',
    'FilterConfiguration',
    
    # Container and builders
    'get_container',
    'get_service_builder',
    
    # Factories
    'StorageFactory',
    'LoggerFactory', 
    'FilterFactory'
]