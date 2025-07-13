"""
Refactored sitemap to RSS flow following SOLID principles.
Each task has a single responsibility and uses dependency injection.
"""
from prefect import flow, task
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add lib to path
sys.path.append(str(Path(__file__).parent.parent))

from lib.interfaces import ContentEntry
from lib.container import get_service_builder
from lib.config import FilterConfiguration


@task(log_prints=True)
def fetch_sitemap_entries(sitemap_url: str) -> List[ContentEntry]:
    """Fetch content entries from sitemap URL"""
    builder = get_service_builder()
    fetcher = builder.container.get_sitemap_fetcher()
    
    entries = fetcher.fetch(sitemap_url)
    print(f"Fetched {len(entries)} entries from sitemap")
    return entries


@task(log_prints=True)
def filter_content_entries(entries: List[ContentEntry], 
                          filter_config: Optional[Dict] = None) -> List[ContentEntry]:
    """Filter content entries based on configuration"""
    if not filter_config or not entries:
        return entries
    
    builder = get_service_builder()
    content_filter = builder.container.get_content_filter(filter_config)
    
    filtered_entries = content_filter.filter(entries)
    print(f"Filtered entries: {len(entries)} -> {len(filtered_entries)}")
    return filtered_entries


@task(log_prints=True)
def enrich_content_entries(entries: List[ContentEntry], 
                          fetch_titles: bool = False) -> List[ContentEntry]:
    """Enrich content entries with additional data"""
    if not entries:
        return entries
    
    builder = get_service_builder()
    
    # Build processor pipeline based on options
    processors = []
    
    if fetch_titles:
        processors.append(builder.container.get_title_enricher(
            fetch_from_web=True
        ))
    
    processors.append(builder.container.get_metadata_processor())
    
    # Create pipeline
    pipeline = builder.container.get_processor_pipeline(processors)
    
    enriched_entries = pipeline.process(entries)
    print(f"Enriched {len(enriched_entries)} entries")
    return enriched_entries


@task(log_prints=True) 
def sort_content_entries(entries: List[ContentEntry],
                        sort_by_date: bool = True) -> List[ContentEntry]:
    """Sort content entries"""
    if not entries or not sort_by_date:
        return entries
    
    builder = get_service_builder()
    sorter = builder.container.get_content_sorter(reverse=True)
    
    sorted_entries = sorter.process(entries)
    print(f"Sorted {len(sorted_entries)} entries by date")
    return sorted_entries


@task(log_prints=True)
def transform_to_rss(entries: List[ContentEntry], 
                    channel_config: Dict) -> str:
    """Transform content entries to RSS XML"""
    if not entries:
        return ""
    
    builder = get_service_builder()
    transformer = builder.container.get_rss_transformer(channel_config)
    
    rss_xml = transformer.transform(entries)
    print(f"Generated RSS XML with {len(entries)} items")
    return rss_xml


@task(log_prints=True)
def store_content(content: str, key: str, storage_type: str = "local",
                 storage_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Store content using specified storage provider"""
    if not content:
        return {"success": False, "error": "No content to store"}
    
    builder = get_service_builder()
    storage_config = storage_config or {}
    
    if storage_type == "local":
        storage = builder.container.get_local_storage(
            storage_config.get('base_path', 'output')
        )
    elif storage_type == "r2":
        storage = builder.container.get_r2_storage()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    result = storage.store(content, key, content_type='application/rss+xml')
    
    if result.get("success"):
        print(f"Content stored successfully: {result.get('file_url', key)}")
    else:
        print(f"Failed to store content: {result.get('error')}")
    
    return result


@flow(name="Sitemap to RSS (Refactored)")
def sitemap_to_rss_refactored(
    sitemap_url: str,
    channel_config: Dict,
    output_key: str = "rss_feed.xml",
    filter_config: Optional[Dict] = None,
    fetch_titles: bool = False,
    sort_by_date: bool = True,
    storage_type: str = "local",
    storage_config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Refactored sitemap to RSS flow using SOLID principles
    
    Args:
        sitemap_url: URL of the sitemap to process
        channel_config: RSS channel configuration
        output_key: Output file key/name
        filter_config: Content filtering configuration
        fetch_titles: Whether to fetch titles from web pages
        sort_by_date: Whether to sort entries by date
        storage_type: Storage type ("local" or "r2")
        storage_config: Storage-specific configuration
    """
    print(f"Starting sitemap to RSS workflow: {sitemap_url}")
    
    # Step 1: Fetch sitemap entries
    entries = fetch_sitemap_entries(sitemap_url)
    
    if not entries:
        print("No entries found in sitemap. Exiting.")
        return {"success": False, "error": "No entries found"}
    
    # Step 2: Filter entries
    if filter_config:
        entries = filter_content_entries(entries, filter_config)
        
        if not entries:
            print("No entries match filter criteria. Exiting.")
            return {"success": False, "error": "No entries after filtering"}
    
    # Step 3: Enrich entries
    entries = enrich_content_entries(entries, fetch_titles)
    
    # Step 4: Sort entries
    entries = sort_content_entries(entries, sort_by_date)
    
    # Step 5: Transform to RSS
    rss_content = transform_to_rss(entries, channel_config)
    
    if not rss_content:
        print("Failed to generate RSS content. Exiting.")
        return {"success": False, "error": "Failed to generate RSS"}
    
    # Step 6: Store content
    storage_result = store_content(
        rss_content, output_key, storage_type, storage_config
    )
    
    # Build final result
    result = {
        "success": storage_result.get("success", False),
        "total_entries": len(entries),
        "output_key": output_key,
        "storage_type": storage_type,
        "storage_result": storage_result
    }
    
    if result["success"]:
        print(f"Workflow completed successfully! Generated RSS with {len(entries)} items.")
    else:
        print(f"Workflow failed: {storage_result.get('error', 'Unknown error')}")
    
    return result


# Example configurations for different sites
SAMPLE_WORKFLOWS = {
    "prefect_blog": {
        "sitemap_url": "https://www.prefect.io/sitemap.xml",
        "channel_config": {
            "title": "Prefect Blog Updates",
            "link": "https://www.prefect.io",
            "description": "Latest blog posts from Prefect",
            "language": "en"
        },
        "filter_config": {
            "include_patterns": ["/blog/"],
            "exclude_patterns": ["/blog/tags/", "/blog/page/"],
            "max_items": 20
        },
        "output_key": "prefect-blog.xml"
    },
    
    "lennys_newsletter": {
        "sitemap_url": "https://www.lennysnewsletter.com/sitemap.xml",
        "channel_config": {
            "title": "Lenny's Newsletter Updates",
            "link": "https://www.lennysnewsletter.com",
            "description": "Latest updates from Lenny's Newsletter",
            "language": "en"
        },
        "filter_config": {
            "include_patterns": ["/p/"],
            "max_items": 15
        },
        "output_key": "lennys-newsletter.xml"
    }
}


if __name__ == "__main__":
    # Example usage with local storage
    config = SAMPLE_WORKFLOWS["prefect_blog"]
    
    result = sitemap_to_rss_refactored(
        sitemap_url=config["sitemap_url"],
        channel_config=config["channel_config"],
        output_key=config["output_key"],
        filter_config=config["filter_config"],
        fetch_titles=True,
        sort_by_date=True,
        storage_type="local",
        storage_config={"base_path": "output"}
    )
    
    print(f"\nWorkflow result: {result}")