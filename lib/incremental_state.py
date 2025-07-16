"""
增量状态管理器 - 用于跟踪 sitemap 处理状态和实现增量更新
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class SiteState:
    """站点状态数据结构"""

    site_name: str
    sitemap_url: str
    last_run: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class UrlState:
    """URL状态数据结构"""

    site_name: str
    url: str
    state: int  # 0:未处理, 1:已处理, 2:处理失败
    first_seen: datetime
    last_seen: datetime
    deleted_at: datetime | None = None  # 被删除的时间


@dataclass
class IncrementalResult:
    """增量检测结果"""

    new_urls: list[str]
    pending_urls: list[str]  # 之前失败的URL
    skipped_urls: list[str]  # 已处理的URL
    total_to_process: int


class IncrementalStateManager:
    """增量状态管理器"""

    def __init__(self, db_path: str = "rss_incremental.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize_db(self):
        """初始化数据库表结构"""
        async with aiosqlite.connect(self.db_path) as db:
            # 创建站点状态表
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS site_states (
                    site_name TEXT PRIMARY KEY,
                    sitemap_url TEXT NOT NULL,
                    last_run TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 创建URL状态表
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS url_states (
                    site_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    state INTEGER DEFAULT 0,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP NULL,
                    PRIMARY KEY (site_name, url),
                    FOREIGN KEY (site_name) REFERENCES site_states(site_name)
                )
            """
            )

            # 为现有表添加deleted_at列（如果不存在）
            try:
                await db.execute("ALTER TABLE url_states ADD COLUMN deleted_at TIMESTAMP NULL")
                await db.commit()
                logger.info("添加了 deleted_at 列")
            except Exception:
                # 列已存在，忽略错误
                pass

            # 创建性能优化索引
            await db.execute("CREATE INDEX IF NOT EXISTS idx_url_state ON url_states(state)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_url_lastseen ON url_states(last_seen)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_url_deleted ON url_states(deleted_at)")

            await db.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    async def get_site_state(self, site_name: str) -> SiteState | None:
        """获取站点状态"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT site_name, sitemap_url, last_run, created_at, updated_at FROM site_states WHERE site_name = ?",
                (site_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return SiteState(
                        site_name=row[0],
                        sitemap_url=row[1],
                        last_run=datetime.fromisoformat(row[2]) if row[2] else None,
                        created_at=datetime.fromisoformat(row[3]),
                        updated_at=datetime.fromisoformat(row[4]),
                    )
                return None

    async def update_site_state(self, site_name: str, sitemap_url: str, last_run: datetime | None = None):
        """更新站点状态"""
        now = datetime.now()
        if last_run is None:
            last_run = now

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO site_states (site_name, sitemap_url, last_run, created_at, updated_at)
                VALUES (?, ?, ?, COALESCE((SELECT created_at FROM site_states WHERE site_name = ?), ?), ?)
            """,
                (site_name, sitemap_url, last_run.isoformat(), site_name, now.isoformat(), now.isoformat()),
            )
            await db.commit()

    async def sync_sitemap_urls(self, site_name: str, current_urls: list[str]) -> dict:
        """同步sitemap URLs到数据库，包括新增、更新和删除检测"""
        async with aiosqlite.connect(self.db_path) as db:
            # 获取已存在的URL（排除已删除的）
            async with db.execute(
                "SELECT url, state FROM url_states WHERE site_name = ? AND deleted_at IS NULL", (site_name,)
            ) as cursor:
                existing_urls = await cursor.fetchall()

        # 构建现有URL状态字典
        existing_url_states = {url: state for url, state in existing_urls}
        existing_url_set = set(existing_url_states.keys())
        current_url_set = set(current_urls)

        # 分类URLs
        new_urls = list(current_url_set - existing_url_set)
        deleted_urls = list(existing_url_set - current_url_set)
        existing_current_urls = list(current_url_set & existing_url_set)

        # 1. 插入新URL
        if new_urls:
            await self._batch_insert_urls(site_name, new_urls, state=0)

        # 2. 标记删除的URL
        if deleted_urls:
            await self._mark_urls_deleted(site_name, deleted_urls)

        # 3. 更新现有URL的last_seen时间，清除deleted_at
        if existing_current_urls:
            await self._update_urls_last_seen(site_name, existing_current_urls, clear_deleted=True)

        # 4. 更新站点最后运行时间
        await self.update_site_state(site_name, "", datetime.now())

        result = {
            "new_urls": len(new_urls),
            "deleted_urls": len(deleted_urls),
            "updated_urls": len(existing_current_urls),
            "total_current_urls": len(current_urls),
        }

        logger.info(f"站点 {site_name} URL同步完成: {result}")
        return result

    async def detect_new_urls(self, site_name: str, current_urls: list[str]) -> IncrementalResult:
        """检测新增和需要处理的URL（保持向后兼容）"""
        async with aiosqlite.connect(self.db_path) as db:
            # 获取已存在的URL及其状态（排除已删除的）
            async with db.execute(
                "SELECT url, state FROM url_states WHERE site_name = ? AND deleted_at IS NULL", (site_name,)
            ) as cursor:
                existing_urls = await cursor.fetchall()

        # 构建现有URL状态字典
        existing_url_states = {url: state for url, state in existing_urls}
        existing_url_set = set(existing_url_states.keys())
        current_url_set = set(current_urls)

        # 分类URLs
        new_urls = list(current_url_set - existing_url_set)
        pending_urls = [url for url in current_urls if existing_url_states.get(url) == 2]  # 失败的URL
        skipped_urls = [url for url in current_urls if existing_url_states.get(url) == 1]  # 已处理的URL

        # 更新URL状态表 - 记录新发现的URL
        if new_urls:
            await self._batch_insert_urls(site_name, new_urls, state=0)

        # 更新现有URL的last_seen时间
        if current_urls:
            await self._update_urls_last_seen(site_name, current_urls)

        total_to_process = len(new_urls) + len(pending_urls)

        return IncrementalResult(
            new_urls=new_urls, pending_urls=pending_urls, skipped_urls=skipped_urls, total_to_process=total_to_process
        )

    async def _batch_insert_urls(self, site_name: str, urls: list[str], state: int = 0):
        """批量插入URL"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT OR IGNORE INTO url_states (site_name, url, state, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?)
            """,
                [(site_name, url, state, now, now) for url in urls],
            )
            await db.commit()

    async def _mark_urls_deleted(self, site_name: str, urls: list[str]):
        """标记URL为已删除"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                UPDATE url_states SET deleted_at = ? WHERE site_name = ? AND url = ?
            """,
                [(now, site_name, url) for url in urls],
            )
            await db.commit()
        logger.info(f"标记 {len(urls)} 个URL为已删除")

    async def _update_urls_last_seen(self, site_name: str, urls: list[str], clear_deleted: bool = False):
        """更新URL的last_seen时间"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            if clear_deleted:
                # 同时清除deleted_at标记
                await db.executemany(
                    """
                    UPDATE url_states SET last_seen = ?, deleted_at = NULL WHERE site_name = ? AND url = ?
                """,
                    [(now, site_name, url) for url in urls],
                )
            else:
                await db.executemany(
                    """
                    UPDATE url_states SET last_seen = ? WHERE site_name = ? AND url = ?
                """,
                    [(now, site_name, url) for url in urls],
                )
            await db.commit()

    async def mark_urls_processed(self, site_name: str, urls: list[str], success: bool = True):
        """标记URL处理状态"""
        state = 1 if success else 2
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                UPDATE url_states SET state = ? WHERE site_name = ? AND url = ?
            """,
                [(state, site_name, url) for url in urls],
            )
            await db.commit()

        logger.info(f"标记 {len(urls)} 个URL为{'成功' if success else '失败'}处理状态")

    async def cleanup_old_states(self, days_to_keep: int = 30):
        """清理过期的状态数据"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # 删除过期的已处理URL（state=1）
            result = await db.execute(
                """
                DELETE FROM url_states 
                WHERE state = 1 AND last_seen < ?
            """,
                (cutoff_date,),
            )

            deleted_count = result.rowcount
            await db.commit()

            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 条过期的URL状态记录")

    async def get_site_stats(self, site_name: str) -> dict:
        """获取站点统计信息"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT 
                    COUNT(*) as total_urls,
                    SUM(CASE WHEN deleted_at IS NULL AND state = 0 THEN 1 ELSE 0 END) as pending_urls,
                    SUM(CASE WHEN deleted_at IS NULL AND state = 1 THEN 1 ELSE 0 END) as processed_urls,
                    SUM(CASE WHEN deleted_at IS NULL AND state = 2 THEN 1 ELSE 0 END) as failed_urls,
                    SUM(CASE WHEN deleted_at IS NOT NULL THEN 1 ELSE 0 END) as deleted_urls,
                    SUM(CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END) as active_urls
                FROM url_states 
                WHERE site_name = ?
            """,
                (site_name,),
            ) as cursor:
                row = await cursor.fetchone()

                return {
                    "total_urls": row[0] or 0,
                    "pending_urls": row[1] or 0,
                    "processed_urls": row[2] or 0,
                    "failed_urls": row[3] or 0,
                    "deleted_urls": row[4] or 0,
                    "active_urls": row[5] or 0,
                }

    async def reset_site_state(self, site_name: str):
        """重置站点状态（用于重新开始全量处理）"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM url_states WHERE site_name = ?", (site_name,))
            await db.execute("DELETE FROM site_states WHERE site_name = ?", (site_name,))
            await db.commit()

        logger.info(f"重置站点 {site_name} 的所有状态")

    async def initialize_baseline(self, site_name: str, baseline_urls: list[str]):
        """初始化基线状态（首次运行时使用）"""
        # 将基线URL直接标记为已处理
        await self._batch_insert_urls(site_name, baseline_urls, state=1)
        logger.info(f"初始化基线状态，标记 {len(baseline_urls)} 个URL为已处理")
