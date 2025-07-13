"""
Dependency injection container following SOLID principles.
Implements Dependency Inversion Principle by managing dependencies centrally.
"""
from typing import Dict, Any, Optional, TypeVar, Type, Callable
from .interfaces import (
    DataFetcher, ContentProcessor, ContentFilter, 
    ContentTransformer, StorageProvider, Logger
)
from .config import ConfigurationManager, EnvironmentConfigProvider
from .fetchers import SitemapDataFetcher, HTTPContentFetcher
from .filters import FilterFactory
from .processors import (
    ContentSorter, TitleEnrichmentProcessor, 
    ContentEnrichmentProcessor, MetadataProcessor, ProcessorPipeline
)
from .transformers import RSSTransformer, JSONTransformer
from .storage import StorageFactory
from .logging import LoggerFactory

T = TypeVar('T')


class DIContainer:
    """Dependency injection container for managing application dependencies"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        
        # Register default factories
        self._register_default_factories()
    
    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """Register a singleton instance"""
        key = service_type.__name__
        self._singletons[key] = instance
    
    def register_factory(self, service_type: Type[T], factory: Callable[..., T]) -> None:
        """Register a factory function for creating instances"""
        key = service_type.__name__
        self._factories[key] = factory
    
    def get(self, service_type: Type[T]) -> T:
        """Get an instance of the requested service type"""
        key = service_type.__name__
        
        # Check singletons first
        if key in self._singletons:
            return self._singletons[key]
        
        # Check factories
        if key in self._factories:
            instance = self._factories[key]()
            return instance
        
        # Check if it's a registered service
        if key in self._services:
            return self._services[key]
        
        raise ValueError(f"Service {service_type.__name__} not registered")
    
    def get_logger(self, name: str = "app", logger_type: str = "console") -> Logger:
        """Get a logger instance"""
        if logger_type == "console":
            return LoggerFactory.create_console_logger(name)
        elif logger_type == "prefect":
            return LoggerFactory.create_prefect_logger(name)
        elif logger_type == "standard":
            return LoggerFactory.create_standard_logger(name)
        else:
            raise ValueError(f"Unknown logger type: {logger_type}")
    
    def get_config_manager(self) -> ConfigurationManager:
        """Get configuration manager instance"""
        return ConfigurationManager(EnvironmentConfigProvider())
    
    def get_sitemap_fetcher(self, logger: Optional[Logger] = None) -> SitemapDataFetcher:
        """Get sitemap data fetcher instance"""
        return SitemapDataFetcher(logger or self.get_logger())
    
    def get_http_fetcher(self, logger: Optional[Logger] = None) -> HTTPContentFetcher:
        """Get HTTP content fetcher instance"""
        return HTTPContentFetcher(logger or self.get_logger())
    
    def get_content_filter(self, filter_config: dict, 
                          logger: Optional[Logger] = None) -> ContentFilter:
        """Get content filter instance from configuration"""
        config_manager = self.get_config_manager()
        filter_cfg = config_manager.get_filter_config(filter_config)
        return FilterFactory.create_from_config(filter_cfg, logger or self.get_logger())
    
    def get_content_sorter(self, reverse: bool = True, 
                          logger: Optional[Logger] = None) -> ContentSorter:
        """Get content sorter instance"""
        return ContentSorter(reverse=reverse, logger=logger or self.get_logger())
    
    def get_title_enricher(self, fetch_from_web: bool = False,
                          logger: Optional[Logger] = None) -> TitleEnrichmentProcessor:
        """Get title enrichment processor instance"""
        http_fetcher = self.get_http_fetcher(logger)
        return TitleEnrichmentProcessor(
            fetch_from_web=fetch_from_web,
            content_fetcher=http_fetcher,
            logger=logger or self.get_logger()
        )
    
    def get_content_enricher(self, logger: Optional[Logger] = None) -> ContentEnrichmentProcessor:
        """Get content enrichment processor instance"""
        http_fetcher = self.get_http_fetcher(logger)
        return ContentEnrichmentProcessor(
            content_fetcher=http_fetcher,
            logger=logger or self.get_logger()
        )
    
    def get_metadata_processor(self, logger: Optional[Logger] = None) -> MetadataProcessor:
        """Get metadata processor instance"""
        return MetadataProcessor(logger or self.get_logger())
    
    def get_processor_pipeline(self, processors: list, 
                              logger: Optional[Logger] = None) -> ProcessorPipeline:
        """Get processor pipeline instance"""
        return ProcessorPipeline(processors, logger or self.get_logger())
    
    def get_rss_transformer(self, channel_config: dict,
                           logger: Optional[Logger] = None) -> RSSTransformer:
        """Get RSS transformer instance"""
        config_manager = self.get_config_manager()
        rss_config = config_manager.get_rss_config(**channel_config)
        return RSSTransformer(rss_config, logger or self.get_logger())
    
    def get_json_transformer(self, logger: Optional[Logger] = None) -> JSONTransformer:
        """Get JSON transformer instance"""
        return JSONTransformer(logger or self.get_logger())
    
    def get_local_storage(self, base_path: str = "output",
                         logger: Optional[Logger] = None) -> StorageProvider:
        """Get local file storage instance"""
        return StorageFactory.create_local_storage(base_path, logger or self.get_logger())
    
    def get_r2_storage(self, logger: Optional[Logger] = None) -> StorageProvider:
        """Get R2 storage instance"""
        return StorageFactory.create_r2_storage(logger=logger or self.get_logger())
    
    def _register_default_factories(self) -> None:
        """Register default factory functions"""
        self.register_factory(ConfigurationManager, self.get_config_manager)


class ServiceBuilder:
    """Builder class for constructing common service combinations"""
    
    def __init__(self, container: DIContainer):
        self.container = container
        self.logger = container.get_logger()
    
    def build_basic_pipeline(self, sitemap_url: str, filter_config: dict = None,
                            fetch_titles: bool = False, sort_by_date: bool = True):
        """Build a basic content processing pipeline"""
        # Get services
        fetcher = self.container.get_sitemap_fetcher(self.logger)
        content_filter = self.container.get_content_filter(
            filter_config or {}, self.logger
        )
        
        # Build processor pipeline
        processors = []
        if fetch_titles:
            processors.append(self.container.get_title_enricher(
                fetch_from_web=True, logger=self.logger
            ))
        
        processors.append(self.container.get_metadata_processor(self.logger))
        
        if sort_by_date:
            processors.append(self.container.get_content_sorter(
                reverse=True, logger=self.logger
            ))
        
        pipeline = self.container.get_processor_pipeline(processors, self.logger)
        
        return {
            'fetcher': fetcher,
            'filter': content_filter,
            'processor': pipeline
        }
    
    def build_rss_workflow(self, sitemap_url: str, channel_config: dict,
                          filter_config: dict = None, fetch_titles: bool = False,
                          storage_type: str = "local", storage_config: dict = None):
        """Build complete RSS generation workflow"""
        # Get basic pipeline
        pipeline = self.build_basic_pipeline(
            sitemap_url, filter_config, fetch_titles, sort_by_date=True
        )
        
        # Add transformer
        transformer = self.container.get_rss_transformer(channel_config, self.logger)
        
        # Add storage
        storage_config = storage_config or {}
        if storage_type == "local":
            storage = self.container.get_local_storage(
                storage_config.get('base_path', 'output'), self.logger
            )
        elif storage_type == "r2":
            storage = self.container.get_r2_storage(self.logger)
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
        
        return {
            **pipeline,
            'transformer': transformer,
            'storage': storage
        }


# Global container instance
_container = DIContainer()

def get_container() -> DIContainer:
    """Get the global container instance"""
    return _container

def get_service_builder() -> ServiceBuilder:
    """Get a service builder instance"""
    return ServiceBuilder(get_container())