import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
from prefect import flow, task

from lib.incremental_state import IncrementalResult, IncrementalStateManager
from lib.sitemap import SitemapEntry, fetch_sitemap

sys.path.append(str(Path(__file__).parent.parent))


@task(log_prints=True)
def apply_filters(entries: list[SitemapEntry], filter_config: dict | None = None) -> list[SitemapEntry]:
    """
    Apply URL filters to sitemap entries
    """
    if not filter_config:
        return entries

    filtered_entries = []

    for entry in entries:
        include = True

        # Apply in_url filters (include URLs containing these strings)
        if "in_url" in filter_config:
            in_url_patterns = filter_config["in_url"]
            if not any(pattern in entry.url for pattern in in_url_patterns):
                include = False

        # Apply not_in_url filters (exclude URLs containing these strings)
        if "not_in_url" in filter_config:
            not_in_url_patterns = filter_config["not_in_url"]
            if any(pattern in entry.url for pattern in not_in_url_patterns):
                include = False

        if include:
            filtered_entries.append(entry)

    print(
        f"Applied filters: {len(entries)} -> {len(filtered_entries)} entries")
    return filtered_entries


@task(log_prints=True)
async def initialize_incremental_state(
    site_name: str, sitemap_url: str, db_path: str = "rss_incremental.db"
) -> IncrementalStateManager:
    """
    初始化增量状态管理器
    """
    state_manager = IncrementalStateManager(db_path)
    await state_manager.initialize_db()

    # 检查站点是否已存在
    site_state = await state_manager.get_site_state(site_name)
    if not site_state:
        await state_manager.update_site_state(site_name, sitemap_url)
        print(f"初始化站点状态: {site_name}")
    else:
        print(f"站点状态已存在: {site_name}")

    return state_manager


@task(log_prints=True)
async def detect_incremental_changes(
    state_manager: IncrementalStateManager,
    site_name: str,
    sitemap_entries: list[SitemapEntry],
    enable_incremental: bool = True,
) -> IncrementalResult:
    """
    检测增量变化
    """
    if not enable_incremental:
        # 非增量模式，处理所有URL
        all_urls = [entry.url for entry in sitemap_entries]
        return IncrementalResult(new_urls=all_urls, pending_urls=[], skipped_urls=[], total_to_process=len(all_urls))

    # 增量模式
    current_urls = [entry.url for entry in sitemap_entries]
    result = await state_manager.detect_new_urls(site_name, current_urls)

    print("增量检测结果:")
    print(f"  新增URL: {len(result.new_urls)}")
    print(f"  待重试URL: {len(result.pending_urls)}")
    print(f"  已跳过URL: {len(result.skipped_urls)}")
    print(f"  需要处理: {result.total_to_process}")

    return result


@task(log_prints=True)
async def filter_urls_for_processing(
    sitemap_entries: list[SitemapEntry], incremental_result: IncrementalResult, enable_incremental: bool = True
) -> list[SitemapEntry]:
    """
    根据增量结果过滤需要处理的URL
    """
    if not enable_incremental:
        return sitemap_entries

    # 需要处理的URL集合
    urls_to_process = set(incremental_result.new_urls +
                          incremental_result.pending_urls)

    # 过滤出需要处理的条目
    filtered_entries = [
        entry for entry in sitemap_entries if entry.url in urls_to_process]

    print(f"过滤后需要处理的条目数: {len(filtered_entries)}")
    return filtered_entries


@task(log_prints=True)
async def sync_sitemap_to_database(
    state_manager: IncrementalStateManager,
    site_name: str,
    sitemap_entries: list[SitemapEntry],
) -> dict:
    """
    同步sitemap URLs到数据库
    """
    current_urls = [entry.url for entry in sitemap_entries]
    result = await state_manager.sync_sitemap_urls(site_name, current_urls)

    print("URL同步结果:")
    print(f"  新增: {result['new_urls']}")
    print(f"  删除: {result['deleted_urls']}")
    print(f"  更新: {result['updated_urls']}")
    print(f"  当前总数: {result['total_current_urls']}")

    return result


@flow(name="Sitemap URL Sync Workflow")
async def sitemap_url_sync_workflow(
    sitemap_url: str,
    site_name: str,
    filter: dict | None = None,
    db_path: str = "rss_incremental.db",
):
    """
    简化的工作流：只同步sitemap URLs到数据库
    """
    print(f"Starting sitemap URL sync for: {sitemap_url}")

    # Step 1: Initialize state manager
    state_manager = await initialize_incremental_state(site_name, sitemap_url, db_path)

    # Step 2: Fetch sitemap
    sitemap_entries = fetch_sitemap(sitemap_url)

    if not sitemap_entries:
        print("No sitemap entries found. Exiting workflow.")
        return

    # Step 3: Apply filters (if any)
    if filter:
        sitemap_entries = apply_filters(sitemap_entries, filter)

        if not sitemap_entries:
            print("No entries match the filter criteria. Exiting workflow.")
            return

    # Step 4: Sync URLs to database
    sync_result = await sync_sitemap_to_database(state_manager, site_name, sitemap_entries)

    # Step 5: Get final stats
    stats = await state_manager.get_site_stats(site_name)
    print(f"站点 {site_name} 最终统计:")
    print(f"  总URL数: {stats['total_urls']}")
    print(f"  活跃URL: {stats['active_urls']}")
    print(f"  待处理: {stats['pending_urls']}")
    print(f"  已处理: {stats['processed_urls']}")
    print(f"  失败: {stats['failed_urls']}")
    print(f"  已删除: {stats['deleted_urls']}")

    print("Workflow completed!")
    return sitemap_entries


# Example usage
if __name__ == "__main__":
    import asyncio

    # Example with URL sync workflow
    async def run_example():
        await sitemap_url_sync_workflow(
            sitemap_url="https://www.prefect.io/sitemap.xml",
            site_name="prefect_blog",
            filter={"in_url": ["/blog/"]},
        )

    # Run the example
    asyncio.run(run_example())
