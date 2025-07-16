# ADR-003: 增量RSS更新架构设计

## 状态
提议中 (Proposed)

## 背景
当前项目已实现从 sitemap 生成 RSS feed 的功能。为了提高效率和符合 RSS 的实时更新定位，需要实现增量更新功能，避免每次都重新处理全部内容。

现有问题：
1. **性能浪费**：每次都处理完整 sitemap，包括未变化的内容
2. **资源消耗**：开启 `fetch_titles=True` 时会产生大量不必要的网络请求
3. **不符合RSS语义**：RSS 本质是"最新内容推送"，应该只包含变化内容
4. **Worker分布式挑战**：Prefect Worker 环境下的状态共享问题

## 决策

### 采用 SQLite 数据库的增量状态管理方案

**核心原则**：
- **状态跟踪**：记录每个站点的处理历史和URL状态
- **变化检测**：基于 `lastmod` 时间戳和URL集合对比
- **增量处理**：只处理新增和修改的内容
- **向后兼容**：保持现有代码结构，通过参数控制增量模式

### 架构设计

#### 1. 状态存储方案
**SQLite 数据库**：
```python
# 文件结构
rss_incremental.db            # SQLite数据库文件
```

**优势**：
- **架构简单**：只需要一个数据库文件
- **强大查询**：SQLite 支持复杂的增量逻辑
- **事务保证**：数据一致性好
- **易于迁移**：后续可切换到远程数据库
- **调试友好**：可用 SQLite 工具直接查看数据

#### 2. 数据库设计
```sql
-- 站点状态表
CREATE TABLE site_states (
    site_name TEXT PRIMARY KEY,
    sitemap_url TEXT,
    last_run TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- URL状态表
CREATE TABLE url_states (
    site_name TEXT,
    url TEXT,
    state INTEGER DEFAULT 0,      -- 0:未处理, 1:已处理, 2:处理失败
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (site_name, url),
    FOREIGN KEY (site_name) REFERENCES site_states(site_name)
);

-- 性能优化索引
CREATE INDEX idx_url_state ON url_states(state);
CREATE INDEX idx_url_lastseen ON url_states(last_seen);
```

#### 3. 增量检测逻辑
**简化的检测策略**：
1. **新增URL**：在 `url_states` 表中不存在的URL
2. **未处理URL**：存在但 `state = 0` 的URL
3. **已处理URL**：`state = 1` 的URL（跳过）

**处理逻辑**：
- 只处理新增和未处理的URL
- 处理成功后将 `state` 设置为 1
- 处理失败的设置为 2，下次可以重试

#### 4. 核心组件设计

**状态管理器**：
```python
class IncrementalStateManager:
    def __init__(self, db_path: str = "rss_incremental.db"):
        self.db_path = db_path
    
    async def get_site_state(self, site_name: str) -> SiteState
    async def detect_new_urls(self, site_name: str, current_entries: List[SitemapEntry]) -> List[str]
    async def mark_urls_processed(self, site_name: str, urls: List[str], success: bool = True)
    async def cleanup_old_states(self, days_to_keep: int = 30)
```

**数据结构**：
```python
@dataclass
class SiteState:
    site_name: str
    sitemap_url: str
    last_run: Optional[datetime]

@dataclass  
class IncrementalResult:
    new_urls: List[str]
    pending_urls: List[str]  # 之前失败的URL
    skipped_urls: List[str]  # 已处理的URL
    total_to_process: int
```

#### 5. 工作流集成

**增量流程**：
```python
@flow(name="Incremental Sitemap to RSS")
async def incremental_sitemap_to_rss_flow(
    sitemap_url: str,
    site_name: str,
    channel_config: Dict,
    enable_incremental: bool = True,  # 新增参数控制增量模式
    max_items: int = 50
):
    # 1. 获取sitemap
    # 2. 增量检测（如果启用）
    # 3. 处理变化内容
    # 4. 生成RSS
    # 5. 更新状态
```

### 现有代码复用分析

**可直接复用 (90%)**：
- ✅ `fetch_sitemap()` - sitemap获取
- ✅ `apply_rss_filters()` - 过滤逻辑
- ✅ `sort_entries_by_date()` - 排序逻辑
- ✅ `create_rss_items()` - RSS条目生成
- ✅ `generate_rss_xml()` - XML生成
- ✅ 所有配置和示例代码

**需要增强的部分 (10%)**：
- 在主流程中增加增量检测步骤
- 添加简单的状态管理逻辑
- 增加配置参数控制增量行为

### 容错和恢复机制

#### 1. 错误降级策略
**三级降级机制**：
1. **轻微错误**：跳过单个URL，将状态记录为失败（state=2）
2. **中等错误**：重试之前失败的URL（state=2）
3. **严重错误**：降级到全量模式

```python
@task(retries=2)
async def incremental_fetch_with_fallback():
    try:
        return await incremental_mode()
    except DatabaseCorrupted:
        logger.warning("数据库损坏，降级到全量模式")
        return await full_refresh_mode()
```

#### 2. 状态清理策略
**基于时间和数量的双重清理**：
- 保留最近30天的URL状态
- 每个站点最多保留1000个URL记录
- 每次运行自动清理过期状态
- 优先清理已处理成功的URL（state=1）

#### 3. 首次运行处理
**智能初始化**：
```python
def initialize_incremental_state(site_config):
    if not state_exists():
        # 首次运行：处理最近N条作为基线
        baseline_items = fetch_recent_baseline(max_items=10)
        # 将基线项目直接标记为已处理（state=1）
        save_initial_state(baseline_items, state=1)
    return load_state()
```

### 部署环境适配

#### 1. 当前环境（单机）
- 使用相对路径 `rss_incremental.db`
- Worker直接访问本地数据库文件
- SQLite文件在项目目录下

#### 2. Docker环境（未来）
- 使用volume挂载：`/app/rss_incremental.db`
- 保持状态在容器重启后持久化
- 环境变量控制数据库路径

#### 3. 集群环境（未来）
- 切换到远程数据库（PostgreSQL/MySQL）
- 或者使用共享文件系统（NFS + SQLite）
- 通过配置轻松切换存储后端

## 后果

### 优势
1. **性能大幅提升**：只处理变化内容，减少70-90%的处理时间
2. **资源节约**：减少不必要的网络请求和计算
3. **更符合RSS语义**：真正的"最新内容推送"
4. **向后兼容**：现有功能完全不受影响
5. **部署灵活**：适配单机到集群的不同环境
6. **调试友好**：SQLite数据清晰可查，支持SQL调试

### 潜在风险及缓解
1. **状态损坏风险**
   - 缓解：定期备份 + 自动降级到全量模式
2. **首次运行处理**
   - 缓解：智能基线初始化
3. **并发访问问题**（集群环境）
   - 缓解：后续迁移到远程数据库

### 成本分析
1. **开发成本**：约1-2天（简化的状态管理逻辑）
2. **维护成本**：低（SQLite文件简单可靠）
3. **运行成本**：大幅降低（减少API调用和网络请求）

## 实施计划

### Phase 1: 核心状态管理 (0.5天)
- [ ] 实现 `IncrementalStateManager` 类
- [ ] 设计数据库schema和初始化逻辑
- [ ] 编写基础的增量检测逻辑

### Phase 2: 工作流集成 (0.5天)
- [ ] 集成到现有的 `sitemap_to_rss_flow`
- [ ] 添加增量模式参数和配置
- [ ] 实现错误降级机制

### Phase 3: 测试和优化 (0.5天)
- [ ] 端到端测试增量更新流程
- [ ] 性能测试和优化
- [ ] 边界情况测试

### Phase 4: 文档和清理 (0.5天)
- [ ] 更新配置示例和文档
- [ ] 添加增量模式使用指南
- [ ] 性能对比数据收集

## 配置示例

### 启用增量更新的配置
```python
# 增量模式配置示例
INCREMENTAL_CONFIGS = {
    "prefect": {
        "sitemap_url": "https://www.prefect.io/sitemap.xml",
        "site_name": "prefect_blog",  # 新增：状态管理标识
        "enable_incremental": True,   # 新增：启用增量
        "channel_config": {
            "title": "Prefect Blog Updates (Incremental)",
            "description": "Latest blog posts from Prefect - incremental updates"
        },
        "incremental_config": {       # 新增：增量配置
            "db_path": "rss_incremental.db",
            "max_history_days": 30,
            "baseline_items": 10,
            "cleanup_interval_days": 7,
            "retry_failed_urls": True
        }
    }
}
```

### 部署配置
```python
# 增量定时任务示例
def deploy_incremental_rss_feeds():
    for name, config in INCREMENTAL_CONFIGS.items():
        incremental_sitemap_to_rss_flow.serve(
            name=f"incremental-rss-{name}",
            cron="0 */2 * * *",  # 每2小时检查一次增量更新
            parameters={
                **config,
                "max_items": 20,
                "fetch_titles": True
            }
        )
```

## 相关决策
- [ADR-001: RSS 语义化总结架构设计](001-rss-semantic-summary-architecture.md)
- [ADR-002: 采用 PyRSS2Gen 库简化 RSS 生成](002-adopt-pyrss2gen-library.md)

## 相关文档
- [现有 sitemap 到 RSS 实现](../flows/sitemap_to_rss.py)
- [RSS 生成器库](../lib/rss_generator.py)

---
**创建日期**: 2025-07-12  
**作者**: Claude Code  
**审核**: 待定  
**关联**: ADR-001, ADR-002