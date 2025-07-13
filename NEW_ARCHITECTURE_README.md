# Refactored Architecture - SOLID Principles

This directory contains the refactored codebase following SOLID principles. The new architecture provides a clean, maintainable, and extensible foundation for content processing workflows.

## Quick Start

### Basic Usage

```python
from lib import get_service_builder

# Create service builder
builder = get_service_builder()

# Build complete RSS workflow
workflow = builder.build_rss_workflow(
    sitemap_url="https://example.com/sitemap.xml",
    channel_config={
        "title": "My RSS Feed",
        "link": "https://example.com", 
        "description": "Latest updates"
    },
    filter_config={
        "include_patterns": ["/blog/"],
        "max_items": 20
    },
    fetch_titles=True,
    storage_type="local"
)

# Use components
entries = workflow['fetcher'].fetch(sitemap_url)
filtered = workflow['filter'].filter(entries)
processed = workflow['processor'].process(filtered)
rss_xml = workflow['transformer'].transform(processed)
result = workflow['storage'].store(rss_xml, "feed.xml")
```

### Prefect Flow Usage

```python
from flows.sitemap_to_rss_refactored import sitemap_to_rss_refactored

result = sitemap_to_rss_refactored(
    sitemap_url="https://example.com/sitemap.xml",
    channel_config={
        "title": "My Feed",
        "link": "https://example.com",
        "description": "Latest updates"
    },
    filter_config={"include_patterns": ["/blog/"]},
    fetch_titles=True,
    storage_type="local"
)
```

## Architecture Overview

### Core Interfaces (`lib/interfaces.py`)
- `DataFetcher` - Fetch content from sources
- `ContentFilter` - Filter content entries  
- `ContentProcessor` - Process and enrich content
- `ContentTransformer` - Transform to output formats
- `StorageProvider` - Store content to destinations

### Key Components

1. **Fetchers** (`lib/fetchers.py`)
   - `SitemapDataFetcher` - Fetch from sitemap XML
   - `HTTPContentFetcher` - Fetch from web pages

2. **Filters** (`lib/filters.py`)
   - `URLPatternFilter` - Filter by URL patterns
   - `DateRangeFilter` - Filter by date ranges
   - `LimitFilter` - Limit number of entries

3. **Processors** (`lib/processors.py`)
   - `ContentSorter` - Sort entries
   - `TitleEnrichmentProcessor` - Enrich with titles
   - `MetadataProcessor` - Add metadata

4. **Transformers** (`lib/transformers.py`)
   - `RSSTransformer` - Generate RSS XML
   - `JSONTransformer` - Generate JSON output

5. **Storage** (`lib/storage.py`)
   - `LocalFileStorage` - Local file system
   - `R2Storage` - Cloudflare R2 storage

### Dependency Injection

The `DIContainer` manages all dependencies:

```python
from lib import get_container

container = get_container()

# Get configured services
fetcher = container.get_sitemap_fetcher()
storage = container.get_r2_storage()
transformer = container.get_rss_transformer(channel_config)
```

## Configuration

### Environment Variables
```bash
# R2 Storage (optional)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket
R2_CUSTOM_DOMAIN=your-domain.com
```

### Configuration Objects
```python
from lib.config import R2Configuration, RSSConfiguration

# R2 config
r2_config = R2Configuration.from_env()

# RSS config
rss_config = RSSConfiguration(
    title="My Feed",
    link="https://example.com",
    description="Latest updates"
)
```

## Extending the Architecture

### Add New Data Source

```python
from lib.interfaces import DataFetcher, ContentEntry

class CustomDataFetcher(DataFetcher):
    def fetch(self, source: str) -> List[ContentEntry]:
        # Implement custom fetching logic
        return entries
```

### Add New Output Format

```python
from lib.interfaces import ContentTransformer

class XMLTransformer(ContentTransformer):
    def transform(self, entries: List[ContentEntry]) -> str:
        # Implement XML transformation
        return xml_content
```

### Add New Storage Backend

```python
from lib.interfaces import StorageProvider

class S3Storage(StorageProvider):
    def store(self, content: str, key: str) -> Dict[str, Any]:
        # Implement S3 storage logic
        return result
```

## Testing

Test the architecture with mock data:

```bash
python test_solid_architecture.py
```

## Benefits

✅ **Single Responsibility** - Each class has one reason to change  
✅ **Open/Closed** - Easy to extend without modifying existing code  
✅ **Liskov Substitution** - All implementations are substitutable  
✅ **Interface Segregation** - Small, focused interfaces  
✅ **Dependency Inversion** - Depend on abstractions, not concretions  

## Migration

The new architecture is designed to coexist with existing code:

1. Use new flows for new workflows
2. Gradually migrate existing flows
3. Eventually retire old monolithic files

See `docs/SOLID_REFACTORING_REPORT.md` for detailed migration guide.