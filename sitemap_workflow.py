from prefect import flow, task
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

from prefect_github.repository import GitHubRepository

github_repository_block = GitHubRepository.load("github-my-prefect-flows")


@dataclass
class SitemapEntry:
    """Represents a single entry from sitemap"""
    url: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


@dataclass
class UpdatedPage:
    """Represents a page that has been updated"""
    url: str
    lastmod: datetime
    title: Optional[str] = None
    content_preview: Optional[str] = None


@dataclass
class TodoItem:
    """Represents a TODO item generated from updates"""
    title: str
    description: str
    url: str
    priority: str
    created_at: datetime


@task(log_prints=True)
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


@task(log_prints=True)
def find_recent_updates(entries: List[SitemapEntry], days_back: int = 7) -> List[SitemapEntry]:
    """
    Filter sitemap entries to find recently updated pages
    """
    cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(days=days_back)
    
    recent_updates = []
    for entry in entries:
        if entry.lastmod and entry.lastmod.replace(tzinfo=None) > cutoff_date:
            recent_updates.append(entry)
    
    print(f"Found {len(recent_updates)} pages updated in the last {days_back} days")
    return recent_updates


@task(log_prints=True)
def fetch_page_content(url: str) -> Optional[Dict[str, str]]:
    """
    Fetch page content to extract title and preview
    """
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text
        
        # Simple title extraction
        title_start = content.find('<title>')
        title_end = content.find('</title>')
        title = None
        if title_start != -1 and title_end != -1:
            title = content[title_start + 7:title_end].strip()
        
        # Simple content preview (first 200 chars of body)
        body_start = content.find('<body')
        if body_start != -1:
            body_start = content.find('>', body_start) + 1
            body_end = content.find('</body>')
            if body_end != -1:
                body_content = content[body_start:body_end]
                # Remove HTML tags for preview
                import re
                clean_content = re.sub(r'<[^>]+>', '', body_content)
                preview = clean_content.strip()[:200] + "..." if len(clean_content) > 200 else clean_content.strip()
            else:
                preview = None
        else:
            preview = None
        
        return {
            'title': title,
            'preview': preview
        }
        
    except Exception as e:
        print(f"Error fetching content for {url}: {e}")
        return None


@task(log_prints=True)
def enrich_updates(recent_updates: List[SitemapEntry]) -> List[UpdatedPage]:
    """
    Enrich recent updates with page content
    """
    enriched_pages = []
    
    for entry in recent_updates:
        print(f"Enriching content for: {entry.url}")
        content = fetch_page_content(entry.url)
        
        page = UpdatedPage(
            url=entry.url,
            lastmod=entry.lastmod,
            title=content.get('title') if content else None,
            content_preview=content.get('preview') if content else None
        )
        enriched_pages.append(page)
    
    return enriched_pages


@task(log_prints=True)
def generate_todos(filtered_pages: List[UpdatedPage]) -> List[TodoItem]:
    """
    Generate TODO items from filtered pages
    """
    todos = []
    
    for page in filtered_pages:
        # Determine priority based on URL patterns and recency
        priority = "medium"
        if "/blog/" in page.url or "/news/" in page.url:
            priority = "high"
        elif "/docs/" in page.url or "/api/" in page.url:
            priority = "high"
        elif page.lastmod and (datetime.now().replace(tzinfo=None) - page.lastmod.replace(tzinfo=None)).days < 1:
            priority = "high"
        
        # Generate meaningful TODO title and description
        title = f"Review updated page: {page.title or page.url.split('/')[-1]}"
        
        description = f"Page updated on {page.lastmod.strftime('%Y-%m-%d %H:%M')}\n"
        description += f"URL: {page.url}\n"
        if page.content_preview:
            description += f"Preview: {page.content_preview[:100]}..."
        
        todo = TodoItem(
            title=title,
            description=description,
            url=page.url,
            priority=priority,
            created_at=datetime.now()
        )
        todos.append(todo)
    
    print(f"Generated {len(todos)} TODO items")
    return todos


@task(log_prints=True)
def save_todos(todos: List[TodoItem], output_file: str = "todos.json"):
    """
    Save TODO items to file
    """
    todos_data = []
    for todo in todos:
        todos_data.append({
            'title': todo.title,
            'description': todo.description,
            'url': todo.url,
            'priority': todo.priority,
            'created_at': todo.created_at.isoformat()
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(todos_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(todos)} TODOs to {output_file}")
    return output_file

@flow(name="Sitemap to TODO Workflow")
def sitemap_to_todo_workflow(
    sitemap_url: str,
    days_back: int = 7,
    output_file: str = "todos.json"
):
    """
    Complete workflow: Sitemap → Updates → Filtering → TODO Generation
    """
    print(f"Starting sitemap to TODO workflow for: {sitemap_url}")
    
    
    # Step 1: Fetch sitemap
    sitemap_entries = fetch_sitemap(sitemap_url)
    
    if not sitemap_entries:
        print("No sitemap entries found. Exiting workflow.")
        return
    
    # Step 2: Find recent updates
    recent_updates = find_recent_updates(sitemap_entries, days_back)
    
    if not recent_updates:
        print("No recent updates found. Exiting workflow.")
        return
    
    # Step 3: Enrich with content
    enriched_pages = enrich_updates(recent_updates)
    
    # Step 4: Generate TODOs
    todos = generate_todos(enriched_pages)
    
    # Step 5: Save TODOs
    output_path = save_todos(todos, output_file)
    
    print(f"Workflow completed! TODOs saved to: {output_path}")
    return todos


# Example usage
# if __name__ == "__main__":
#     # Example with a real sitemap
#     sitemap_to_todo_workflow(
#         sitemap_url="https://www.lennysnewsletter.com/sitemap.xml",
#         days_back=7,
#         output_file="website_todos.json"
#     )

# Uncomment to deploy as a scheduled workflow
if __name__ == "__main__":
    sitemap_to_todo_workflow.serve(
        name="sitemap-todo-deployment",
        cron="0 9 * * *",  # Daily at 9 AM
        parameters={
            "sitemap_url": "https://www.lennysnewsletter.com/sitemap.xml",
            "days_back": 7,
        }
    )
