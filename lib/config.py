"""
Configuration management following Single Responsibility Principle.
Centralizes all configuration handling logic.
"""
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, fields
from .interfaces import ConfigurationProvider

# Auto-load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Re-export R2 configuration from the main r2 module for consistency
from .r2 import R2Config


@dataclass 
class RSSConfiguration:
    """Configuration for RSS feed generation"""
    title: str
    link: str
    description: str
    language: str = "zh-CN"
    ttl: int = 60
    generator: str = "Prefect RSS Generator"


@dataclass
class FilterConfiguration:
    """Configuration for content filtering"""
    include_patterns: Optional[list] = None
    exclude_patterns: Optional[list] = None
    max_items: Optional[int] = None
    days_back: Optional[int] = None


class EnvironmentConfigProvider:
    """Configuration provider that reads from environment variables"""
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value from environment"""
        env_key = f"{self.prefix}{key}" if self.prefix else key
        return os.getenv(env_key, default)
    
    def validate(self) -> bool:
        """Basic validation - always returns True for env provider"""
        return True


class DictConfigProvider:
    """Configuration provider that reads from a dictionary"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value from dictionary"""
        return self.config.get(key, default)
    
    def validate(self) -> bool:
        """Validate that configuration dictionary is not empty"""
        return bool(self.config)


class ConfigurationManager:
    """Centralized configuration manager"""
    
    def __init__(self, provider: ConfigurationProvider):
        self.provider = provider
    
    def get_r2_config(self) -> R2Config:
        """Get R2 configuration"""
        return R2Config()
    
    def get_rss_config(self, title: str, link: str, description: str, 
                      language: str = "zh-CN", ttl: int = 60) -> RSSConfiguration:
        """Get RSS configuration with provided values"""
        return RSSConfiguration(
            title=title,
            link=link, 
            description=description,
            language=language,
            ttl=ttl
        )
    
    def get_filter_config(self, config_dict: Optional[Dict] = None) -> FilterConfiguration:
        """Get filter configuration"""
        if config_dict is None:
            return FilterConfiguration()
        
        return FilterConfiguration(
            include_patterns=config_dict.get("include_patterns"),
            exclude_patterns=config_dict.get("exclude_patterns"), 
            max_items=config_dict.get("max_items"),
            days_back=config_dict.get("days_back")
        )
    
    def validate_all(self) -> bool:
        """Validate all configurations"""
        return self.provider.validate()